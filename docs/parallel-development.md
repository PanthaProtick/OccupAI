# Parallel Development Guide

This repository provides a stable HTTP boundary so frontend and backend work can begin independently. The generated fixture files are shared test data; they are not a frontend API.

## Source of truth

- API contract: `contracts/openapi.yaml`
- Compact response examples: `contracts/examples/`
- Generated simulation data: `mock/generated/`
- Frontend work plan: `frontend/task.md`
- Backend work plan: `backend/task.md`

Camera IDs use `cam_001`–`cam_007`. Timestamps are UTC ISO-8601 values. Camera status is one of `online`, `stale`, or `offline`.

## Start the mock-backed API

From PowerShell at the repository root:

```powershell
.\scripts\start-backend.ps1
```

The API is available at `http://127.0.0.1:8000`, with interactive documentation at `http://127.0.0.1:8000/docs`.

Useful requests:

```text
GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8000/api/rooms
GET http://127.0.0.1:8000/api/occupancy
GET http://127.0.0.1:8000/api/history?room_id=room_cse_201&range=day&metric=percentage
```

## Frontend setup

Copy `frontend/.env.example` to the environment file expected by the selected frontend toolchain. Components should call a centralized API client using `VITE_API_BASE_URL`; they should not import fixture JSON.

The frontend can develop normal screens against the running API and use the compact files in `contracts/examples/` for isolated component tests and edge states such as over-capacity, zero occupancy, partial coverage, and empty history.

## Backend setup

The product API supports `DATA_SOURCE=mock` and `DATA_SOURCE=database`. Routes depend on one repository protocol; neither mode changes the HTTP shape. In database mode, an optional backend-owned ingestion worker polls the model server and serializes SQLite writes. API routes never invoke inference or model-server code.

Configuration is documented in `backend/.env.example`.
Migration, seed, sampling, aggregation, retention, backup, failure, and seven-room coverage behavior are documented in `backend/README.md`.

## Regenerate the contract

Whenever an approved API change is made:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run python -m scripts.export_api_contract
uv run python -m unittest discover -s tests -p "test_*.py"
```

Commit the backend change, `contracts/openapi.yaml`, and affected examples together. Contract changes require coordination between frontend and backend owners.

## First integration gate

The initial dashboard slice is ready when:

- `/api/rooms` and `/api/occupancy` pass contract tests.
- The frontend renders all seven rooms.
- Online, stale, and offline states are distinct.
- Switching the frontend from component mocks to the running API only changes configuration.

The second slice adds `/api/history` with `hour`, `day`, and `week` aggregations and `occupancy` or `percentage` metrics.

