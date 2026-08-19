# Backend Development Plan

The backend owns the product API and hides the difference between mock fixtures and the real model server. The frontend must consume API responses, not read files from `mock/generated` directly.

## Contract and conventions

- [ ] Use `cam_001`–`cam_007` as canonical camera IDs.
- [ ] Use the existing `room_*` IDs from `mock/generated/rooms.json`.
- [ ] Use UTC ISO-8601 timestamps with a `Z` suffix.
- [ ] Support camera statuses: `online`, `stale`, and `offline`.
- [ ] Preserve raw occupancy values for diagnostics.
- [ ] Cap display occupancy percentage at `100`; never expose a display percentage above `100`.
- [ ] Define one consistent JSON error shape for `400`, `404`, and `500` responses.

## Milestone 1: Backend foundation

### Modules

- [ ] Create the backend application entry point and local development command.
- [ ] Add environment-based configuration for data source, fixture directory, host, and port.
- [ ] Add structured logging and a request/error handling policy.
- [ ] Add dependency and test configuration if not already present.

### Done when

- [ ] The service starts locally with one documented command.
- [ ] `GET /health` returns a predictable success response.
- [ ] Configuration does not contain hardcoded machine-specific paths.

## Milestone 2: Domain models and validation

### Modules

- [ ] Define models for rooms, camera occupancy, room views, historical records, history points, and API errors.
- [ ] Validate fixture data at load time.
- [ ] Validate IDs, statuses, timestamps, capacity, occupancy ranges, and coverage percentages.
- [ ] Define the distinction between zero occupancy and unavailable occupancy.

### Done when

- [ ] Invalid fixture data fails with an actionable error.
- [ ] All model fields used by the frontend are explicit and documented.

## Milestone 3: Repository layer

### Modules

- [ ] Define interfaces for room, occupancy, and history access.
- [ ] Implement a mock repository backed by `mock/generated/*.json`.
- [ ] Load fixtures once and avoid rereading large history files on every request.
- [ ] Build indexes by room ID and camera ID for lookup performance.
- [ ] Implement filtering by room, camera, range, metric, and time window.

### Done when

- [ ] The HTTP layer does not access JSON files directly.
- [ ] The repository can be replaced without changing route behavior.
- [ ] Missing history is represented explicitly rather than silently fabricated as zeros.

## Milestone 4: Core API

### Endpoints

- [ ] `GET /health`
- [ ] `GET /rooms`
- [ ] `GET /rooms/{room_id}`
- [ ] `GET /occupancy`
- [ ] `GET /occupancy/{camera_id}`
- [ ] `GET /history?room_id=...&range=hour|day|week&metric=occupancy|percentage`

### Modules

- [ ] Add query-parameter validation and useful error messages.
- [ ] Return `404` for unknown rooms and cameras.
- [ ] Return stable response envelopes for collections and history.
- [ ] Return `updated_at`, status, capacity, raw occupancy, display occupancy, and percentage where applicable.
- [ ] Preserve stale last-known values while clearly exposing stale status.
- [ ] Keep offline and zero-occupancy responses distinguishable.

### Done when

- [ ] Every endpoint can be exercised using the generated mock data.
- [ ] Response shapes are documented with examples.
- [ ] The frontend can implement its first dashboard without reading fixture files.

## Milestone 5: Contract and edge-case tests

### Modules

- [ ] Test that all seven rooms and cameras load correctly.
- [ ] Test room/camera relationship and ID uniqueness.
- [ ] Test online, stale, and offline behavior.
- [ ] Test zero occupancy, missing history, partial coverage, and over-capacity data.
- [ ] Test invalid ranges, metrics, IDs, and malformed dates.
- [ ] Test history ordering and bucket consistency.
- [ ] Add endpoint-level contract tests for the frontend integration.

### Done when

- [ ] Edge cases from `mock/generated/edge_cases.json` are covered.
- [ ] Contract tests fail if a response field or identifier changes unexpectedly.

## Milestone 6: Model-server adapter

### Modules

- [ ] Define the adapter from model-server state to backend domain models.
- [ ] Map model-server output to `cam_001`-style IDs.
- [ ] Normalize timestamps and status values.
- [ ] Preserve raw occupancy, inference diagnostics, and last-known values where useful.
- [ ] Convert source failures into the documented offline/stale behavior.
- [ ] Select mock or model-server repository using configuration, not route-level conditionals.

### Done when

- [ ] Switching from mock data to model-server data requires configuration only.
- [ ] The frontend API contract remains unchanged.

## Milestone 7: Operational readiness

- [ ] Add CORS configuration for the local frontend origin.
- [ ] Add request logging without logging sensitive or excessive data.
- [ ] Add bounded history query limits to prevent expensive requests.
- [ ] Add graceful startup failure for missing or invalid fixtures.
- [ ] Document startup, configuration, fixture regeneration, and test commands.
- [ ] Add one end-to-end smoke test using the mock repository.

## Backend integration gate

The backend is ready for frontend integration when `/rooms`, `/occupancy`, and `/history` are stable, documented, tested against the mocks, and independent of the underlying data source.
