# EPIC E1: Data Ingestion & Validation
🔹 Task E1-S1-T1: CSV Loader
Create a Python module `data_loader.py` that loads the following CSV files from the 'data' folder:
- machines.csv
- products.csv
- routing.csv
- orders.csv

Requirements:
- Use pandas
- Parse datetime fields: order_date, due_date
- Return DataFrames as a dictionary

Output:

data_loader.py

Success Criteria:

load_data() returns dict with 4 DataFrames
No crashes on valid CSVs

🔹 Task E1-S2-T3: Foreign Key Validation

Instruction:

Create `validator.py` with function validate_foreign_keys(data)

Checks:
- All product_id in orders exist in products
- All machine_id in routing exist in machines

Raise ValueError with clear message if invalid

Success Criteria:

Invalid data raises error
Valid data passes silently

🔹 Task E1-S2-T4: Routing Integrity

Instruction:

Add function validate_routing(data)

Checks:
- operation_seq starts at 1
- No missing sequence numbers per product
- No duplicates

Raise ValueError if violated

🔹 Task E1-S2-T5: Null Validation

Instruction:

Add function validate_nulls(data)

Check:
- No nulls in critical fields:
  machine_id, product_id, operation_seq, proc_time_min

Raise error if found

🧱 EPIC E2: Job Preparation
🔹 Task E2-S1-T1: Expand Orders

Instruction:

Create module `job_builder.py`

Function: build_jobs(data)

Logic:
- Join orders with routing on product_id
- Output operation-level DataFrame

Output:

DataFrame with:
order_id, product_id, operation_seq, machine_id, proc_time_min
🔹 Task E2-S1-T2: Sort Operations

Instruction:

Ensure output is sorted by:
- order_id
- operation_seq
🔹 Task E2-S2-T3: Machine State Init

Instruction:

Create function initialize_machine_state(data)

Return:
dict[machine_id] → empty list
🧱 EPIC E3: Scheduling Engine
🔹 Task E3-S2-T3: Slot Finder

Instruction:

Create function find_earliest_slot(bookings, ready_time, duration)

Rules:
- bookings = list of (start, end)
- Return earliest start time without overlap
- Handle gaps between bookings
- If no gap, schedule after last booking

Success Criteria:

No overlap with existing bookings
Always returns valid datetime
🔹 Task E3-S1-T2: Scheduling Loop

Instruction:

Create module `scheduler.py`

Function: run_scheduler(data)

Steps:
1. Sort orders by due_date
2. For each order:
    current_time = order_date

3. For each operation:
    start = max(current_time, machine availability)
    end = start + proc_time

4. Update machine schedule
5. Store result
🔹 Task E3-S3-T5: Precedence Enforcement

Instruction:

Ensure:
- Each operation starts only after previous operation ends
- Maintain current_time per order
🔹 Task E3-S4-T6: Build Output

Instruction:

Return DataFrame with:
order_id, operation_seq, machine_id, start, end
🧱 EPIC E4: Output & KPI
🔹 Task E4-S1-T1: Export Schedule

Instruction:

Create function save_schedule(df_schedule)

- Save as schedule.csv
- Ensure datetime formatting
🔹 Task E4-S2-T2: Completion Time

Instruction:

Create kpi.py

Function compute_completion(df_schedule)

- Group by order_id
- Take max(end)
🔹 Task E4-S2-T3: Delay Calculation

Instruction:

Merge completion with orders

Compute:
delay = completion_time - due_date (in hours)
🔹 Task E4-S2-T4: KPI Summary

Instruction:

Return:
- total_orders
- on_time_orders
- late_orders
- avg_delay
- max_delay
🧱 EPIC E5: Visualization
🔹 Task E5-S1-T2: Gantt Plot

Instruction:

Create visualization.py

Function plot_gantt(df_schedule)

- Y-axis = machine index
- X-axis = time
- Draw horizontal lines for operations
🔹 Task E5-S1-T3: Labels

Instruction:

Add:
- X label = Time
- Y label = Machine
- Title
🧱 EPIC E6: Main Runner
🔹 Task E6-S1: Orchestration

Instruction:

Create main.py

Steps:
1. load_data()
2. run validations
3. build_jobs()
4. initialize machines
5. run_scheduler()
6. save_schedule()
7. compute KPIs
8. plot_gantt()
🧪 EPIC E7: Testing
🔹 Task E7-S1-T5: No Overlap Test

Instruction:

Verify:
- No machine has overlapping operations
🔹 Task E7-S1-T6: Sequence Test

Instruction:

Verify:
- No machine has overlapping operations
- operation_seq order is respected per order
