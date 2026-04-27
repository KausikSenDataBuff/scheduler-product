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
- `machines.csv` - Machine information (Phase 1.5: added `capacity`, `section_id` columns)
- `products.csv` - Product information
- `routing.csv` - Routing information (Phase 1.5: added `buffer_id`, `transfer_time_min` columns)
- `orders.csv` - Order information

### Phase 1.5 Files
- `machine_calendar.csv` - Machine availability windows (machine_id, start_time, end_time, is_available)
- `setup_matrix.csv` - Product transition setup times (765K rows: from_product, to_product, machine_id, setup_time_min)
- `sections.csv` - Section definitions (section_id, description, max_wip)
- `buffers.csv` - Buffer capacity (buffer_id, section_id, capacity)

### Alternative/Updated Files
- `machines_updated.csv` - Extended machine data with capacity/section_id
- `routing_updated.csv` - Extended routing with buffer_id/transfer_time_min

## Documentation (`/docs`)
- `algorithm_details.md` - Scheduling algorithm details (Phase 1.5 updated)
- `api_reference.md` - API endpoint documentation
- `changelog.md` - Version history (Phase 1.5 added)
- `development-steps.md` - Development workflow
- `example_usage.py` - Example usage script
- `flow.png` - System flow diagram
- `frontend_plan.md` - Frontend development plan

## Tests (`/tests`)
- `test_baseline.py` - Baseline schedule verification (Phase 1.5)
- `test_calendar.py` - Downtime violation check (Phase 1.5)
- `test_setup.py` - Setup time verification (Phase 1.5)
- `test_backend_direct.py` - Direct backend testing
- `test_frontend_integration.py` - Frontend-backend integration
- `test_integration.py` - Integration testing
- `test_integration.html` - Integration test HTML
- `test_frontend_workflow.html` - Frontend workflow test
- `frontend_test.html` - Basic frontend test
- `test_upload.py` - Upload simulation test

## Instructions (`/instructions`)
- `phase-1.5.md` - Phase 1.5 implementation requirements

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
