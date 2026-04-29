import pandas as pd
import os

def load_data(data_dir=None):
    """
    Load CSV files from the data folder and return a dictionary of DataFrames.
    Parses datetime fields: order_date, due_date, start_time, end_time.

    Supports Phase 1.5 and Phase 2 data files:
    - Phase 2: routing_alternate.csv (multi-machine routing), orders_phase2.csv (with release_time)

    Parameters:
        data_dir (str, optional): The directory containing the CSV files.
                                  If not provided, uses the 'data' folder in the same directory as this script.

    Returns:
        dict: Dictionary of DataFrames with keys 'machines', 'products', 'routing', 'orders',
              and optionally 'routing_alt', 'machine_calendar', 'setup_matrix', 'sections', 'buffers'.
    """
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), 'data')

    # Dictionary to hold DataFrames
    dataframes = {}

    # Helper to load a file if it exists
    def load_if_exists(filename, key, datetime_cols=None):
        file_path = os.path.join(data_dir, filename)
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            if datetime_cols:
                for col in datetime_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
            dataframes[key] = df
            return True
        return False

    # ---- Core files (Phase 1.5 names, with Phase 2 fallbacks) ----
    # Machines
    load_if_exists('machines_updated.csv', 'machines')
    load_if_exists('machines.csv', 'machines')

    # Products
    load_if_exists('products.csv', 'products')

    # Routing - check Phase 2 alternate routing first
    if load_if_exists('routing_alternate.csv', 'routing_alt'):
        # Also provide legacy routing for compatibility (point to same data if needed)
        if 'routing' not in dataframes:
            dataframes['routing'] = dataframes['routing_alt']
    else:
        load_if_exists('routing_updated.csv', 'routing')
        load_if_exists('routing.csv', 'routing')

    # Orders - check Phase 2 orders first
    if not load_if_exists('orders_phase2.csv', 'orders',
                         datetime_cols=['order_date', 'due_date', 'release_time', 'material_available_time']):
        load_if_exists('orders_updated.csv', 'orders', datetime_cols=['order_date', 'due_date'])
        load_if_exists('orders.csv', 'orders', datetime_cols=['order_date', 'due_date'])

    # ---- Optional Phase 1.5 files ----
    load_if_exists('machine_calendar.csv', 'machine_calendar',
                   datetime_cols=['start_time', 'end_time'])
    load_if_exists('setup_matrix.csv', 'setup_matrix')
    load_if_exists('sections.csv', 'sections')
    load_if_exists('buffers.csv', 'buffers')

    return dataframes

if __name__ == "__main__":
    # For testing
    dfs = load_data()
    for name, df in dfs.items():
        print(f"{name}: {df.shape}")
        print(df.head())
        print("-" * 40)
