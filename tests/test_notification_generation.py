from __future__ import annotations

import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.database import (
    Base,
    CameraRow,
    CameraStateRow,
    NotificationPreferenceRow,
    RoomRow,
    UserNotificationRow,
    UserRow,
    make_session_factory,
)
from backend.ingestion import IngestionRecord, SerializedDatabaseWriter


class NotificationGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        database = Path(self.temp.name) / "generation.db"
        self.url = f"sqlite:///{database.as_posix()}"
        self.engine = create_engine(
            self.url,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(self.engine)
        self.sessions = make_session_factory(self.engine)
        self.writer = SerializedDatabaseWriter(self.sessions, sample_interval_seconds=5)
        self.start = datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc)
        with self.sessions.begin() as db:
            self._add_room(db, "room_target", "Target 201", "Building One", 2, "cam_001", 100, 0, "offline")
            self._add_room(db, "room_same_floor", "Nearby 202", "Building One", 2, "cam_002", 100, 30)
            self._add_room(db, "room_other_floor", "Nearby 301", "Building One", 3, "cam_003", 100, 10)
            self._add_room(db, "room_other_building", "Remote 201", "Building Two", 2, "cam_004", 100, 5)
        self.default_user = self._add_user("default-user")

    def tearDown(self):
        self.engine.dispose()
        self.temp.cleanup()

    def _add_room(
        self,
        db,
        room_id: str,
        name: str,
        building: str,
        floor: int,
        camera_id: str,
        capacity: int,
        occupancy: int,
        status: str = "online",
    ) -> None:
        stamp = self.start.isoformat()
        db.add(RoomRow(
            room_id=room_id,
            name=name,
            capacity=capacity,
            building=building,
            floor=floor,
            behavior_profile="classroom",
            created_at=stamp,
            updated_at=stamp,
            camera=CameraRow(
                camera_id=camera_id,
                enabled=True,
                stale_after_seconds=120,
                created_at=stamp,
                updated_at=stamp,
                state=CameraStateRow(
                    camera_id=camera_id,
                    raw_occupancy=occupancy,
                    occupancy=occupancy,
                    status=status,
                    observed_at=stamp,
                    updated_at=stamp,
                ),
            ),
        ))

    def _add_user(
        self,
        prefix: str,
        *,
        enabled: bool | None = None,
        threshold: int = 80,
        cooldown: int = 30,
    ) -> str:
        user_id = str(uuid.uuid4())
        stamp = self.start.isoformat()
        with self.sessions.begin() as db:
            db.add(UserRow(
                id=user_id,
                name=prefix,
                email=f"{prefix}@aust.edu",
                normalized_email=f"{prefix}@aust.edu",
                password_hash="not-used",
                role="user",
                is_active=True,
                created_at=stamp,
                updated_at=stamp,
            ))
            if enabled is not None:
                db.add(NotificationPreferenceRow(
                    user_id=user_id,
                    in_app_enabled=enabled,
                    high_occupancy_enabled=enabled,
                    high_occupancy_threshold=threshold,
                    cooldown_minutes=cooldown,
                    created_at=stamp,
                    updated_at=stamp,
                ))
        return user_id

    def _ingest(self, minute: int, occupancy: int, status: str = "online", event: str | None = None) -> bool:
        return self.writer.ingest(IngestionRecord(
            camera_id="cam_001",
            observed_at=self.start + timedelta(minutes=minute),
            raw_occupancy=occupancy,
            occupancy=occupancy,
            status=status,
            source_event_id=event or f"event-{minute}-{occupancy}-{status}",
        ))

    def _notifications(self, user_id: str) -> list[UserNotificationRow]:
        with self.sessions() as db:
            return list(db.scalars(
                select(UserNotificationRow)
                .where(UserNotificationRow.user_id == user_id)
                .order_by(UserNotificationRow.created_at)
            ))

    def test_threshold_crossing_cooldown_preferences_and_recommendation(self):
        disabled_user = self._add_user("disabled-user", enabled=False)
        threshold_user = self._add_user("threshold-user", enabled=True, threshold=90)

        self.assertTrue(self._ingest(1, 85))
        default_notifications = self._notifications(self.default_user)
        self.assertEqual(len(default_notifications), 1)
        self.assertEqual(default_notifications[0].room_id, "room_target")
        self.assertEqual(default_notifications[0].suggested_room_id, "room_same_floor")
        self.assertEqual(default_notifications[0].occupancy_percentage, 85)
        self.assertEqual(self._notifications(disabled_user), [])
        self.assertEqual(self._notifications(threshold_user), [])

        self.assertTrue(self._ingest(2, 90))
        self.assertEqual(len(self._notifications(self.default_user)), 1)
        self.assertEqual(len(self._notifications(threshold_user)), 1)

        self.assertTrue(self._ingest(3, 70))
        self.assertTrue(self._ingest(4, 85))
        self.assertEqual(len(self._notifications(self.default_user)), 1)

        self.assertTrue(self._ingest(32, 70))
        self.assertTrue(self._ingest(33, 85))
        self.assertEqual(len(self._notifications(self.default_user)), 2)

        before_stale = len(self._notifications(self.default_user))
        self.assertTrue(self._ingest(34, 95, status="stale"))
        self.assertEqual(len(self._notifications(self.default_user)), before_stale)
        self.assertTrue(self.writer.mark_offline("cam_001"))
        self.assertEqual(len(self._notifications(self.default_user)), before_stale)

    def test_duplicate_ingestion_cannot_create_duplicate_notification(self):
        record = IngestionRecord(
            camera_id="cam_001",
            observed_at=self.start + timedelta(minutes=1),
            raw_occupancy=85,
            occupancy=85,
            status="online",
            source_event_id="concurrent-event",
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(self.writer.ingest, (record, record)))
        self.assertEqual(sorted(results), [False, True])
        notifications = self._notifications(self.default_user)
        self.assertEqual(len(notifications), 1)
        self.assertIsNotNone(notifications[0].deduplication_key)

    def test_no_false_recommendation_when_no_online_lower_room_exists(self):
        with self.sessions.begin() as db:
            for camera_id in ("cam_002", "cam_003", "cam_004"):
                db.get(CameraStateRow, camera_id).status = "offline"
        self.assertTrue(self._ingest(1, 85))
        notification = self._notifications(self.default_user)[0]
        self.assertIsNone(notification.suggested_room_id)
        self.assertNotIn("nearby room is available", notification.message)

    def test_stale_online_candidate_is_not_recommended(self):
        with self.sessions.begin() as db:
            for camera_id in ("cam_003", "cam_004"):
                db.get(CameraStateRow, camera_id).status = "offline"
            same_floor = db.get(CameraStateRow, "cam_002")
            same_floor.status = "online"
            same_floor.observed_at = (self.start - timedelta(minutes=2)).isoformat()
        self.assertTrue(self._ingest(1, 85))
        self.assertIsNone(self._notifications(self.default_user)[0].suggested_room_id)


if __name__ == "__main__":
    unittest.main()
