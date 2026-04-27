import pandas as pd

def compute_completion(df_schedule, orders_df=None):
    """
    Compute the completion time for each order by taking the maximum end time.
    Optionally, merge with orders to compute delay.

    Args:
        df_schedule (pandas.DataFrame): DataFrame with columns:
                                        order_id, operation_seq, machine_id, start, end
                                        where start and end are Timestamps or strings in datetime format.
        orders_df (pandas.DataFrame, optional): DataFrame with order information, must contain
                                                'order_id' and 'due_date' columns.
                                                If provided, the function will merge completion times
                                                with orders to compute delay.

    Returns:
        pandas.DataFrame:
            If orders_df is None:
                DataFrame with columns: order_id, completion_time
            If orders_df is provided:
                DataFrame with columns: order_id, completion_time, due_date, delay_hours
                where delay_hours is a float representing the delay in hours
                (completion_time - due_date).
    """
    # Ensure the 'end' column is in datetime format for comparison
    df = df_schedule.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['end']):
        df['end'] = pd.to_datetime(df['end'])

    # Group by order_id and take the maximum end time
    completion_df = df.groupby('order_id')['end'].max().reset_index()
    completion_df = completion_df.rename(columns={'end': 'completion_time'})

    # If orders_df is provided, merge and compute delay
    if orders_df is not None:
        # Ensure we have the required columns
        if 'order_id' not in orders_df.columns or 'due_date' not in orders_df.columns:
            raise ValueError("orders_df must contain 'order_id' and 'due_date' columns")

        # Merge with orders to get due_date
        merged_df = completion_df.merge(orders_df[['order_id', 'due_date']], on='order_id', how='left')

        # Ensure due_date is datetime
        if not pd.api.types.is_datetime64_any_dtype(merged_df['due_date']):
            merged_df['due_date'] = pd.to_datetime(merged_df['due_date'])

        # Compute delay in hours
        merged_df['delay_hours'] = (merged_df['completion_time'] - merged_df['due_date']).dt.total_seconds() / 3600.0

        # Reorder columns for clarity
        result_df = merged_df[['order_id', 'completion_time', 'due_date', 'delay_hours']]
        return result_df
    else:
        return completion_df


def compute_kpi_metrics(df_schedule, orders_df):
    """
    Compute key performance indicators from the schedule and orders data.

    Args:
        df_schedule (pandas.DataFrame): DataFrame with columns:
                                        order_id, operation_seq, machine_id, start, end
                                        where start and end are Timestamps or strings in datetime format.
        orders_df (pandas.DataFrame): DataFrame with order information, must contain
                                      'order_id' and 'due_date' columns.

    Returns:
        dict: Dictionary containing KPI metrics:
              - total_orders: total number of orders
              - on_time_orders: number of orders completed on or before due date
              - late_orders: number of orders completed after due date
              - avg_delay: average delay in hours (negative = early, positive = late)
              - max_delay: maximum delay in hours
    """
    # Compute completion times with delay
    kpi_df = compute_completion(df_schedule, orders_df)

    # Calculate metrics
    total_orders = len(kpi_df)
    on_time_orders = (kpi_df['delay_hours'] <= 0).sum()  # Completed on time or early
    late_orders = (kpi_df['delay_hours'] > 0).sum()      # Completed late
    avg_delay = kpi_df['delay_hours'].mean()
    max_delay = kpi_df['delay_hours'].max()

    return {
        'total_orders': total_orders,
        'on_time_orders': int(on_time_orders),
        'late_orders': int(late_orders),
        'avg_delay': float(avg_delay),
        'max_delay': float(max_delay)
    }

if __name__ == "__main__":
    # For testing - import the scheduler to get a schedule, then compute completion and delay
    from scheduler import run_scheduler
    from data_loader import load_data
    try:
        data = load_data()
        print("Loaded data successfully")

        # Run the scheduler to get a schedule
        schedule_df = run_scheduler(data)
        print(f"Scheduled {len(schedule_df)} operations")

        # Compute completion times (without orders)
        completion_df = compute_completion(schedule_df)
        print(f"\nComputed completion times for {len(completion_df)} orders (without delay)")

        # Show first few completion times
        print("\nFirst 5 completion times:")
        print(completion_df.head())

        # Compute completion times with delay (using orders data)
        delay_df = compute_completion(schedule_df, data['orders'])
        print(f"\nComputed completion times with delay for {len(delay_df)} orders")

        # Show first few rows with delay
        print("\nFirst 5 rows with delay:")
        print(delay_df.head())

        # Show delay statistics
        print("\nDelay statistics (in hours):")
        print(f"Average delay: {delay_df['delay_hours'].mean():.2f} hours")
        print(f"Median delay: {delay_df['delay_hours'].median():.2f} hours")
        print(f"Minimum delay: {delay_df['delay_hours'].min():.2f} hours")
        print(f"Maximum delay: {delay_df['delay_hours'].max():.2f} hours")

        # Count orders completed early (negative delay) vs late (positive delay)
        early_orders = (delay_df['delay_hours'] < 0).sum()
        on_time_orders = (delay_df['delay_hours'] == 0).sum()
        late_orders = (delay_df['delay_hours'] > 0).sum()
        print(f"\nOrders completed early: {early_orders}")
        print(f"Orders completed on time: {on_time_orders}")
        print(f"Orders completed late: {late_orders}")

        # Test the new KPI metrics function
        print("\n=== KPI METRICS ===")
        kpi_metrics = compute_kpi_metrics(schedule_df, data['orders'])
        for key, value in kpi_metrics.items():
            print(f"{key}: {value}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()