# Algorithm Details

## Scheduling Algorithm (Phase 2)

The Phase 2 scheduling algorithm in `scheduler.py` extends Phase 1.5 with alternate machine routing and release constraints.

### Phase 2 Key Changes

1. **Alternate Machine Selection**: Each operation has multiple candidate machines. The scheduler picks the one with earliest completion time.
2. **Release + Material Constraints**: Orders can't start until `release_time` and `material_available_time` are satisfied.

### 1. Order Prioritization
- Orders are sorted by `due_date` in ascending order (earliest due date first)

### 2. Machine State Tracking (Phase 1.5+)
Each machine maintains:
```python
machine_intervals[machine_id] = [(start1, end1), (start2, end2), ...]  # Active intervals
machine_capacity[machine_id] = N  # Concurrent operation capacity
last_product[machine_id] = product_id  # For setup time calculation
```

### 3. Release Constraint (Phase 2)
Before scheduling, compute earliest valid start time:
```python
current_time = max(order_date, release_time, material_available_time)
```

### 4. Operation Scheduling with Candidate Machines (Phase 2)
For each order (in due date order):
- Set `current_time = max(order_date, release_time, material_time)` (Phase 2)
- For each operation (sorted by `operation_seq`):
  - Build `candidate_machines` list from routing_alt
  - Call `select_best_machine()` to pick earliest-finishing machine
  - Adjust for calendar availability
  - Add setup time if transitioning products
  - Find slot with `get_earliest_slot()`
  - Adjust end for calendar
  - Record operation with `is_primary` flag

### 5. Key Scheduling Functions (Phase 2)

#### select_best_machine() [NEW]
```python
def select_best_machine(candidate_machines, machine_intervals, machine_capacity,
                       current_time, setup_dict, last_product, calendar_df):
    best_machine = None
    best_end = None
    for option in candidate_machines:
        m = option['machine_id']
        proc_time = int(option['proc_time'])
        start = get_earliest_slot(machine_intervals[m], machine_capacity[m], current_time, proc_time)
        end = start + pd.Timedelta(minutes=proc_time)
        if best_end is None or end < best_end:
            best_machine = m
            best_start = start
            best_end = end
    return best_machine, best_start, best_end, option['is_primary']
```

#### apply_release_constraint() [NEW]
```python
def apply_release_constraint(order_date, release_time, material_available_time):
    return max(order_date, release_time, material_available_time)
```

---

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

### Phase 2 KPI Metrics
- `avg_utilization`: (total busy hours) / (num_machines * available_time) * 100
- `alt_machine_usage_pct`: (jobs where is_primary=False) / total jobs * 100
- `avg_release_delay`: Mean of (first_op_start - release_time) for constrained orders

**Typical Phase 2 Results:**
- Alternate machine usage: ~70% (scheduler optimizes for fastest completion)
- Machine utilization: ~15%
- Average release delay: ~36 hours

### Frontend KPI Display
The frontend (`frontend/script.js`) displays Phase 2 KPIs in a separate section:
- `avg_utilization`: Shown with ⚡ icon in blue
- `alt_machine_usage_pct`: Shown with 🔀 icon in purple
- `avg_release_delay`: Shown with 📦 icon in orange

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