# OccupAI SQLite Schema

Status: implemented through Alembic migrations. Migration `0004` adds persistent user
notification tables; migration `0005` makes ingestion deduplication keys unique.

## Scope and decisions

- Database engine: SQLite for the current single-machine deployment.
- Database owner: the backend process. The frontend and model-server workers must not write to SQLite directly.
- API read path: `API route -> repository protocol -> database repository -> SQLite`.
- Live write path: `model server -> backend ingestion adapter -> single writer/short transaction -> SQLite`.
- Development fallback: the existing fixture repository remains available with `DATA_SOURCE=mock`.
- Production-like local mode: use `DATA_SOURCE=database`.
- Timestamps: UTC ISO-8601 text values, normalized by the application before persistence.
- Current room-camera cardinality: one camera per room. `cameras.room_id` is unique until a multi-camera aggregation rule is designed.
- History source: five-minute buckets. Hourly, daily, and weekly API responses are derived from these buckets.

## Why writes are controlled

SQLite supports concurrent readers but serializes writes. All writes should therefore pass through one backend-owned ingestion service. Keep transactions short and never persist every 3 FPS inference result.

Recommended sampling policy:

- Upsert the latest state for every accepted stabilized update.
- Persist a raw sample every 5–10 seconds, or when occupancy/status changes, plus a heartbeat.
- Build one five-minute aggregate per camera and bucket.
- Apply configurable retention to raw samples; retain aggregates longer.

## Table: `rooms`

Stores product-facing room metadata.

| Column | SQLite type | Null | Rules |
|---|---|---:|---|
| `room_id` | `TEXT` | No | Primary key; canonical `room_*` identifier |
| `name` | `TEXT` | No | Non-empty |
| `capacity` | `INTEGER` | No | Greater than zero |
| `building` | `TEXT` | No | Non-empty |
| `floor` | `INTEGER` | No | Zero or greater |
| `behavior_profile` | `TEXT` | No | Non-empty; simulation metadata for now |
| `created_at` | `TEXT` | No | UTC ISO-8601 |
| `updated_at` | `TEXT` | No | UTC ISO-8601 |

Proposed SQL:

