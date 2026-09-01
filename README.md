# Multi-camera occupancy checkpoint

This project runs a multi-camera people-occupancy pipeline. Each camera has a capture thread and an independent ByteTrack tracker; one shared YOLO11 detector performs inference, and a scheduler samples the latest frame from each camera at about 3 FPS. A two-second per-camera history produces the stabilized occupancy value.

The repository also includes mock- and SQLite-backed product API modes for parallel frontend/backend development. See [`backend/README.md`](backend/README.md) for migration, ingestion, retention, recovery, and configuration operations; see [`docs/parallel-development.md`](docs/parallel-development.md) and [`contracts/openapi.yaml`](contracts/openapi.yaml) for the shared API boundary.

## Requirements

- Python 3.12 (the required version is recorded in `.python-version` and `pyproject.toml`).
- [`uv`](https://docs.astral.sh/uv/).
- A Windows, Linux, or macOS environment that can open the configured video files. Display mode additionally requires a graphical desktop.
- By default, PyTorch is resolved from the CUDA 12.4 index and the configuration uses `device: 0`. For a CPU-only machine, change `device` to `cpu` in `model_server/config/cameras.yaml` before starting the application.

The YOLO11 model weights are included under `model_server/models/`. The demo videos are intentionally not included: create `model_server/videos/` and provide the three files referenced by `model_server/config/cameras.yaml`, or edit that configuration to use your own local files. Video files, logs, caches, and virtual environments are ignored by Git.

## Reproduce the environment

From the repository root:

```powershell
uv sync
```

If `uv` cannot create its default cache in a locked-down environment, point it at a writable directory inside the project:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv sync --link-mode copy
```

Run the unit tests before starting the inference pipeline:

```powershell
uv run python -m unittest discover -s tests -p "test_*.py"
```

## Run the local video demo

After the three configured video files are present:

```powershell
uv run python -m model_server.main
```

For annotated OpenCV windows:

```powershell
uv run python -m model_server.main --display
```

Press `q` to stop display mode. Results are appended to `model_server/logs/occupancy.jsonl`. Each JSONL record includes the camera ID, local ISO-8601 timestamp, raw and stabilized occupancy, inference/processing latency, source and sampled FPS, and dropped-frame count.

The configured videos loop at EOF. At each loop boundary, that camera's tracker and stabilizer reset so track IDs do not leak from the end of a clip into its beginning.

## Run the REST API

Start the background CV worker and API:

```powershell
uv run uvicorn model_server.model_server:app --host 127.0.0.1 --port 8001
```

For annotated windows in PowerShell, set the display flag before starting the server:

```powershell
$env:OCCUPANCY_DISPLAY = "1"
uv run uvicorn model_server.model_server:app --host 127.0.0.1 --port 8001
```

The API reads the latest in-memory state; requests never trigger inference:

```text
GET /health
GET /occupancy
GET /occupancy/cam_001
```

For example:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/occupancy
```

Camera results become `stale` after 10 seconds without an update. Failed sources are marked `offline`, while the last known occupancy values are preserved when available. Override the timeout with `OCCUPANCY_STALE_AFTER_SECONDS`; override the config and log paths with `OCCUPANCY_CONFIG` and `OCCUPANCY_LOG`.

## Run the full application stack

To run the complete system with the model server, product API backend, and the React frontend, you will need three separate terminal windows.

**1. Model Server:**
From the repository root, start the computer vision worker on port 8001:

```powershell
uv run uvicorn model_server.model_server:app --host 127.0.0.1 --port 8001
```

**2. Backend (Product API):**
From a new terminal at the repository root, start the backend. Enable ingestion and simulation to connect to the model server:

```powershell
$env:DATA_SOURCE = "database"
$env:INGESTION_ENABLED = "true"
$env:SIMULATION_ENABLED = "true"
$env:MODEL_SERVER_URL = "http://127.0.0.1:8001"
.\scripts\start-backend.ps1
```

**3. Frontend:**
From a third terminal, navigate to the `frontend` directory, set up the environment, and start the development server:

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

The frontend will start and provide a local URL (typically `http://localhost:5173/`) that you can open in your browser to view the dashboard.

## Configuration notes

Edit `model_server/config/cameras.yaml` to change sources, model path, confidence, input size, device, sample rate, looping, or stabilization window. The default `track_buffer: 9` in `model_server/config/bytetrack_custom.yaml` is approximately three seconds at the configured 3 FPS sampling rate; it is measured in processed tracker frames, not wall-clock seconds.

The pipeline is designed for local-file reproducibility. Live RTSP/HTTP sources may require additional OpenCV/FFmpeg support and their availability, latency, and credentials are outside this repository's reproducible setup.
