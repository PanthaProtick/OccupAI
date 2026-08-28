# OccupAI backend operations

The product API has one stable HTTP contract and two read sources: `mock` and `database`. Routes only use the `OccupancyRepository` protocol. The model server never writes SQLite; its `/occupancy` snapshot is validated by `ModelServerIngestionAdapter` and passed to the serialized backend writer.

## Install, migrate, seed, and run

From the repository root in PowerShell:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv sync
$env:DATA_SOURCE = "database"
$env:DATABASE_URL = "sqlite:///./data/occupai.db"
uv run python -m scripts.database migrate
uv run python -m scripts.database seed
uv run python -m scripts.database import-history # optional development history
.\scripts\start-backend.ps1
```

`migrate` is the only operation that creates or changes schema. Seed is idempotent and refuses to silently remap a room to a different camera. A newly seeded database retains all 20 canonical rooms; cameras with no live source report `offline`, not zero, and are never omitted.

Run all tests with `.\scripts\test.ps1`. API documentation is at `/docs`. `/health` reports process health and `/ready` checks the active repository. Public errors use `{ "error": { "code", "message", "details" } }` and never include stack traces or local paths.

`scripts/start-backend.ps1` reads `backend/.env` before applying its development defaults; explicitly exported environment variables still take precedence. Restart the backend after changing that file.

## Configuration

- `DATA_SOURCE`: `mock` or `database`.
- `MOCK_DATA_DIR`: fixture directory used in mock mode and by seed.
- `DATABASE_URL`: configurable SQLite URL; default is `data/occupai.db`.
- `SQLITE_BUSY_TIMEOUT_MS`: lock wait, default 5000 ms.
- `RAW_SAMPLE_INTERVAL_SECONDS`: adapter sampling target, default 10 seconds. Do not persist inference FPS.
- `RAW_SAMPLE_RETENTION_DAYS` / `AGGREGATE_RETENTION_DAYS`: defaults 30/365.
- `RETENTION_BATCH_SIZE`: bounded deletion size, default 1000.
- `MODEL_SERVER_URL` / `MODEL_SERVER_TIMEOUT_SECONDS`: model-server polling settings.
- `MODEL_SERVER_POLL_INTERVAL_SECONDS`: delay between latest-state polls, default 2 seconds.
- `INGESTION_ENABLED`: starts the backend-owned polling worker in database mode; default `false`.
- `LIVE_CAMERA_IDS`: canonical cameras expected from the model server. The current configuration is `cam_001,cam_002,cam_003`.
- `MAINTENANCE_ENABLED`: starts recurring incremental aggregation and bounded retention in database mode.
- `MAINTENANCE_INTERVAL_SECONDS`: maintenance cadence, default 60 seconds.
- `SIMULATION_ENABLED`: starts synthetic ingestion for every canonical camera not listed in `LIVE_CAMERA_IDS`; requires database mode.
- `SIMULATION_TICK_INTERVAL_SECONDS`: synthetic-reading cadence, default 10 seconds.
- `FRONTEND_ORIGINS`: comma-separated CORS allowlist.

Every SQLite connection enables foreign keys, WAL, and the busy timeout. Writes use short transactions and the ingestion writer is serialized. API reads continue serving the last durable state during model-server downtime. A successful stale result preserves its last occupancy and observation time; offline remains unavailable and distinct from a measured zero. One malformed camera result is isolated from other cameras.

The checked-in `model_server/config/cameras.yaml` has exactly three sources. With `SIMULATION_ENABLED=true`, `cam_004`–`cam_020` receive synthetic readings through the same database writer, so they remain visibly fresh in the frontend. IDs are always normalized to `cam_NNN`; aliases never cross the product API boundary.

To run ingestion, start the model server on port 8001, then the product API on port 8000:

```powershell
uv run uvicorn model_server.model_server:app --host 127.0.0.1 --port 8001
$env:DATA_SOURCE = "database"
$env:INGESTION_ENABLED = "true"
$env:SIMULATION_ENABLED = "true"
$env:MODEL_SERVER_URL = "http://127.0.0.1:8001"
.\scripts\start-backend.ps1
```

The adapter polls `/occupancy`; request handlers never call the model server. Timeouts or an unavailable server mark configured cameras offline while API reads continue from durable state. Malformed camera output is isolated to that camera. The next valid poll recovers it. Online states become stale after the camera-specific timeout without destroying the last trustworthy occupancy and observation timestamp.

## History and maintenance

Samples are unique by `(camera_id, observed_at)` and, when supplied, `(camera_id, source_event_id)`. Run `uv run python -m scripts.database aggregate` to upsert UTC-aligned five-minute buckets. Hour/day/week API results derive from those buckets, weight occupancy by samples, cap percentages at 100, calculate coverage, and leave downtime gaps missing.

Run `uv run python -m scripts.database retention` periodically. Each run deletes at most `RETENTION_BATCH_SIZE` expired samples and buckets, minimizing write locks. Repeat until it reports zero for both tables. Never run this on the request path.

For an always-running database deployment, set `MAINTENANCE_ENABLED=true`. The backend lifecycle service incrementally recomputes the latest/new five-minute buckets and performs one bounded retention batch every interval. Manual commands remain available for administration and catch-up.

Five-minute buckets are aligned in UTC. Hour points contain at most 168 retained points, day points at most seven, and week produces at most one retained-seven-day point. Occupancy is sample-weighted; percentage is calculated with each bucket's capacity snapshot; coverage includes missing expected samples. Missing intervals remain absent rather than becoming zero-valued measurements.

For a consistent backup, use Python's SQLite backup API while the service is running:

```python
import sqlite3
with sqlite3.connect("data/occupai.db") as source, sqlite3.connect("data/occupai.backup.db") as target:
    source.backup(target)
```

Do not copy the database file blindly while WAL writes are active. Test restore procedures and keep backups outside the application data directory.

The same safe operation is available from the maintenance command:

```powershell
uv run python -m scripts.database backup --path D:\backups\occupai.db
```

## HTTP behavior

- Successful reads return `200`.
- Unknown room/camera returns `404` with the standard envelope.
- Invalid query parameters return `400`.
- Readiness dependency failure returns `503`.
- Unexpected failures return a sanitized `500`.

Every response includes `X-Request-ID` (a caller value is retained). Room metadata is cacheable for five minutes; occupancy responses are `no-store`. Shutdown disposes database connections.

Run a consumer-facing smoke test against a running API with:

```powershell
.\scripts\smoke-backend.ps1 -BaseUrl http://127.0.0.1:8000
```

That command also runs `frontend/smoke-api.mjs`, a Node/browser-compatible consumer that parses rooms, occupancy, and history using the frontend-facing contract.
