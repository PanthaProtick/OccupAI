# Campus Assistant architecture and operations

The Campus Assistant is a backend-grounded, deterministic room-discovery feature. Its core path
does not require an external language model. The optional provider can improve wording only; it
cannot select rooms, query the database, invoke tools, or override validated results.

## Request architecture

`React /assistant -> cookie auth + Origin/CSRF + rate limits -> safety inspection -> deterministic parser -> bulk validated occupancy snapshot -> deterministic filtering/ranking -> deterministic answer -> optional bounded provider rewrite -> user-owned conversation storage -> response`

The repository rejects disabled cameras and missing, stale, offline, future-dated, inconsistent, or
over-capacity readings before filtering. One bulk snapshot avoids per-room database queries. The
response contains only `BROWSER_SAFE_RESULT_FIELDS`. Operational logs contain a request ID,
pseudonymous user reference, intent, result count, duration, provider/fallback state, and safe error
category—not raw questions, email addresses, credentials, authorization data, or provider keys.

## Supported intents and deterministic rules

- Find available or least-occupied rooms: valid online rooms, lowest occupancy first.
- Find a room for a group: sufficient available capacity, highest available capacity first.
- Find rooms by floor or A/B/C block: exact validated filters and room-number ordering.
- Find a nearby alternative: exclude the source; prefer its building, floor, block, then lower
  occupancy.
- Identify crowded rooms: threshold filter, highest occupancy first.
- Compare rooms and explain room status: require explicit canonical room references.
- Unsupported, ambiguous, or unsafe requests receive a bounded clarification/refusal and never
  execute code, SQL, shell commands, URLs, or client-supplied tools.

The default result limit is 3 and the hard maximum is 10. Ranking is stable and uses canonical room
identity as its final tie-breaker. Percentages are capacity-bounded. Every result includes the
observation time and `online` status; stale/offline/unavailable data is excluded and the answer warns
when fewer reliable matches exist.

Supported room queries are also scoped to the authenticated user's persisted "My used floors":
Ground Floor and Floor 1 plus selected Floors 2–9. A query without an explicit floor searches that
scope. Explicit unselected floors are excluded with a warning directing the user to Profile.

## API and persistence

- `POST /api/assistant/query` creates or continues an authenticated conversation.
- `GET /api/assistant/conversations?page=1&limit=20` lists the current user's history newest first.
- `GET /api/assistant/conversations/{conversation_id}` loads only an owned conversation.
- `DELETE /api/assistant/conversations/{conversation_id}` deletes only an owned conversation and
  requires an allowed Origin.

All responses are `Cache-Control: no-store`. Invalid or foreign conversation IDs use safe standard
errors; a foreign ID is reported as not found. `assistant_conversations` belongs to `users` and
stores title/timestamps. `assistant_messages` belongs to a conversation and stores only the
sanitized user message, deterministic/provider-safe assistant answer, browser-safe structured
results, role, and timestamp. Cascading foreign keys remove messages with their conversation or
account. History survives logout, refresh, restart, and later login because logout deletes only the
session.

## Configuration and provider fallback

- `ASSISTANT_ENABLED` enables the feature (default `true`).
- `ASSISTANT_RATE_LIMIT_ATTEMPTS` and `ASSISTANT_RATE_LIMIT_WINDOW_SECONDS` configure isolated,
  process-local per-user and per-IP limits.
- `ASSISTANT_PROVIDER=deterministic` disables external provider use and is the default. Set it to
  `gemini` to enable the fixed-purpose Gemini phrasing adapter.
- `ASSISTANT_MODEL` and `ASSISTANT_API_KEY` are required only for an injected external adapter in
  production. Keys must be deployment secrets and are never included in safe settings summaries.
- `ASSISTANT_TIMEOUT_SECONDS` bounds optional rewriting (default 3 seconds).

For a low-latency Gemini configuration, set `ASSISTANT_PROVIDER=gemini`,
`ASSISTANT_MODEL=gemini-3.5-flash-lite`, and place a newly generated key in
`ASSISTANT_API_KEY` inside the untracked `backend/.env` file or deployment secret manager. Never
put the key in `.env.example`, source code, frontend variables, Git, screenshots, or chat messages.

The provider receives only the deterministic answer and validated result projection. Timeout,
exception, empty/oversized output, or any invented room identifier/name/percentage falls back to
the verified deterministic answer. No vendor adapter or provider dependency is enabled by default.

