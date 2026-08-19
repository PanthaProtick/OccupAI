# Backend Developer Tasks

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

## Start here

Read `docs/parallel-development.md`, `contracts/README.md`, `contracts/openapi.yaml`, and `contracts/examples/`.

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

- [ ] Routes depend on the repository protocol, not fixtures or model-server internals.
- [ ] Route handlers do not contain `DATA_SOURCE` conditionals.
- [ ] Mock and model-server repositories return the same domain models.
- [ ] Responses do not change without an approved contract change.
- [ ] Offline remains distinguishable from a valid zero measurement.
- [ ] Stale data preserves the last trustworthy value and timestamp.
- [ ] Raw values may exceed capacity; public percentage remains capped at `100`.
- [ ] Missing history remains missing and is never synthesized as zero.

## Milestone 1: Complete validation tests

### Tasks

- [ ] Test all seven room/camera mappings.
- [ ] Test valid zero occupancy and over-capacity raw occupancy.
- [ ] Test partial coverage and empty history.
- [ ] Test duplicate room IDs and camera IDs.
- [ ] Test negative occupancy and invalid occupancy ranges.
- [ ] Test invalid coverage percentages.
- [ ] Test missing or non-UTC timestamps.
- [ ] Test missing files and malformed fixture JSON.
- [ ] Test unknown room and camera responses.
- [ ] Test invalid history range and metric responses.
- [ ] Test history ordering and bucket counts.
- [ ] Test CORS for the documented frontend origin.

### Acceptance gate

- [ ] Every case in `mock/generated/edge_cases.json` has a backend test or documented example.
- [ ] Invalid fixtures fail at startup with an actionable error.
- [ ] All public errors use the standard envelope.

## Milestone 2: Operational hardening

### Tasks

- [ ] Add structured request logging and request IDs.
- [ ] Log the active data source and safe configuration at startup.
- [ ] Keep stack traces and internal paths out of public `500` responses.
- [ ] Add bounded history query behavior before arbitrary date filters are introduced.
- [ ] Define cache headers for mock metadata and live occupancy.
- [ ] Verify graceful shutdown and repository cleanup hooks.
- [ ] Add a readiness check for external dependencies.
- [ ] Document expected status codes and operational configuration.

### Acceptance gate

- [ ] Requests are traceable by request ID.
- [ ] Failures are diagnosable without leaking internals.
- [ ] Startup fails clearly when required configuration is unavailable.

## Milestone 3: Model-server repository adapter

Create a new implementation of the existing repository protocol. Do not call model-server code from route handlers.

### Tasks

- [ ] Define the model-server connection or in-process access strategy.
- [ ] Implement `ModelServerOccupancyRepository`.
- [ ] Normalize camera IDs to `cam_001` format.
- [ ] Map model output into existing domain models.
- [ ] Preserve raw and stabilized occupancy separately where available.
- [ ] Calculate percentage from configured room capacity and cap it at `100`.
- [ ] Map source failures to `offline`.
- [ ] Calculate `stale` from the last successful update.
- [ ] Preserve the last trustworthy stale occupancy.
- [ ] Handle timeout, unavailable server, malformed response, and recovery.
- [ ] Select the repository once at startup using `DATA_SOURCE`.

### Acceptance gate

- [ ] `DATA_SOURCE=mock` and `DATA_SOURCE=model_server` satisfy the same contract.
- [ ] Switching source requires configuration only.
- [ ] Existing frontend parsing does not change.

## Milestone 4: Resolve seven-room live coverage

The model-server configuration has three cameras, while the product contract has seven.

### Tasks

- [ ] Confirm whether four additional camera sources will be configured.
- [ ] If sources are unavailable, retain all rooms and return unavailable/offline occupancy for those cameras.
- [ ] Do not silently omit unconfigured rooms from `/api/rooms`.
- [ ] Do not renumber or alias camera IDs differently between sources.
- [ ] Add tests for configured and unconfigured cameras.
- [ ] Document the selected live-coverage policy.

### Acceptance gate

- [ ] All seven rooms behave predictably in both data-source modes.
- [ ] The frontend needs no separate mock-mode and live-mode room logic.

## Milestone 5: Historical persistence and aggregation

The model server exposes latest state; the history API requires durable samples.

### Tasks

- [ ] Propose the storage technology and obtain lead approval.
- [ ] Define records for room, camera, timestamp, raw occupancy, display occupancy, and status.
- [ ] Persist normalized UTC samples and add room/timestamp indexes.
- [ ] Define retention and cleanup policy.
- [ ] Aggregate samples into hourly, daily, and weekly points.
- [ ] Calculate coverage percentage for each bucket.
- [ ] Preserve downtime gaps instead of writing artificial zeros.
- [ ] Implement live `/api/history` through the repository boundary.
- [ ] Test boundary timestamps, empty ranges, partial buckets, and performance.

### Acceptance gate

- [ ] Live history satisfies `contracts/openapi.yaml`.
- [ ] Aggregation matches the documented semantics.
- [ ] Partial and missing data are represented accurately.

## Milestone 6: Repository parity and recovery tests

### Tasks

- [ ] Run shared contract tests against both repository implementations.
- [ ] Test offline-to-online, online-to-stale, and stale-to-online transitions.
- [ ] Test concurrent reads during occupancy updates.
- [ ] Test model-server timeout and malformed output.
- [ ] Ensure one failed camera does not fail the complete response.
- [ ] Test percentage capping and raw-value retention in both repositories.

### Acceptance gate

- [ ] Both repositories produce contract-equivalent responses.
- [ ] Camera-level failures remain isolated.
- [ ] Concurrent reads do not observe partially updated state.

## Milestone 7: Documentation and integration

### Tasks

- [ ] Document install, start, test, and configuration commands.
- [ ] Document model-server connectivity and failure behavior.
- [ ] Document history storage and retention.
- [ ] Update `backend/.env.example` for every supported source.
- [ ] Regenerate the contract after approved API changes:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run python -m scripts.export_api_contract
```

- [ ] Run the complete test suite after contract generation.
- [ ] Perform a frontend/backend smoke test using rooms, occupancy, and history.

### Final backend gate

- [ ] The mock API remains available for frontend development.
- [ ] Model-server mode can be enabled through configuration.
- [ ] The contract remains stable across data sources.
- [ ] Operational and recovery behavior is documented and tested.

## Contract change rule

1. Describe the problem and affected frontend behavior.
2. Agree on the change with the frontend developer and lead.
3. Update backend models and routes.
4. Regenerate `contracts/openapi.yaml` and examples.
5. Update contract and frontend tests together.
6. Do not merge while the checked-in contract differs from `app.openapi()`.
