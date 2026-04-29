# API Reference

## data_loader.py

### load_data()
Loads CSV files from the 'data' folder and returns a dictionary of pandas DataFrames. Supports Phase 1.5 and Phase 2 data files.

**Parameters:** None

**Returns:**
- dict: Dictionary with keys:
  - 'machines': DataFrame with columns [machine_id, department, shift_start, shift_end, capacity]
  - 'products': DataFrame with columns [product_id, family, complexity]
  - 'routing': DataFrame (Phase 1.5 routing)
  - 'routing_alt': DataFrame with columns [product_id, operation_seq, department, machine_id, proc_time_min, is_primary, efficiency]
  - 'orders': DataFrame with columns [order_id, product_id, quantity, order_date, due_date, priority, release_time, material_available_time, penalty_per_hour]
  - Optional: 'machine_calendar', 'setup_matrix', 'sections', 'buffers'

**Phase 2 Notes:**
- `routing_alternate.csv` is loaded as 'routing_alt' (primary data source)
- `orders_phase2.csv` is loaded as 'orders' (replaces legacy orders)
- Datetime columns parsed: order_date, due_date, release_time, material_available_time

**Example:**
```python
from data_loader import load_data
data = load_data()
print(data['orders'].columns)  # Shows Phase 2 columns
print(data['routing_alt'].head())  # Shows alternate routing
```

## validator.py

### validate_foreign_keys(data)
Validates foreign key relationships in the loaded data.

**Parameters:**
- data (dict): Dictionary of DataFrames with keys 'machines', 'products', 'routing', 'orders'

**Returns:** None

**Raises:**
- ValueError: If any foreign key constraint is violated with a clear message

**Checks:**
- All product_id in orders exist in products
- All machine_id in routing exist in machines

**Example:**
```python
from validator import validate_foreign_keys
validate_foreign_keys(data)  # Raises ValueError if validation fails
```

### validate_nulls(data)
Validates that critical fields contain no null values.

**Parameters:**
- data (dict): Dictionary of DataFrames with keys 'machines', 'products', 'routing', 'orders'

**Returns:** None

**Raises:**
- ValueError: If any null values are found in critical fields with a clear message

**Checks:**
- machine_id (in machines and routing DataFrames)
- product_id (in products, routing, and orders DataFrames)
- operation_seq (in routing DataFrame)
- proc_time_min (in routing DataFrame)
- capacity (in machines DataFrame, Phase 1.5+):
  - Null values in capacity column
  - Capacity values < 1
  - Missing capacity column

**Example:**
```python
from validator import validate_nulls
validate_nulls(data)  # Raises ValueError if validation fails
```

### validate_routing_alternate(data) [Phase 2]
Validates Phase 2 alternate routing data.

**Parameters:**
- data (dict): Dictionary of DataFrames with keys 'routing_alt' and 'machines'

**Returns:** None

**Raises:**
- ValueError: If validation fails

**Checks:**
- Each (product_id, operation_seq) has at least 1 machine candidate
- All machine_ids in routing_alt exist in machines

**Example:**
```python
from validator import validate_routing_alternate
validate_routing_alternate(data)  # Raises ValueError if validation fails
```

### validate_orders_phase2(data) [Phase 2]
Validates Phase 2 orders data.

**Parameters:**
- data (dict): Dictionary of DataFrames with key 'orders'

**Returns:** None

**Raises:**
- ValueError: If validation fails

**Checks:**
- release_time <= due_date
- material_available_time <= due_date

**Example:**
```python
from validator import validate_orders_phase2
validate_orders_phase2(data)  # Raises ValueError if validation fails
```

## job_builder.py

### build_jobs(data)
Builds operation-level jobs by joining orders with routing. **Phase 2 version** outputs candidate_machines list per operation.

**Parameters:**
- data (dict): Dictionary of DataFrames with keys 'orders' and 'routing_alt'

