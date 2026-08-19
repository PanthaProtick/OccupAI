# Frontend Development Plan

The frontend consumes the backend API through a typed client. It must not import or read files from `mock/generated` directly; the mock data is exposed through the backend during development.

## Contract and conventions

- [ ] Use `cam_001`–`cam_007` and the backend-provided room IDs.
- [ ] Treat `online`, `stale`, and `offline` as distinct UI states.
- [ ] Treat zero occupancy as a valid value, not as missing data.
- [ ] Display unavailable occupancy as `—` or an explicit unavailable state.
- [ ] Never display occupancy percentages above `100%`.
- [ ] Format timestamps consistently and indicate the source timezone where needed.

## Milestone 1: Frontend foundation

### Modules

- [ ] Establish the application shell, routing, styling, and reusable component conventions.
- [ ] Add environment-based API configuration, for example `VITE_API_BASE_URL`.
- [ ] Add a shared loading, error, empty, and retry pattern.
- [ ] Add a shared formatting layer for occupancy, percentage, timestamps, and statuses.

### Done when

- [ ] The application starts with one documented command.
- [ ] The API base URL is configurable without code changes.
- [ ] Common state and formatting behavior is not duplicated across pages.

## Milestone 2: Typed API client

### Modules

- [ ] Define types for rooms, occupancy, statuses, history points, and API errors.
- [ ] Implement `getRooms()`.
- [ ] Implement `getRoom(roomId)`.
- [ ] Implement `getOccupancy()`.
- [ ] Implement `getOccupancyByCamera(cameraId)`.
- [ ] Implement `getHistory({ roomId, range, metric })`.
- [ ] Centralize HTTP errors, parsing, request cancellation, and retry behavior.

### Done when

- [ ] UI components never construct API URLs or call `fetch` directly.
- [ ] Client types match the backend contract rather than the raw fixture nesting.
- [ ] Invalid or incomplete API responses produce a controlled error state.

## Milestone 3: Room overview dashboard

### Modules

- [ ] Load and display the room list.
- [ ] Build reusable room/occupancy cards.
- [ ] Display room name, building, floor, capacity, occupancy, percentage, intensity, and camera status.
- [ ] Show last-updated time.
- [ ] Add refresh behavior and refresh failure feedback.
- [ ] Add loading skeletons and a meaningful empty state.

### Done when

- [ ] All seven mock rooms render correctly.
- [ ] Cards remain readable across normal, busy, stale, and offline states.
- [ ] Existing data is retained while a refresh is in progress or fails.

## Milestone 4: Status and edge-case UX

### Modules

- [ ] Design the `online` state.
- [ ] Design the `stale` state with last update time and warning treatment.
- [ ] Design the `offline` state without misleading users into thinking occupancy is zero.
- [ ] Display valid zero occupancy clearly.
- [ ] Display over-capacity data with a capped percentage and optional raw-value detail.
- [ ] Display missing history and partial coverage without inventing data.

### Done when

- [ ] Every case in `mock/generated/edge_cases.json` has an intentional UI representation.
- [ ] Status is communicated by text and not color alone.

## Milestone 5: Room detail view

### Modules

- [ ] Add room detail routing by `room_id`.
- [ ] Display room metadata and current occupancy summary.
- [ ] Display camera status and update timestamp.
- [ ] Add navigation back to the room overview.
- [ ] Handle unknown room IDs with a not-found state.

### Done when

- [ ] Every room card links to a working detail view.
- [ ] Direct navigation to an invalid room is handled gracefully.

## Milestone 6: Historical analytics

### Modules

- [ ] Add range selector: hour, day, week.
- [ ] Add metric selector: occupancy, percentage.
- [ ] Build the historical chart using backend history responses.
- [ ] Render tooltips with bucket timestamps and values.
- [ ] Handle empty data, missing buckets, and partial coverage.
- [ ] Prevent stale requests from overwriting newer selections.
- [ ] Add chart loading and error states.

### Done when

- [ ] Switching room, range, or metric requests the correct backend query.
- [ ] Charts do not assume a fixed number of data points.
- [ ] Missing intervals are visually distinguishable from zero values.

## Milestone 7: Frontend tests

### Modules

- [ ] Test API client success and failure responses.
- [ ] Test dashboard rendering with normal room data.
- [ ] Test zero occupancy, stale, offline, and over-capacity states.
- [ ] Test unknown room and empty-history states.
- [ ] Test range and metric query selection.
- [ ] Test that rapid room/filter changes do not show stale request results.
- [ ] Add accessibility checks for status, controls, keyboard navigation, and chart labels.

### Done when

- [ ] The core user flows work without a real model server.
- [ ] Edge-case fixtures are covered by UI tests.

## Milestone 8: Integration and polish

- [ ] Connect the UI to the backend mock API.
- [ ] Remove direct fixture imports and temporary hardcoded data.
- [ ] Verify behavior at narrow and wide viewport sizes.
- [ ] Add auto-refresh only after manual refresh and stale-state behavior are correct.
- [ ] Avoid overlapping refresh requests and cancel obsolete history requests.
- [ ] Add a user-visible last-refresh indicator.
- [ ] Document local startup and API configuration.
- [ ] Verify the UI against both mock-backed and model-server-backed API responses.

## Frontend integration gate

The frontend is ready for model-server integration when it depends only on the documented backend API, handles all mock edge cases, and does not require code changes when the backend switches data sources.
