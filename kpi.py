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


def compute_kpi_metrics(df_schedule, orders_df, order_links_df=None, orders_multi_df=None, original_orders_count=None):
    """
    Compute key performance indicators from the schedule and orders data.

    Phase 3 adds:
    - dependency_delay: parent_start - max(child_completion)
    - critical_path_length: longest chain per top-level order
    - component_service_level: % of child orders completed before parent need
    - wip_explosion_factor: total_orders_multilevel / original_orders

    Args:
        df_schedule (pandas.DataFrame): DataFrame with columns:
                                        order_id, operation_seq, machine_id, start, end, is_primary
                                        where start and end are Timestamps or strings in datetime format.
        orders_df (pandas.DataFrame): DataFrame with order information, must contain
                                      'order_id' and 'due_date' columns.
        order_links_df (pandas.DataFrame, optional): Phase 3 order links for dependency KPIs.
        orders_multi_df (pandas.DataFrame, optional): Phase 3 multi-level orders.
        original_orders_count (int, optional): Original order count for WIP explosion.

    Returns:
        dict: Dictionary containing KPI metrics:
              - total_orders: total number of orders
              - on_time_orders: number of orders completed on or before due date
              - late_orders: number of orders completed after due date
              - avg_delay: average delay in hours (negative = early, positive = late)
              - max_delay: maximum delay in hours
              - avg_utilization: average machine utilization %
              - alt_machine_usage_pct: % of jobs not using primary machine
              - avg_release_delay: avg delay due to release constraint (hours, first operation only)
              - dependency_delay: Phase 3 - avg delay from dependency constraints
              - critical_path_length: Phase 3 - longest parent-child chain
              - component_service_level: Phase 3 - % child orders meeting parent need
              - wip_explosion_factor: Phase 3 - ratio of multi-level to flat orders
    """
    # Compute completion times with delay
    kpi_df = compute_completion(df_schedule, orders_df)

    # Calculate metrics
    total_orders = len(kpi_df)
    on_time_orders = (kpi_df['delay_hours'] <= 0).sum()
    late_orders = (kpi_df['delay_hours'] > 0).sum()
    avg_delay = kpi_df['delay_hours'].mean()
    max_delay = kpi_df['delay_hours'].max()

    # Phase 2: Machine utilization
    avg_utilization = compute_machine_utilization(df_schedule, orders_df)

    # Phase 2: Alternate machine usage
    alt_machine_usage_pct = compute_alt_machine_usage(df_schedule)

    # Phase 2: Release delay
    avg_release_delay = compute_release_delay(df_schedule, orders_df)

    result = {
        'total_orders': total_orders,
        'on_time_orders': int(on_time_orders),
        'late_orders': int(late_orders),
        'avg_delay': float(avg_delay),
        'max_delay': float(max_delay),
        'avg_utilization': float(avg_utilization),
        'alt_machine_usage_pct': float(alt_machine_usage_pct),
        'avg_release_delay': float(avg_release_delay)
    }

    # Phase 3 KPIs
    if order_links_df is not None:
        result['dependency_delay'] = float(compute_dependency_delay(df_schedule, order_links_df))
        result['critical_path_length'] = int(compute_critical_path_length(df_schedule, orders_df, order_links_df))
        result['component_service_level'] = float(compute_component_service_level(df_schedule, orders_df, order_links_df))

    if orders_multi_df is not None:
        orig_count = original_orders_count if original_orders_count else len(orders_df)
        result['wip_explosion_factor'] = float(compute_wip_explosion_factor(orders_multi_df, orig_count))

    return result


def compute_machine_utilization(df_schedule, orders_df=None):
    """
    Calculate average machine utilization across all machines.

    utilization = busy_time / available_time

    where available_time is the time from earliest start to latest end
    across all scheduled operations.

    Args:
        df_schedule (pandas.DataFrame): DataFrame with order_id, operation_seq, machine_id, start, end
        orders_df: Ignored (for API compatibility)

    Returns:
        float: Average utilization as a percentage (0-100)
    """
    df = df_schedule.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['start']):
        df['start'] = pd.to_datetime(df['start'])
    if not pd.api.types.is_datetime64_any_dtype(df['end']):
        df['end'] = pd.to_datetime(df['end'])

    # Calculate busy time per machine
    machine_busy_time = {}
    for machine_id, group in df.groupby('machine_id'):
        busy = (group['end'] - group['start']).sum()
        machine_busy_time[machine_id] = busy.total_seconds() / 3600.0  # Convert to hours

    # Calculate available time (from earliest start to latest end)
    earliest = df['start'].min()
    latest = df['end'].max()
    available_time = (latest - earliest).total_seconds() / 3600.0  # Total hours

    if available_time <= 0:
        return 0.0

    # Average utilization across all machines
    total_busy = sum(machine_busy_time.values())
    num_machines = len(machine_busy_time)

    if num_machines == 0:
        return 0.0

    # utilization = total busy hours / (num_machines * available_time)
    avg_utilization = (total_busy / (num_machines * available_time)) * 100.0
    return avg_utilization


