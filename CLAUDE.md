# CLAUDE.md - Scheduler Product v1.5

## Project Overview
Production scheduler that processes orders through operations on machines. Currently at Phase 1.5 with support for parallel capacity, machine calendars, setup times, sections, buffers, and transfer times.

## Entry Points

### backend_api.py (Web Interface)
FastAPI server serving the frontend UI. Endpoints:
- `POST /upload` - Upload CSV files (accepts optional Phase 1.5 files)
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
python tests/test_baseline.py  # Core schedule validity
python tests/test_calendar.py  # No downtime violations
python tests/test_setup.py      # Setup time applied correctly
```

## Core Modules

### scheduler.py (Main Logic)
**Key Functions:**
- `run_scheduler(data)` - Main scheduling entry point
- `get_earliest_slot(intervals, capacity, time, duration)` - Find slot respecting capacity
- `adjust_to_calendar(machine_id, time, calendar_df)` - Bypass downtime periods
- `get_setup_time(machine_id, from_product, to_product, setup_dict)` - O(1) setup lookup
- `build_setup_dict(setup_df)` - Pre-index setup matrix for fast lookups
- `verify_schedule(df, machines_df)` - Validate schedule correctness (capacity-aware)
- `save_schedule(df, path)` - Save to CSV

**Machine State (Phase 1.5):**
```python
machine_intervals[machine_id] = [(start1, end1), ...]  # NOT single timestamp
machine_capacity[machine_id] = N  # Concurrent operation limit
last_product[machine_id] = product_id  # For setup calculation
```

### data_loader.py
Loads CSV files from `/data`:
- Core: `machines.csv`, `products.csv`, `routing.csv`, `orders.csv`
- Phase 1.5: `machine_calendar.csv`, `setup_matrix.csv`, `sections.csv`, `buffers.csv`

**Returns:** `dict[str, DataFrame]`

### kpi.py
- `compute_completion(df_schedule, orders_df)` - Per-order completion times
- `compute_kpi_metrics(df_schedule, orders_df)` - KPI dictionary

### validator.py
- `validate_foreign_keys(data)` - Ensures referential integrity
- `validate_nulls(data)` - Checks for null values in critical fields, including capacity validation

### job_builder.py
- `build_jobs(data)` - Join orders with routing
- `initialize_machine_state(data)` - Create empty machine state dict

## Data Files

### machines.csv
```
machine_id,department,shift_start,shift_end,capacity
MIX_M1,MIX,08:00,20:00,1
```
- `capacity` defaults to 1 (Phase 1.5)

### machine_calendar.csv
```
machine_id,start_time,end_time,is_available
MIX_M1,2025-01-01 08:00,2025-01-01 16:00,1
MIX_M1,2025-01-01 12:00,2025-01-01 14:00,0  # Downtime
```
- `is_available=0` = unavailable period

### setup_matrix.csv
```
from_product,to_product,machine_id,setup_time_min
TYRE_0000,TYRE_0001,MIX_M1,17
```
- 765K rows; use `build_setup_dict()` for O(1) lookups

### sections.csv
```
section_id,description,max_wip
SEC_1,Section 1,15
```

### buffers.csv
```
buffer_id,section_id,capacity
BUF_SEC_1,SEC_1,11
```

## Scheduling Algorithm

1. Sort orders by `due_date` (ascending)
2. For each order:
   - `current_time = order_date`
   - For each operation (sorted by `operation_seq`):
     - `current_time = adjust_to_calendar(machine_id, current_time)`
     - Add setup time if product changed
     - `start, end = get_earliest_slot(machine_intervals, capacity, current_time, duration)`
     - `end = adjust_to_calendar(machine_id, end)`
     - Record and update `machine_intervals[machine_id]`
     - `last_product[machine_id] = current_product`
     - `current_time = end`

## Verification
`verify_schedule(df_schedule, machines_df=None)` checks:
1. **No overlaps beyond capacity**: For each machine, counts max concurrent operations at any point in time (respects capacity > 1)
2. operation_seq order respected per order
3. (Phase 1.5) No operations in downtime periods

**Note:** For capacity > 1, legitimate overlaps are allowed up to the capacity limit. The algorithm properly handles interleaved overlaps (e.g., A-B-C where A overlaps with B and B overlaps with C but A doesn't overlap with C).

## Tests
```bash
python tests/test_baseline.py  # Core schedule validity
python tests/test_calendar.py  # No downtime violations
python tests/test_setup.py      # Setup time applied correctly
```

## Key Metrics
- 7609 operations scheduled across 34 machines
- 1000 orders processed
- ~100% on-time delivery typical
- Avg delay: -100 to -130 hours (orders finish early relative to due dates)

## Common Issues
- **Slow setup lookup**: Always use `build_setup_dict()` first, don't iterate 765K rows
- **Timestamp comparison**: Use pandas Timestamp for all time comparisons
- **Empty intervals**: `machine_intervals[machine_id]` starts as `[]`, not single timestamp

## File Naming Conventions
- `*_updated.csv` - Extended data with new columns (alternate versions)
- `machine_calendar.csv` - Calendar/availability data
- `setup_matrix.csv` - Setup transition times

## TODO (Future Phases)
- Step 4: Section validation (structure only)
- Step 5: Buffer WIP enforcement
- Step 6: Transfer time gaps between operations
