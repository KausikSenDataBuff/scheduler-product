# Scheduler Product v3

A production scheduling system that processes orders through operations on machines, with support for alternate machine routing, release/material constraints, parallel capacity, machine calendars, setup times, multi-level orders with parent-child dependencies, and BOM-based scheduling.

## Features

### Phase 3.0 Features (NEW)
- **Multi-Level Orders**: Hierarchical orders with parent-child dependencies
- **Dependency Constraints**: Child orders must complete before parent starts
- **BOM Support**: Bill of Materials for product hierarchy visualization
- **Phase 3 KPIs**: Dependency delay, critical path length, component service level, WIP explosion factor

### Phase 2.0 Features
- **Alternate Machine Routing**: Each operation can run on multiple machines; scheduler picks the fastest
- **Release + Material Constraints**: Orders can't start until materials are available
- **Phase 2 KPIs**: Machine utilization, alternate usage %, release delay metrics

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
- KPI computation (on-time delivery, delay metrics, utilization)
- Gantt chart visualization

## Installation

```bash
pip install pandas matplotlib fastapi uvicorn python-multipart pytest
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
   - Required: `machines_updated.csv`, `products.csv`, `routing_alternate.csv`, `orders_phase2.csv`
   - Optional Phase 1.5: `machine_calendar.csv`, `setup_matrix.csv`, `sections.csv`, `buffers.csv`
   - Optional Phase 3: `orders_multilevel.csv`, `order_links.csv`, `bom.csv`

### Option 2: Command Line

```bash
python main.py
```

### Run Tests

```bash
# Phase 2 tests
python -m pytest tests/test_phase2.py -v

# Phase 1.5 tests
python tests/test_baseline.py
python tests/test_calendar.py
python tests/test_setup.py
```

## Data Files

### Core Data (`/data`)
| File | Phase | Description |
|------|-------|-------------|
| `machines_updated.csv` | 1.5+ | Machine info with capacity |
| `products.csv` | 1.0 | Product info |
| `routing_alternate.csv` | **2.0** | Multi-machine routing (is_primary, efficiency) |
| `orders_phase2.csv` | **2.0** | Orders with release_time, material_available_time |

### Phase 1.5 Data
| File | Description |
|------|-------------|
| `machine_calendar.csv` | Machine availability windows |
| `setup_matrix.csv` | Product transition setup times |
| `sections.csv` | Section definitions |
| `buffers.csv` | Buffer capacity per section |

### Phase 3 Data (Multi-Level Orders)
| File | Description |
|------|-------------|
| `orders_multilevel.csv` | Orders with level, parent_order_id |
| `order_links.csv` | Parent-child order dependencies |
| `bom.csv` | Bill of Materials (parent→child) |

### Phase 2 Data Format

**routing_alternate.csv:**
```csv
product_id,operation_seq,department,machine_id,proc_time_min,is_primary,efficiency
TYRE_0000,1,MIX,MIX_M1,10.0,1,1.0
TYRE_0000,1,MIX,BLD_M3,12.76,0,0.78
```

**orders_phase2.csv:**
```csv
order_id,product_id,quantity,order_date,due_date,release_time,material_available_time,penalty_per_hour
ORD_00000,TYRE_0036,56,2026-01-07,2026-01-10,2026-01-08 12:00:00,2026-01-09 00:00:00,69
```

## Output
- `schedule.csv` - Scheduled operations with `is_primary` flag
- `gantt_chart.png` - Visual schedule (CLI mode)
- Web UI displays Gantt charts and KPIs (web mode)

## API Endpoints (Web Mode)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Upload CSV files (Phase 1.5 + Phase 2) |
| POST | `/process/{session_id}` | Run scheduling workflow |
| GET | `/status/{session_id}` | Get workflow status |
| GET | `/data/{session_id}/{data_type}` | Get jobs/schedule/KPI data |
| GET | `/download/{session_id}/schedule` | Download schedule.csv |

## Phase 2 KPIs

| Metric | Description |
|--------|-------------|
| `avg_utilization` | Machine busy time / available time (%) |
| `alt_machine_usage_pct` | % of jobs using non-primary machines |
| `avg_release_delay` | Avg delay from release constraints (hrs) |

## Phase 3 KPIs

| Metric | Description |
|--------|-------------|
| `dependency_delay` | Avg parent_start - max(child_completion) (hrs) |
| `critical_path_length` | Longest chain per top-level order |
| `component_service_level` | % child orders meeting parent need |
| `wip_explosion_factor` | multi-level orders / original orders |

## Module Overview

```
data_loader.py → validator.py → job_builder.py → scheduler.py → kpi.py
                    ↓                              ↓
              validation errors          verification + KPIs
```

## Documentation
- [CLAUDE.md](CLAUDE.md) - Agent documentation
- [docs/changelog.md](docs/changelog.md) - Version history
- [docs/algorithm_details.md](docs/algorithm_details.md) - Algorithm explanation
- [docs/api_reference.md](docs/api_reference.md) - API documentation

## Version
Current: **v2.1.0** (Phase 3: Multi-Level Orders & BOM Integration)
