🧠 CLAUDE INSTRUCTIONS — Phase 1.5 (Stabilize Engine)
⚙️ Context

You are modifying an existing production scheduler with modules:

data_loader.py
validator.py
job_builder.py
scheduler.py
kpi.py

Current scheduler:

single-capacity machines
no setup times
no calendars
no WIP constraints

Goal: incrementally add Phase 1.5 features without breaking baseline behavior.

🔁 STEP 0 — Baseline Lock
Task
Run main.py
Save:
schedule.csv
KPI output
Add test
Create tests/test_baseline.py
Assert:
assert verify_schedule(df_schedule)[0] == True
🧩 STEP 1 — Parallel Capacity
Input changes

machines.csv → add column

capacity (int, default=1)
Code changes
scheduler.py
Replace machine state:
machine_state = {machine_id: []}

WITH:

machine_state = {machine_id: []}  # list of active intervals
machine_capacity = {machine_id: capacity}
Modify availability logic:
def get_earliest_slot(machine_id, current_time, duration):
    # allow up to capacity overlaps
Test
Add test:
# no more than capacity overlaps per machine
Re-run baseline → ensure no regression when capacity=1
🧩 STEP 2 — Machine Calendar
New file

machine_calendar.csv

machine_id, start_time, end_time, is_available
Input loader
data_loader.py
Load machine_calendar.csv
Code changes
scheduler.py
Add:
def adjust_to_calendar(machine_id, start_time):
    # shift to next available slot
Modify scheduling:
start = adjust_to_calendar(machine_id, start)
end = adjust_to_calendar(machine_id, end)
Validator
Add:
calendar entries exist for all machines
Test
Create downtime scenario
Assert:
no operation scheduled during is_available=0
🧩 STEP 3 — Setup Time
New file

setup_matrix.csv

machine_id, from_product, to_product, setup_time_min
Input loader
Load setup matrix
Code changes
scheduler.py
Track last product per machine:
last_product = {machine_id: None}
Before scheduling:
setup_time = lookup(machine_id, last_product, current_product)
start += setup_time
Update:
last_product[machine_id] = current_product
Test
Same product sequence → setup = 0
Different product → setup added
🧩 STEP 4 — Sections
Input changes

machines.csv → add

section_id
New file

sections.csv

section_id, max_wip
Loader
Load sections
Code changes
No scheduling logic yet (structure only)
Test
Validate:
all machines have valid section_id
🧩 STEP 5 — Buffers (WIP Control)
New file

buffers.csv

buffer_id, section_id, capacity
routing.csv → add
buffer_id
Loader
Load buffers
Code changes
scheduler.py
Track buffer state:
buffer_load = {buffer_id: 0}
After operation:
if buffer full:
    delay next operation
else:
    buffer_load += 1
On next operation start:
buffer_load -= 1
Test
Create small buffer capacity
Assert:
operations get delayed when buffer full
🧩 STEP 6 — Transfer Time
routing.csv → add
transfer_time_min
Code changes
scheduler.py
After each operation:
current_time += transfer_time
Test
Assert gap between operations ≥ transfer_time
🧪 FINAL INTEGRATION TEST
Run full pipeline
Validate:
verify_schedule(df)[0] == True
Add assertions
No overlap beyond capacity
No scheduling during downtime
Setup time respected
Buffer limits respected
⚠️ Implementation Rules
Do NOT rewrite scheduler completely
Extend existing logic incrementally
Keep all new logic modular:
get_earliest_slot()
adjust_to_calendar()
get_setup_time()
check_buffer()
🚀 Expected Outcome

After Phase 1.5:

multi-capacity machines
calendar-aware scheduling
setup-aware sequencing
basic flow constraints (buffers)

System evolves from:

deterministic scheduler → constrained scheduling engine