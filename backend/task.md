# Backend Developer Tasks

Status: completed and re-audited on 2026-09-02. All 69 backend and 38 frontend automated tests, contract-drift and compile checks, real HTTP model-contract ingestion, and frontend smoke coverage pass.


Complete these milestones in order. The product API, contract, mock repository, and core routes already exist. Extend and harden them; do not rebuild the foundation or expose a second API shape.

## Already completed

- [x] Canonical IDs, UTC timestamps, and camera statuses are defined.
- [x] Raw occupancy is preserved and display percentage is capped at `100`.
- [x] A consistent JSON error envelope exists.
- [x] FastAPI application and environment configuration exist.
- [x] Domain and response models exist.
- [x] A repository protocol and fixture-backed implementation exist.
- [x] `/health` and the core `/api/*` routes are implemented.
- [x] CORS is configured for the local frontend.
- [x] OpenAPI generation and contract-drift testing exist.
- [x] Documented start and test commands exist.
- [x] The proposed SQLite schema and persistence rules are documented in `backend/database-schema.md`.

## Start here

Read `docs/parallel-development.md`, `contracts/README.md`, `contracts/openapi.yaml`, `contracts/examples/`, and `backend/database-schema.md`.

Run:

```powershell
.\scripts\start-backend.ps1
```

In a second terminal:

```powershell
.\scripts\test.ps1
```

Confirm API documentation at `http://127.0.0.1:8000/docs`.

## Required architectural rules

- [x] Routes depend on the repository protocol, not fixtures or model-server internals.
- [x] Route handlers do not contain `DATA_SOURCE` conditionals.
- [x] Mock and database repositories return the same domain models.
- [x] Responses do not change without an approved contract change.
- [x] Offline remains distinguishable from a valid zero measurement.
- [x] Stale data preserves the last trustworthy value and timestamp.
- [x] Raw values may exceed capacity; public percentage remains capped at `100`.
- [x] Missing history remains missing and is never synthesized as zero.
- [x] Only the backend owns database writes; frontend and model-server workers never write SQLite directly.
- [x] Schema changes are delivered through Alembic migrations, not startup-time table mutation.
- [x] Do not persist every 3 FPS inference result; use controlled sampling and five-minute aggregation.

## Milestone 1: Complete validation tests

### Tasks

- [x] Test all 155 room/camera mappings across floors 0-9.
- [x] Test valid zero occupancy and over-capacity raw occupancy.
- [x] Test partial coverage and empty history.
- [x] Test duplicate room IDs and camera IDs.
- [x] Test negative occupancy and invalid occupancy ranges.
- [x] Test invalid coverage percentages.
- [x] Test missing or non-UTC timestamps.
- [x] Test missing files and malformed fixture JSON.
- [x] Test unknown room and camera responses.
- [x] Test invalid history range and metric responses.
- [x] Test history ordering and bucket counts.
- [x] Test CORS for the documented frontend origin.

### Acceptance gate

- [x] Every case in `mock/generated/edge_cases.json` has a backend test or documented example.
- [x] Invalid fixtures fail at startup with an actionable error.
- [x] All public errors use the standard envelope.

## Milestone 2: SQLite database foundation

Use `backend/database-schema.md` as the implementation specification. Any schema deviation requires lead review and a corresponding documentation update.

### Tasks

- [x] Add SQLAlchemy and Alembic dependencies.
- [x] Add `DATABASE_URL` and retention/sampling settings to backend configuration and `.env.example`.
- [x] Default local database storage to a configurable path under `data/`; do not hardcode an absolute path.
- [x] Configure SQLite foreign keys, WAL mode, and a busy timeout on every connection.
- [x] Implement SQLAlchemy models for `rooms`, `cameras`, `camera_states`, `occupancy_samples`, and `occupancy_buckets_5m`.
- [x] Create the initial Alembic migration with all foreign keys, checks, uniqueness constraints, and indexes.
- [x] Implement `DatabaseOccupancyRepository` using the existing repository protocol.
- [x] Add an idempotent seed command for the 155 canonical rooms and cameras.
- [x] Add an optional development importer for `mock/generated/history_5min_7days.json`.
- [x] Ensure seed/import retries do not duplicate records or change canonical IDs silently.
- [x] Add migration tests using a temporary SQLite database.
- [x] Add database repository contract tests matching the fixture repository behavior.
- [x] Ensure the SQLite file and transient journal files are ignored by Git.

### Acceptance gate

- [x] A new database can be created entirely by running migrations and the seed command.
- [x] `/api/rooms`, `/api/occupancy`, and `/api/history` pass the same contract tests with `DATA_SOURCE=database`.
- [x] Restarting the backend preserves room, latest-state, and historical data.
- [x] No application code creates or modifies schema outside migrations.

## Milestone 3: Operational hardening

### Tasks

- [x] Add structured request logging and request IDs.
- [x] Log the active data source and safe configuration at startup.
- [x] Keep stack traces and internal paths out of public `500` responses.
- [x] Add bounded history query behavior before arbitrary date filters are introduced.
- [x] Define cache headers for mock metadata and live occupancy.
- [x] Verify graceful shutdown and repository cleanup hooks.
- [x] Add a readiness check for external dependencies.
- [x] Document expected status codes and operational configuration.

