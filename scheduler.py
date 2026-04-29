import pandas as pd

def get_earliest_slot(machine_intervals, machine_capacity, current_time, duration):
    """
    Find the earliest time slot that can accommodate an operation of given duration.

    Args:
        machine_intervals: list of (start, end) tuples for active operations on this machine
        machine_capacity: maximum number of operations that can run concurrently
        current_time: earliest time we can start (from order date or previous op end)
        duration: operation duration in minutes

    Returns:
        (start_time, end_time) tuple
    """
    duration_delta = pd.Timedelta(minutes=duration)

    # Start by trying to fit at current_time
    candidate_start = current_time
    candidate_end = candidate_start + duration_delta

    # Keep iterating until we find a slot with enough capacity
    max_iterations = 1000  # Safety limit
    for _ in range(max_iterations):
        # Count how many intervals overlap with [candidate_start, candidate_end)
        overlapping = 0
        for int_start, int_end in machine_intervals:
            # Check overlap: interval overlaps if it starts before candidate_end and ends after candidate_start
            if int_start < candidate_end and int_end > candidate_start:
                overlapping += 1

        if overlapping < machine_capacity:
            # Found a slot with enough capacity
            return candidate_start, candidate_end

        # Not enough capacity - find when the earliest overlapping operation ends
        # to potentially start after it
        earliest_end = candidate_end
        for int_start, int_end in machine_intervals:
            if int_start < candidate_end and int_end > candidate_start:
                if int_end < earliest_end:
                    earliest_end = int_end

        # Move candidate start to when capacity becomes available
        candidate_start = earliest_end
        candidate_end = candidate_start + duration_delta

    raise ValueError(f"Could not find slot after {max_iterations} iterations")


def adjust_to_calendar(machine_id, time, calendar_df):
    """
    Adjust a timestamp to the next available time if it falls in an unavailable window.

    Args:
        machine_id: the machine ID to check calendar for
        time: the proposed timestamp
        calendar_df: DataFrame with machine_id, start_time, end_time, is_available columns

    Returns:
        Adjusted timestamp that falls in an available window
    """
    if calendar_df is None or calendar_df.empty:
        return time

    # Get calendar entries for this machine
    machine_cal = calendar_df[calendar_df['machine_id'] == machine_id].copy()

    if machine_cal.empty:
        return time  # No calendar, assume always available

    # Check if time falls within an available window
    for _, entry in machine_cal.iterrows():
        start_time = entry['start_time']
        end_time = entry['end_time']
        is_available = entry['is_available']

        if start_time <= time < end_time:
            # Time falls within this window
            if is_available == 0:
                # Unavailable - return the end of this window
                return end_time
            else:
                # Available - return the original time
                return time

    # Time doesn't fall within any calendar window
    # Find the next available window
    future_windows = machine_cal[machine_cal['end_time'] > time].sort_values('start_time')

    for _, entry in future_windows.iterrows():
        if entry['is_available'] == 1:
            return entry['start_time']

    # No available window found - return original time (fallback)
    return time


def get_setup_time(machine_id, from_product, to_product, setup_dict):
    """
    Look up the setup time for transitioning from one product to another on a machine.

    Args:
        machine_id: the machine ID
        from_product: the product that was previously on this machine (or None for first use)
        to_product: the product to be scheduled next
        setup_dict: dict with (machine_id, from_product, to_product) -> setup_time_min

    Returns:
        setup time in minutes (0 if same product or no setup defined)
    """
    if setup_dict is None or from_product is None:
        return 0

    return setup_dict.get((machine_id, from_product, to_product), 0)


def build_setup_dict(setup_df):
    """
    Build an indexed dictionary for fast setup time lookups.

    Args:
        setup_df: DataFrame with from_product, to_product, machine_id, setup_time_min columns

    Returns:
        dict with (machine_id, from_product, to_product) -> setup_time_min
    """
    if setup_df is None or setup_df.empty:
        return None

    setup_dict = {}
    for _, row in setup_df.iterrows():
        key = (row['machine_id'], row['from_product'], row['to_product'])
        setup_dict[key] = int(row['setup_time_min'])
    return setup_dict


