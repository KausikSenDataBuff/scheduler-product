import pandas as pd

def validate_foreign_keys(data):
    """
    Validate foreign key relationships in the loaded data.

    Checks:
    - All product_id in orders exist in products
    - All machine_id in routing exist in machines

    Args:
        data (dict): Dictionary of DataFrames with keys 'machines', 'products', 'routing', 'orders'

    Raises:
        ValueError: If any foreign key constraint is violated with a clear message
    """
    # Extract DataFrames
    machines_df = data['machines']
    products_df = data['products']
    routing_df = data['routing']
    orders_df = data['orders']

    errors = []

    # Check 1: All product_id in orders exist in products
    if not orders_df['product_id'].isin(products_df['product_id']).all():
        invalid_products = orders_df.loc[~orders_df['product_id'].isin(products_df['product_id']), 'product_id'].unique()
        errors.append(f"The following product_id in orders do not exist in products: {list(invalid_products)}")

    # Check 2: All machine_id in routing exist in machines
    if not routing_df['machine_id'].isin(machines_df['machine_id']).all():
        invalid_machines = routing_df.loc[~routing_df['machine_id'].isin(machines_df['machine_id']), 'machine_id'].unique()
        errors.append(f"The following machine_id in routing do not exist in machines: {list(invalid_machines)}")

    if errors:
        raise ValueError("\n".join(errors))

def validate_nulls(data):
    """
    Validate that critical fields contain no null values.

    Checks for nulls in:
    - machine_id (in machines and routing DataFrames)
    - product_id (in products, routing, and orders DataFrames)
    - operation_seq (in routing DataFrame)
    - proc_time_min (in routing DataFrame)

    Args:
        data (dict): Dictionary of DataFrames with keys 'machines', 'products', 'routing', 'orders'

    Raises:
        ValueError: If any null values are found in critical fields with a clear message
    """
    # Extract DataFrames
    machines_df = data['machines']
    products_df = data['products']
    routing_df = data['routing']
    orders_df = data['orders']

    errors = []

    # Check machine_id in machines
    if machines_df['machine_id'].isnull().any():
        null_count = machines_df['machine_id'].isnull().sum()
        errors.append(f"Found {null_count} null values in machine_id column of machines DataFrame")

    # Check machine_id in routing
    if routing_df['machine_id'].isnull().any():
        null_count = routing_df['machine_id'].isnull().sum()
        errors.append(f"Found {null_count} null values in machine_id column of routing DataFrame")

    # Check product_id in products
    if products_df['product_id'].isnull().any():
        null_count = products_df['product_id'].isnull().sum()
        errors.append(f"Found {null_count} null values in product_id column of products DataFrame")

    # Check product_id in routing
    if routing_df['product_id'].isnull().any():
        null_count = routing_df['product_id'].isnull().sum()
        errors.append(f"Found {null_count} null values in product_id column of routing DataFrame")

    # Check product_id in orders
    if orders_df['product_id'].isnull().any():
        null_count = orders_df['product_id'].isnull().sum()
        errors.append(f"Found {null_count} null values in product_id column of orders DataFrame")

    # Check operation_seq in routing
    if routing_df['operation_seq'].isnull().any():
        null_count = routing_df['operation_seq'].isnull().sum()
        errors.append(f"Found {null_count} null values in operation_seq column of routing DataFrame")

    # Check proc_time_min in routing
    if routing_df['proc_time_min'].isnull().any():
        null_count = routing_df['proc_time_min'].isnull().sum()
        errors.append(f"Found {null_count} null values in proc_time_min column of routing DataFrame")

    # Check capacity in machines (should be positive integer)
    if 'capacity' in machines_df.columns:
        if not machines_df['capacity'].notnull().all():
            null_count = machines_df['capacity'].isnull().sum()
            errors.append(f"Found {null_count} null values in capacity column of machines DataFrame")
        if (machines_df['capacity'] < 1).any():
            invalid = machines_df[machines_df['capacity'] < 1]['machine_id'].tolist()
            errors.append(f"Machine(s) with invalid capacity (< 1): {invalid}")
    else:
        errors.append("machines.csv is missing 'capacity' column (required for Phase 1.5+)")

    if errors:
        raise ValueError("\n".join(errors))

if __name__ == "__main__":
    # For testing - import data_loader and validate
    from data_loader import load_data
    try:
        data = load_data()
        validate_foreign_keys(data)
        validate_nulls(data)
        print("Validation passed: All foreign key and null checks are satisfied.")
    except ValueError as e:
        print(f"Validation failed:\n{e}")
    except Exception as e:
        print(f"Unexpected error: {e}")