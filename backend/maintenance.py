from __future__ import annotations

import json
import sqlite3
import threading
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy.engine import make_url

from sqlalchemy import delete, select, tuple_
from sqlalchemy.dialects.sqlite import insert

from backend.database import (
    CameraRow, CameraStateRow, IngestionReceiptRow, OccupancyBucketRow,
    OccupancySampleRow, RoomRow,
)


logger = logging.getLogger(__name__)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_bucket_start(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None or parsed.utcoffset() != timedelta(0):
        raise ValueError(f"Bucket timestamp must be UTC: {value}")
    if parsed.minute % 5 or parsed.second or parsed.microsecond:
        raise ValueError(f"Bucket timestamp must align to a UTC five-minute boundary: {value}")
    return iso(parsed)


def seed_canonical(session_factory, fixture_dir: Path) -> None:
    payload = json.loads((fixture_dir / "rooms.json").read_text(encoding="utf-8"))
    now = iso(datetime.now(timezone.utc))
    with session_factory.begin() as session:
        desired_rooms = {item["room_id"] for item in payload["rooms"]}
        desired_mapping = {item["camera_id"]: item["room_id"] for item in payload["rooms"]}
        existing_cameras = session.scalars(select(CameraRow)).all()
        retired_camera_ids = {
            row.camera_id for row in existing_cameras
            if row.camera_id not in desired_mapping or desired_mapping[row.camera_id] != row.room_id
        }
        retired_room_ids = {
            row.room_id for row in session.scalars(select(RoomRow)).all()
            if row.room_id not in desired_rooms
        }
        if retired_camera_ids:
            session.execute(delete(OccupancyBucketRow).where(OccupancyBucketRow.camera_id.in_(retired_camera_ids)))
            session.execute(delete(OccupancySampleRow).where(OccupancySampleRow.camera_id.in_(retired_camera_ids)))
            session.execute(delete(IngestionReceiptRow).where(IngestionReceiptRow.camera_id.in_(retired_camera_ids)))
            session.execute(delete(CameraStateRow).where(CameraStateRow.camera_id.in_(retired_camera_ids)))
            session.execute(delete(CameraRow).where(CameraRow.camera_id.in_(retired_camera_ids)))
        if retired_room_ids:
            session.execute(delete(RoomRow).where(RoomRow.room_id.in_(retired_room_ids)))
        for item in payload["rooms"]:
            existing_for_room = session.scalar(select(CameraRow).where(CameraRow.room_id == item["room_id"]))
            if existing_for_room and existing_for_room.camera_id != item["camera_id"]:
                raise ValueError(f"Refusing to change canonical camera for {item['room_id']}")
            existing_camera = session.get(CameraRow, item["camera_id"])
            if existing_camera and existing_camera.room_id != item["room_id"]:
                raise ValueError(
                    f"Refusing to remap canonical camera {item['camera_id']} from {existing_camera.room_id} to {item['room_id']}"
                )
            room_values = {key: item[key] for key in ("room_id", "name", "capacity", "building", "floor", "behavior_profile")}
            statement = insert(RoomRow).values(**room_values, created_at=now, updated_at=now)
            session.execute(statement.on_conflict_do_update(index_elements=[RoomRow.room_id], set_={**room_values, "updated_at": now}))
            statement = insert(CameraRow).values(camera_id=item["camera_id"], room_id=item["room_id"], enabled=True,
                                                 stale_after_seconds=10, created_at=now, updated_at=now)
            session.execute(statement.on_conflict_do_update(index_elements=[CameraRow.camera_id], set_={"enabled": True, "updated_at": now}))
            state = insert(CameraStateRow).values(camera_id=item["camera_id"], status="offline", updated_at=now)
            session.execute(state.on_conflict_do_nothing(index_elements=[CameraStateRow.camera_id]))


def import_history(session_factory, path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records", payload.get("buckets", payload.get("data", payload if isinstance(payload, list) else [])))
    count = 0
    with session_factory.begin() as session:
        cameras = {row.room_id: row.camera_id for row in session.scalars(select(CameraRow)).all()}
        for item in records:
            room_id = item.get("room_id")
            canonical_camera = cameras.get(room_id)
            camera_id = item.get("camera_id") or canonical_camera
            if canonical_camera is None:
                raise ValueError(f"History contains unknown room: {room_id}")
            if camera_id != canonical_camera:
                raise ValueError(
                    f"History camera mapping mismatch for {room_id}: expected {canonical_camera}, received {camera_id}"
                )
            expected_count = item.get("expected_sample_count", 100)
            sample_count = item.get("sample_count", round(item.get("coverage_percentage", 100) / 100 * expected_count))
            bucket_start = validate_bucket_start(item["bucket_start"])
            values = dict(camera_id=camera_id, bucket_start=bucket_start, avg_occupancy=item["avg_occupancy"],
                          min_occupancy=item["min_occupancy"], max_occupancy=item["max_occupancy"],
                          capacity_snapshot=item["capacity_snapshot"], coverage_percentage=item.get("coverage_percentage", 100),
                          sample_count=sample_count, expected_sample_count=expected_count,
                          updated_at=payload.get("generated_at", iso(datetime.now(timezone.utc))))
            statement = insert(OccupancyBucketRow).values(**values)
            session.execute(statement.on_conflict_do_update(index_elements=["camera_id", "bucket_start"], set_=values))
            count += 1
    return count


def aggregate_five_minute_buckets(session_factory, expected_sample_count: int = 30, batch_size: int = 100) -> int:
    if expected_sample_count <= 0 or batch_size <= 0:
        raise ValueError("expected_sample_count and batch_size must be positive")
    samples: list[OccupancySampleRow] = []
    with session_factory() as session:
        camera_ids = session.scalars(select(OccupancySampleRow.camera_id).distinct()).all()
        for camera_id in camera_ids:
            latest_bucket = session.scalar(select(OccupancyBucketRow.bucket_start).where(
                OccupancyBucketRow.camera_id == camera_id
            ).order_by(OccupancyBucketRow.bucket_start.desc()).limit(1))
            statement = select(OccupancySampleRow).where(OccupancySampleRow.camera_id == camera_id)
            if latest_bucket is not None:
                statement = statement.where(OccupancySampleRow.observed_at >= latest_bucket)
            samples.extend(session.scalars(statement.order_by(OccupancySampleRow.observed_at)).all())
    groups: dict[tuple[str, str], list[OccupancySampleRow]] = {}
    for sample in samples:
        observed = datetime.fromisoformat(sample.observed_at.replace("Z", "+00:00"))
        start = observed.replace(minute=observed.minute - observed.minute % 5, second=0, microsecond=0)
        groups.setdefault((sample.camera_id, iso(start)), []).append(sample)
    now = iso(datetime.now(timezone.utc))
    rows: list[dict[str, object]] = []
    for (camera_id, start), items in groups.items():
        values = [item.occupancy for item in items]
        rows.append(dict(camera_id=camera_id, bucket_start=start, avg_occupancy=sum(values) / len(values),
                   min_occupancy=min(values), max_occupancy=max(values), capacity_snapshot=items[-1].capacity_snapshot,
                   coverage_percentage=min(len(values) / expected_sample_count * 100, 100), sample_count=len(values),
                   expected_sample_count=max(expected_sample_count, len(values)), updated_at=now))
    for offset in range(0, len(rows), batch_size):
        with session_factory.begin() as session:
            for row in rows[offset:offset + batch_size]:
                statement = insert(OccupancyBucketRow).values(**row)
                session.execute(statement.on_conflict_do_update(index_elements=["camera_id", "bucket_start"], set_=row))
    return len(groups)


def apply_retention(session_factory, raw_days: int, aggregate_days: int, batch_size: int = 1000) -> tuple[int, int]:
    if raw_days <= 0 or aggregate_days <= 0 or batch_size <= 0:
        raise ValueError("retention days and batch_size must be positive")
    now = datetime.now(timezone.utc)
    deleted = []
    with session_factory.begin() as session:
        sample_ids = session.scalars(select(OccupancySampleRow.id).where(OccupancySampleRow.observed_at < iso(now - timedelta(days=raw_days))).limit(batch_size)).all()
        deleted.append(session.execute(delete(OccupancySampleRow).where(OccupancySampleRow.id.in_(sample_ids))).rowcount if sample_ids else 0)
        receipt_ids = session.scalars(select(IngestionReceiptRow.id).where(
            IngestionReceiptRow.observed_at < iso(now - timedelta(days=raw_days))
        ).limit(batch_size)).all()
        if receipt_ids:
            session.execute(delete(IngestionReceiptRow).where(IngestionReceiptRow.id.in_(receipt_ids)))
        bucket_keys = session.execute(select(OccupancyBucketRow.camera_id, OccupancyBucketRow.bucket_start).where(
            OccupancyBucketRow.bucket_start < iso(now - timedelta(days=aggregate_days))).limit(batch_size)).all()
        predicate = tuple_(OccupancyBucketRow.camera_id, OccupancyBucketRow.bucket_start).in_(bucket_keys)
        deleted.append(session.execute(delete(OccupancyBucketRow).where(predicate)).rowcount if bucket_keys else 0)
    return deleted[0], deleted[1]


def backup_sqlite_database(database_url: str, destination: Path) -> None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("Backup requires a file-backed SQLite DATABASE_URL")
    source_path = Path(url.database).resolve()
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(source_path)
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


class DatabaseMaintenanceService:
    """Runs incremental aggregation and bounded retention outside request handlers."""

    def __init__(
        self,
        session_factory,
        raw_retention_days: int,
        aggregate_retention_days: int,
        retention_batch_size: int,
        expected_sample_count: int,
        interval_seconds: float = 60.0,
    ) -> None:
        self.session_factory = session_factory
        self.raw_retention_days = raw_retention_days
        self.aggregate_retention_days = aggregate_retention_days
        self.retention_batch_size = retention_batch_size
        self.expected_sample_count = expected_sample_count
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="database-maintenance", daemon=True)
        self.last_error: str | None = None

    def run_once(self) -> tuple[int, tuple[int, int]]:
        try:
            aggregated = aggregate_five_minute_buckets(
                self.session_factory, self.expected_sample_count, batch_size=100
            )
            deleted = apply_retention(
                self.session_factory, self.raw_retention_days,
                self.aggregate_retention_days, self.retention_batch_size,
            )
            self.last_error = None
            return aggregated, deleted
        except Exception as exc:
            self.last_error = type(exc).__name__
            logger.exception("database maintenance failed")
            raise

    def start(self) -> None:
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)

    @property
    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception:
                pass
            self._stop.wait(self.interval_seconds)
