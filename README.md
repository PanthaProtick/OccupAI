# Multi-camera occupancy checkpoint

The checkpoint service simulates three independent CCTV cameras with local video files. Capture runs continuously into one latest-frame slot per camera; the scheduler samples each source at about 3 FPS, shares one YOLO11m detector, and keeps one ByteTrack instance per camera.

Video inputs are intentionally excluded from this repository to keep it compact. To run the demo, create `model_server/videos/`, add `test1.mp4`, `test2.mp4`, and `test3.avi`, or update `model_server/config/cameras.yaml` to point at your own files. Video files and common video extensions are ignored by Git.

Run from the repository root after installing the project dependencies:

```powershell
uv sync
uv run python -m model_server.main
```

For a live demonstration with annotated windows, run:

```powershell
uv run python -m model_server.main --display
```

Each camera window shows the sampled frame, person boxes, isolated track IDs, `Raw`, `Stable`, and processing latency. Press `q` to stop the run.

Occupancy stabilization uses a separate two-second history per camera. Samples older than the window are discarded, then the mode is emitted; ties prefer the most recent tied count. The JSONL output contains both `raw_occupancy` and `stable_occupancy` so tracking failures remain visible during testing.

## Model server API

Start the background CV worker and REST API with:

```powershell
uv run uvicorn model_server.model_server:app --host 0.0.0.0 --port 8000
```

For a judge/demo run with looping videos and annotated OpenCV windows:

Git Bash:

```bash
export OCCUPANCY_DISPLAY=1
uv run uvicorn model_server.model_server:app --host 127.0.0.1 --port 8000
```

PowerShell:

```powershell
$env:OCCUPANCY_DISPLAY = "1"
uv run uvicorn model_server.model_server:app --host 127.0.0.1 --port 8000
```

Set `OCCUPANCY_DISPLAY` back to `0` for a headless server. The configured videos loop at EOF, and each camera's tracker and stabilizer reset at the loop boundary so identities do not leak from the end of a clip into its beginning. Press `q` in an OpenCV window to stop the worker.

The API only reads the latest in-memory state; requests never trigger inference:

```text
GET /health
GET /occupancy
GET /occupancy/camera_01
```

Camera results become `stale` after 10 seconds without an update. Failed sources are marked `offline`, while the last known occupancy values are preserved when available. Override the stale timeout with `OCCUPANCY_STALE_AFTER_SECONDS`.

If `uv` reports that a package cannot be linked and recommends copy mode, use
`uv sync --link-mode copy` (or set `$env:UV_LINK_MODE = "copy"` in PowerShell).
That warning is about package installation and is unrelated to GPU inference.

Results are appended to `model_server/logs/occupancy.jsonl`. Each record contains `camera_id`, a local ISO-8601 timestamp, raw active-track occupancy, processing and inference latency, source FPS, sampled FPS, and dropped-frame count.

The default `track_buffer: 9` is intentionally configured for roughly three seconds at the checkpoint's 3 FPS sampling rate. Re-test it against observed occlusions before changing it; the value is measured in processed tracker frames, not wall-clock seconds.
