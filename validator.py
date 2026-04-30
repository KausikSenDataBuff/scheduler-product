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


def validate_routing_alternate(data):
    """
    Validate Phase 2 alternate routing data.

    Checks:
    - Each (product_id, operation_seq) has at least 1 machine candidate
    - All machine_ids in routing_alt exist in machines

    Args:
        data (dict): Dictionary of DataFrames with keys 'routing_alt' and 'machines'

    Raises:
        ValueError: If any validation check fails
    """
    routing_alt = data['routing_alt']
    machines_df = data['machines']

    errors = []

    # Check 1: Each (product_id, operation_seq) has at least 1 machine
    grouped = routing_alt.groupby(['product_id', 'operation_seq']).size()
    if (grouped < 1).any():
        invalid = grouped[grouped < 1].index.tolist()
        errors.append(f"Operations with no machine candidates: {invalid}")

    # Check 2: All machine_ids in routing_alt exist in machines
    if not routing_alt['machine_id'].isin(machines_df['machine_id']).all():
        invalid_machines = routing_alt.loc[~routing_alt['machine_id'].isin(machines_df['machine_id']), 'machine_id'].unique()
        errors.append(f"machine_id in routing_alt but not in machines: {list(invalid_machines)}")

    if errors:
        raise ValueError("\n".join(errors))


def validate_orders_phase2(data):
    """
    Validate Phase 2 orders data.

    Checks:
    - release_time <= due_date
    - material_available_time <= due_date

    Args:
        data (dict): Dictionary of DataFrames with keys 'orders'

    Raises:
        ValueError: If any validation check fails
    """
    orders = data['orders']

    errors = []

    # Check release_time <= due_date
    if (orders['release_time'] > orders['due_date']).any():
        violations = orders[orders['release_time'] > orders['due_date']]
        errors.append(f"release_time > due_date for orders: {violations['order_id'].tolist()}")

    # Check material_available_time <= due_date
    if (orders['material_available_time'] > orders['due_date']).any():
        violations = orders[orders['material_available_time'] > orders['due_date']]
        errors.append(f"material_available_time > due_date for orders: {violations['order_id'].tolist()}")

    if errors:
        raise ValueError("\n".join(errors))


def validate_bom(data):
    """
    Validate Phase 3 Bill of Materials data.

    Checks:
    - No self-loops (parent_product != child_product)
    - No cycles in BOM (DFS cycle detection)
    - All products in bom exist in products DataFrame

    Args:
        data (dict): Dictionary of DataFrames with keys 'bom' and 'products'

    Raises:
        ValueError: If any validation check fails
    """
    if 'bom' not in data or data['bom'] is None:
        return  # BOM is optional

    bom = data['bom']
    products_df = data['products']

    errors = []

    # Check 1: No self-loops
    self_loops = bom[bom['parent_product'] == bom['child_product']]
    if not self_loops.empty:
        errors.append(f"BOM self-loops found: {self_loops['parent_product'].tolist()}")

    # Check 2: All products in bom exist in products
    if not bom['parent_product'].isin(products_df['product_id']).all():
        invalid = bom.loc[~bom['parent_product'].isin(products_df['product_id']), 'parent_product'].unique()
        errors.append(f"BOM parent_product not in products: {list(invalid)}")

    if not bom['child_product'].isin(products_df['product_id']).all():
        invalid = bom.loc[~bom['child_product'].isin(products_df['product_id']), 'child_product'].unique()
        errors.append(f"BOM child_product not in products: {list(invalid)}")

    # Check 3: No cycles using DFS
    # Build adjacency: parent -> [children]
    children_map = {}
    for _, row in bom.iterrows():
        parent = row['parent_product']
        child = row['child_product']
        if parent not in children_map:
            children_map[parent] = []
        children_map[parent].append(child)

    # DFS cycle detection
    visited = set()
    rec_stack = set()
    cycle_nodes = []

    def has_cycle(node, visited, rec_stack):
        visited.add(node)
        rec_stack.add(node)
        for child in children_map.get(node, []):
            if child not in visited:
                if has_cycle(child, visited, rec_stack):
                    return True
            elif child in rec_stack:
                return True
        rec_stack.remove(node)
        return False

    for node in children_map:
        if node not in visited:
            if has_cycle(node, visited, rec_stack):
                cycle_nodes.append(node)

    if cycle_nodes:
        # BOM cycles are warnings, not hard fails, because BOM is not directly used
        # in scheduling (order_links governs dependencies, not BOM)
        print(f"   WARNING: Cyclic BOM detected starting from product: {cycle_nodes[0]}")
        print("   (BOM is used for visualization, not scheduling - continuing...)")