def apply_release_constraint(order_date, release_time, material_available_time):
    """
    Returns the earliest valid start time for an order based on release and material constraints.

    Args:
        order_date: When the order was placed
        release_time: When the order is released for scheduling
        material_available_time: When materials are available

    Returns:
        Timestamp: The earliest valid start time
    """
    return max(order_date, release_time, material_available_time)


def select_best_machine(candidate_machines, machine_intervals, machine_capacity,
                       current_time, setup_dict, last_product, calendar_df):
    """
    Select the machine that allows earliest completion from a list of candidates.

    Args:
        candidate_machines: list of dicts with machine_id, proc_time, is_primary, efficiency
        machine_intervals: dict of machine_id -> list of (start, end) tuples
        machine_capacity: dict of machine_id -> capacity
        current_time: earliest time we can start
        setup_dict: pre-indexed setup time lookup
        last_product: dict of machine_id -> last product scheduled
        calendar_df: DataFrame with machine availability

    Returns:
        tuple: (machine_id, start_time, end_time, is_primary) or (None, None, None, None) if no valid machine
    """
    best_machine = None
    best_start = None
    best_end = None
    best_is_primary = False

    for option in candidate_machines:
        m = option['machine_id']
        proc_time = int(option['proc_time'])

        # Get earliest slot for this machine
        start, _ = get_earliest_slot(machine_intervals[m], machine_capacity[m], current_time, proc_time)
        end = start + pd.Timedelta(minutes=proc_time)

        if best_end is None or end < best_end:
            best_machine = m
            best_start = start
            best_end = end
            best_is_primary = option['is_primary']

    return best_machine, best_start, best_end, best_is_primary


def run_scheduler(data, jobs_df=None):
    """
    Run a Phase 2 scheduling algorithm with alternate machine selection and release constraints.

    Steps:
    1. Sort orders by due_date (ascending)
    2. For each order:
       - current_time = max(order_date, release_time, material_available_time)
       3. For each operation:
          - Select best machine from candidate_machines (earliest completion)
          - Add setup time if transitioning products
          - Schedule on best machine with capacity awareness
          - Update machine state
       4. Store result

    Args:
        data (dict): Dictionary of DataFrames with keys:
                     'orders', 'routing_alt', 'machines'
                     (Phase 2 uses routing_alt for multi-machine routing)
        jobs_df (DataFrame, optional): Pre-built jobs from job_builder.
                                       If not provided, builds jobs internally.

    Returns:
        pandas.DataFrame: DataFrame with columns:
                          order_id, operation_seq, machine_id, start, end, is_primary
                          where start and end are Timestamps.
    """
    # Extract DataFrames
    orders_df = data['orders']
    machines_df = data['machines']

    # Get optional calendar data
    calendar_df = data.get('machine_calendar', None)
    # Get optional setup matrix (pre-indexed for fast lookup)
    setup_df = data.get('setup_matrix', None)
    setup_dict = build_setup_dict(setup_df)

    # Build jobs if not provided
    if jobs_df is None:
        from job_builder import build_jobs
        jobs_df = build_jobs(data)

    # 1. Sort jobs by due_date (need to join with orders)
    jobs_with_orders = jobs_df.merge(
        orders_df[['order_id', 'due_date', 'release_time', 'material_available_time', 'order_date']],
        on='order_id',
        how='left'
    )
    jobs_sorted = jobs_with_orders.sort_values('due_date', ascending=True)

    # 2. Initialize machine state with capacity support
    machine_intervals = {row['machine_id']: [] for _, row in machines_df.iterrows()}
    machine_capacity = {}
    last_product = {}
    for _, row in machines_df.iterrows():
        machine_id = row['machine_id']
        cap = int(row.get('capacity', 1)) if 'capacity' in row.index else 1
        machine_capacity[machine_id] = cap
        last_product[machine_id] = None

    # List to collect scheduled operations
    scheduled_ops = []

    # 3. Process each job in due_date order
    for _, job in jobs_sorted.iterrows():
        order_id = job['order_id']
        product_id = job['product_id']
        operation_seq = job['operation_seq']
        order_date = job['order_date']
        candidate_machines = job['candidate_machines']

        # Phase 2: Apply release and material constraints
        release_time = job.get('release_time', order_date)
        material_time = job.get('material_available_time', order_date)
        current_time = apply_release_constraint(order_date, release_time, material_time)

        # Phase 2: Select best machine from candidates
        best_machine, start_time, end_time, is_primary = select_best_machine(
            candidate_machines, machine_intervals, machine_capacity,
            current_time, setup_dict, last_product, calendar_df
        )

        if best_machine is None:
            raise ValueError(f"No valid machine found for order {order_id} operation {operation_seq}")

        # Add setup time if transitioning from a different product
        setup_time = get_setup_time(best_machine, last_product[best_machine], product_id, setup_dict)
        if setup_time > 0:
            current_time = current_time + pd.Timedelta(minutes=setup_time)
            # Adjust to calendar after adding setup time
            current_time = adjust_to_calendar(best_machine, current_time, calendar_df)
            # Recalculate slot after adjusting for setup
            proc_time = int(candidate_machines[0]['proc_time'])  # Use first candidate's proc_time
            start_time, end_time = get_earliest_slot(
                machine_intervals[best_machine],
                machine_capacity[best_machine],
                current_time,
                proc_time
            )
            end_time = start_time + pd.Timedelta(minutes=proc_time)

        # Adjust end_time to calendar availability
        end_time = adjust_to_calendar(best_machine, end_time, calendar_df)

        # Record the scheduled operation
        scheduled_ops.append({
            'order_id': order_id,
            'operation_seq': operation_seq,
            'machine_id': best_machine,
            'start': start_time,
            'end': end_time,
            'is_primary': is_primary
        })

        # Add this interval to the machine's active intervals
        machine_intervals[best_machine].append((start_time, end_time))

        # Update last product for this machine
        last_product[best_machine] = product_id

        # For the next operation in this order, we start when this operation ends
        current_time = end_time

    # Return the scheduled operations as a DataFrame
    return pd.DataFrame(scheduled_ops)


