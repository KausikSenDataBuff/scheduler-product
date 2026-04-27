# Changelog

## [Unreleased]
- Initial release of the Scheduler Product system

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