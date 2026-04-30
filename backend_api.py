from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import os
import shutil
import uuid
from pathlib import Path

app = FastAPI(title="Scheduler Product API", description="API for the production scheduling system")

# Import backend modules
from data_loader import load_data
from validator import (
    validate_foreign_keys, validate_nulls,
    validate_routing_alternate, validate_orders_phase2,
    validate_bom, validate_order_links, validate_orders_multilevel
)
from job_builder import build_jobs, initialize_machine_state
from scheduler import run_scheduler, save_schedule, verify_schedule
from kpi import compute_kpi_metrics
import pandas as pd

# Create directories for storing uploaded files and sessions
UPLOAD_DIR = Path("uploads")
SESSION_DIR = Path("sessions")
UPLOAD_DIR.mkdir(exist_ok=True)
SESSION_DIR.mkdir(exist_ok=True)

# In-memory storage for session data (in production, use Redis or database)
sessions = {}

@app.post("/upload")
async def upload_files(
    machines: UploadFile = File(...),
    products: UploadFile = File(...),
    routing: UploadFile = File(...),
    orders: UploadFile = File(...),
    machine_calendar: UploadFile = File(None),
    setup_matrix: UploadFile = File(None),
    sections: UploadFile = File(None),
    buffers: UploadFile = File(None),
    orders_multilevel: UploadFile = File(None),
    order_links: UploadFile = File(None),
    bom: UploadFile = File(None)
):
    """
    Upload CSV files and validate them.
    Returns a session ID for subsequent operations.
    """
    # Create a unique session ID
    session_id = str(uuid.uuid4())
    session_upload_dir = UPLOAD_DIR / session_id
    session_upload_dir.mkdir(exist_ok=True)

    # Save required files
    file_mapping = {
        "machines": machines,
        "products": products,
        "routing_alternate": routing,
        "orders_phase2": orders
    }

    for name, file in file_mapping.items():
        file_path = session_upload_dir / f"{name}.csv"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    # Save optional Phase 1.5 files
    optional_mapping = {
        "machine_calendar": machine_calendar,
        "setup_matrix": setup_matrix,
        "sections": sections,
        "buffers": buffers
    }

    phase15_summary = {}
    for name, file in optional_mapping.items():
        if file:
            file_path = session_upload_dir / f"{name}.csv"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            phase15_summary[f"{name}_uploaded"] = True

    # Save optional Phase 3 files
    phase3_mapping = {
        "orders_multilevel": orders_multilevel,
        "order_links": order_links,
        "bom": bom
    }

    phase3_summary = {}
    for name, file in phase3_mapping.items():
        if file:
            file_path = session_upload_dir / f"{name}.csv"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            phase3_summary[f"{name}_uploaded"] = True

    # Load and validate data
    try:
        data = load_data(str(session_upload_dir))
        validate_foreign_keys(data)
        validate_nulls(data)

        # Phase 2 validation if Phase 2 data exists
        if 'routing_alt' in data:
            validate_routing_alternate(data)
        if 'orders' in data and 'release_time' in data['orders'].columns:
            validate_orders_phase2(data)

        # Phase 3 validation if Phase 3 data exists
        if 'bom' in data and data['bom'] is not None:
            validate_bom(data)
        if 'order_links' in data and data['order_links'] is not None:
            validate_order_links(data)
        if 'orders_multi' in data and data['orders_multi'] is not None:
            validate_orders_multilevel(data)

        validation_passed = True
        validation_message = "All validations passed"
    except ValueError as e:
        validation_passed = False
        validation_message = str(e)
        # Still store the data so user can see what went wrong
        data = load_data(str(session_upload_dir))

    # Build phase15_summary if Phase 1.5 data exists
    if 'machine_calendar' in data:
        # Calculate calendar availability
        cal = data['machine_calendar']
        if 'is_available' in cal.columns:
            available = cal[cal['is_available'] == 1]
            total = len(cal)
            phase15_summary['calendar_available'] = len(available) / total if total > 0 else 0
            phase15_summary['machines_with_calendar'] = cal['machine_id'].nunique()

    if 'setup_matrix' in data:
        phase15_summary['setup_transitions'] = len(data['setup_matrix'])

    if 'sections' in data:
        phase15_summary['sections_count'] = len(data['sections'])

    if 'buffers' in data:
        phase15_summary['buffers_count'] = len(data['buffers'])

    # Machine capacities
    if 'machines' in data and 'capacity' in data['machines'].columns:
        caps = data['machines'].groupby('department')['capacity'].first().to_dict()
        phase15_summary['machines_capacity'] = caps

    # Store session data
    sessions[session_id] = {
        "data": data,
        "upload_dir": str(session_upload_dir),
        "validation_passed": validation_passed,
        "validation_message": validation_message,
        "jobs_df": None,
        "machine_state": None,
        "schedule_df": None,
        "kpi_metrics": None,
        "verification_passed": None,
        "verification_errors": None
    }

    return {
        "session_id": session_id,
        "validation_passed": validation_passed,
        "validation_message": validation_message,
        "phase15_summary": phase15_summary if phase15_summary else None,
        "phase3_summary": phase3_summary if phase3_summary else None
    }

