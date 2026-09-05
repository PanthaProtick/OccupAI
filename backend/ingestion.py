from __future__ import annotations

import re
import threading
import logging
from datetime import datetime, timezone
from typing import Any
import json
import urllib.request
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.dialects.sqlite import insert

from backend.database import (
    CameraRow,
    CameraStateRow,
    IngestionReceiptRow,
    NotificationPreferenceRow,
    OccupancySampleRow,
    RoomRow,
    UserNotificationRow,
    UserRow,
)
from backend.maintenance import iso


logger = logging.getLogger(__name__)


class IngestionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    camera_id: str
    observed_at: datetime
    raw_occupancy: int = Field(ge=0)
    occupancy: int = Field(ge=0)
    source_event_id: str | None = None
    source_sequence: int | None = None
    status: str = Field(default="online", pattern="^(online|stale)$")

    @field_validator("camera_id", mode="before")
    @classmethod
    def normalize_camera(cls, value: Any) -> str:
        match = re.fullmatch(r"(?:cam[_-]?)?(\d{1,3})", str(value).lower())
        if not match:
            raise ValueError("camera_id must identify a canonical camera")
        return f"cam_{int(match.group(1)):03d}"

    @field_validator("observed_at")
    @classmethod
    def utc_only(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("observed_at must include a UTC offset")
        return value.astimezone(timezone.utc)


class SerializedDatabaseWriter:
    def __init__(self, session_factory, sample_interval_seconds: float = 10.0) -> None:
        self.session_factory = session_factory
        self.sample_interval_seconds = sample_interval_seconds
        self._lock = threading.Lock()

    def ingest(self, record: IngestionRecord) -> bool:
        with self._lock, self.session_factory.begin() as session:
            camera = session.scalar(select(CameraRow).where(CameraRow.camera_id == record.camera_id))
            if camera is None or not camera.enabled:
                return False
            timestamp = iso(record.observed_at)
            receipt_conditions = [IngestionReceiptRow.observed_at == timestamp]
            if record.source_event_id is not None:
                receipt_conditions.append(IngestionReceiptRow.source_event_id == record.source_event_id)
            received = session.scalar(select(IngestionReceiptRow.id).where(
                IngestionReceiptRow.camera_id == record.camera_id, or_(*receipt_conditions)
            ))
            if received is not None:
                return False
            duplicate_conditions = [OccupancySampleRow.observed_at == timestamp]
            if record.source_event_id is not None:
                duplicate_conditions.append(OccupancySampleRow.source_event_id == record.source_event_id)
            duplicate = session.scalar(select(OccupancySampleRow.id).where(
                OccupancySampleRow.camera_id == record.camera_id, or_(*duplicate_conditions)
            ))
            if duplicate is not None:
                return False
            previous = session.get(CameraStateRow, record.camera_id)
            previous_diagnostics: dict[str, Any] = {}
            if previous and previous.diagnostics_json:
                try:
                    previous_diagnostics = json.loads(previous.diagnostics_json)
                except (TypeError, json.JSONDecodeError):
                    previous_diagnostics = {}
            if previous and previous.observed_at:
                previous_time = datetime.fromisoformat(previous.observed_at.replace("Z", "+00:00"))
                if record.observed_at <= previous_time:
                    return False
            if record.source_event_id and previous_diagnostics.get("source_event_id") == record.source_event_id:
                return False
            meaningful_change = previous is None or previous.occupancy != record.occupancy or previous.status != record.status
            last_sample_time = session.scalar(select(OccupancySampleRow.observed_at).where(
                OccupancySampleRow.camera_id == record.camera_id).order_by(OccupancySampleRow.observed_at.desc()).limit(1))
            interval_elapsed = last_sample_time is None or (
                record.observed_at - datetime.fromisoformat(last_sample_time.replace("Z", "+00:00"))
            ).total_seconds() >= self.sample_interval_seconds
            diagnostics = {"source": "model_server"}
            if record.source_event_id is not None:
                diagnostics["source_event_id"] = record.source_event_id
            if record.source_sequence is not None:
                diagnostics["source_sequence"] = record.source_sequence
            self._create_high_occupancy_notifications(
                session,
                camera,
                previous,
                record,
                timestamp,
            )
            state = dict(camera_id=record.camera_id, raw_occupancy=record.raw_occupancy, occupancy=record.occupancy,
                         status=record.status, observed_at=timestamp, updated_at=iso(datetime.now(timezone.utc)),
                         diagnostics_json=json.dumps(diagnostics, sort_keys=True))
            statement = insert(CameraStateRow).values(**state)
            session.execute(statement.on_conflict_do_update(index_elements=[CameraStateRow.camera_id], set_=state))
            session.add(IngestionReceiptRow(
                camera_id=record.camera_id,
                observed_at=timestamp,
                source_event_id=record.source_event_id,
                accepted_at=iso(datetime.now(timezone.utc)),
            ))
            sample = dict(camera_id=record.camera_id, observed_at=timestamp, raw_occupancy=record.raw_occupancy,
                          occupancy=record.occupancy, status=record.status, capacity_snapshot=camera.room.capacity,
                          source_event_id=record.source_event_id, source_sequence=record.source_sequence,
                          created_at=iso(datetime.now(timezone.utc)))
            if meaningful_change or interval_elapsed:
                statement = insert(OccupancySampleRow).values(**sample).on_conflict_do_nothing()
                session.execute(statement)
            return True

    @staticmethod
    def _recommended_room(
        session,
        crowded_camera: CameraRow,
        crowded_percentage: float,
        event_time: datetime,
    ) -> str | None:
        candidates: list[tuple[tuple[int, int, int, float, str], str]] = []
        rows = session.execute(
            select(RoomRow, CameraRow, CameraStateRow)
            .join(CameraRow, CameraRow.room_id == RoomRow.room_id)
            .join(CameraStateRow, CameraStateRow.camera_id == CameraRow.camera_id)
            .where(
                RoomRow.room_id != crowded_camera.room_id,
                CameraRow.enabled.is_(True),
                CameraStateRow.status == "online",
                CameraStateRow.occupancy.is_not(None),
            )
        )
        for room, camera, state in rows:
            if state.observed_at is None:
                continue
            observed_at = datetime.fromisoformat(state.observed_at).astimezone(timezone.utc)
            if (event_time - observed_at).total_seconds() > camera.stale_after_seconds:
                continue
            percentage = state.occupancy * 100 / room.capacity
            if percentage >= crowded_percentage:
                continue
            rank = (
                0 if room.building == crowded_camera.room.building else 1,
                0 if room.floor == crowded_camera.room.floor else 1,
                0 if percentage < 40 else 1,
                percentage,
                room.room_id,
            )
            candidates.append((rank, room.room_id))
        return min(candidates)[1] if candidates else None

    def _create_high_occupancy_notifications(
        self,
        session,
        camera: CameraRow,
        previous: CameraStateRow | None,
        record: IngestionRecord,
        timestamp: str,
    ) -> None:
        if record.status != "online":
            return
        current_percentage = min(100.0, record.occupancy * 100 / camera.room.capacity)
        user_preferences = session.execute(
            select(UserRow, NotificationPreferenceRow)
            .outerjoin(NotificationPreferenceRow, NotificationPreferenceRow.user_id == UserRow.id)
            .where(UserRow.is_active.is_(True))
        )
        recommendation: str | None = None
        recommendation_loaded = False
        event_time = record.observed_at.astimezone(timezone.utc)
        for user, preference in user_preferences:
            in_app_enabled = preference.in_app_enabled if preference else True
            high_occupancy_enabled = preference.high_occupancy_enabled if preference else True
            threshold = preference.high_occupancy_threshold if preference else 80
            cooldown_minutes = preference.cooldown_minutes if preference else 30
            if not in_app_enabled or not high_occupancy_enabled or current_percentage < threshold:
                continue
            previous_percentage = None
            if previous and previous.status == "online" and previous.occupancy is not None:
                previous_percentage = min(100.0, previous.occupancy * 100 / camera.room.capacity)
            if previous_percentage is not None and previous_percentage >= threshold:
                continue

            latest = session.scalar(
                select(UserNotificationRow.created_at)
                .where(
                    UserNotificationRow.user_id == user.id,
                    UserNotificationRow.type == "high_occupancy",
                    UserNotificationRow.room_id == camera.room_id,
                )
                .order_by(UserNotificationRow.created_at.desc())
                .limit(1)
            )
            if latest is not None:
                last_time = datetime.fromisoformat(latest).astimezone(timezone.utc)
                if (event_time - last_time).total_seconds() < cooldown_minutes * 60:
                    continue
            if not recommendation_loaded:
                recommendation = self._recommended_room(
                    session, camera, current_percentage, event_time
                )
                recommendation_loaded = True
            room_name = camera.room.name
            message = f"{room_name} is {current_percentage:.1f}% occupied. Consider another room."
            if recommendation:
                message += " A less occupied nearby room is available."
            session.add(UserNotificationRow(
                id=str(uuid.uuid4()),
                user_id=user.id,
                type="high_occupancy",
                category="occupancy",
                title=f"High occupancy in {room_name}",
                message=message,
                room_id=camera.room_id,
                suggested_room_id=recommendation,
                occupancy_percentage=round(current_percentage, 2),
                deduplication_key=f"high_occupancy:{user.id}:{camera.room_id}:{timestamp}",
                created_at=timestamp,
            ))

    def mark_offline(self, camera_id: str, diagnostics: str | None = None) -> bool:
        with self._lock, self.session_factory.begin() as session:
            state = session.get(CameraStateRow, camera_id)
            if state:
                state.status = "offline"
                state.updated_at = iso(datetime.now(timezone.utc))
                state.diagnostics_json = diagnostics
                return True
            return False

    def mark_many_offline(self, camera_ids: tuple[str, ...], reason: str) -> None:
        diagnostics = json.dumps({"source": "model_server", "error": reason}, sort_keys=True)
        for camera_id in camera_ids:
            self.mark_offline(camera_id, diagnostics)


class ModelServerIngestionAdapter:
    """Polls the model server's latest-state endpoint and hands validated records to one writer."""

    def __init__(self, endpoint: str, writer: SerializedDatabaseWriter, timeout_seconds: float = 2.0) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.writer = writer
        self.timeout_seconds = timeout_seconds

    def poll_once(self) -> dict[str, bool]:
        try:
            with urllib.request.urlopen(f"{self.endpoint}/occupancy", timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except Exception as exc:
            raise RuntimeError(f"Model server unavailable: {type(exc).__name__}") from exc
        cameras = payload.get("cameras")
        if not isinstance(cameras, dict):
            raise ValueError("Malformed model-server response: cameras must be an object")
        results: dict[str, bool] = {}
        for source_id, item in cameras.items():
            try:
                normalized = IngestionRecord.normalize_camera(source_id)
                if not isinstance(item, dict):
                    raise ValueError("camera state must be an object")
                status = item.get("status", "offline")
                if status == "offline":
                    self.writer.mark_offline(normalized, json.dumps({"source": "model_server"}))
                    results[normalized] = True
                    continue
                record = IngestionRecord(camera_id=source_id, observed_at=item.get("updated_at") or item.get("timestamp"),
                                         raw_occupancy=item["raw_occupancy"], occupancy=item["occupancy"], status=status,
                                         source_event_id=item.get("event_id"), source_sequence=item.get("sequence"))
                results[record.camera_id] = self.writer.ingest(record)
            except Exception:
                try:
                    self.writer.mark_offline(normalized, json.dumps({
                        "source": "model_server", "error": "malformed_camera_response",
                    }, sort_keys=True))
                except Exception:
                    pass
                results[str(source_id)] = False
        return results


class ModelServerIngestionService:
    """Owns polling lifecycle; API reads remain independent from model-server availability."""

    def __init__(
        self,
        adapter: ModelServerIngestionAdapter,
        writer: SerializedDatabaseWriter,
        configured_camera_ids: tuple[str, ...],
        poll_interval_seconds: float = 2.0,
    ) -> None:
        self.adapter = adapter
        self.writer = writer
        self.configured_camera_ids = configured_camera_ids
        self.poll_interval_seconds = poll_interval_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="model-server-ingestion", daemon=True)
        self.last_error: str | None = None

    def start(self) -> None:
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)

    @property
    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def run_once(self) -> dict[str, bool]:
        try:
            result = self.adapter.poll_once()
            self.last_error = None
            return result
        except Exception as exc:
            self.last_error = type(exc).__name__
            self.writer.mark_many_offline(self.configured_camera_ids, self.last_error)
            logger.warning(json.dumps({"event": "model_server_poll_failed", "error_type": self.last_error}))
            return {camera_id: False for camera_id in self.configured_camera_ids}

    def _run(self) -> None:
        while not self._stop.is_set():
            self.run_once()
            self._stop.wait(self.poll_interval_seconds)