**Returns:**
- pandas.DataFrame: DataFrame with columns:
  - order_id
  - product_id
  - operation_seq
  - candidate_machines (list of dicts)

**candiate_machines format:**
```python
[
    {'machine_id': 'M1', 'proc_time': 10.0, 'is_primary': True, 'efficiency': 1.0},
    {'machine_id': 'M2', 'proc_time': 12.76, 'is_primary': False, 'efficiency': 0.78}
]
```

**Example:**
```python
from job_builder import build_jobs
jobs_df = build_jobs(data)
print(jobs_df['candidate_machines'].head())
```

### initialize_machine_state(data)
Initializes machine state with empty job lists for each machine.

**Parameters:**
- data (dict): Dictionary of DataFrames with key 'machines'

**Returns:**
- dict: Dictionary mapping machine_id to an empty list of jobs
  Format: {machine_id: []}

**Example:**
```python
from job_builder import initialize_machine_state
machine_state = initialize_machine_state(data)
```

## scheduler.py

### run_scheduler(data, jobs_df=None)
**Phase 2** scheduling algorithm with alternate machine selection and release constraints.

**Parameters:**
- data (dict): Dictionary of DataFrames with keys:
  - 'orders' (Phase 2 orders with release_time)
  - 'routing_alt' (alternate routing with candidates)
  - 'machines'
  - Optional: 'machine_calendar', 'setup_matrix'
- jobs_df (DataFrame, optional): Pre-built jobs from job_builder. If not provided, builds jobs internally.

**Returns:**
- pandas.DataFrame: DataFrame with columns:
  - order_id
  - operation_seq
  - machine_id
  - start (Timestamp)
  - end (Timestamp)
  - is_primary (bool)

**Algorithm:**
1. Sort jobs by due_date (ascending)
2. For each order: current_time = max(order_date, release_time, material_time)
3. For each operation:
   - Select best machine from candidates (earliest completion)
   - Add setup time if transitioning products
   - Schedule on best machine
   - Store result

**Example:**
```python
from scheduler import run_scheduler
schedule_df = run_scheduler(data)
print(schedule_df[['order_id', 'machine_id', 'is_primary']].head())
```

### select_best_machine(candidate_machines, machine_intervals, machine_capacity, current_time, setup_dict, last_product, calendar_df) [Phase 2]
Selects the machine that allows earliest completion from a list of candidates.

**Parameters:**
- candidate_machines: list of dicts with machine_id, proc_time, is_primary, efficiency
- machine_intervals: dict of machine_id -> list of (start, end) tuples
- machine_capacity: dict of machine_id -> capacity
- current_time: earliest time we can start
- setup_dict: pre-indexed setup time lookup
- last_product: dict of machine_id -> last product scheduled
- calendar_df: DataFrame with machine availability

**Returns:**
- tuple: (machine_id, start_time, end_time, is_primary)

**Example:**
```python
best_machine, start, end, is_primary = select_best_machine(
    candidates, machine_intervals, machine_capacity,
    current_time, setup_dict, last_product, calendar_df
)
```

### apply_release_constraint(order_date, release_time, material_available_time) [Phase 2]
Returns the earliest valid start time for an order based on release and material constraints.

**Parameters:**
- order_date: When the order was placed
- release_time: When the order is released for scheduling
- material_available_time: When materials are available

**Returns:**
- Timestamp: The earliest valid start time

**Example:**
```python
current_time = apply_release_constraint(order_date, release_time, material_time)
```

### save_schedule(df_schedule)
Saves the schedule DataFrame to a CSV file named 'schedule.csv'.

**Parameters:**
- df_schedule (pandas.DataFrame): DataFrame with columns:
  - order_id
  - operation_seq
  - machine_id
  - start
  - end
  where start and end are Timestamps.

**Returns:** None

**Effects:**
- Creates/overwrites 'schedule.csv' in the current directory
- Converts timestamp columns to string format: YYYY-MM-DD HH:MM:SS