def save_schedule(df_schedule, file_path='schedule.csv'):
    """
    Save the schedule DataFrame to a CSV file.
    Ensures proper datetime formatting for the 'start' and 'end' columns.

    Args:
        df_schedule (pandas.DataFrame): DataFrame with columns:
                                        order_id, operation_seq, machine_id, start, end, is_primary
                                        where start and end are Timestamps.
        file_path (str or Path): The path where the CSV file should be saved.
                                Defaults to 'schedule.csv'.

    Returns:
        None
    """
    # Create a copy to avoid modifying the original DataFrame
    df_to_save = df_schedule.copy()

    # Convert the timestamp columns to a string format for consistent output
    df_to_save['start'] = df_to_save['start'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df_to_save['end'] = df_to_save['end'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Ensure the directory exists
    import os
    dir_path = os.path.dirname(str(file_path))
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    # Save to CSV
    df_to_save.to_csv(file_path, index=False)

    print(f"Schedule saved to {file_path} with {len(df_to_save)} rows")
    print(f"File exists after save: {os.path.exists(str(file_path))}")


def verify_schedule(df_schedule, machines_df=None):
    """
    Verify the schedule for two conditions:
    1. No machine has overlapping operations beyond its capacity.
    2. For each order, operation_seq order is respected.

    Args:
        df_schedule (pandas.DataFrame): DataFrame with columns:
                                        order_id, operation_seq, machine_id, start, end, is_primary
                                        where start and end are Timestamps or strings in datetime format.
        machines_df (pandas.DataFrame, optional): DataFrame with machine_id and capacity columns.
                                                  If not provided, capacity defaults to 1 for all machines.

    Returns:
        tuple: (bool, list) where bool is True if all checks pass, False otherwise,
               and list contains error messages if any.
    """
    # Ensure the start and end columns are datetime
    df = df_schedule.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['start']):
        df['start'] = pd.to_datetime(df['start'])
    if not pd.api.types.is_datetime64_any_dtype(df['end']):
        df['end'] = pd.to_datetime(df['end'])

    # Build machine capacity dict (default to 1 if not provided)
    machine_capacity = {}
    if machines_df is not None:
        for _, row in machines_df.iterrows():
            machine_id = row['machine_id']
            cap = int(row.get('capacity', 1)) if 'capacity' in row.index else 1
            machine_capacity[machine_id] = cap
    else:
        # Default capacity of 1 for all machines if machines_df not provided
        for machine_id in df['machine_id'].unique():
            machine_capacity[machine_id] = 1

    errors = []

    # Check 1: No machine has overlapping operations beyond capacity
    for machine_id, group in df.groupby('machine_id'):
        capacity = machine_capacity.get(machine_id, 1)
        group_sorted = group.sort_values('start')
        intervals = []
        for _, row in group_sorted.iterrows():
            intervals.append({
                'start': row['start'],
                'end': row['end'],
                'order_id': row['order_id'],
                'operation_seq': row['operation_seq']
            })

        # Check for capacity violations
        time_points = []
        for interval in intervals:
            time_points.append((interval['start'], 'start', interval))
            time_points.append((interval['end'], 'end', interval))

        time_points.sort(key=lambda x: (x[0], 0 if x[1] == 'end' else 1))

        max_concurrent = 0
        current_concurrent = 0
        violation_time = None
        violation_interval = None

        for time, event_type, interval in time_points:
            if event_type == 'start':
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
                    violation_time = time
                    violation_interval = interval
            else:
                current_concurrent -= 1

        if max_concurrent > capacity:
            active_ops = []
            for interval in intervals:
                if interval['start'] <= violation_time < interval['end']:
                    active_ops.append(f"{interval['order_id']} seq {interval['operation_seq']}")

            errors.append(
                f"Machine {machine_id} (capacity={capacity}): capacity exceeded. "
                f"At {violation_time}, {max_concurrent} operations are running (exceeds capacity {capacity}). "
                f"Active: {', '.join(active_ops)}"
            )
            break

    # Check 2: For each order, operation_seq order is respected
    for order_id, group in df.groupby('order_id'):
        group_sorted = group.sort_values('operation_seq')
        seqs = group_sorted['operation_seq'].tolist()
        if seqs != sorted(seqs):
            errors.append(
                f"Order {order_id}: operation_seq values are not in strictly increasing order: {seqs}"
            )
        prev_start = None
        for _, row in group_sorted.iterrows():
            if prev_start is not None and row['start'] < prev_start:
                errors.append(
                    f"Order {order_id}: operation_seq order not respected. "
                    f"Operation at seq {row['operation_seq']} starts at {row['start']} "
                    f"which is before previous operation (seq {prev_op_seq}) started at {prev_start}."
                )
                break
            prev_start = row['start']
            prev_op_seq = row['operation_seq']

    if errors:
        return False, errors
    else:
        return True, []


if __name__ == "__main__":
    # For testing - import data_loader and run the scheduler
    from data_loader import load_data
    try:
        data = load_data()
        print("Loaded data successfully")
        print(f"Orders: {len(data['orders'])}")
        print(f"Routing alt entries: {len(data['routing_alt'])}")
        print(f"Machines: {len(data['machines'])}")

        # Run the scheduler
        schedule_df = run_scheduler(data)
        print(f"\nScheduled {len(schedule_df)} operations")

        # Show first few scheduled operations
        print("\nFirst 5 scheduled operations:")
        print(schedule_df.head())

        # Show basic stats
        print("\nSchedule summary:")
        print(f"Earliest start: {schedule_df['start'].min()}")
        print(f"Latest end: {schedule_df['end'].max()}")
        print(f"Total scheduled time: {schedule_df['end'].max() - schedule_df['start'].min()}")

        # Save the schedule
        save_schedule(schedule_df)

        # Verify the schedule
        print("\nVerifying schedule...")
        passed, errors = verify_schedule(schedule_df, machines_df)
        if passed:
            print("   PASS: Schedule verification passed.")
        else:
            print("   FAIL: Schedule verification failed:")
            for err in errors[:5]:
                print(f"     - {err}")
            if len(errors) > 5:
                print(f"     ... and {len(errors) - 5} more errors.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
