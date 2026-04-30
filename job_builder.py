import pandas as pd

def build_jobs(data):
    """
    Build operation-level jobs by joining orders with routing on product_id.

    For Phase 3 (multi-level), uses orders_multilevel and includes parent-child
    dependency metadata. For Phase 2, uses orders with routing_alternate.

    Args:
        data (dict): Dictionary of DataFrames. Phase 3 uses 'orders_multi' and
                     'order_links'. Phase 2 uses 'orders' and 'routing_alt'.

    Returns:
        pandas.DataFrame: DataFrame with columns:
                          order_id, product_id, operation_seq, candidate_machines
                          [, parent_order_id, level, child_orders] (Phase 3)
                          where candidate_machines is a list of dicts:
                          [{'machine_id': 'M1', 'proc_time': 10, 'is_primary': True, 'efficiency': 1.0}, ...]
    """
    # Determine which orders to use (Phase 3 multi-level or Phase 2)
    orders_multi = data.get('orders_multi')
    orders_df = data['orders'] if orders_multi is None else orders_multi

    # Use routing_alt if available
    routing_alt_df = data['routing_alt']
    order_links_df = data.get('order_links')

    # Build child orders mapping for Phase 3
    child_orders_map = {}
    if order_links_df is not None:
        for _, row in order_links_df.iterrows():
            parent = row['parent_order_id']
            child = row['child_order_id']
            if parent not in child_orders_map:
                child_orders_map[parent] = []
            child_orders_map[parent].append(child)

    # Group routing by (product_id, operation_seq) to build candidate lists
    grouped = routing_alt_df.groupby(['product_id', 'operation_seq'])

    result_rows = []

    for (product_id, op_seq), group in grouped:
        # Build list of candidate machines for this operation
        candidates = []
        for _, row in group.iterrows():
            candidates.append({
                'machine_id': row['machine_id'],
                'proc_time': row['proc_time_min'],
                'is_primary': row['is_primary'] == 1,
                'efficiency': row['efficiency']
            })

        # Get all orders for this product
        product_orders = orders_df[orders_df['product_id'] == product_id]

        for _, order in product_orders.iterrows():
            row_data = {
                'order_id': order['order_id'],
                'product_id': product_id,
                'operation_seq': op_seq,
                'candidate_machines': candidates
            }

            # Phase 3: Add hierarchy metadata
            if orders_multi is not None:
                row_data['parent_order_id'] = order.get('parent_order_id', None)
                row_data['level'] = order.get('level', 0)
                row_data['child_orders'] = child_orders_map.get(order['order_id'], [])

            result_rows.append(row_data)

    return pd.DataFrame(result_rows)

def initialize_machine_state(data):
    """
    Initialize machine state with empty job lists for each machine.

    Args:
        data (dict): Dictionary of DataFrames with keys 'machines' (as returned by load_data)

    Returns:
        dict: Dictionary mapping machine_id to an empty list of jobs
              Format: {machine_id: []}
    """
    machines_df = data['machines']
    # Create a dictionary with machine_id as keys and empty lists as values
    machine_state = {machine_id: [] for machine_id in machines_df['machine_id']}
    return machine_state

if __name__ == "__main__":
    # For testing - import data_loader and test functions
    from data_loader import load_data
    try:
        data = load_data()

        # Test build_jobs
        jobs_df = build_jobs(data)
        print(f"Built {len(jobs_df)} job operations from {len(data['orders'])} orders")
        print(f"Columns: {list(jobs_df.columns)}")
        print("\nFirst 3 rows:")
        for i, row in jobs_df.head(3).iterrows():
            print(f"  {row['order_id']}: {row['product_id']} op {row['operation_seq']}")
            print(f"    Candidates: {len(row['candidate_machines'])} machines")
            for c in row['candidate_machines'][:2]:
                print(f"      {c['machine_id']}: {c['proc_time']}min (primary={c['is_primary']})")

        # Test initialize_machine_state
        machine_state = initialize_machine_state(data)
        print(f"\nInitialized state for {len(machine_state)} machines")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
