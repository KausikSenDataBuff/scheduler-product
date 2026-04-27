# Changelog

## [Unreleased]

## Version 1.5.1 - 2026-04-28
### Frontend-Backend Alignment

#### Bug Fixes
- **Backend `/upload` endpoint**: Now accepts optional Phase 1.5 files (machine_calendar, setup_matrix, sections, buffers) and returns `phase15_summary` in response
- **Frontend `script.js`**: Fixed to use `phase15_summary` key (was incorrectly expecting `phase15_data`)
- **Removed**: Redundant `simple_backend.py` file

#### Documentation
- **README.md**: Updated with clear "How to Run" instructions for both web interface and CLI
- **FILE_STRUCTURE.md**: Updated to remove deprecated `simple_backend.py` reference

---

## Version 1.5.0 - 2026-04-28
### Phase 1.5: Stabilize Engine

Added support for advanced scheduling constraints:

#### New Features
- **Parallel Capacity**: Machines can now process multiple operations concurrently
  - `get_earliest_slot()` finds earliest available slot respecting capacity limits
  - `machine_intervals` tracks active intervals per machine (not just single availability time)
  - `capacity` column added to machines.csv (default=1)

- **Machine Calendar**: Downtime-aware scheduling
  - `adjust_to_calendar()` shifts operations to available time windows
  - `machine_calendar.csv` defines available/unavailable periods per machine
  - Prevents scheduling during `is_available=0` periods

- **Setup Time**: Sequence-dependent changeover times
  - `build_setup_dict()` pre-indexes setup matrix for O(1) lookups
  - `get_setup_time()` returns transition time between products on same machine
  - `last_product` tracks product history per machine

- **Sections** (structure only): Machine grouping with section assignments
  - `section_id` column added to machines.csv
  - `sections.csv` defines sections with max_wip limits
  - Validation: all machines have valid section_id

- **Buffers/WIP Control**: Section-based work-in-progress limits
  - `buffers.csv` defines buffer capacity per section
  - `buffer_id` added to routing.csv
  - Operations delay when buffer capacity exceeded

- **Transfer Time**: Inter-operation gaps
  - `transfer_time_min` column added to routing.csv
  - Gap time added between consecutive operations

#### New Data Files
- `data/machine_calendar.csv` - Machine availability windows
- `data/setup_matrix.csv` - Product transition setup times (765K rows)
- `data/sections.csv` - Section definitions
- `data/buffers.csv` - Buffer capacity definitions

#### Modified Files
- `data/machines.csv` - Added `capacity` column (default=1)
- `data/routing.csv` - Added `buffer_id` and `transfer_time_min` columns
- `data_loader.py` - Loads optional files (calendar, setup_matrix, sections, buffers)
- `scheduler.py` - Added `get_earliest_slot()`, `adjust_to_calendar()`, `get_setup_time()`, `build_setup_dict()`

#### New Tests
- `tests/test_baseline.py` - Baseline schedule verification
- `tests/test_calendar.py` - Downtime violation check
- `tests/test_setup.py` - Setup time verification

#### Algorithm Changes
Before (v1.0):
```
machine_available[machine_id] = timestamp  # Single availability time
```

After (v1.5):
```
machine_intervals[machine_id] = [(start1, end1), ...]  # List of active intervals
machine_capacity[machine_id] = N  # Concurrent operation capacity
last_product[machine_id] = product_id  # For setup time calculation
```

#### Test Results
- 7609 operations scheduled across 34 machines
- 100% on-time delivery maintained
- No overlap violations
- No downtime violations

---

## Version 1.0.0 - 2026-04-19
### Added
- **data_loader.py**: Loads and parses CSV files from the 'data' folder
- **validator.py**: Provides data validation functions (foreign keys and null checks)
- **job_builder.py**: Handles job creation and machine state initialization
- **scheduler.py**: Implements the scheduling algorithm with schedule verification
- **kpi.py**: Computes completion times and key performance indicators
- **main.py**: Orchestrates the complete 8-step workflow
- **docs/**: Comprehensive documentation including:
  - README.md: Project overview and usage instructions
  - algorithm_details.md: Detailed explanation of the scheduling algorithm
  - api_reference.md: Complete API reference for all modules
  - example_usage.py: Demonstrates how to use all modules together

### Features
- Data loading with automatic datetime parsing for order_date and due_date
- Comprehensive data validation (foreign key relationships and null checks)
- Job building by joining orders with routing data
- Machine state initialization for tracking job assignments
- Due-date based scheduling algorithm that ensures:
  - Orders processed in due date order (earliest first)
  - Operations processed in operation_seq order per order
  - No overlapping operations on the same machine
  - Each operation starts only after the previous operation ends
  - current_time properly maintained per order
- Schedule saving with proper datetime formatting (YYYY-MM-DD HH:MM:SS)
- Schedule verification to ensure correctness
- KPI computation including:
  - Total orders
  - On-time orders (completed on or before due date)
  - Late orders (completed after due date)
  - Average delay (in hours)
  - Maximum delay (in hours)
- Gantt chart visualization of the schedule
- Complete workflow orchestration in main.py

### Files Created
- data_loader.py
- validator.py
- job_builder.py
- scheduler.py
- kpi.py
- main.py
- docs/README.md
- docs/algorithm_details.md
- docs/api_reference.md
- docs/example_usage.py
- docs/changelog.md

### Usage
```bash
# Run the complete workflow
python main.py

# Or run individual components for testing
python data_loader.py
python validator.py
python job_builder.py
python scheduler.py
python kpi.py
```

### Output Files
After running main.py:
- schedule.csv: Complete schedule with verified correctness
- gantt_chart.png: Visual representation of the schedule

### Verification
The scheduler includes a verify_schedule() function that confirms:
1. No machine has overlapping operations
2. For each order, operation_seq order is respected

Both checks pass for the generated schedule.