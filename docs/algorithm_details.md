# Algorithm Details

## Scheduling Algorithm

The scheduling algorithm implemented in `scheduler.py` follows these steps:

### 1. Order Prioritization
- Orders are sorted by `due_date` in ascending order (earliest due date first)
- This ensures that orders with earlier due dates are scheduled first

### 2. Machine Availability Tracking
- Each machine's availability is tracked using a dictionary: `machine_available[machine_id] = timestamp`
- Initially, all machines are available at `pd.Timestamp.min` (effectively time zero)
- After scheduling an operation on a machine, the machine's availability is updated to the end time of that operation

### 3. Operation Scheduling
For each order (in due date order):
- Set `current_time = order_date` (the earliest time this order can start)
- For each operation in the order (sorted by `operation_seq`):
  - Get the machine's next available time: `avail_time = machine_available[machine_id]`
  - Calculate start time: `start_time = max(current_time, avail_time)`
    - This ensures the operation starts when both:
      1. The order is ready (`current_time`)
      2. The machine is available (`avail_time`)
  - Calculate end time: `end_time = start_time + proc_time_min` (converted to timedelta)
  - Record the scheduled operation
  - Update machine availability: `machine_available[machine_id] = end_time`
  - Update current_time for next operation: `current_time = end_time`

### 4. Key Properties
- **No overlapping operations on the same machine**: By tracking machine availability and updating it after each operation, we ensure that no two operations on the same machine overlap in time.
- **Operation sequence order respected**: For each order, we process operations in increasing `operation_seq` order, and set `current_time` to the end time of the previous operation, ensuring that each operation starts after the previous one ends.
- **Orders start at or after their order date**: By initializing `current_time = order_date` for each order, we ensure that no operation in an order starts before the order date.

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

### 1. No Machine Overlaps
For each machine:
- Sort operations by start time
- Check that each operation's start time is >= previous operation's end time
- If any operation starts before the previous one ends, there's an overlap

### 2. Operation Sequence Order Respected
For each order:
- Sort operations by operation_seq
- Check that operation_seq values are strictly increasing
- Check that start times are non-decreasing when ordered by operation_seq
- If any operation starts before the previous one ends (when ordered by sequence), the sequence order is not respected

These verifications ensure that the scheduling algorithm produces a valid, feasible schedule.