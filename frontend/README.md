# OccupAI frontend

React, TypeScript, and Vite application for the OccupAI product API.

## Start

Requires a current Node.js LTS release.

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

Vite prints the local application URL. Start the API separately from the repository root with `./scripts/start-backend.ps1`.

## Other commands

```powershell
npm test
npm run build
npm run preview
```

`VITE_API_BASE_URL` is validated in `src/config/env.ts`. Change it through the environment; do not put API URLs in components.

## Behavior and architecture

- `src/api/client.ts` is the only code that performs HTTP requests. It validates responses and owns URL construction, query serialization, timeout, cancellation, and API errors.
- The dashboard refreshes every 30 seconds while the page is visible. Manual and automatic refreshes cannot overlap, and the last successful data remains visible after a temporary failure.
- Room detail routes use `/rooms/{room_id}` and load independently of dashboard state.
- History controls select aggregation across the retained seven-day dataset: `hour` (hourly), `day` (daily), and `week` (one weekly bucket). They do not select a lookback period.
- Timestamps retain their UTC API strings in application data and are displayed in the browser's local timezone.
- Offline occupancy is unavailable, while a measured zero remains `0`. Displayed percentages are capped at 100%.

## Testing

The test suite consumes the compact payloads under `contracts/examples/`; production frontend code never imports fixtures or `mock/generated`.

```powershell
npm test
```
