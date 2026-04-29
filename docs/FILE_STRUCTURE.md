# Scheduler Product - File Structure

## Root Directory
- `backend_api.py` - Main FastAPI backend application
- `data_loader.py` - Data loading utilities (Phase 1.5: loads optional calendar/setup/sections/buffers)
- `job_builder.py` - Job building logic
- `kpi.py` - KPI calculation module
- `main.py` - Entry point (CLI mode)
- `scheduler.py` - Core scheduling algorithm (Phase 1.5: capacity/calendar/setup-aware)
- `validator.py` - Data validation logic
- `README.md` - Project overview and running instructions
- `.claude.json` - Claude Code configuration
- `CLAUDE.md` - Agent documentation

## Data Directory (`/data`)

### Core Files
- `machines_updated.csv` - Machine information (Phase 1.5+: capacity, section_id)
- `products.csv` - Product information
- `orders_phase2.csv` - Phase 2 orders with release_time, material_available_time
- `orders.csv` - Legacy order information

### Phase 2 Files
- `routing_alternate.csv` - Multi-machine routing (is_primary, efficiency columns)
  - Each operation can have multiple candidate machines
  - is_primary: 1 = primary machine, 0 = alternate
  - efficiency: Processing time multiplier

### Phase 1.5 Files
- `machine_calendar.csv` - Machine availability windows (machine_id, start_time, end_time, is_available)
- `setup_matrix.csv` - Product transition setup times (from_product, to_product, machine_id, setup_time_min)
- `sections.csv` - Section definitions (section_id, description, max_wip)
- `buffers.csv` - Buffer capacity (buffer_id, section_id, capacity)

## Frontend Directory (`/frontend`)
- `index.html` - Main dashboard with file upload, workflow controls, and Phase 2 features
- `style.css` - Styling for the web interface
- `script.js` - Frontend logic with Phase 2 KPI and jobs display support
  - `displayKPIs()`: Shows Phase 2 KPIs (avg_utilization, alt_machine_usage_pct, avg_release_delay)
  - `displayJobs()`: Handles Phase 2 `candidate_machines` format

## Documentation (`/docs`)
- `algorithm_details.md` - Scheduling algorithm details (Phase 2 updated)
- `api_reference.md` - API endpoint documentation
- `changelog.md` - Version history (Phase 2 added)
- `development-steps.md` - Development workflow
- `example_usage.py` - Example usage script
- `flow.png` - System flow diagram
- `frontend_plan.md` - Frontend development plan

## Tests (`/tests`)
- `test_baseline.py` - Baseline schedule verification
- `test_calendar.py` - Downtime violation check
- `test_setup.py` - Setup time verification
- `test_phase2.py` - Phase 2 integration tests (11 tests)
  - Release constraint logic, best machine selection, alternate vs primary usage, KPI validation
- `test_backend_direct.py` - Direct backend testing
- `test_frontend_integration.py` - Frontend-backend integration
- `test_integration.py` - Integration testing

## Instructions (`/instructions`)
- `phase-1.5.md` - Phase 1.5 implementation requirements
- `phase-2.md` - Phase 2 implementation requirements (alternate machines, release constraints)

## Test Data (`/test_data`)
- CSV files used for testing (machines.csv, products.csv, etc.)
- Generated schedule files from tests

## Test Outputs (`/test_outputs`)
- Generated charts and visualizations from testing

## Temporary Outputs (`/outputs`)
- Directory for runtime outputs

## Sessions (`/sessions`)
- Session storage directory

## Uploads (`/uploads`)
- Temporary file upload storage (auto-generated)

## Cache (`/__pycache__)
- Python bytecode cache
