# API Contract

`openapi.yaml` is generated from `backend.app` and is the shared frontend/backend contract. Files in `examples/` provide compact normal, failure, and edge-case payloads for development and tests.

The history query currently uses `range` for compatibility with the mock-data vocabulary. Its values describe aggregation granularity across the retained seven-day dataset:

- `hour`: 168 hourly points
- `day`: 7 daily points
- `week`: 1 weekly point

It does not mean “look back one hour/day/week.” If the product later needs arbitrary date windows, add explicit `from` and `to` parameters through an approved contract change.

Regenerate the contract after an API change:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run python -m scripts.export_api_contract
```

The backend test suite detects a checked-in contract that has drifted from the application.

Authenticated account routes use the HttpOnly session cookie and return `no-store` data.
The contract includes database-backed profile reads/updates, password change, persistent
notification cursor pagination and mutations, and per-user notification preferences.
Mutation requests must originate from a configured `FRONTEND_ORIGINS` value.

