from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import os
import shutil
import uuid
from pathlib import Path
from data_loader import load_data
from validator import validate_foreign_keys, validate_nulls
from job_builder import build_jobs, initialize_machine_state
from scheduler import run_scheduler, save_schedule, verify_schedule
from kpi import compute_kpi_metrics
import json

app = FastAPI(title="Scheduler Product API", description="API for the production scheduling system")

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
    orders: UploadFile = File(...)
):
    """
    Upload the four required CSV files and validate them.
    Returns a session ID for subsequent operations.
    """
    # Create a unique session ID
    session_id = str(uuid.uuid4())
    session_upload_dir = UPLOAD_DIR / session_id
    session_upload_dir.mkdir(exist_ok=True)

    # Save uploaded files
    file_mapping = {
        "machines": machines,
        "products": products,
        "routing": routing,
        "orders": orders
    }

    for name, file in file_mapping.items():
        file_path = session_upload_dir / f"{name}.csv"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    # Load and validate data
    try:
        data = load_data(str(session_upload_dir))
        validate_foreign_keys(data)
        validate_nulls(data)
        validation_passed = True
        validation_message = "All validations passed"
    except ValueError as e:
        validation_passed = False
        validation_message = str(e)
        # Still store the data so user can see what went wrong
        data = load_data(str(session_upload_dir))

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
        "validation_message": validation_message
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
        print(f"Saving schedule to: {schedule_path}")
        print(f"Session upload dir: {session_upload_dir}")
        print(f"Session upload dir exists: {session_upload_dir.exists()}")
        save_schedule(schedule_df, schedule_path)
        session["schedule_path"] = str(schedule_path)
        print(f"Schedule saved. File exists: {schedule_path.exists()}")
        if schedule_path.exists():
            print(f"Schedule file size: {schedule_path.stat().st_size} bytes")

        # Verify schedule
        passed, errors = verify_schedule(schedule_df)
        session["verification_passed"] = passed
        session["verification_errors"] = errors

        # Compute KPIs
        kpi_metrics = compute_kpi_metrics(schedule_df, data['orders'])
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