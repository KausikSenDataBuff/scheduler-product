# CLAUDE.md - Scheduler Product v2.1

## Project Overview
Production scheduler that processes orders through operations on machines. Phase 3.0 with support for multi-level orders, BOM dependencies, alternate machine routing, release/material constraints, plus Phase 1.5 features (parallel capacity, machine calendars, setup times).

## Entry Points

### backend_api.py (Web Interface)
FastAPI server serving the frontend UI. Endpoints:
- `POST /upload` - Upload CSV files (Phase 1.5 + Phase 2 + Phase 3 files)
- `POST /process/{session_id}` - Run scheduling workflow
- `GET /data/{session_id}/{data_type}` - Get jobs/schedule/KPI/verification data
- `GET /download/{session_id}/schedule` - Download schedule.csv

### main.py (CLI)
Command-line pipeline: load → validate → build jobs → schedule → save → KPIs → Gantt chart

## Quick Start
```bash
# Web interface (recommended)
python backend_api.py  # Then open http://localhost:8000

# Command line
python main.py  # Run full pipeline

# Run tests
python -m pytest tests/test_phase2.py -v  # Phase 2 tests
python tests/test_baseline.py             # Core schedule validity
```

## Core Modules

### scheduler.py (Main Logic)
**Key Functions:**
- `run_scheduler(data, jobs_df=None)` - Phase 2 scheduling with alternate machines & constraints
- `select_best_machine(candidates, ...)` - Pick fastest machine from candidates
- `apply_release_constraint(order_date, release_time, material_time)` - Enforce time constraints
- `get_earliest_slot(intervals, capacity, time, duration)` - Find slot respecting capacity
- `adjust_to_calendar(machine_id, time, calendar_df)` - Bypass downtime periods
- `get_setup_time(machine_id, from_product, to_product, setup_dict)` - O(1) setup lookup
- `build_setup_dict(setup_df)` - Pre-index setup matrix for fast lookups
- `verify_schedule(df, machines_df)` - Validate schedule correctness
- `save_schedule(df, path)` - Save to CSV

**Machine State (Phase 1.5+):**
```python
machine_intervals[machine_id] = [(start1, end1), ...]  # NOT single timestamp
machine_capacity[machine_id] = N  # Concurrent operation limit
last_product[machine_id] = product_id  # For setup calculation
```

### data_loader.py
Loads CSV files from `/data`:
- Core: `machines_updated.csv`, `products.csv`, `routing_updated.csv`, `orders.csv`
- Phase 1.5: `machine_calendar.csv`, `setup_matrix.csv`, `sections.csv`, `buffers.csv`
- Phase 2: `routing_alternate.csv`, `orders_phase2.csv`
- Phase 3: `orders_multilevel.csv`, `order_links.csv`, `bom.csv`

**Returns:** `dict[str, DataFrame]`

### job_builder.py
- `build_jobs(data)` - Join orders with routing_alt, output candidate_machines list
- `initialize_machine_state(data)` - Create empty machine state dict

### kpi.py
- `compute_completion(df_schedule, orders_df)` - Per-order completion times
- `compute_kpi_metrics(df_schedule, orders_df, ...)` - Phase 2/3 KPIs including utilization
- `compute_machine_utilization(df_schedule, orders_df)` - % machine utilization
- `compute_alt_machine_usage(df_schedule)` - % jobs using non-primary machines
- `compute_release_delay(df_schedule, orders_df)` - Avg delay from release constraints
- `compute_dependency_delay(df_schedule, order_links)` - Phase 3: parent vs child delay
- `compute_critical_path_length(...)` - Phase 3: longest chain
- `compute_component_service_level(...)` - Phase 3: % meeting parent need
- `compute_wip_explosion_factor(...)` - Phase 3: multilevel vs flat ratio

### validator.py
- `validate_foreign_keys(data)` - Ensures referential integrity
- `validate_nulls(data)` - Checks null values in critical fields
- `validate_routing_alternate(data)` - Phase 2 routing validation
- `validate_orders_phase2(data)` - Phase 2 orders validation
- `validate_bom(data)` - Phase 3: No self-loops, no cycles, products exist
- `validate_order_links(data)` - Phase 3: Order IDs exist, no cycles
- `validate_orders_multilevel(data)` - Phase 3: level >= 0, parent valid

## Data Files

### Core Data (`/data`)
| File | Phase | Description |
|------|-------|-------------|
| `machines_updated.csv` | 1.5+ | Machine info with capacity |
| `products.csv` | 1.0 | Product info |
| `routing_updated.csv` | 1.5 | Operation routing |
| `routing_alternate.csv` | **2.0** | Multi-machine routing |
| `orders.csv` | 1.0 | Legacy orders |
| `orders_phase2.csv` | **2.0** | Orders with release/material constraints |

### Phase 1.5 Data
| File | Description |
|------|-------------|
| `machine_calendar.csv` | Machine availability windows |
| `setup_matrix.csv` | Product transition setup times |
| `sections.csv` | Section definitions |
| `buffers.csv` | Buffer capacity per section |

### Phase 3 Data
| File | Description |
|------|-------------|
| `orders_multilevel.csv` | Orders with level, parent_order_id |
| `order_links.csv` | Parent-child order dependencies |
| `bom.csv` | Bill of Materials (parent→child) |