**Example:**
```python
from scheduler import save_schedule
save_schedule(schedule_df)
```

### verify_schedule(df_schedule, machines_df=None)
Verifies the schedule for correctness, respecting machine capacity.

**Parameters:**
- df_schedule (pandas.DataFrame): DataFrame with columns:
  - order_id
  - operation_seq
  - machine_id
  - start
  - end
  where start and end are Timestamps or strings in datetime format.
- machines_df (pandas.DataFrame, optional): DataFrame with machine_id and capacity columns.
  If not provided, capacity defaults to 1 for all machines.

**Returns:**
- tuple: (bool, list) where:
  - bool: True if all checks pass, False otherwise
  - list: Error messages if any (empty list if all checks pass)

**Checks:**
1. No machine exceeds its capacity (checks actual maximum concurrency at any point in time)
   - For each machine, counts active operations at each point in time
   - Flags error only if max concurrent > machine capacity
2. For each order, operation_seq order is respected (operations are in increasing order of operation_seq and start times are non-decreasing)

**Capacity Handling:**
- With capacity=1 (default): No two operations can overlap on the same machine
- With capacity=2: Up to 2 operations can overlap legitimately
- The check properly handles interleaved overlaps (e.g., A-B-C where A overlaps with B, B overlaps with C, but A does not overlap with C)

**Example:**
```python
from scheduler import verify_schedule
# Basic usage (capacity defaults to 1)
passed, errors = verify_schedule(schedule_df)

# With capacity information (Phase 1.5+)
passed, errors = verify_schedule(schedule_df, data['machines'])
if passed:
    print("Schedule is valid")
else:
    print("Schedule has errors:", errors)
```

## kpi.py

### compute_completion(df_schedule, orders_df=None)
Computes the completion time for each order by taking the maximum end time.

**Parameters:**
- df_schedule (pandas.DataFrame): DataFrame with columns:
  - order_id
  - operation_seq
  - machine_id
  - start
  - end
  where start and end are Timestamps or strings in datetime format.
- orders_df (pandas.DataFrame, optional): DataFrame with order information, must contain
  'order_id' and 'due_date' columns.

**Returns:**
- pandas.DataFrame:
  - If orders_df is None:
    DataFrame with columns: order_id, completion_time
  - If orders_df is provided:
    DataFrame with columns: order_id, completion_time, due_date, delay_hours
    where delay_hours is a float representing the delay in hours
    (completion_time - due_date).

**Example:**
```python
from kpi import compute_completion
# Without delay calculation
completion_df = compute_completion(schedule_df)
# With delay calculation
delay_df = compute_completion(schedule_df, orders_df)
```

### compute_kpi_metrics(df_schedule, orders_df)
Computes key performance indicators. **Phase 2** version includes additional metrics.

**Parameters:**
- df_schedule (pandas.DataFrame): DataFrame with columns:
  - order_id
  - operation_seq
  - machine_id
  - start
  - end
  - is_primary (Phase 2)
- orders_df (pandas.DataFrame): DataFrame with order information, must contain
  'order_id' and 'due_date' columns.

**Returns:**
- dict: Dictionary containing KPI metrics:
  - total_orders: total number of orders
  - on_time_orders: number of orders completed on or before due date
  - late_orders: number of orders completed after due date
  - avg_delay: average delay in hours (negative = early, positive = late)
  - max_delay: maximum delay in hours
  - **avg_utilization** (Phase 2): Machine utilization %
  - **alt_machine_usage_pct** (Phase 2): % jobs using non-primary machines
  - **avg_release_delay** (Phase 2): Avg delay from release constraints (hours)