## Local development and verification

From the repository root:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv sync
uv run alembic upgrade head
.\scripts\start-backend.ps1
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Focused and release verification commands:

```powershell
uv run python -m unittest discover -s tests -p "test_assistant_smoke.py" -v
uv run python -m unittest discover -s tests -p "test_assistant*.py" -v
uv run python -m unittest discover -s tests -p "test_assistant_conversations.py" -v
uv run python -m unittest discover -s tests -p "test_*.py"
cd frontend
npm test
npm run build
```

Regenerate the checked-in API contract after route/model changes with
`uv run python -m scripts.export_api_contract`. This project currently has no configured Python or
frontend lint command; use the test/build commands plus `git diff --check` as the release checks.

## Existing application architecture

- **Frontend:** React with TypeScript and Vite. `react-router-dom` defines public routes (`/` and
  `/login`) and cookie-authenticated routes under `ProtectedRoute`. The browser calls only the
  configured OccupAI API through `frontend/src/api/client.ts` with `credentials: "include"`.
- **Backend:** FastAPI with Pydantic response/request models, SQLAlchemy 2, Alembic, and a replaceable
  `OccupancyRepository` protocol. `DatabaseOccupancyRepository` is the production data source;
  `MockOccupancyRepository` supports development and tests.
- **Authentication:** an opaque `HttpOnly` cookie contains a random session token. Only an
  HMAC-SHA256 token hash is stored. Mutating account endpoints validate the configured frontend
  `Origin`; production requires secure cookies and a non-default session pepper.
- **Errors:** API failures use `{ "error": { "code", "message", "details" } }`, set
  `X-OccupAI-Error-Envelope: 1`, and never require the frontend to interpret database errors.
- **Rate limiting:** `AuthenticationRateLimiter` is a thread-safe, process-local sliding-window
  limiter keyed by endpoint-specific caller identity. The assistant will receive its own per-user
  and per-IP keys in Module 2; distributed deployments will eventually need a shared store.

## Room and live-state representation

- `rooms` contains canonical `room_*` identifiers, name, positive capacity, building, non-negative
  integer floor, and behavior profile. Ground Floor is represented by `floor = 0`.
- `cameras` maps one canonical `cam_NNN` feed to a room and stores `enabled` plus
  `stale_after_seconds`.
- `camera_states` stores the latest occupancy, raw occupancy, status, observed time, and update time.
  Occupancy samples permit `online` or `stale`; current state additionally supports `offline`.
- `DatabaseOccupancyRepository` joins room, camera, and state data. A missing state is `offline`.
  An online state older than its camera freshness window is normalized to `stale`. Offline readings
  expose no trusted occupancy. Percentage is capacity-bounded and never derived from absent data.
- The current public `Room` model carries building and floor directly. Block is encoded by the room
  naming convention and is presently derived in the frontend; a single backend derivation will be
  introduced with the assistant query engine rather than duplicated here.

## Existing recommendations

The frontend `SmartRecommendations` component sorts currently online room snapshots for display.
Persistent high-occupancy notifications use a backend database query that excludes the source room,
disabled cameras, non-online states, missing occupancy, and stale readings. It prefers the same
building, then the same floor, then rooms below 40%, then lower percentage. The Campus Assistant
will reuse these principles but centralize its factual filtering and ranking in later backend modules.

## Enforced assistant boundary

`AssistantOccupancySource` is a read-only backend protocol exposing validated rooms, validated
occupancy states, and data-generation time. Future assistant services must depend on this boundary,
not accept database queries or tool instructions from the browser or an LLM.

The data flow is fixed as:

`React UI -> authenticated OccupAI API -> assistant service -> validated repository -> database`

An optional provider may later interpret phrasing or rewrite already-grounded results, but it will
not receive a database session, credentials, unrestricted records, authorization internals, arbitrary
HTTP/shell tools, or ownership of factual filtering/ranking. `BROWSER_SAFE_RESULT_FIELDS` is the
maximum result projection intended for the client; `FORBIDDEN_BROWSER_FIELDS` documents sensitive
names that must never cross that boundary.

This separation keeps provider secrets and system instructions on the backend and makes the core
assistant useful through a deterministic implementation even when no external provider is enabled.
