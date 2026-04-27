# Scheduler Product Documentation

## Overview

This project implements a production scheduling system that processes orders through a series of operations on various machines. The system consists of multiple Python modules that work together to load data, validate it, build job operations, schedule them based on due dates, and compute key performance indicators (KPIs).

## Module Descriptions

### 1. data_loader.py
Loads CSV files from the 'data' folder and returns a dictionary of pandas DataFrames.

**Files Loaded:**
- machines.csv: Contains machine information (machine_id, department, shift_start, shift_end)
- products.csv: Contains product information (product_id, family, complexity)
- routing.csv: Contains routing information (product_id, operation_seq, department, machine_id, proc_time_min)
- orders.csv: Contains order information (order_id, product_id, quantity, order_date, due_date, priority)

**Features:**
- Automatically parses datetime fields: order_date, due_date
- Returns DataFrames as a dictionary with keys: 'machines', 'products', 'routing', 'orders'

### 2. validator.py
Provides data validation functions to ensure data integrity.

**Functions:**
- `validate_foreign_keys(data)`: Checks that all product_id in orders exist in products and all machine_id in routing exist in machines
- `validate_nulls(data)`: Checks for null values in critical fields:
  - machine_id (in machines and routing DataFrames)
  - product_id (in products, routing, and orders DataFrames)
  - operation_seq (in routing DataFrame)
  - proc_time_min (in routing DataFrame)

Both functions raise ValueError with clear messages if validation fails, and pass silently for valid data.

### 3. job_builder.py
Handles job creation and machine state initialization.

**Functions:**
- `build_jobs(data)`: Joins orders with routing on product_id to create operation-level DataFrame with columns: order_id, product_id, operation_seq, machine_id, proc_time_min
- `initialize_machine_state(data)`: Returns a dictionary mapping each machine_id to an empty list: {machine_id: []}

### 4. scheduler.py
Implements the scheduling algorithm and provides schedule verification.

**Functions:**
- `run_scheduler(data)`: Implements the scheduling algorithm based on due dates:
  1. Sorts orders by due_date (ascending)
  2. For each order: sets current_time = order_date
  3. For each operation (sorted by operation_seq): 
     - start = max(current_time, machine availability)
     - end = start + proc_time (converted from minutes to timedelta)
  4. Updates machine schedule
  5. Stores result
  Returns DataFrame with columns: order_id, operation_seq, machine_id, start, end
  
- `save_schedule(df_schedule)`: Saves the schedule DataBus to 'schedule.csv' with proper datetime formatting (YYYY-MM-DD HH:MM:SS)
  
- `verify_schedule(df_schedule)`: Verifies the schedule for two conditions:
  1. No machine has overlapping operations
  2. For each order, operation_seq order is respected (operations are in increasing order of operation_seq and start times are non-decreasing)
  Returns tuple: (bool, list) where bool is True if all checks pass, False otherwise, and list contains error messages if any.

### 5. kpi.py
Computes completion times and key performance indicators.

**Functions:**
- `compute_completion(df_schedule, orders_df=None)`: 
  - Groups schedule DataFrame by order_id
  - Takes max(end) for each order to compute completion time
  - If orders_df is provided, merges with orders to compute delay = completion_time - due_date (in hours)
  - Returns DataFrame with order_id, completion_time, and optionally due_date, delay_hours
  
- `compute_kpi_metrics(df_schedule, orders_df)`: 
  - Computes key performance indicators:
    - total_orders: total number of orders
    - on_time_orders: number of orders completed on or before due date
    - late_orders: number of orders completed after due date
    - avg_delay: average delay in hours (negative = early, positive = late)
    - max_delay: maximum delay in hours

### 6. main.py
Orchestrates the complete workflow as requested:
1. load_data()
2. run validations
3. build_jobs()
4. initialize machines
5. run_scheduler()
6. save_schedule()
7. compute KPIs
8. plot_gantt()

## Data Flow

```
data_loader.py → validator.py → job_builder.py → scheduler.py → kpi.py
```

The main.py file orchestrates this flow and adds visualization capabilities.

## Usage

### Running the Complete Workflow
```bash
python main.py
```

This will:
1. Load and validate the data
2. Build job operations
3. Initialize machine states
4. Run the scheduling algorithm
5. Save the schedule to schedule.csv
6. Compute and display KPI metrics
7. Generate and save a Gantt chart visualization as gantt_chart.png

### Running Individual Components
Each module can be tested independently:
```bash
python data_loader.py   # Test data loading
python validator.py     # Test validation
python job_builder.py   # Test job building
python scheduler.py     # Test scheduling and verification
python kpi.py           # Test KPI computation
python main.py          # Run complete workflow
```

## Expected Output

When running main.py, you should see output similar to:
```
=== Starting Production Scheduling Workflow ===

1. Loading data...
   Loaded 4 DataFrames
   Orders: 1000 rows
   Machines: 34 rows
   Products: 150 rows
   Routing: 1133 rows

2. Running validations...
   All validations passed

3. Building jobs...
   Built 7609 job operations
   Columns: ['order_id', 'product_id', 'operation_seq', 'machine_id', 'proc_time_min']

4. Initializing machine state...
   Initialized state for 34 machines
   Example: ('MIX_M1', [])

5. Running scheduler...
   Scheduled 7609 operations
   Columns: ['order_id', 'operation_seq', 'machine_id', 'start', 'end']

6. Saving schedule...
   Schedule saved to schedule.csv

7. Computing KPIs...
   KPI Metrics:
     total_orders: 1000
     on_time_orders: 1000
     late_orders: 0
     avg_delay: -33.94 hours
     max_delay: -1.47 hours

8. Plotting Gantt chart...
   Gantt chart saved as 'gantt_chart.png'

=== Workflow Completed Successfully ===
```

## Output Files

After running main.py, the following files will be generated in the project directory:
- schedule.csv: The complete schedule with columns order_id, operation_seq, machine_id, start, end
- gantt_chart.png: A visualization of the schedule as a Gantt chart

## Verification

The scheduler.py module includes a verify_schedule() function that checks:
1. No machine has overlapping operations
2. For each order, operation_seq order is respected

These checks are automatically performed when running scheduler.py or main.py, and the results are displayed in the output.

## Requirements

- Python 3.x
- pandas
- matplotlib (for Gantt chart visualization)

Install requirements with:
```bash
pip install pandas matplotlib
```

## Notes

- The scheduling algorithm prioritizes orders by due_date (earliest first)
- For each order, operations are processed in operation_seq order
- Machine availability is tracked to prevent overlapping operations
- All datetime values are properly formatted in the output CSV
- The system handles edge cases such as missing data or invalid references through validation functions