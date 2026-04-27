import pandas as pd
import os

def load_data(data_dir=None):
    """
    Load CSV files from the data folder and return a dictionary of DataFrames.
    Parses datetime fields: order_date, due_date, start_time, end_time.

    Parameters:
        data_dir (str, optional): The directory containing the CSV files.
                                  If not provided, uses the 'data' folder in the same directory as this script.

    Returns:
        dict: Dictionary of DataFrames with keys 'machines', 'products', 'routing', 'orders',
              and optionally 'machine_calendar', 'setup_matrix', 'sections', 'buffers'.
    """
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), 'data')

    # Define file paths
    files = {
        'machines': 'machines.csv',
        'products': 'products.csv',
        'routing': 'routing.csv',
        'orders': 'orders.csv'
    }

    # Optional files
    optional_files = {
        'machine_calendar': 'machine_calendar.csv',
        'setup_matrix': 'setup_matrix.csv',
        'sections': 'sections.csv',
        'buffers': 'buffers.csv'
    }

    # Dictionary to hold DataFrames
    dataframes = {}

    for key, filename in files.items():
        file_path = os.path.join(data_dir, filename)

        # Read CSV
        df = pd.read_csv(file_path)

        # Parse datetime fields if they exist
        if key == 'orders':
            datetime_cols = ['order_date', 'due_date']
            for col in datetime_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

        dataframes[key] = df

    # Load optional files if they exist
    for key, filename in optional_files.items():
        file_path = os.path.join(data_dir, filename)
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            # Parse datetime fields for machine_calendar
            if key == 'machine_calendar':
                df['start_time'] = pd.to_datetime(df['start_time'], errors='coerce')
                df['end_time'] = pd.to_datetime(df['end_time'], errors='coerce')
            dataframes[key] = df

    return dataframes

if __name__ == "__main__":
    # For testing
    dfs = load_data()
    for name, df in dfs.items():
        print(f"{name}: {df.shape}")
        print(df.head())
        print("-" * 40)