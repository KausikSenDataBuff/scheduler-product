# Scheduler Product v1.5

A production scheduling system that processes orders through operations on machines, with support for parallel capacity, machine calendars, setup times, and WIP control.

## Features

### Phase 1.5 Features
- **Parallel Capacity**: Machines can process multiple concurrent operations
- **Machine Calendar**: Downtime-aware scheduling (prevents scheduling during unavailable periods)
- **Setup Time**: Product transition times between operations on same machine
- **Sections**: Machine grouping with WIP limits
- **Buffers**: Section-based work-in-progress control
- **Transfer Time**: Gap time between consecutive operations

### Core Features
- Due-date based scheduling (earliest due date first)
- Operation sequence enforcement per order
- No overlapping operations on same machine (respecting capacity)
- Schedule verification
- KPI computation (on-time delivery, delay metrics)
- Gantt chart visualization

## Installation

```bash
pip install pandas matplotlib fastapi uvicorn python-multipart
```

## How to Run

### Option 1: Web Interface (Recommended)

1. **Start the backend server:**
   ```bash
   python backend_api.py
   ```

2. **Open your browser:**
   Navigate to `http://localhost:8000`

3. **Upload your data files:**
   - Required: `machines.csv`, `products.csv`, `routing.csv`, `orders.csv`
   - Optional: `machine_calendar.csv`, `setup_matrix.csv`, `sections.csv`, `buffers.csv`

### Option 2: Command Line

```bash
python main.py
```

### Run Tests

```bash
python tests/test_baseline.py
python tests/test_calendar.py
python tests/test_setup.py
```

## Data Files

### Core Data (`/data`)
| File | Description |
|------|-------------|
| `machines.csv` | Machine info (id, department, shift, capacity) |
| `products.csv` | Product info |
| `routing.csv` | Operation routing (product → machine → time) |
| `orders.csv` | Order info (product, quantities, dates) |

### Phase 1.5 Data
| File | Description |
|------|-------------|
| `machine_calendar.csv` | Machine availability windows |
| `setup_matrix.csv` | Product transition setup times |
| `sections.csv` | Section definitions |
| `buffers.csv` | Buffer capacity per section |

## Output
- `schedule.csv` - Scheduled operations
- `gantt_chart.png` - Visual schedule (CLI mode)
- Web UI displays Gantt charts and KPIs (web mode)

## API Endpoints (Web Mode)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Upload CSV files |
| POST | `/process/{session_id}` | Run scheduling workflow |
| GET | `/status/{session_id}` | Get workflow status |
| GET | `/data/{session_id}/{data_type}` | Get jobs/schedule/KPI data |
| GET | `/download/{session_id}/schedule` | Download schedule.csv |

## Module Overview

```
data_loader.py → validator.py → job_builder.py → scheduler.py → kpi.py
                    ↓                              ↓
              validation errors          verification
```

## Documentation
- [CLAUDE.md](CLAUDE.md) - Agent documentation
- [docs/changelog.md](docs/changelog.md) - Version history
- [docs/algorithm_details.md](docs/algorithm_details.md) - Algorithm explanation
- [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md) - File organization

## Version
Current: **v1.5.2** (Capacity-Aware Verification)