@app.post("/process/{session_id}")
async def process_workflow(session_id: str):
    """
    Process the complete workflow for a given session.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    if not session["validation_passed"]:
        raise HTTPException(status_code=400, detail="Data validation failed. Please fix the data and re-upload.")

    try:
        data = session["data"]
        session_upload_dir = Path(session["upload_dir"])

        # Build jobs
        jobs_df = build_jobs(data)
        session["jobs_df"] = jobs_df

        # Initialize machine state
        machine_state = initialize_machine_state(data)
        session["machine_state"] = machine_state

        # Run scheduler
        schedule_df = run_scheduler(data)
        session["schedule_df"] = schedule_df

        # Save schedule
        schedule_path = session_upload_dir / "schedule.csv"
        save_schedule(schedule_df, str(schedule_path))
        session["schedule_path"] = str(schedule_path)

        # Verify schedule
        passed, errors = verify_schedule(schedule_df, data['machines'])
        session["verification_passed"] = passed
        session["verification_errors"] = errors

        # Compute KPIs (Phase 3 aware)
        orders_df = data.get('orders_multi', data.get('orders'))
        original_orders_count = len(data.get('orders', orders_df)) if data.get('orders') is not None else len(orders_df)
        kpi_metrics = compute_kpi_metrics(
            schedule_df,
            orders_df,
            order_links_df=data.get('order_links'),
            orders_multi_df=data.get('orders_multi'),
            original_orders_count=original_orders_count
        )
        session["kpi_metrics"] = kpi_metrics

        return {"status": "completed"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.get("/status/{session_id}")
async def get_status(session_id: str):
    """
    Get the current status of a session.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    return {
        "session_id": session_id,
        "validation_passed": session["validation_passed"],
        "validation_message": session["validation_message"],
        "jobs_count": len(session["jobs_df"]) if session["jobs_df"] is not None else 0,
        "machine_count": len(session["machine_state"]) if session["machine_state"] is not None else 0,
        "schedule_count": len(session["schedule_df"]) if session["schedule_df"] is not None else 0,
        "verification_passed": session["verification_passed"],
        "kpi_metrics": session["kpi_metrics"]
    }

@app.get("/data/{session_id}/{data_type}")
async def get_data(session_id: str, data_type: str):
    """
    Get specific data for a session (jobs, schedule, etc.)
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if data_type == "jobs":
        if session["jobs_df"] is None:
            raise HTTPException(status_code=400, detail="Jobs data not available")
        return session["jobs_df"].to_dict(orient="records")

    elif data_type == "schedule":
        if session["schedule_df"] is None:
            raise HTTPException(status_code=400, detail="Schedule data not available")
        return session["schedule_df"].to_dict(orient="records")

    elif data_type == "kpi":
        if session["kpi_metrics"] is None:
            raise HTTPException(status_code=400, detail="KPI data not available")
        return session["kpi_metrics"]

    elif data_type == "verification":
        return {
            "passed": session["verification_passed"],
            "errors": session["verification_errors"]
        }

    else:
        raise HTTPException(status_code=400, detail=f"Unknown data type: {data_type}")

@app.get("/download/{session_id}/{file_type}")
async def download_file(session_id: str, file_type: str):
    """
    Download generated files (schedule.csv, etc.)
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if file_type == "schedule":
        if not session.get("schedule_path") or not os.path.exists(session["schedule_path"]):
            raise HTTPException(status_code=404, detail="Schedule file not found")
        return FileResponse(
            path=session["schedule_path"],
            filename="schedule.csv",
            media_type="text/csv"
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unknown file type: {file_type}")

# Mount static files for serving the frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)