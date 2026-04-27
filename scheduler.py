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


def run_scheduler(data):
    """
    Run a simple scheduling algorithm based on order due dates.

    Steps:
    1. Sort orders by due_date (ascending)
    2. For each order:
        current_time = order_date
        3. For each operation:
            start = adjust_to_calendar(current_time)
            start, end = get_earliest_slot(capacity-aware)
            end = adjust_to_calendar(end)
        4. Update machine schedule
        5. Store result

    Args:
        data (dict): Dictionary of DataFrames with keys:
                     'orders', 'routing', 'machines'
                     (as returned by load_data)

    Returns:
        pandas.DataFrame: DataFrame with columns:
                          order_id, operation_seq, machine_id, start, end
                          where start and end are Timestamps.
    """
    # Extract DataFrames
    orders_df = data['orders']
    routing_df = data['routing']
    machines_df = data['machines']

    # Get optional calendar data
    calendar_df = data.get('machine_calendar', None)
    # Get optional setup matrix (pre-indexed for fast lookup)
    setup_df = data.get('setup_matrix', None)
    setup_dict = build_setup_dict(setup_df)

    # 1. Sort orders by due_date (ascending)
    orders_sorted = orders_df.sort_values('due_date', ascending=True)

    # 2. Initialize machine state with capacity support
    # machine_intervals: list of (start, end) tuples for each machine
    # machine_capacity: capacity per machine (defaults to 1)
    # last_product: tracks the product that was last scheduled on each machine
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

    # 3. Process each order in due_date order
    for _, order in orders_sorted.iterrows():
        order_id = order['order_id']
        product_id = order['product_id']
        order_date = order['order_date']  # This is already a Timestamp from data_loader

        # current_time starts at the order date for the first operation
        current_time = order_date

        # Get operations for this product, sorted by operation_seq
        product_operations = routing_df[
            routing_df['product_id'] == product_id
        ].sort_values('operation_seq')

        # 4. Process each operation in the order
        for _, op in product_operations.iterrows():
            machine_id = op['machine_id']
            proc_time_min = op['proc_time_min']  # This is in minutes
            current_product = op['product_id']

            # Adjust current_time to calendar availability first
            current_time = adjust_to_calendar(machine_id, current_time, calendar_df)

            # Add setup time if transitioning from a different product
            setup_time = get_setup_time(machine_id, last_product[machine_id], current_product, setup_dict)
            if setup_time > 0:
                current_time = current_time + pd.Timedelta(minutes=setup_time)
                # Adjust to calendar after adding setup time
                current_time = adjust_to_calendar(machine_id, current_time, calendar_df)

            # Use capacity-aware slot finding
            start_time, end_time = get_earliest_slot(
                machine_intervals[machine_id],
                machine_capacity[machine_id],
                current_time,
                proc_time_min
            )

            # Adjust end_time to calendar availability
            end_time = adjust_to_calendar(machine_id, end_time, calendar_df)

            # Record the scheduled operation
            scheduled_ops.append({
                'order_id': order_id,
                'operation_seq': op['operation_seq'],
                'machine_id': machine_id,
                'start': start_time,
                'end': end_time
            })

            # Add this interval to the machine's active intervals
            machine_intervals[machine_id].append((start_time, end_time))

            # Update last product for this machine
            last_product[machine_id] = current_product

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
                                        order_id, operation_seq, machine_id, start, end
                                        where start and end are Timestamps.
        file_path (str or Path): The path where the CSV file should be saved.
                                Defaults to 'schedule.csv'.

    Returns:
        None
    """
    # Create a copy to avoid modifying the original DataFrame
    df_to_save = df_schedule.copy()

    # Convert the timestamp columns to a string format for consistent output
    # Using ISO format (YYYY-MM-DD HH:MM:SS) for readability
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


def verify_schedule(df_schedule):
    """
    Verify the schedule for two conditions:
    1. No machine has overlapping operations.
    2. For each order, operation_seq order is respected (i.e., operations are in increasing order of operation_seq
       and start times are non-decreasing).

    Args:
        df_schedule (pandas.DataFrame): DataFrame with columns:
                                        order_id, operation_seq, machine_id, start, end
                                        where start and end are Timestamps or strings in datetime format.

    Returns:
        tuple: (bool, list) where bool is True if all checks pass, False otherwise,
               and list contains error messages if any.

    Raises:
        ValueError: If any of the checks fail (if you prefer to raise instead of return).
    """
    # Ensure the start and end columns are datetime
    df = df_schedule.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['start']):
        df['start'] = pd.to_datetime(df['start'])
    if not pd.api.types.is_datetime64_any_dtype(df['end']):
        df['end'] = pd.to_datetime(df['end'])

    errors = []

    # Check 1: No machine has overlapping operations
    for machine_id, group in df.groupby('machine_id'):
        # Sort by start time
        group_sorted = group.sort_values('start')
        # Check that each operation starts after or at the same time as the previous one ends
        prev_end = None
        for _, row in group_sorted.iterrows():
            if prev_end is not None and row['start'] < prev_end:
                errors.append(
                    f"Machine {machine_id}: overlapping operations. "
                    f"Operation at {row['start']} (order {row['order_id']}, seq {row['operation_seq']}) "
                    f"starts before previous operation ended at {prev_end} "
                    f"(order {prev_order_id}, seq {prev_op_seq})."
                )
                # Break early for this machine to avoid too many messages
                break
            prev_end = row['end']
            prev_order_id = row['order_id']
            prev_op_seq = row['operation_seq']

    # Check 2: For each order, operation_seq order is respected
    for order_id, group in df.groupby('order_id'):
        # Sort by operation_seq
        group_sorted = group.sort_values('operation_seq')
        # Check that operation_seq is strictly increasing (should be, but verify)
        seqs = group_sorted['operation_seq'].tolist()
        if seqs != sorted(seqs):
            errors.append(
                f"Order {order_id}: operation_seq values are not in strictly increasing order: {seqs}"
            )
        # Check that start times are non-decreasing when ordered by operation_seq
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
        # If you want to raise an exception, uncomment the following line:
        # raise ValueError("Schedule verification failed:\n" + "\n".join(errors))
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
        print(f"Routing entries: {len(data['routing'])}")
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
        passed, errors = verify_schedule(schedule_df)
        if passed:
            print("   PASS: Schedule verification passed: no overlaps and operation_seq order respected.")
        else:
            print("   FAIL: Schedule verification failed:")
            for err in errors[:5]:  # Show first 5 errors
                print(f"     - {err}")
            if len(errors) > 5:
                print(f"     ... and {len(errors) - 5} more errors.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()