### routing_alternate.csv (Phase 2)
```
product_id,operation_seq,department,machine_id,proc_time_min,is_primary,efficiency
TYRE_0000,1,MIX,MIX_M1,10.0,1,1.0
TYRE_0000,1,MIX,BLD_M3,12.76,0,0.78  # Alternate machine
```
- Multiple rows per (product_id, operation_seq)
- `is_primary`: 1 = primary machine, 0 = alternate
- `efficiency`: Processing time multiplier

### orders_phase2.csv (Phase 2)
```
order_id,product_id,quantity,order_date,due_date,release_time,material_available_time,penalty_per_hour
ORD_00000,TYRE_0036,56,2026-01-07,2026-01-10,2026-01-08 12:00:00,2026-01-09 00:00:00,69
```
- `release_time`: Order released for scheduling
- `material_available_time`: Materials ready for production

## Phase 2 Features

### 1. Alternate Machine Routing
**Problem:** 1 operation can run on multiple machines.

**Solution:** `select_best_machine()` picks machine with earliest completion time.

```python
candidates = [
    {'machine_id': 'M1', 'proc_time': 10, 'is_primary': True, 'efficiency': 1.0},
    {'machine_id': 'M2', 'proc_time': 12, 'is_primary': False, 'efficiency': 0.8}
]
best_machine, start, end, is_primary = select_best_machine(candidates, ...)
```

### 2. Release + Material Constraints
**Problem:** Orders can't start until materials are available.

**Solution:** `apply_release_constraint()` enforces timing constraints.

```python
current_time = max(order_date, release_time, material_available_time)
```

## Scheduling Algorithm (Phase 2)

1. Sort jobs by `due_date` (ascending), then `order_id`, then `operation_seq`
2. Build jobs with `candidate_machines` per operation
3. Track `order_end_times[order_id]` - end time of last scheduled operation per order
4. For each job:
   - **First operation of order**: `current_time = max(order_date, release_time, material_available_time)`
   - **Subsequent operations**: `current_time = order_end_times[order_id]` (chain after previous op)
   - Select best machine from candidates (earliest end time)
   - Add setup time if product changed
   - `start, end = get_earliest_slot(...)`
   - Record and update machine state
   - `order_end_times[order_id] = end` (for next operation)

## Phase 2 KPIs

| Metric | Description |
|--------|-------------|
| `avg_utilization` | Machine busy time / available time (%) |
| `alt_machine_usage_pct` | % jobs using non-primary machines |
| `avg_release_delay` | Avg delay from release constraints (hrs) |

**Typical Phase 2 Results:**
- Alternate machine usage: ~70% (scheduler prefers efficient machines)
- Avg utilization: ~15%
- Avg release delay: ~36 hours

## Phase 3 Features

### 1. Multi-Level Orders
**Problem:** Orders have parent-child dependencies (child must complete before parent).

**Solution:** `topological_sort_orders()` ensures child-first scheduling order.

```python
# Kahn's algorithm for topological sort (child-first)
topo_order = topological_sort_orders(order_links_df, orders_df)
```

### 2. Dependency Constraints
**Problem:** Parent order can't start until all children complete.

**Solution:** `build_dependency_graph()` tracks `order_completion_time[order_id]`.

```python
dependency_ready_time = max(order_completion_time[child] for child in children)
current_time = max(constraint_time, dependency_ready_time)
```

### 3. BOM Validation
**Problem:** Bill of Materials may have cycles or invalid references.

**Solution:** `validate_bom()` uses DFS for cycle detection.

## Phase 3 KPIs

| Metric | Description |
|--------|-------------|
| `dependency_delay` | Avg parent_start - max(child_completion) (hrs) |
| `critical_path_length` | Longest chain per top-level order |
| `component_service_level` | % child orders meeting parent need |
| `wip_explosion_factor` | multi-level orders / original orders |

## Verification
`verify_schedule(df_schedule, machines_df=None)` checks:
1. **No overlaps beyond capacity**: Max concurrent ops at any point
2. operation_seq order respected per order
3. No operations in downtime periods
4. **Phase 3: Dependency check**: child_end <= parent_start for all links
5. **Phase 3: Level consistency**: child.level > parent.level for all links

## Tests
```bash
python -m pytest tests/test_phase2.py -v  # Phase 2 tests
python tests/test_baseline.py             # Core schedule validity
python tests/test_calendar.py            # No downtime violations
python tests/test_setup.py               # Setup time applied correctly
python -m pytest tests/test_kpi_phase3.py -v  # Phase 3 KPI tests
python -m pytest tests/test_bom_explosion.py -v  # BOM tests
```

## Key Metrics
- 7609 operations scheduled across 34 machines
- 1000 orders processed
- ~85% on-time delivery
- ~70% alternate machine usage (scheduler optimizes for speed)
- Avg delay: -77 hours (orders finish early)

## Common Issues
- **Slow setup lookup**: Always use `build_setup_dict()` first
- **Timestamp comparison**: Use pandas Timestamp for all time comparisons
- **Empty intervals**: `machine_intervals[machine_id]` starts as `[]`
- **Phase 2 data**: Use `routing_alternate.csv` and `orders_phase2.csv`
- **Phase 3 data**: Use `orders_multilevel.csv`, `order_links.csv` (optional `bom.csv`)

## File Naming Conventions
- `*_updated.csv` - Extended data with new columns
- `*_alternate.csv` - Phase 2 multi-machine routing
- `*_phase2.csv` - Phase 2 orders with constraints
- `machine_calendar.csv` - Calendar/availability data
- `setup_matrix.csv` - Setup transition times
- `orders_multilevel.csv` - Phase 3 multi-level orders
- `order_links.csv` - Phase 3 parent-child links
- `bom.csv` - Bill of Materials