### Acceptance gate

- [x] Requests are traceable by request ID.
- [x] Failures are diagnosable without leaking internals.
- [x] Startup fails clearly when required configuration is unavailable.

## Milestone 4: Model-server ingestion adapter

The model server feeds a backend-owned ingestion service. API routes continue reading through `DatabaseOccupancyRepository`; they must not call model-server code directly.

### Tasks

- [x] Define the model-server connection or in-process access strategy.
- [x] Implement a model-server ingestion adapter and a serialized database writer.
- [x] Normalize camera IDs to `cam_001` format.
- [x] Map model output into validated ingestion records.
- [x] Preserve raw and stabilized occupancy separately where available.
- [x] Calculate percentage from configured room capacity and cap it at `100`.
- [x] Map source failures to `offline`.
- [x] Calculate `stale` from the last successful update.
- [x] Preserve the last trustworthy stale occupancy.
- [x] Handle timeout, unavailable server, malformed response, and recovery.
- [x] Upsert `camera_states` on every accepted stabilized update.
- [x] Persist samples every 5–10 seconds, on meaningful changes, or on a heartbeat—not at inference FPS.
- [x] Make ingestion idempotent using source event IDs or `(camera_id, observed_at)`.
- [x] Keep database transactions short and isolate one camera failure from other cameras.

### Acceptance gate

- [x] `DATA_SOURCE=mock` and `DATA_SOURCE=database` satisfy the same contract.
- [x] Switching API read source requires configuration only.
- [x] Existing frontend parsing does not change.
- [x] Model-server downtime does not block API reads of the last durable state.

## Milestone 5: Resolve full-building live coverage

The model-server configuration has three cameras, while the product contract has 155 spaces.

### Tasks

- [x] Confirm whether additional camera sources will be configured.
- [x] If sources are unavailable, retain all rooms and return unavailable/offline occupancy for those cameras.
- [x] Do not silently omit unconfigured rooms from `/api/rooms`.
- [x] Do not renumber or alias camera IDs differently between sources.
- [x] Add tests for configured and unconfigured cameras.
- [x] Document the selected live-coverage policy.

### Acceptance gate

- [x] All 155 rooms behave predictably in both data-source modes.
- [x] The frontend needs no separate mock-mode and live-mode room logic.

## Milestone 6: Historical aggregation and retention

SQLite stores controlled samples and canonical five-minute buckets. The history API derives its requested granularity from those buckets.

### Tasks

- [x] Implement five-minute bucket generation from persisted samples.
- [x] Enforce UTC five-minute bucket boundaries.
- [x] Persist capacity snapshots with samples and buckets.
- [x] Aggregate samples into hourly, daily, and weekly points.
- [x] Calculate coverage percentage for each bucket.
- [x] Preserve downtime gaps instead of writing artificial zeros.
- [x] Implement `/api/history` through `DatabaseOccupancyRepository`.
- [x] Add configurable raw-sample and aggregate retention jobs.
- [x] Delete expired data in bounded batches to avoid long SQLite write locks.
- [x] Add safe backup instructions using SQLite's backup API or another transactionally safe method.
- [x] Test boundary timestamps, empty ranges, partial buckets, and performance.

### Acceptance gate

- [x] Live history satisfies `contracts/openapi.yaml`.
- [x] Aggregation matches the documented semantics.
- [x] Partial and missing data are represented accurately.
- [x] Retention and aggregation do not block normal API reads for unacceptable periods.

## Milestone 7: Repository parity and recovery tests

### Tasks

- [x] Run shared contract tests against fixture and database repositories.
- [x] Test offline-to-online, online-to-stale, and stale-to-online transitions.
- [x] Test concurrent reads during occupancy updates.
- [x] Test model-server timeout, malformed output, and ingestion retry.
- [x] Ensure one failed camera does not fail the complete response.
- [x] Test percentage capping and raw-value retention in both read repositories.
- [x] Test SQLite busy-timeout handling and serialized writes.
- [x] Test idempotent ingestion and duplicate event rejection.

### Acceptance gate

- [x] Both repositories produce contract-equivalent responses.
- [x] Camera-level failures remain isolated.
- [x] Concurrent reads do not observe partially updated state.

## Milestone 8: Documentation and integration

### Tasks

- [x] Document install, start, test, and configuration commands.
- [x] Document model-server connectivity and failure behavior.
- [x] Document SQLite location, migrations, backup, sampling, aggregation, and retention.
- [x] Update `backend/.env.example` for every supported source.
- [x] Regenerate the contract after approved API changes:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run python -m scripts.export_api_contract
```

- [x] Run the complete test suite after contract generation.
- [x] Perform a frontend/backend smoke test using rooms, occupancy, and history.

### Final backend gate

- [x] The mock API remains available for frontend development.
- [x] Database mode can be enabled through configuration.
- [x] Model-server ingestion populates durable database state.
- [x] The contract remains stable across data sources.
- [x] Operational and recovery behavior is documented and tested.

## Contract change rule

1. Describe the problem and affected frontend behavior.
2. Agree on the change with the frontend developer and lead.
3. Update backend models and routes.
4. Regenerate `contracts/openapi.yaml` and examples.
5. Update contract and frontend tests together.
6. Do not merge while the checked-in contract differs from `app.openapi()`.