def compute_alt_machine_usage(df_schedule):
    """
    Calculate percentage of jobs that did not use their primary machine.

    Args:
        df_schedule (pandas.DataFrame): DataFrame with is_primary column

    Returns:
        float: Percentage of jobs using alternate machines (0-100)
    """
    if 'is_primary' not in df_schedule.columns:
        return 0.0

    total = len(df_schedule)
    if total == 0:
        return 0.0

    # Count jobs where is_primary is False (alternate machine used)
    alt_count = (df_schedule['is_primary'] == False).sum()
    alt_pct = (alt_count / total) * 100.0

    return alt_pct


def compute_release_delay(df_schedule, orders_df):
    """
    Calculate average delay due to release constraints.

    delay_due_to_release = start_time of first operation - release_time

    Args:
        df_schedule (pandas.DataFrame): DataFrame with order_id, operation_seq, start
        orders_df (pandas.DataFrame): DataFrame with order_id, release_time

    Returns:
        float: Average release delay in hours (positive = started after release)
    """
    df = df_schedule.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['start']):
        df['start'] = pd.to_datetime(df['start'])

    # Get first operation (operation_seq = 1) for each order
    first_ops = df[df['operation_seq'] == 1].copy()

    if len(first_ops) == 0:
        return 0.0

    # Merge with orders to get release_time
    merged = first_ops.merge(
        orders_df[['order_id', 'release_time', 'order_date']],
        on='order_id',
        how='left'
    )

    # Calculate delay
    merged['release_delay'] = (merged['start'] - merged['release_time']).dt.total_seconds() / 3600.0

    # Filter to only orders where release_time was actually after order_date
    # (meaning the order was constrained by release time)
    constrained = merged[merged['release_time'] > merged['order_date']]
    if len(constrained) == 0:
        return 0.0

    avg_delay = constrained['release_delay'].mean()
    return avg_delay


def compute_dependency_delay(df_schedule, order_links_df):
    """
    Calculate Phase 3 dependency delay.

    For each parent order, compute: parent_start - max(child_completion_times)
    Average across all parent orders that have children.

    Args:
        df_schedule (pandas.DataFrame): DataFrame with order_id, operation_seq, start, end
        order_links_df (pandas.DataFrame): DataFrame with parent_order_id, child_order_id

    Returns:
        float: Average dependency delay in hours
    """
    if order_links_df is None or order_links_df.empty:
        return 0.0

    df = df_schedule.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['end']):
        df['end'] = pd.to_datetime(df['end'])
    if not pd.api.types.is_datetime64_any_dtype(df['start']):
        df['start'] = pd.to_datetime(df['start'])

    # Get first operation start time for each order (parent start)
    parent_starts = df.groupby('order_id')['start'].min()
    # Get last operation end time for each order (child completion)
    child_ends = df.groupby('order_id')['end'].max()

    delays = []
    for _, link in order_links_df.iterrows():
        parent_id = link['parent_order_id']
        child_id = link['child_order_id']

        if parent_id in parent_starts.index and child_id in child_ends.index:
            parent_start = parent_starts[parent_id]
            child_end = child_ends[child_id]
            delay = (parent_start - child_end).total_seconds() / 3600.0
            delays.append(delay)

    if not delays:
        return 0.0

    return sum(delays) / len(delays)


