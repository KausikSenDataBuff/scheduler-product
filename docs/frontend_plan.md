# Frontend Design Plan for Scheduler Product

## Overview
This plan outlines a simple web-based frontend for the existing Python scheduling system. The frontend will provide an intuitive interface for users to interact with the scheduling workflow without needing to use the command line or write Python code.

## Goals
1. Provide a user-friendly web interface for the scheduling system
2. Allow users to upload/input data files
3. Execute the scheduling workflow with visual feedback
4. Display results including schedules, KPIs, and visualizations
5. Maintain compatibility with the existing Python backend modules

## Technology Choices (Simple & Lightweight)
- **Backend API Layer**: FastAPI (minimal wrapper around existing Python modules)
- **Frontend**: Vanilla HTML/CSS/JavaScript (no build steps required)
- **Charting**: Chart.js (for interactive Gantt chart and KPI visualizations)
- **Communication**: RESTful JSON API over HTTP
- **Why these choices?**: 
  - Zero setup for frontend users (just open HTML file in browser)
  - FastAPI is easy to integrate with existing Python code
  - Chart.js provides good visualization without complexity
  - Avoids frontend build tools (Webpack, etc.) for simplicity

## System Architecture
```
[User Browser] 
     ↓ HTTP/JSON
[FastAPI Server] ←→ [Existing Python Modules]
     ↓          ↑
[Static Files] [data_loader.py, validator.py, etc.]
```

## Key Features to Implement

### 1. Main Dashboard Page
- File upload section for the 4 required CSV files
- Status indicators for each processing step
- "Run Workflow" button
- Real-time progress updates

### 2. Data Validation View
- Shows results from validate_foreign_keys() and validate_nulls()
- Displays any errors/warnings in a clear format
- Option to fix common issues or proceed anyway

### 3. Job Building View
- Displays the built jobs DataFrame (order_id, product_id, operation_seq, machine_id, proc_time_min)
- Summary statistics (number of jobs, unique orders, etc.)
- Basic filtering/sorting capabilities

### 4. Scheduling & Verification View
- Shows the generated schedule (first/last few rows)
- Visual Gantt chart using Chart.js
- Verification results (pass/fail with details if failed)
- Option to download schedule.csv

### 5. KPI Dashboard
- Displays all KPI metrics in a clear layout:
  - Total Orders
  - On-time Orders
  - Late Orders
  - Average Delay (with color coding: green for negative/early, red for positive/late)
  - Maximum Delay
- Additional charts: delay distribution, orders completed early/late/on-time

### 6. Results & Export Section
- Download buttons for:
  - schedule.csv
  - Gantt chart (as PNG)
  - KPI report (as JSON or CSV)
- Option to run the workflow again with different data

## Data Flow Implementation Plan

### Step 1: Create FastAPI Wrapper (backend_api.py)
```python
# This will be a thin layer exposing our existing functions as API endpoints
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
import pandas as pd
import os
from data_loader import load_data
from validator import validate_foreign_keys, validate_nulls
from job_builder import build_jobs, initialize_machine_state
from scheduler import run_scheduler, save_schedule, verify_schedule
from kpi import compute_kpi_metrics
import uuid

app = FastAPI()

# In-memory storage for current session data (simple approach)
sessions = {}

@app.post("/upload")
async def upload_files(
    machines: UploadFile = File(...),
    products: UploadFile = File(...),
    routing: UploadFile = File(...),
    orders: UploadFile = File(...)
):
    # Save uploaded files temporarily
    session_id = str(uuid.uuid4())
    session_dir = f"sessions/{session_id}"
    os.makedirs(session_dir, exist_ok=True)
    
    # Save each file
    for name, file in [("machines", machines), ("products", products), 
                       ("routing", routing), ("orders", orders)]:
        content = await file.read()
        with open(f"{session_dir}/{name}.csv", "wb") as f:
            f.write(content)
    
    # Load and validate data
    data = load_data(session_dir)  # Modified to accept directory path
    try:
        validate_foreign_keys(data)
        validate_nulls(data)
        validation_passed = True
        validation_message = "All validations passed"
    except ValueError as e:
        validation_passed = False
        validation_message = str(e)
    
    sessions[session_id] = {
        "data": data,
        "validation_passed": validation_passed,
        "validation_message": validation_message,
        "session_dir": session_dir
    }
    
    return {"session_id": session_id, "validation_passed": validation_passed, 
            "validation_message": validation_message}

@app.post("/process/{session_id}")
async def process_workflow(session_id: str):
    if session_id not in sessions:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    
    session = sessions[session_id]
    data = session["data"]
    
    # Process through the workflow
    jobs_df = build_jobs(data)
    machine_state = initialize_machine_state(data)
    schedule_df = run_scheduler(data)
    
    # Save schedule
    schedule_path = f"{session['session_dir']}/schedule.csv"
    save_schedule(schedule_df)  # This writes to schedule.csv in current dir - need to modify
    
    # Verify schedule
    passed, errors = verify_schedule(schedule_df)
    
    # Compute KPIs
    kpi_metrics = compute_kpi_metrics(schedule_df, data['orders'])
    
    # Generate Gantt chart data (for frontend rendering)
    # We'll send the raw data and let frontend render with Chart.js
    
    sessions[session_id].update({
        "jobs_df": jobs_df.to_dict('records'),
        "machine_state": machine_state,
        "schedule_df": schedule_df.to_dict('records'),
        "schedule_path": schedule_path,
        "verification_passed": passed,
        "verification_errors": errors,
        "kpi_metrics": kpi_metrics
    })
    
    return {"status": "completed"}

@app.get("/results/{session_id}")
async def get_results(session_id: str):
    if session_id not in sessions:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    
    session = sessions[session_id]
    return {
        "jobs_count": len(session.get("jobs_df", [])),
        "verification_passed": session.get("verification_passed", False),
        "verification_errors": session.get("verification_errors", []),
        "kpi_metrics": session.get("kpi_metrics", {}),
        # We'll send actual data for charts in a separate endpoint or include here
    }

# Additional endpoints for serving static files and chart data would go here
```

