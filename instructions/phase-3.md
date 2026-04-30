🧠 CLAUDE INSTRUCTIONS — PHASE 3 (BOM + MULTI-LEVEL ORDERS)
🎯 OBJECTIVE

Extend scheduler from flat orders → hierarchical production using:

BOM (multi-level)
Order explosion
Parent-child dependencies
Precedence-constrained scheduling
1. 📁 NEW DATA MODELS
1.1 bom.csv
parent_product,child_product,quantity
1.2 orders_multilevel.csv

Extend Phase 2 schema:

order_id,product_id,quantity,order_date,due_date,
release_time,material_available_time,penalty_per_hour,
level,parent_order_id
1.3 order_links.csv
parent_order_id,child_order_id
2. 🔧 BACKEND CHANGES
2.1 data_loader.py

ADD:

load_bom()
load_order_links()
load_orders_multilevel()

Ensure:

datetime parsing same as Phase 2
optional fallback to Phase 2 if files missing

RETURN:

{
  ...existing,
  "bom_df": df,
  "order_links_df": df,
  "orders_multi_df": df
}
2.2 validator.py

ADD:

validate_bom()
no self loops
no cycles (DFS or topo check)
all products exist
validate_order_links()
all order_ids exist
no cycles
validate_orders_multilevel()
level >= 0
parent_order_id valid or null
consistency with order_links

FAIL FAST on:

cyclic BOM
orphan child orders
2.3 job_builder.py

MODIFY:

Instead of:

orders + routing → jobs

DO:

orders_multilevel + routing → jobs

ADD per job:

parent_order_id
level
child_orders (list from order_links)

OUTPUT:

candidate_machines (unchanged)
+ dependency metadata
3. ⚙️ SCHEDULER CORE CHANGE (CRITICAL)
3.1 New Constraint

For each order:

start_time >= max(
    release_time,
    material_available_time,
    previous_operation_end,
    max(child_order_completion_times)
)
3.2 Implementation Steps
Step 1: Precompute dependency graph
order_children_map
order_parents_map
Step 2: Track completion
order_completion_time[order_id]
Step 3: Modify scheduling loop

Before scheduling first operation:

dependency_ready_time = max(
    order_completion_time[child]
    for child in children
) if children else 0

Then:

current_time = max(
    order_date,
    release_time,
    material_time,
    dependency_ready_time
)
3.3 Important
Child orders MUST be scheduled before parent
Use topological sort of orders

IF not sorted:
→ scheduling will violate dependencies

3.4 Topological Ordering

Apply Kahn’s algorithm on order_links

Fallback:

sort by level DESC (quick heuristic)
4. 📊 KPI EXTENSIONS

ADD in kpi.py:

4.1 dependency_delay
parent_start - max(child_completion)
4.2 critical_path_length

Longest chain per top-level order

4.3 component_service_level

% of child orders completed before parent need

4.4 WIP explosion factor
total_orders_multilevel / original_orders
5. 🧪 VALIDATION LOGIC (POST-SCHEDULE)

ADD in verify_schedule():

5.1 Dependency Check

For every link:

child_end <= parent_start
5.2 Level Consistency
child.level > parent.level

FAIL if violated

6. 🌐 FRONTEND CHANGES
6.1 Upload

ADD support:

bom.csv
order_links.csv
orders_multilevel.csv
6.2 Jobs View

DISPLAY:

level
parent_order_id
number of children
6.3 Gantt Enhancement

COLOR by:

level OR
top-level order group

OPTION:

collapse/expand hierarchy
6.4 Dependency Visualization (NEW PANEL)

Simple graph:

Parent → Children

Optional:

tree view
6.5 KPI Dashboard

ADD:

Dependency delay
Critical path
WIP explosion factor
7. ⚠️ EDGE CASES

HANDLE:

No BOM → fallback to Phase 2
Deep BOM (>5 levels) → warn
Circular BOM → hard fail
Missing child order → fail
Parallel child orders → allowed
8. 🧱 DESIGN PRINCIPLES
DO NOT break Phase 2 compatibility
Keep scheduler deterministic
Avoid recursive scheduling (use topo order)
Minimize changes to machine selection logic
9. 🚀 TEST CASES (MANDATORY)

CREATE:

test_bom_explosion.py
multi-level correctness
test_dependency_enforcement.py
parent never starts early
test_kpi_phase3.py
new KPI correctness
10. 📦 OUTPUT CHANGES

schedule.csv ADD:

level
parent_order_id
11. 🧠 IMPLEMENTATION ORDER (STRICT)
data_loader
validator
job_builder
scheduler (topo + constraint)
KPI
verify_schedule
frontend
🔚 FINAL NOTE

Phase 3 is not a feature add—it changes scheduling from:

linear sequencing → graph-constrained optimization

If implemented incorrectly:
→ you’ll get logically valid schedules that are physically impossible