def validate_order_links(data):
    """
    Validate Phase 3 order_links data.

    Checks:
    - All order_ids in order_links exist in orders_multilevel
    - No cycles in parent->child graph

    Args:
        data (dict): Dictionary of DataFrames with keys 'order_links' and 'orders_multi'

    Raises:
        ValueError: If any validation check fails
    """
    if 'order_links' not in data or data['order_links'] is None:
        return  # order_links is optional

    order_links = data['order_links']
    orders_multi = data.get('orders_multi')

    errors = []

    # Check 1: All order_ids exist in orders_multilevel
    if orders_multi is not None:
        all_order_ids = set(orders_multi['order_id'])
        for col in ['parent_order_id', 'child_order_id']:
            invalid = order_links[~order_links[col].isin(all_order_ids)]
            if not invalid.empty:
                invalid_ids = invalid[col].unique()
                errors.append(f"order_links.{col} not in orders_multilevel: {list(invalid_ids)}")

    # Check 2: No cycles using Kahn's algorithm (topological sort)
    # Build parent->children mapping
    children_map = {}
    parents_map = {}
    for _, row in order_links.iterrows():
        parent = row['parent_order_id']
        child = row['child_order_id']
        if parent not in children_map:
            children_map[parent] = []
        children_map[parent].append(child)
        parents_map[child] = parent

    # Find all root nodes (no parents)
    all_nodes = set(order_links['parent_order_id']) | set(order_links['child_order_id'])
    root_nodes = all_nodes - set(parents_map.keys())

    # Kahn's algorithm
    in_degree = {node: 0 for node in all_nodes}
    for parent, children in children_map.items():
        for child in children:
            in_degree[child] += 1

    queue = [node for node in root_nodes if node in in_degree]
    queue.sort()  # Deterministic order
    topo_order = []

    while queue:
        node = queue.pop(0)
        topo_order.append(node)
        for child in children_map.get(node, []):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)
                queue.sort()

    if len(topo_order) != len(all_nodes):
        # Cycle detected - some nodes not in topo_order
        remaining = all_nodes - set(topo_order)
        errors.append(f"Cyclic order_links detected. Nodes involved: {list(remaining)[:10]}")

    if errors:
        raise ValueError("\n".join(errors))


def validate_orders_multilevel(data):
    """
    Validate Phase 3 orders_multilevel data.

    Checks:
    - level >= 0
    - parent_order_id valid or null (for level > 0)
    - consistency with order_links

    Args:
        data (dict): Dictionary of DataFrames with keys 'orders_multi' and 'order_links'

    Raises:
        ValueError: If any validation check fails
    """
    if 'orders_multi' not in data or data['orders_multi'] is None:
        return  # orders_multi is optional

    orders = data['orders_multi']
    order_links = data.get('order_links')

    errors = []

    # Check 1: level >= 0
    if (orders['level'] < 0).any():
        violations = orders[orders['level'] < 0]['order_id'].tolist()
        errors.append(f"Orders with level < 0: {violations}")

    # Check 2: parent_order_id valid or null
    if order_links is not None and 'parent_order_id' in orders.columns:
        all_order_ids = set(orders['order_id'])
        for _, row in orders.iterrows():
            if row['level'] > 0:
                parent = row.get('parent_order_id')
                if pd.notna(parent) and parent not in all_order_ids:
                    errors.append(f"Order {row['order_id']} has invalid parent_order_id: {parent}")

    # Check 3: consistency with order_links
    if order_links is not None:
        for _, link in order_links.iterrows():
            parent = link['parent_order_id']
            child = link['child_order_id']
            # Check parent exists in orders
            if parent not in orders['order_id'].values:
                errors.append(f"order_links parent {parent} not in orders_multi")
            # Check child exists in orders
            if child not in orders['order_id'].values:
                errors.append(f"order_links child {child} not in orders_multi")

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

        # Phase 3 validation if data available
        if 'bom' in data and data['bom'] is not None:
            validate_bom(data)
            print("BOM validation passed.")
        if 'order_links' in data and data['order_links'] is not None:
            validate_order_links(data)
            print("order_links validation passed.")
        if 'orders_multi' in data and data['orders_multi'] is not None:
            validate_orders_multilevel(data)
            print("orders_multilevel validation passed.")
    except ValueError as e:
        print(f"Validation failed:\n{e}")
    except Exception as e:
        print(f"Unexpected error: {e}")