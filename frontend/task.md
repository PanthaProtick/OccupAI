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

- [ ] Use `cam_001`–`cam_007` and room IDs returned by the API.
- [ ] Treat `online`, `stale`, and `offline` as different UI states.
- [ ] Treat `0` occupancy as a valid measurement and `null` as unavailable.
- [ ] Never display an occupancy percentage above `100%`.
- [ ] Display timestamps consistently in the user's timezone while retaining UTC API values.
- [ ] Use one centralized API client; components must not call `fetch` directly.
- [ ] Do not import files from `mock/generated` into frontend code.
- [ ] Do not reinterpret API fields without coordinating a contract change.

## Milestone 1: Application foundation

### Tasks

- [ ] Confirm the frontend stack with the lead. Recommended: React, TypeScript, and Vite.
- [ ] Scaffold the application in `frontend/`.
- [ ] Add routing, global layout, styling conventions, and test configuration.
- [ ] Configure `VITE_API_BASE_URL` from the environment.
- [ ] Add shared loading, empty, error, retry, and not-found components.
- [ ] Add shared formatters for occupancy, percentage, status, and timestamps.

### Acceptance gate

- [ ] The frontend starts with one documented command.
- [ ] The application shell works at narrow and wide viewport sizes.
- [ ] No API URL or machine-specific path is hardcoded in components.

## Milestone 2: Typed API client

### Tasks

- [ ] Generate or define TypeScript types from `contracts/openapi.yaml`.
- [ ] Define types for rooms, occupancy, status, history, metadata, and API errors.
- [ ] Implement `getRooms()` using `GET /api/rooms`.
- [ ] Implement `getRoom(roomId)` using `GET /api/rooms/{room_id}`.
- [ ] Implement `getOccupancy()` using `GET /api/occupancy`.
- [ ] Implement `getOccupancyByCamera(cameraId)` using `GET /api/occupancy/{camera_id}`.
- [ ] Implement `getHistory({ roomId, range, metric })` using `GET /api/history`.
- [ ] Centralize query serialization, JSON parsing, API errors, timeout, and cancellation.
- [ ] Reject malformed responses through runtime validation or a controlled client error.
- [ ] Add API-client tests using `contracts/examples/`.

### Acceptance gate

- [ ] UI components do not construct URLs or call `fetch` directly.
- [ ] The client handles success, `400`, `404`, and network failures.
- [ ] Switching API environments requires configuration only.

## Milestone 3: Room overview dashboard

### Tasks

- [ ] Fetch rooms and current occupancy.
- [ ] Join room and occupancy records using `camera_id`.
- [ ] Build a reusable room card.
- [ ] Display room name, building, floor, capacity, occupancy, percentage, status, and update time.
- [ ] Add loading, empty, error, retry, and manual-refresh states.
- [ ] Preserve existing data while a refresh is running or fails.
- [ ] Prevent overlapping refresh requests.
- [ ] Link each room card to `/rooms/{room_id}`.

### Acceptance gate

- [ ] All seven mock rooms render from the running API.
- [ ] `cam_001`–`cam_007` map to the correct rooms.
- [ ] No dashboard data is hardcoded or imported from fixtures.

## Milestone 4: Status and edge-case UX

Use the named files under `contracts/examples/` for component tests.

### Tasks

- [ ] Render normal online data using `occupancy.json`.
- [ ] Render stale status with last-known occupancy using `stale-room.json`.
- [ ] Render offline occupancy as unavailable using `offline-camera.json`.
- [ ] Render a valid zero measurement using `zero-occupancy.json`.
- [ ] Cap display percentage while retaining raw occupancy using `over-capacity.json`.
- [ ] Render no-data history using `empty-history.json`.
- [ ] Communicate incomplete data using `partial-coverage-history.json`.
- [ ] Render the provided not-found and validation errors.
- [ ] Communicate status through text or icons as well as color.

### Acceptance gate

- [ ] Offline is never presented as a measured occupancy of zero.
- [ ] Missing history is never converted into artificial zero points.
- [ ] Every provided edge-case payload has an automated UI test.

## Milestone 5: Room detail page

### Tasks

- [ ] Add a route using `room_id`.
- [ ] Fetch and display the room-detail response.
- [ ] Display room metadata, current occupancy, status, and update timestamp.
- [ ] Add navigation back to the dashboard.
- [ ] Add loading, retry, and not-found states.
- [ ] Handle direct navigation to an unknown room gracefully.

### Acceptance gate

- [ ] Every dashboard card opens the correct room detail page.
- [ ] Refreshing a detail URL works without dashboard state.
- [ ] Invalid room IDs show a not-found view instead of crashing.

## Milestone 6: Historical analytics

The current `range` parameter means aggregation granularity across the retained seven-day dataset:

- `hour`: 168 hourly points
- `day`: 7 daily points
- `week`: 1 weekly point

It does not mean “look back one hour/day/week.”

### Tasks

- [ ] Add `hour`, `day`, and `week` controls.
- [ ] Add `occupancy` and `percentage` metric controls.
- [ ] Request history for the selected room, range, and metric.
- [ ] Build the chart without assuming a fixed point count.
- [ ] Show timestamp, value, and coverage percentage in chart details.
- [ ] Render missing intervals as gaps rather than zero values.
- [ ] Add chart loading, empty, error, and retry states.
- [ ] Cancel obsolete requests when room or filters change quickly.
- [ ] Prevent a slow old response from replacing a newer selection.

### Acceptance gate

- [ ] Every range and metric combination renders correctly.
- [ ] Empty and partial-coverage history are visually distinct from complete history.
- [ ] Rapid filter changes never show data for the wrong selection.

## Milestone 7: Refresh and resilience

### Tasks

- [ ] Add a visible last-refresh timestamp.
- [ ] Add auto-refresh only after manual refresh is stable.
- [ ] Avoid overlapping occupancy requests.
- [ ] Retain the last successful state during temporary network failure.
- [ ] Show a non-blocking warning when cached data remains visible.
- [ ] Pause or reduce refresh activity when the page is hidden if appropriate.

### Acceptance gate

- [ ] Temporary backend failure does not blank a loaded dashboard.
- [ ] Auto-refresh does not create duplicate or accumulating requests.

## Milestone 8: Quality and integration

### Tasks

- [ ] Add unit tests for formatters and API error handling.
- [ ] Add component tests for dashboard cards and room detail.
- [ ] Add interaction tests for history controls and refresh.
- [ ] Verify keyboard navigation, visible focus, and screen-readable labels.
- [ ] Verify narrow and wide layouts.
- [ ] Run the UI against the local mock-backed API.
- [ ] Document install, start, test, and build commands.

### Final frontend gate

- [ ] The frontend depends only on the documented product API.
- [ ] It handles all normal and edge-case examples.
- [ ] Changing from mock data to model-server data requires no frontend code change.

## Contract change rule

If a field is missing or unsuitable:

1. Document the UI requirement.
2. Discuss it with the backend developer and lead.
3. Update backend models and routes.
4. Regenerate `contracts/openapi.yaml` and examples.
5. Update frontend types and tests in the same integration window.

Do not create an undocumented frontend-only interpretation as a workaround.