**Example:**
```python
from kpi import compute_kpi_metrics
kpi_metrics = compute_kpi_metrics(schedule_df, data['orders'])
print(f"Total orders: {kpi_metrics['total_orders']}")
print(f"Average delay: {kpi_metrics['avg_delay']:.2f} hours")
print(f"Alt machine usage: {kpi_metrics['alt_machine_usage_pct']:.1f}%")
```

### compute_machine_utilization(df_schedule, orders_df=None) [Phase 2]
Calculates average machine utilization across all machines.

**Parameters:**
- df_schedule (pandas.DataFrame): DataFrame with machine_id, start, end
- orders_df: Ignored (for API compatibility)

**Returns:**
- float: Average utilization as a percentage (0-100)

**Example:**
```python
from kpi import compute_machine_utilization
util = compute_machine_utilization(schedule_df)
print(f"Avg utilization: {util:.1f}%")
```

### compute_alt_machine_usage(df_schedule) [Phase 2]
Calculates percentage of jobs that did not use their primary machine.

**Parameters:**
- df_schedule (pandas.DataFrame): DataFrame with is_primary column

**Returns:**
- float: Percentage of jobs using alternate machines (0-100)

**Example:**
```python
from kpi import compute_alt_machine_usage
alt_pct = compute_alt_machine_usage(schedule_df)
print(f"Alternate machine usage: {alt_pct:.1f}%")
```

### compute_release_delay(df_schedule, orders_df) [Phase 2]
Calculates average delay due to release constraints.

**Parameters:**
- df_schedule (pandas.DataFrame): DataFrame with order_id, operation_seq, start
- orders_df (pandas.DataFrame): DataFrame with order_id, release_time

**Returns:**
- float: Average release delay in hours

**Example:**
```python
from kpi import compute_release_delay
delay = compute_release_delay(schedule_df, orders_df)
print(f"Avg release delay: {delay:.1f} hours")
```

## main.py

### main()
Orchestrates the complete workflow as requested.

**Steps Executed:**
1. load_data()
2. Run validations (validate_foreign_keys, validate_nulls)
3. build_jobs()
4. initialize machines (initialize_machine_state)
5. run_scheduler()
6. save_schedule()
7. compute KPIs (compute_kpi_metrics)
8. plot_gantt()

**Returns:** int (exit code: 0 for success, 1 for error)

**Example:**
```bash
python main.py
```

**Output Files:**
- schedule.csv: The complete schedule
- gantt_chart.png: Gantt chart visualization of the schedule

**Example:**
```python
from main import main
exit_code = main()
```

## Usage Examples

### Basic Usage
```python
# Load data
from data_loader import load_data
data = load_data()

# Validate data
from validator import validate_foreign_keys, validate_nulls
validate_foreign_keys(data)
validate_nulls(data)

# Build jobs
from job_builder import build_jobs, initialize_machine_state
jobs_df = build_jobs(data)
machine_state = initialize_machine_state(data)

# Run scheduler
from scheduler import run_scheduler, save_schedule
schedule_df = run_scheduler(data)
save_schedule(schedule_df)

# Compute KPIs
from kpi import compute_kpi_metrics
kpi_metrics = compute_kpi_metrics(schedule_df, data['orders'])

# Or use main.py to run everything
from main import main
main()
```

### Custom Workflow
```python
# Load and validate data
from data_loader import load_data
from validator import validate_foreign_keys, validate_nulls
data = load_data()
validate_foreign_keys(data)
validate_nulls(data)

# Build jobs
from job_builder import build_jobs
jobs_df = build_jobs(data)

# Initialize machines
from job_builder import initialize_machine_state
machine_state = initialize_machine_state(data)

# Run custom scheduling logic (if needed)
# ... custom code here ...

# Use standard scheduler for comparison
from scheduler import run_scheduler
schedule_df = run_scheduler(data)

# Calculate custom metrics
# ... custom KPI code here ...

# Or use standard KPI functions
from kpi import compute_kpi_metrics
kpi_metrics = compute_kpi_metrics(schedule_df, data['orders'])
```