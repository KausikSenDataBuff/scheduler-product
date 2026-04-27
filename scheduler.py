import pandas as pd

def run_scheduler(data):
    """
    Run a simple scheduling algorithm based on order due dates.

    Steps:
    1. Sort orders by due_date (ascending)
    2. For each order:
        current_time = order_date
        3. For each operation:
            start = max(current_time, machine availability)
            end = start + proc_time (in minutes)
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

    # 1. Sort orders by due_date (ascending)
    orders_sorted = orders_df.sort_values('due_date', ascending=True)

    # 2. Initialize machine availability: track when each machine is free next
    # Start with the earliest possible time (we'll use Timestamp.min)
    machine_available = {
        machine_id: pd.Timestamp.min
        for machine_id in machines_df['machine_id']
    }

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

            # When is this machine next available?
            avail_time = machine_available[machine_id]

            # Start time is the later of: when we're ready (current_time) or when the machine is free
            start_time = max(current_time, avail_time)
            # End time is start time plus processing time (convert minutes to timedelta)
            end_time = start_time + pd.Timedelta(minutes=proc_time_min)

            # Record the scheduled operation
            scheduled_ops.append({
                'order_id': order_id,
                'operation_seq': op['operation_seq'],
                'machine_id': machine_id,
                'start': start_time,
                'end': end_time
            })

            # 5. Update machine availability: this machine will be free at end_time
            machine_available[machine_id] = end_time

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
    os.makedirs(os.path.dirname(str(file_path)), exist_ok=True)

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