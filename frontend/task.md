# Frontend Developer Tasks

Complete these milestones in order. The frontend can start immediately using the mock-backed product API; it does not need to wait for model-server integration.

## Already provided

- API contract: `contracts/openapi.yaml`
- Normal and edge-case payloads: `contracts/examples/`
- API startup command: `scripts/start-backend.ps1`
- Environment template: `frontend/.env.example`
- Development guide: `docs/parallel-development.md`

Start the API from the repository root:

```powershell
.\scripts\start-backend.ps1
```

Use this frontend configuration:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

## Required conventions

- [x] Use canonical `cam_NNN` IDs and room IDs returned by the API.
- [x] Treat `online`, `stale`, and `offline` as different UI states.
- [x] Treat `0` occupancy as a valid measurement and `null` as unavailable.
- [x] Never display an occupancy percentage above `100%`.
- [x] Display timestamps consistently in the user's timezone while retaining UTC API values.
- [x] Use one centralized API client; components must not call `fetch` directly.
- [x] Do not import files from `mock/generated` into frontend code.
- [x] Do not reinterpret API fields without coordinating a contract change.

## Milestone 1: Application foundation

### Tasks

- [x] Confirm the frontend stack with the lead. Recommended: React, TypeScript, and Vite.
- [x] Scaffold the application in `frontend/`.
- [x] Add routing, global layout, styling conventions, and test configuration.
- [x] Configure `VITE_API_BASE_URL` from the environment.
- [x] Add shared loading, empty, error, retry, and not-found components.
- [x] Add shared formatters for occupancy, percentage, status, and timestamps.

### Acceptance gate

- [x] The frontend starts with one documented command.
- [x] The application shell works at narrow and wide viewport sizes.
- [x] No API URL or machine-specific path is hardcoded in components.

## Milestone 2: Typed API client

### Tasks

- [x] Generate or define TypeScript types from `contracts/openapi.yaml`.
- [x] Define types for rooms, occupancy, status, history, metadata, and API errors.
- [x] Implement `getRooms()` using `GET /api/rooms`.
- [x] Implement `getRoom(roomId)` using `GET /api/rooms/{room_id}`.
- [x] Implement `getOccupancy()` using `GET /api/occupancy`.
- [x] Implement `getOccupancyByCamera(cameraId)` using `GET /api/occupancy/{camera_id}`.
- [x] Implement `getHistory({ roomId, range, metric })` using `GET /api/history`.
- [x] Centralize query serialization, JSON parsing, API errors, timeout, and cancellation.
- [x] Reject malformed responses through runtime validation or a controlled client error.
- [x] Add API-client tests using `contracts/examples/`.

### Acceptance gate

- [x] UI components do not construct URLs or call `fetch` directly.
- [x] The client handles success, `400`, `404`, and network failures.
- [x] Switching API environments requires configuration only.

## Milestone 3: Room overview dashboard

### Tasks

- [x] Fetch rooms and current occupancy.
- [x] Join room and occupancy records using `camera_id`.
- [x] Build a reusable room card.
- [x] Display room name, building, floor, capacity, occupancy, percentage, status, and update time.
- [x] Add loading, empty, error, retry, and manual-refresh states.
- [x] Preserve existing data while a refresh is running or fails.
- [x] Prevent overlapping refresh requests.
- [x] Link each room card to `/rooms/{room_id}`.

### Acceptance gate

- [x] All 155 mock rooms render from the running API and filter by floor.
- [x] `cam_001`–`cam_155` map to the correct rooms.
- [x] No dashboard data is hardcoded or imported from fixtures.

## Milestone 4: Status and edge-case UX

Use the named files under `contracts/examples/` for component tests.

### Tasks

- [x] Render normal online data using `occupancy.json`.
- [x] Render stale status with last-known occupancy using `stale-room.json`.
- [x] Render offline occupancy as unavailable using `offline-camera.json`.
- [x] Render a valid zero measurement using `zero-occupancy.json`.
- [x] Cap display percentage while retaining raw occupancy using `over-capacity.json`.
- [x] Render no-data history using `empty-history.json`.
- [x] Communicate incomplete data using `partial-coverage-history.json`.
- [x] Render the provided not-found and validation errors.
- [x] Communicate status through text or icons as well as color.

### Acceptance gate

- [x] Offline is never presented as a measured occupancy of zero.
- [x] Missing history is never converted into artificial zero points.
- [x] Every provided edge-case payload has an automated UI test.

## Milestone 5: Room detail page

### Tasks

- [x] Add a route using `room_id`.
- [x] Fetch and display the room-detail response.
- [x] Display room metadata, current occupancy, status, and update timestamp.
- [x] Add navigation back to the dashboard.
- [x] Add loading, retry, and not-found states.
- [x] Handle direct navigation to an unknown room gracefully.

### Acceptance gate

- [x] Every dashboard card opens the correct room detail page.
- [x] Refreshing a detail URL works without dashboard state.
- [x] Invalid room IDs show a not-found view instead of crashing.

## Milestone 6: Historical analytics

The current `range` parameter means aggregation granularity across the retained seven-day dataset:

- `hour`: 168 hourly points
- `day`: 7 daily points
- `week`: 1 weekly point

It does not mean “look back one hour/day/week.”

### Tasks

- [x] Add `hour`, `day`, and `week` controls.
- [x] Add `occupancy` and `percentage` metric controls.
- [x] Request history for the selected room, range, and metric.
- [x] Build the chart without assuming a fixed point count.
- [x] Show timestamp, value, and coverage percentage in chart details.
- [x] Render missing intervals as gaps rather than zero values.
- [x] Add chart loading, empty, error, and retry states.
- [x] Cancel obsolete requests when room or filters change quickly.
- [x] Prevent a slow old response from replacing a newer selection.

### Acceptance gate

- [x] Every range and metric combination renders correctly.
- [x] Empty and partial-coverage history are visually distinct from complete history.
- [x] Rapid filter changes never show data for the wrong selection.

## Milestone 7: Refresh and resilience

### Tasks

- [x] Add a visible last-refresh timestamp.
- [x] Add auto-refresh only after manual refresh is stable.
- [x] Avoid overlapping occupancy requests.
- [x] Retain the last successful state during temporary network failure.
- [x] Show a non-blocking warning when cached data remains visible.
- [x] Pause or reduce refresh activity when the page is hidden if appropriate.

### Acceptance gate

- [x] Temporary backend failure does not blank a loaded dashboard.
- [x] Auto-refresh does not create duplicate or accumulating requests.

## Milestone 8: Quality and integration

### Tasks

- [x] Add unit tests for formatters and API error handling.
- [x] Add component tests for dashboard cards and room detail.
- [x] Add interaction tests for history controls and refresh.
- [x] Verify keyboard navigation, visible focus, and screen-readable labels.
- [x] Verify narrow and wide layouts.
- [x] Run the UI against the local mock-backed API.
- [x] Document install, start, test, and build commands.

### Final frontend gate

- [x] The frontend depends only on the documented product API.
- [x] It handles all normal and edge-case examples.
- [x] Changing from mock data to model-server data requires no frontend code change.

## Contract change rule

If a field is missing or unsuitable:

1. Document the UI requirement.
2. Discuss it with the backend developer and lead.
3. Update backend models and routes.
4. Regenerate `contracts/openapi.yaml` and examples.
5. Update frontend types and tests in the same integration window.

Do not create an undocumented frontend-only interpretation as a workaround.
