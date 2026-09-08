# OccupAI

Campus occupancy monitoring with multi-camera person detection, a persistent API, and a React dashboard.

OccupAI represents **155 spaces across floors 0–9**. The local demonstration combines three video-backed rooms with synthetic occupancy for the other 152 spaces. It includes room discovery, occupancy history, account profiles, in-app notifications, and a database-grounded Campus Assistant.

## Architecture

```text
Video sources → YOLO11 + per-camera ByteTrack → Model API :8001
                                                     ↓ polling
Synthetic room schedules ───────────────→ Backend ingestion writer
                                                     ↓
                                              SQLite database
                                                     ↓
                                             Product API :8000
                                                     ↓
                                            React / Vite :5173
```

- **Model server:** one shared detector, independent capture threads and trackers, and per-camera occupancy stabilization. API requests read the latest state without triggering inference.
- **Backend:** FastAPI, SQLAlchemy, Alembic, and SQLite. Validated model readings and synthetic readings pass through the backend ingestion writer.
- **Frontend:** React, TypeScript, and Vite. The dashboard consumes the product API; it does not connect directly to the model server.
- **Campus Assistant:** deterministic room filtering and ranking, with optional provider-assisted wording. The default mode needs no external API key.

## Requirements

The commands below use **PowerShell**, run from the repository root unless stated otherwise.

| Requirement | Notes |
| --- | --- |
| Python 3.12 | Version selected by `.python-version`. |
| `uv` | Python environment and dependency management; use the committed `uv.lock`. |
| Node.js 22.12 or newer and npm | Meets the Node requirement of the locked Vite version. |
| NVIDIA GPU and compatible driver | The committed PyTorch source is CUDA 12.4; inference uses `device: 0`. |
| Graphical desktop | Required only for OpenCV video windows. |
| Local video files | Three inputs are required for the video-backed demonstration; they are not committed. |

The documented inference setup targets Windows with NVIDIA CUDA. On a CPU-only Windows/Linux machine, set `device: cpu` in `model_server/config/cameras.yaml`; inference throughput will depend on the machine. Other platforms may require a different PyTorch installation: the committed CUDA environment is not a universal platform setup.

Model weights (`yolo11m.pt`, `yolo11s.pt`, and `yolo11n.pt`) are tracked under `model_server/models/`. The default uses `yolo11m.pt`. Generated fixtures, databases, video inputs, logs, secrets, and virtual environments are excluded from version control.

## Setup

### 1. Install dependencies

Clone or download this repository, open its root directory, and run:

```powershell
uv sync --locked
npm --prefix frontend ci
```

If the default Python cache is not writable:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv sync --locked --link-mode copy
```

Use the committed Python and npm lockfiles for reproduction rather than resolving new dependency versions.

### 2. Create local configuration

These commands preserve configuration files that already exist:

```powershell
if (-not (Test-Path backend/.env)) {
    Copy-Item backend/.env.example backend/.env
}
if (-not (Test-Path frontend/.env.local)) {
    Copy-Item frontend/.env.example frontend/.env.local
}
```

For the full demonstration, set these values in `backend/.env`:

```dotenv
DATA_SOURCE=database
DATABASE_URL=sqlite:///./data/occupai.db
MOCK_DATA_DIR=mock/generated
INGESTION_ENABLED=true
SIMULATION_ENABLED=true
LIVE_CAMERA_IDS=cam_093,cam_047,cam_010
MODEL_SERVER_URL=http://127.0.0.1:8001
SIMULATION_TICK_INTERVAL_SECONDS=5
MAINTENANCE_ENABLED=true
ASSISTANT_PROVIDER=deterministic
```

Keep the remaining example settings for local development. In `frontend/.env.local`, use:

```dotenv
VITE_API_BASE_URL=http://localhost:8000/api
```

Backend process environment variables override `backend/.env`. Restart the relevant service after changing configuration. Use `localhost` consistently for the browser and product API so cookie-based authentication works as expected.

### 3. Generate fixtures and initialize the database

```powershell
uv run python mock/generate_mock_data.py --seed 42
uv run python -m scripts.database migrate
uv run python -m scripts.database seed
```

This creates six fixture files in `mock/generated/`, applies the database schema, and seeds the 155 room/camera mappings. Seeding is idempotent and refuses to silently change existing camera assignments. Authentication also requires the database schema, including when occupancy reads use mock mode.

To populate the history charts with seven days of **synthetic demonstration history**, optionally run:

```powershell
uv run python -m scripts.database import-history
```

Without this import, historical charts fill as readings are collected and aggregated. Newly seeded current states begin offline and update when ingestion starts. Re-running fixture generation does not replace existing database history.

### 4. Supply the video inputs

Place your clips at the following paths, or edit their `source` entries in `model_server/config/cameras.yaml`:

| Room displayed | Camera ID | Default video path |
| --- | --- | --- |
| 7A03 | `cam_093` | `model_server/videos/test3.mp4` |
| 7B03 | `cam_047` | `model_server/videos/test4.mp4` |
| 7C07 | `cam_010` | `model_server/videos/test5.mp4` |

The room labels identify the rooms represented by the demo feeds; they do not establish where a supplied clip was recorded. Exact visual reproduction requires the same source clips, which are not distributed with this repository.

## Run the full application

Use three terminals. Start only one model-server instance and one backend instance.

### Terminal 1 — Model server with video windows

From the repository root:

```powershell
$env:OCCUPANCY_DISPLAY = "1"
uv run uvicorn model_server.model_server:app --host 127.0.0.1 --port 8001
```

Each window shows a large room-number header and occupancy counts above the footage. To run without windows, set `OCCUPANCY_DISPLAY` to `"0"` before launching.

### Terminal 2 — Product API

From the repository root, after completing the database setup:

```powershell
uv run uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