### Step 2: Create Frontend Files
- `index.html`: Main dashboard with file upload and workflow controls
- `style.css`: Simple styling for a clean, professional look
- `script.js`: Handles user interactions, API calls, and dynamic UI updates
- `chart_utils.js`: Helper functions for rendering charts with Chart.js

### Step 3: Key Frontend Components

#### File Upload Section
```html
<div class="upload-section">
    <h2>1. Upload Data Files</h2>
    <div class="file-group">
        <label>machines.csv:</label>
        <input type="file" id="machines-file" accept=".csv" required>
    </div>
    <!-- Repeat for products, routing, orders -->
    <button id="upload-btn">Upload and Validate</button>
</div>
```

#### Progress Tracker
```html
<div class="progress-tracker">
    <div class="step" id="step-validation">⬜ Validation</div>
    <div class="step" id="step-jobs">⬜ Job Building</div>
    <div class="step" id="step-scheduling">⬜ Scheduling</div>
    <div class="step" id="step-verification">⬜ Verification</div>
    <div class="step" id="step-kpi">⬜ KPI Calculation</div>
    <div class="step" id="step-chart">⬜ Visualization</div>
</div>
```

#### Results Display Areas
- Collapsible sections for each step's results
- Tables for tabular data (using simple HTML tables or a lightweight library)
- Chart containers for Canvas elements

### Step 4: Integration Points with Existing Code

The frontend will interact with the existing Python modules through the FastAPI wrapper:

1. **Data Loading**: Uses existing `load_data()` function (modified to accept directory path)
2. **Validation**: Directly calls `validate_foreign_keys()` and `validate_nulls()`
3. **Job Building**: Uses `build_jobs()` and `initialize_machine_state()`
4. **Scheduling**: Uses `run_scheduler()` 
5. **Verification**: Uses `verify_schedule()` (the function we just added)
6. **KPI Computation**: Uses `compute_kpi_metrics()`
7. **Saving**: Uses `save_schedule()` 
8. **Visualization**: Frontend renders charts using Chart.js with data from the scheduler

### Step 5: Detailed Implementation Steps

#### Phase 1: Setup and Basic API
1. Create `backend_api.py` with FastAPI endpoints for upload and basic processing
2. Modify `load_data()` in data_loader.py to accept an optional directory parameter
3. Test API endpoints with curl or Postman

#### Phase 2: Frontend Skeleton
1. Create `index.html` with basic layout and file upload
2. Create `style.css` for basic styling
3. Create `script.js` to handle file upload and API calls
4. Serve static files through FastAPI

#### Phase 3: Workflow Execution
1. Implement the "/process/{session_id}" endpoint
2. Update frontend to show progress through workflow steps
3. Handle asynchronous processing (show loading states)

#### Phase 4: Results Display
1. Create endpoints to retrieve jobs, schedule, KPIs
2. Build frontend components to display:
   - Jobs table
   - Schedule table (first/last N rows)
   - KPI metrics cards
   - Verification status
3. Implement Chart.js rendering for Gantt chart and KPI visualizations

#### Phase 5: Polish and Export
1. Add file download capabilities (schedule.csv, KPI report)
2. Improve error handling and user feedback
3. Add responsive design for mobile/tablet viewing
4. Test with various data sets

## Security and Deployment Considerations

### For Simple Local Use (Recommended Initial Approach)
- Run the FastAPI server locally: `uvicorn backend_api:app --reload`
- Open `http://localhost:8000` in browser
- No authentication needed for personal/local use

### For Shared/Production Use (Future Enhancement)
- Add basic authentication (username/password)
- Implement file upload validation (size limits, CSV format checking)
- Add session cleanup (delete old session files)
- Use HTTPS in production
- Consider rate limiting

## Future Enhancements (Beyond Simple Frontend)
1. User accounts and project saving
2. Advanced scheduling algorithms (priority-based, resource-constrained)
3. Customizable Gantt chart appearance
4. Export to multiple formats (PDF, Excel)
5. Undo/redo functionality for manual schedule adjustments
6. Real-time collaboration features
7. Mobile app version

## Success Criteria for Simple Frontend
- [ ] User can upload all 4 CSV files through a web interface
- [ ] User can initiate the complete workflow with one button
- [ ] User sees clear progress indicators throughout the process
- [ ] User can view results including:
  - Validation status
  - Job count and sample data
  - Schedule verification status
  - KPI metrics with visualizations
  - Interactive Gantt chart
- [ ] User can download the schedule.csv and KPI report
- [ ] Frontend works in modern browsers (Chrome, Firefox, Safari, Edge)
- [ ] No Python knowledge required to operate the frontend
- [ ] Error messages are user-friendly and actionable

## Estimated Effort
- Backend API wrapper: 2-4 hours
- Frontend HTML/CSS/JS: 4-6 hours
- Integration and testing: 2-3 hours
- Documentation and polish: 1-2 hours
- **Total**: ~9-15 hours for a functional simple frontend

This plan provides a path to a simple, usable frontend that leverages all the work we've already done on the backend while keeping the frontend technology choices minimal and accessible.