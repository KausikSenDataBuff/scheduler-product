🧠 CLAUDE INSTRUCTIONS — Phase 2
⚙️ Context

You are extending an existing production scheduler with:

setup time ✔
calendar ✔
capacity ✔

Now add:

1. Alternate machines (multi-machine routing)
2. Release + material availability constraints

Do NOT rewrite system. Extend incrementally.

🔁 STEP 1 — Data Model Upgrade
Routing change (CRITICAL)
Replace assumption:
1 operation → 1 machine
With:
1 operation → multiple candidate machines
Input file change
routing_updated.csv → routing_alternate.csv

New columns:

product_id
operation_seq
machine_id
proc_time_min
is_primary
efficiency

👉 Multiple rows per (product_id, operation_seq)

Orders change
orders.csv → orders_phase2.csv

Add:

release_time
material_available_time
penalty_per_hour
Loader updates (data_loader.py)
Load:
data['routing_alt']
data['orders']
Parse datetime:
release_time
material_available_time
🔁 STEP 2 — Job Builder Changes
job_builder.py
OLD:
1 row per operation
NEW:
multiple machine options per operation
Modify build_jobs():

Output:

order_id
product_id
operation_seq
candidate_machines (list of dicts)

Example:

[
  {'machine_id': 'M1', 'proc_time': 10},
  {'machine_id': 'M2', 'proc_time': 12}
]
🔁 STEP 3 — Scheduler Changes (CORE)
scheduler.py
3.1 Enforce Release Constraint

Before scheduling first operation:

current_time = max(
    order['order_date'],
    order['release_time'],
    order['material_available_time']
)
3.2 Alternate Machine Selection

Replace:

machine_id = row['machine_id']

WITH:

best_machine = None
best_start = None
best_end = None

for option in candidate_machines:
    m = option['machine_id']
    proc_time = option['proc_time']

    start = get_earliest_slot(m, current_time, proc_time)
    end = start + proc_time

    if best_end is None or end < best_end:
        best_machine = m
        best_start = start
        best_end = end

Then:

assign(best_machine, best_start, best_end)
3.3 Maintain compatibility
setup logic ✔
calendar ✔
capacity ✔

All must still work per machine option.

🔁 STEP 4 — Validator Updates
validator.py

Add checks:

1. Routing validity
each (product_id, operation_seq) has ≥ 1 machine
2. Orders validity
release_time <= due_date
material_available_time <= due_date
3. Machine validity
all machine_ids in routing exist in machines
🔁 STEP 5 — KPI Updates
kpi.py
Add new metrics:
1. Machine utilization
utilization = busy_time / available_time
2. Alternate usage ratio
% jobs not using primary machine
3. Release delay impact
delay_due_to_release = start_time - release_time
Extend compute_kpi_metrics()

Add:

avg_utilization
alt_machine_usage_pct
avg_release_delay
🔁 STEP 6 — Frontend Changes

(Assuming basic UI / Gantt exists)

6.1 Gantt Chart
Add:
color by machine
tooltip:
machine_id
is_primary (Y/N)
6.2 Order View

Show:

order_id
release_time
material_available_time
actual_start
delay
6.3 Machine View

Show:

machine_id
utilization %
jobs processed
6.4 Toggle (simple)

Add control:

"Allow Alternate Machines" → ON/OFF

If OFF:

only consider is_primary == 1
🧪 STEP 7 — Tests
Test 1 — Alternate Machines
Create 2 machines:
M1 slow
M2 fast

Assert:

scheduler picks faster machine
Test 2 — Release Constraint
release_time > order_date

Assert:

start_time >= release_time
Test 3 — Combined
late release + alternate machine

Assert:

correct machine + respects release
⚠️ Implementation Rules
DO NOT break existing scheduler flow
Add helper functions:
select_best_machine()
apply_release_constraint()
Keep logic readable (no premature optimization)
🚀 Expected Outcome

After Phase 2:

Scheduler evolves from:
static assignment → dynamic decision engine

Now system can:

choose between machines
respect material readiness
produce realistic schedules