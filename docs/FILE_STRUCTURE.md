# Scheduler Product - File Structure

## Root Directory
- `backend_api.py` - Main FastAPI backend application
- `data_loader.py` - Data loading utilities
- `job_builder.py` - Job building logic
- `kpi.py` - KPI calculation module
- `main.py` - Entry point
- `scheduler.py` - Core scheduling algorithm
- `simple_backend.py` - Simplified backend version
- `validator.py` - Data validation logic
- `test_upload.py` - Upload testing script
- `README.md` - Project overview
- `.claude.json` - Claude Code configuration

## Data Directory (`/data`)
- `machines.csv` - Machine information
- `products.csv` - Product information  
- `routing.csv` - Routing information
- `orders.csv` - Order information

## Documentation (`/docs`)
- `algorithm_details.md` - Scheduling algorithm details
- `api_reference.md` - API endpoint documentation
- `changelog.md` - Version history
- `example_usage.py` - Example usage script
- `flow.png` - System flow diagram
- `frontend_plan.md` - Frontend development plan

## Frontend (`/frontend`)
- `index.html` - Main HTML interface
- `script.js` - JavaScript application logic
- `style.css` - Styling and responsive design

## Tests (`/tests`)
- `test_backend_direct.py` - Direct backend testing
- `test_frontend_integration.py` - Frontend-backend integration
- `test_integration.py` - Integration testing
- `test_integration.html` - Integration test HTML
- `test_frontend_workflow.html` - Frontend workflow test
- `frontend_test.html` - Basic frontend test
- `test_upload.py` - Upload simulation test

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

## Cache (`/__pycache__`)
- Python bytecode cache