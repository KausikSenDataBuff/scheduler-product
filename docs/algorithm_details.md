# Algorithm Details

## Scheduling Algorithm (Phase 1.5)

The scheduling algorithm implemented in `scheduler.py` follows these steps:

### 1. Order Prioritization
- Orders are sorted by `due_date` in ascending order (earliest due date first)
- This ensures that orders with earlier due dates are scheduled first

### 2. Machine State Tracking (Phase 1.5)
Each machine maintains multiple state variables:

```python
machine_intervals[machine_id] = [(start1, end1), (start2, end2), ...]  # Active intervals
machine_capacity[machine_id] = N  # Concurrent operation capacity (from machines.csv)
last_product[machine_id] = product_id  # For setup time calculation
```

### 3. Operation Scheduling
For each order (in due date order):
- Set `current_time = order_date` (the earliest time this order can start)
- For each operation in the order (sorted by `operation_seq`):
  - Adjust for calendar availability: `current_time = adjust_to_calendar(machine_id, current_time)`
  - Add setup time if transitioning products: `current_time += setup_time`
  - Find slot: `start_time, end_time = get_earliest_slot(intervals, capacity, current_time, duration)`
  - Adjust end for calendar: `end_time = adjust_to_calendar(machine_id, end_time)`
  - Record operation and update machine state

### 4. Key Scheduling Functions

#### get_earliest_slot()
Finds earliest slot that fits within capacity constraints:
```python
def get_earliest_slot(machine_intervals, machine_capacity, current_time, duration):
    # Count overlapping intervals at candidate position
    # If overlapping < capacity, slot is available
    # Otherwise, slide to when earliest overlapping op ends
```

#### adjust_to_calendar()
Shifts time to next available window if in downtime:
```python
def adjust_to_calendar(machine_id, time, calendar_df):
    # If time falls in is_available=0 window, return window end
    # Otherwise return original time
```

#### get_setup_time()
O(1) lookup from pre-indexed dict:
```python
def get_setup_time(machine_id, from_product, to_product, setup_dict):
    return setup_dict.get((machine_id, from_product, to_product), 0)
```

### 5. Key Properties
- **No overlapping operations beyond capacity**: By tracking all active intervals and checking overlap count, we enforce capacity limits.
- **Calendar-aware**: Operations never scheduled during `is_available=0` periods.
- **Setup time respected**: Product transitions incur setup time per `setup_matrix.csv`.
- **Operation sequence order respected**: For each order, we process operations in increasing `operation_seq` order.
- **Orders start at or after their order date**: By initializing `current_time = order_date` for each order.

## Data Validation

The validation functions in `validator.py` perform the following checks:

### Foreign Key Validation
- **Product ID validity**: Every `product_id` in the orders DataFrame must exist in the products DataFrame
- **Machine ID validity**: Every `machine_id` in the routing DataFrame must exist in the machines DataFrame

### Null Value Validation
The following columns are checked for null values:
- `machine_id` in machines and routing DataFrames
- `product_id` in products, routing, and orders DataFrames  
- `operation_seq` in routing DataFrame
- `proc_time_min` in routing DataFrame

## Job Building

The job building process in `job_builder.py` performs an inner join between:
- orders DataFrame (on `product_id`)
- routing DataFrame (on `product_id`)

This creates an operation-level view where each row represents a specific operation that needs to be performed for a specific order.

## KPI Computation

The KPI calculations in `kpi.py` work as follows:

### Completion Time
- For each order, find the maximum `end` time among all its operations
- This represents when the order is completely finished

### Delay Calculation
- Delay = completion_time - due_date
- Expressed in hours (using `.dt.total_seconds() / 3600.0`)
- Negative values indicate early completion
- Positive values indicate late completion
- Zero indicates on-time completion

### KPI Metrics
- `total_orders`: Count of unique order_ids
- `on_time_orders`: Count of orders where delay_hours <= 0 (completed on time or early)
- `late_orders`: Count of orders where delay_hours > 0 (completed late)
- `avg_delay`: Mean of delay_hours across all orders
- `max_delay`: Maximum delay_hours value (representing the latest completion relative to due date)

## Gantt Chart Visualization

The Gantt chart in `main.py` provides a visual representation of the schedule:

### Axes
- Y-axis: Machines (sorted alphabetically)
- X-axis: Time (datetime)

### Chart Elements
- Horizontal bars: Represent operations
  - Length: Duration of the operation
  - Position: Start time of the operation
  - Color: Unique color per order (using matplotlib's Set3 colormap)
  - Label: Order ID and operation sequence number (for operations longer than 30 minutes)
- Vertical dashed red lines: Due dates for each order (when orders_df is provided)
- Text labels: Due date labels at the top of the chart

### Features
- Grid lines for easier time reading
- Legend showing order-color mapping (limited to 20 orders for clarity)
- Proper axis labels and title
- Saved as high-resolution PNG (300 DPI)

## Verification Logic

The verification function in `scheduler.py` checks two critical properties:

### 1. No Machine Overlaps Beyond Capacity
For each machine:
- Collect all start and end times from operations on that machine
- Sort time points, handling half-open intervals (end at T doesn't overlap with start at T)
- Count active operations at each point in time
- Find maximum concurrent operations at any moment
- Flag error if max concurrent > machine capacity

**Example of correct capacity handling:**
```
Operations on BLD_M1 (capacity=2):
  A: 05:44-06:11
  B: 05:54-06:25  (overlaps with A at 05:54-06:11)
  C: 06:15-06:37  (overlaps with B at 06:15-06:25)
  D: 06:25-07:03  (overlaps with C at 06:25-06:37)

At 05:54-06:11: 2 operations (A+B) - OK for capacity=2
At 06:15-06:25: 2 operations (B+C) - OK for capacity=2
At 06:25-06:37: 2 operations (C+D) - OK for capacity=2

Max concurrent = 2, which equals capacity=2. No error.
```

### 2. Operation Sequence Order Respected
For each order:
- Sort operations by operation_seq
- Check that operation_seq values are strictly increasing
- Check that start times are non-decreasing when ordered by operation_seq
- If any operation starts before the previous one ends (when ordered by sequence), the sequence order is not respected

These verifications ensure that the scheduling algorithm produces a valid, feasible schedule.