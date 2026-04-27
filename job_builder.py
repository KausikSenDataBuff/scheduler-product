import pandas as pd

def build_jobs(data):
    """
    Build operation-level jobs by joining orders with routing on product_id.

    Args:
        data (dict): Dictionary of DataFrames with keys 'orders' and 'routing'
                     (as returned by load_data)

    Returns:
        pandas.DataFrame: DataFrame with columns:
                          order_id, product_id, operation_seq, machine_id, proc_time_min
    """
    # Extract the required DataFrames
    orders_df = data['orders']
    routing_df = data['routing']

    # Merge orders with routing on product_id
    # We want to keep all orders and match their routing operations
    merged_df = pd.merge(
        orders_df,
        routing_df,
        on='product_id',
        how='inner'  # Only keep orders that have routing defined
    )

    # Select and return the required columns
    result_df = merged_df[['order_id', 'product_id', 'operation_seq', 'machine_id', 'proc_time_min']]

    return result_df

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
        print("\nFirst 5 rows:")
        print(jobs_df.head())

        # Test initialize_machine_state
        machine_state = initialize_machine_state(data)
        print(f"\nInitialized state for {len(machine_state)} machines")
        print("Sample machine states (first 3):")
        for i, (machine_id, jobs) in enumerate(list(machine_state.items())[:3]):
            print(f"  {machine_id}: {jobs} (length: {len(jobs)})")

        print("\nDataFrame info:")
        print(jobs_df.info())
    except Exception as e:
        print(f"Error: {e}")