```sql
CREATE TABLE rooms (
    room_id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    building TEXT NOT NULL CHECK (length(trim(building)) > 0),
    floor INTEGER NOT NULL CHECK (floor >= 0),
    behavior_profile TEXT NOT NULL CHECK (length(trim(behavior_profile)) > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## Table: `cameras`

Stores camera-to-room configuration. A camera may be disabled without deleting history.

| Column | SQLite type | Null | Rules |
|---|---|---:|---|
| `camera_id` | `TEXT` | No | Primary key; canonical `cam_NNN` identifier |
| `room_id` | `TEXT` | No | Foreign key to `rooms`; unique for current one-camera-per-room contract |
| `enabled` | `INTEGER` | No | Boolean `0` or `1`; default `1` |
| `stale_after_seconds` | `REAL` | No | Greater than zero; default `10` |
| `created_at` | `TEXT` | No | UTC ISO-8601 |
| `updated_at` | `TEXT` | No | UTC ISO-8601 |

Proposed SQL:

```sql
CREATE TABLE cameras (
    camera_id TEXT PRIMARY KEY,
    room_id TEXT NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    stale_after_seconds REAL NOT NULL DEFAULT 10 CHECK (stale_after_seconds > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);
```

## Table: `camera_states`

Stores one durable latest-state row per camera for efficient dashboard reads and restart recovery.

| Column | SQLite type | Null | Rules |
|---|---|---:|---|
| `camera_id` | `TEXT` | No | Primary/foreign key to `cameras` |
| `raw_occupancy` | `INTEGER` | Yes | Non-negative; may exceed room capacity |
| `occupancy` | `INTEGER` | Yes | Non-negative stabilized value; `NULL` means unavailable |
| `status` | `TEXT` | No | `online`, `stale`, or `offline` |
| `observed_at` | `TEXT` | Yes | UTC time of last trustworthy observation |
| `updated_at` | `TEXT` | No | UTC time this state row was updated |
| `diagnostics_json` | `TEXT` | Yes | JSON text for internal diagnostics; never required by frontend contract |

Proposed SQL:

```sql
CREATE TABLE camera_states (
    camera_id TEXT PRIMARY KEY,
    raw_occupancy INTEGER CHECK (raw_occupancy IS NULL OR raw_occupancy >= 0),
    occupancy INTEGER CHECK (occupancy IS NULL OR occupancy >= 0),
    status TEXT NOT NULL CHECK (status IN ('online', 'stale', 'offline')),
    observed_at TEXT,
    updated_at TEXT NOT NULL,
    diagnostics_json TEXT,
    FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
        ON UPDATE CASCADE ON DELETE CASCADE
);
```

State rules enforced by application validation:

- `online` and `stale` normally have an `occupancy` and `observed_at`.
- `offline` may retain `raw_occupancy` for diagnostics, but public display occupancy is unavailable unless a separately documented last-known field is introduced.
- `updated_at` must not precede `observed_at`.

## Table: `occupancy_samples`

Stores sampled observations for diagnostics, re-aggregation, and short-term analysis. This is not a frame-by-frame inference log.

| Column | SQLite type | Null | Rules |
|---|---|---:|---|
| `id` | `INTEGER` | No | Primary key |
| `camera_id` | `TEXT` | No | Foreign key to `cameras` |
| `observed_at` | `TEXT` | No | UTC ISO-8601 |
| `raw_occupancy` | `INTEGER` | No | Non-negative; may exceed capacity |
| `occupancy` | `INTEGER` | No | Non-negative stabilized value |
| `status` | `TEXT` | No | `online` or `stale`; offline gaps should not become zero samples |
| `capacity_snapshot` | `INTEGER` | No | Greater than zero |
| `source_sequence` | `INTEGER` | Yes | Optional monotonic source sequence |
| `source_event_id` | `TEXT` | Yes | Optional idempotency identifier |
| `created_at` | `TEXT` | No | UTC insertion time |

Proposed SQL:

```sql
CREATE TABLE occupancy_samples (
    id INTEGER PRIMARY KEY,
    camera_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    raw_occupancy INTEGER NOT NULL CHECK (raw_occupancy >= 0),
    occupancy INTEGER NOT NULL CHECK (occupancy >= 0),
    status TEXT NOT NULL CHECK (status IN ('online', 'stale')),
    capacity_snapshot INTEGER NOT NULL CHECK (capacity_snapshot > 0),
    source_sequence INTEGER,
    source_event_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (camera_id, observed_at),
    UNIQUE (camera_id, source_event_id)
);

CREATE INDEX ix_occupancy_samples_camera_time
    ON occupancy_samples(camera_id, observed_at);

CREATE INDEX ix_occupancy_samples_observed_at
    ON occupancy_samples(observed_at);
```

SQLite permits multiple `NULL` values in the `source_event_id` uniqueness constraint. Ingestion should use `source_event_id` when the source can provide a stable event identifier and otherwise rely on `(camera_id, observed_at)`.

## Table: `occupancy_buckets_5m`

Stores canonical historical aggregates consumed by `/api/history`.

| Column | SQLite type | Null | Rules |
|---|---|---:|---|
| `camera_id` | `TEXT` | No | Foreign key to `cameras` |
| `bucket_start` | `TEXT` | No | UTC ISO-8601 aligned to a five-minute boundary |
| `avg_occupancy` | `REAL` | No | Non-negative |
| `min_occupancy` | `INTEGER` | No | Non-negative |
| `max_occupancy` | `INTEGER` | No | At least `min_occupancy` |
| `capacity_snapshot` | `INTEGER` | No | Greater than zero |
| `coverage_percentage` | `REAL` | No | Between `0` and `100` |
| `sample_count` | `INTEGER` | No | Zero or greater |
| `expected_sample_count` | `INTEGER` | No | Greater than zero |
| `updated_at` | `TEXT` | No | UTC time aggregate was last calculated |

Proposed SQL:

```sql
CREATE TABLE occupancy_buckets_5m (
    camera_id TEXT NOT NULL,
    bucket_start TEXT NOT NULL,
    avg_occupancy REAL NOT NULL CHECK (avg_occupancy >= 0),
    min_occupancy INTEGER NOT NULL CHECK (min_occupancy >= 0),
    max_occupancy INTEGER NOT NULL CHECK (max_occupancy >= min_occupancy),
    capacity_snapshot INTEGER NOT NULL CHECK (capacity_snapshot > 0),
    coverage_percentage REAL NOT NULL
        CHECK (coverage_percentage >= 0 AND coverage_percentage <= 100),
    sample_count INTEGER NOT NULL CHECK (sample_count >= 0),
    expected_sample_count INTEGER NOT NULL CHECK (expected_sample_count > 0),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (camera_id, bucket_start),
    FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE INDEX ix_occupancy_buckets_time
    ON occupancy_buckets_5m(bucket_start);
```

Application validation must additionally enforce:

```text
min_occupancy <= avg_occupancy <= max_occupancy
sample_count <= expected_sample_count
bucket_start minute % 5 == 0
bucket_start seconds and microseconds == 0
```

## Table: `ingestion_receipts`

Added by migration `0002` after explicit task-owner approval on 2026-08-23. This narrow backend-owned ledger closes the idempotency gap created by controlled sample throttling: every accepted polling event records only its identity and timestamps, while `occupancy_samples` remains limited to the 5–10 second/change/heartbeat policy.

| Column | SQLite type | Null | Rules |
|---|---|---:|---|
| `id` | `INTEGER` | No | Primary key |
| `camera_id` | `TEXT` | No | Foreign key to `cameras`, cascade delete |
| `observed_at` | `TEXT` | No | UTC source observation time |
| `source_event_id` | `TEXT` | Yes | Optional stable source identity |
| `accepted_at` | `TEXT` | No | UTC backend acceptance time |

Both `(camera_id, observed_at)` and `(camera_id, source_event_id)` are unique. Receipts use the raw-sample retention window and are removed in the same bounded maintenance batches. They contain no occupancy payload and are not an inference-frame log.

## API mapping

| API data | Database source |
|---|---|
| `GET /api/rooms` | `rooms` joined with `cameras` |
| `GET /api/rooms/{room_id}` | `rooms`, `cameras`, and `camera_states` |
| `GET /api/occupancy` | `cameras`, `rooms`, and `camera_states` |
| `GET /api/occupancy/{camera_id}` | `camera_states` joined with camera and room capacity |
| `GET /api/history` | `occupancy_buckets_5m`, aggregated to requested hour/day/week granularity |
| `GET/PATCH /api/profile` | authenticated row in `users` |
| `GET/PATCH /api/notification-preferences` | authenticated row in `notification_preferences` |
| notification list/read/dismiss routes | authenticated rows in `user_notifications` |

## Account notification tables

`notification_preferences` has one row per user (`user_id` primary key with cascade delete),
boolean in-app/high-occupancy switches, a constrained 50–100 threshold, a positive cooldown,
and UTC creation/update timestamps. Missing rows use and persist defaults of enabled, 80%,
and 30 minutes.

`user_notifications` stores a UUID, owning user, type/category/title/message, optional source
and recommended room foreign keys, optional occupancy percentage, UTC created/read/dismissed/
expiry timestamps, and an optional unique deduplication key. Indexes cover user, creation,
read, dismissed, `(user_id, created_at)`, and deduplication lookup. A session logout never
deletes or changes either account-owned table.

Display percentage is calculated at the API/domain boundary:

```text
min(occupancy / capacity_snapshot * 100, 100)
```

The raw occupancy value remains unchanged for diagnostics.

## SQLite connection settings

Apply these settings to every connection:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
```

Additional rules:

- Keep write transactions short.
- Use one backend-owned write queue or serialized writer.
- Do not place the SQLite file on a network/shared filesystem.
- Do not share a connection object across threads without an explicit safe connection strategy.
- Back up using SQLite's backup API or a transactionally safe mechanism, not a blind file copy during writes.

## Configuration proposal

```env
DATA_SOURCE=database
DATABASE_URL=sqlite:///./data/occupai.db
RAW_SAMPLE_INTERVAL_SECONDS=10
RAW_SAMPLE_RETENTION_DAYS=30
AGGREGATE_RETENTION_DAYS=365
```

The database path must be configurable and must not resolve outside the intended application data directory without explicit deployment configuration.

## Migration and seed plan

1. Add SQLAlchemy and Alembic dependencies.
2. Generate migration `0001_create_occupancy_schema` containing all tables, foreign keys, checks, and indexes.
3. Add an idempotent seed command for rooms and cameras based on the canonical mock definitions.
4. Add an optional development import command for `history_5min_7days.json`.
5. Add migration tests against a temporary SQLite database.
6. Add repository contract tests that run against both fixture and database repositories.

Seed operations must update mutable metadata intentionally without deleting historical rows or silently changing canonical identifiers.

## Retention and maintenance

- Make retention values configurable; proposed defaults are 30 days for raw samples and 365 days for five-minute buckets.
- Delete expired rows in bounded batches to avoid long write locks.
- Run `PRAGMA optimize` periodically after significant data changes.
- Monitor database file size, write-lock retries, aggregation lag, and failed ingestion events.
- Do not run `VACUUM` on the request path; schedule it only if measurements show it is needed.

## Future PostgreSQL migration triggers

Reconsider PostgreSQL when any of these become true:

- Multiple backend instances must write concurrently.
- The database must be remote or shared between machines.
- Camera count or write frequency grows substantially.
- Long analytical queries interfere with ingestion.
- Replication, high availability, or online backups are required.

Keep repository interfaces, migrations, UTC handling, and SQL usage reasonably portable, but do not claim automatic SQLite/PostgreSQL compatibility without testing both engines.