For development with automatic Python reload, `./scripts/start-backend.ps1` is also available. It applies migrations and reads `backend/.env`; the explicit fixture-generation and database-seeding steps above are still required for a fresh database-mode setup.

### Terminal 3 — Frontend

```powershell
cd frontend
npm run dev -- --host localhost --port 5173 --strictPort
```

Open [http://localhost:5173](http://localhost:5173). Create a local account using an `@aust.edu` address to access authenticated features. No preconfigured user account is supplied.

Stop each service with **Ctrl+C in its terminal**. In video display mode, `q` stops the video worker; use Ctrl+C to stop the API process as well.

## Verify the running system

From a fourth terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
Invoke-RestMethod http://127.0.0.1:8001/occupancy
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready
./scripts/smoke-backend.ps1 -BaseUrl http://localhost:8000
```

Expected results:

- Model occupancy contains `cam_093`, `cam_047`, and `cam_010`, with fresh online readings when the clips are processing successfully.
- Product health reports `data_source: database`; readiness succeeds.
- The smoke check finds **155 rooms and 155 camera states**, and validates history metadata and API documentation.
- The dashboard shows the three model-backed rooms alongside the simulated rooms after the first ingestion cycle.

A model-server health response confirms HTTP availability; inspect `/occupancy` to verify that inference is actually producing fresh readings.

| Service | Address / documentation |
| --- | --- |
| Frontend | [localhost:5173](http://localhost:5173) |
| Product API documentation | [localhost:8000/docs](http://localhost:8000/docs) |
| Product room list | [localhost:8000/api/rooms](http://localhost:8000/api/rooms) |
| Model API documentation | [127.0.0.1:8001/docs](http://127.0.0.1:8001/docs) |
| Individual model reading | [127.0.0.1:8001/occupancy/cam_093](http://127.0.0.1:8001/occupancy/cam_093) |

## Alternative run modes

### Standalone annotated video demo

After installing Python dependencies and supplying the clips, run from the repository root:

```powershell
uv run python -m model_server.main --display
```

This mode needs neither the backend nor the frontend and does not serve HTTP. Press `q` or Ctrl+C to stop. Omit `--display` for processing and JSONL logging without windows. Do not run it alongside the model API worker unless you intentionally want a second inference pipeline.

### Dashboard without video inference

Complete dependency installation, configuration, fixture generation, and database migration first. In the backend terminal, override the full-stack settings:

```powershell
$env:DATA_SOURCE = "mock"
$env:INGESTION_ENABLED = "false"
$env:SIMULATION_ENABLED = "false"
$env:MAINTENANCE_ENABLED = "false"
uv run uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Start the frontend normally. This mode reads generated fixtures; occupancy does not advance through live simulation. Regenerate fixtures to refresh their timestamps. Restore the database settings or use a new terminal before returning to the full stack.

## Occupancy behavior and reproducibility

### Video-backed rooms

The default configuration samples at **2 FPS per camera**, uses a **two-second stabilization window**, a **1280-pixel inference size**, and **0.15 confidence**. These are configured targets, not guaranteed throughput. Videos loop at EOF, resetting the corresponding tracker and stabilizer at each boundary.

Processing logs are appended to `model_server/logs/occupancy.jsonl`. They include raw and stabilized counts, timestamps, latency, frame-rate statistics, and dropped-frame counts. Wall-clock scheduling, hardware, and dropped frames can affect results even with identical clips and weights.

### Artificial rooms

`mock/occupancy_patterns.py` supplies the shared schedules used by live simulation and generated mock history:

- Most classrooms remain medium-to-high occupied, with staggered quiet periods.
- Common-use rooms have shorter and less frequent quiet periods.
- Schedules use Dhaka time, stable camera-specific phases, and modest daily/weekend variation.
- Live readings include bounded drift and noise and remain within room capacity.

These are busy-campus demonstration patterns, not measured usage or an opening-hours model. They intentionally remain active at any viewing hour. Seed 42 makes controlled variation repeatable for the same time inputs; default generation dates and live timestamps follow the clock, so successive runs are not byte-identical.

`LIVE_CAMERA_IDS` must match the model-server camera IDs: simulation excludes those cameras to prevent synthetic readings from overwriting model observations. The `room_label` fields control video titles only. Preserve existing room/camera mappings when changing input clips.

## Tests and build

Generate fixtures before running Python tests. These commands do not require running application servers:

```powershell
uv run python -m unittest discover -s tests -p "test_*.py"
npm --prefix frontend test
npm --prefix frontend run build
```

For focused checks of synthetic occupancy behavior and feed assignments:

```powershell
uv run python -m unittest discover -s tests -p test_simulation_patterns.py
```

The frontend build produces `frontend/dist/`. `npm --prefix frontend run preview` serves that build locally; it does not start the backend or model server.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Video windows do not appear | Set `OCCUPANCY_DISPLAY=1` in the same terminal before starting the model API, and use a graphical desktop. |
| Model cameras remain offline | Check video paths, decoding support, GPU availability, and worker terminal output. Verify `/occupancy`, not only `/health`. |
| CUDA device error | Check the installed driver and PyTorch environment, or select `device: cpu` for CPU inference. |
| Missing rooms or database tables | Run fixture generation, `scripts.database migrate`, and `scripts.database seed` in order. Confirm `DATABASE_URL` and `MOCK_DATA_DIR`. |
| Login fails or cookies are missing | Use an `@aust.edu` account, keep browser/API hostnames consistent, and check `FRONTEND_ORIGINS`. |
| Frontend cannot reach the API | Verify `VITE_API_BASE_URL`, port 8000, and backend readiness; restart Vite after configuration changes. |
| A port is already occupied | Stop the existing service in its terminal. Changing ports also requires updating API URLs and allowed frontend origins. |
| History is empty | Import optional synthetic history or allow time for aggregation with `MAINTENANCE_ENABLED=true`. |
| Seed refuses a camera remap | Check the fixture/database mappings. Do not reset an existing database as a routine fix. |

## Project layout

```text
backend/          Product API, authentication, ingestion, simulation, assistant
frontend/         React application and frontend tests
model_server/     Video capture, detector, tracking, visualization, model API
mock/             Room catalog, synthetic schedules, fixture generator
migrations/       Alembic database migrations
contracts/        OpenAPI contract and compact API examples
scripts/          Startup, database operations, smoke checks
tests/            Python tests
docs/             Architecture and historical design notes
```

## Further documentation

- [Backend operations](backend/README.md): authentication, configuration, retention, backup, and recovery.
- [Campus Assistant](backend/assistant/README.md): supported queries, ranking, provider behavior, and privacy boundaries.
- [Frontend guide](frontend/README.md): API client, refresh behavior, routes, and tests.
- [API contract](contracts/openapi.yaml) and [contract guide](contracts/README.md).
- [Development architecture](docs/parallel-development.md).

This README describes local reproduction. Production deployment needs environment-specific configuration; see the backend operations guide before exposing the services beyond localhost.