def compute_critical_path_length(df_schedule, orders_df, order_links_df):
    """
    Calculate Phase 3 critical path length.

    For each top-level order (level=0), find the longest chain to leaf.
    Returns the maximum chain length across all top-level orders.

    Args:
        df_schedule (pandas.DataFrame): DataFrame with order_id, operation_seq, start, end
        orders_df (pandas.DataFrame): DataFrame with order_id, level
        order_links_df (pandas.DataFrame): DataFrame with parent_order_id, child_order_id

    Returns:
        int: Maximum critical path length (number of orders in longest chain)
    """
    if order_links_df is None or order_links_df.empty:
        return 0

    if orders_df is None or 'level' not in orders_df.columns:
        return 0

    # Build parent->children mapping
    children_map = {}
    for _, row in order_links_df.iterrows():
        parent = row['parent_order_id']
        child = row['child_order_id']
        if parent not in children_map:
            children_map[parent] = []
        children_map[parent].append(child)

    # Build child->parent mapping
    parents_map = {}
    for _, row in order_links_df.iterrows():
        parents_map[row['child_order_id']] = row['parent_order_id']

    # Find top-level orders (level=0)
    top_level_orders = orders_df[orders_df['level'] == 0]['order_id'].tolist()

    def get_chain_length(order_id, visited=None):
        """Recursively find longest chain from this order to leaf."""
        if visited is None:
            visited = set()

        if order_id in visited:
            return 0  # Cycle detected
        visited.add(order_id)

        children = children_map.get(order_id, [])
        if not children:
            return 1  # Leaf node

        max_child_len = 0
        for child in children:
            child_len = get_chain_length(child, visited.copy())
            max_child_len = max(max_child_len, child_len)

        return 1 + max_child_len

    max_path = 0
    for order_id in top_level_orders:
        path_len = get_chain_length(order_id)
        max_path = max(max_path, path_len)

    return max_path


def compute_component_service_level(df_schedule, orders_df, order_links_df):
    """
    Calculate Phase 3 component service level.

    Percentage of child orders that completed before their parent needed them.
    (child_end <= parent_start)

    Args:
        df_schedule (pandas.DataFrame): DataFrame with order_id, start, end
        orders_df (pandas.DataFrame): DataFrame with order_id
        order_links_df (pandas.DataFrame): DataFrame with parent_order_id, child_order_id

    Returns:
        float: Percentage of child orders meeting service level (0-100)
    """
    if order_links_df is None or order_links_df.empty:
        return 100.0

    df = df_schedule.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['end']):
        df['end'] = pd.to_datetime(df['end'])
    if not pd.api.types.is_datetime64_any_dtype(df['start']):
        df['start'] = pd.to_datetime(df['start'])

    # Get first operation start time for each order
    parent_starts = df.groupby('order_id')['start'].min()
    # Get last operation end time for each order
    child_ends = df.groupby('order_id')['end'].max()

    met_count = 0
    total_count = 0

    for _, link in order_links_df.iterrows():
        parent_id = link['parent_order_id']
        child_id = link['child_order_id']

        if parent_id in parent_starts.index and child_id in child_ends.index:
            total_count += 1
            parent_start = parent_starts[parent_id]
            child_end = child_ends[child_id]

            if child_end <= parent_start:
                met_count += 1

    if total_count == 0:
        return 100.0

    return (met_count / total_count) * 100.0


def compute_wip_explosion_factor(orders_multi_df, original_orders_count):
    """
    Calculate Phase 3 WIP explosion factor.

    Ratio of total multi-level orders to original flat orders.

    Args:
        orders_multi_df (pandas.DataFrame): Multi-level orders DataFrame
        original_orders_count (int): Count of original flat orders

    Returns:
        float: WIP explosion factor (>1 means hierarchy created more orders)
    """
    if orders_multi_df is None or original_orders_count == 0:
        return 1.0

    multi_count = len(orders_multi_df)
    return multi_count / original_orders_count


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

        # Compute completion times with delay (using orders data)
        delay_df = compute_completion(schedule_df, data['orders'])
        print(f"\nComputed completion times with delay for {len(delay_df)} orders")

        # Show delay statistics
        print("\nDelay statistics (in hours):")
        print(f"Average delay: {delay_df['delay_hours'].mean():.2f} hours")
        print(f"Median delay: {delay_df['delay_hours'].median():.2f} hours")

        # Test the new KPI metrics function
        print("\n=== KPI METRICS ===")
        kpi_metrics = compute_kpi_metrics(schedule_df, data['orders'])
        for key, value in kpi_metrics.items():
            if key in ['avg_delay', 'max_delay', 'avg_utilization', 'avg_release_delay']:
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
