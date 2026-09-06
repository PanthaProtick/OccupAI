from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.assistant import AssistantRoomSnapshot, execute_query_plan, parse_assistant_query
from backend.database import Base, CameraRow, CameraStateRow, RoomRow
from backend.models import CameraStatus, Occupancy, Room
from backend.repositories import DatabaseOccupancyRepository


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)


def snapshot(
    name: str,
    occupancy: int | None,
    *,
    capacity: int = 40,
    floor: int = 1,
    status: CameraStatus = CameraStatus.ONLINE,
    enabled: bool = True,
    fresh: bool = True,
    observed: bool = True,
    occupancy_room_id: str | None = None,
    building: str = "University Building",
) -> AssistantRoomSnapshot:
    slug = name.lower().replace(" ", "_")
    room_id = f"room_{slug}"
    camera_id = f"cam_{abs(hash(name)) % 1000:03d}"
    room = Room(
        room_id=room_id, name=name, capacity=capacity, building=building,
        floor=floor, camera_id=camera_id, behavior_profile="study_room",
    )
    percentage = None if occupancy is None else min(occupancy / capacity * 100, 100)
    reading = Occupancy(
        camera_id=camera_id, room_id=occupancy_room_id or room_id, occupancy=occupancy,
        raw_occupancy=occupancy, capacity=capacity, occupancy_percentage=percentage,
        status=status, updated_at=NOW,
    )
    return AssistantRoomSnapshot(
        room=room, occupancy=reading, camera_enabled=enabled,
        observed_at=NOW if observed else None, is_fresh=fresh,
    )


class _Source:
    generated_at = NOW

    def __init__(self, snapshots):
        self.snapshots = snapshots
        self.calls = 0

    def list_rooms(self):
        raise AssertionError("query engine must use the trusted bulk snapshot boundary")

    def list_occupancy(self):
        raise AssertionError("query engine must use the trusted bulk snapshot boundary")

    def list_assistant_snapshots(self):
        self.calls += 1
        return self.snapshots


class AssistantQueryEngineTests(unittest.TestCase):
    def test_only_enabled_fresh_online_complete_consistent_readings_are_candidates(self):
        source = _Source([
            snapshot("1A01", 10),
            snapshot("1A02", 10, enabled=False),
            snapshot("1A03", 10, fresh=False),
            snapshot("1A04", 10, status=CameraStatus.STALE),
            snapshot("1A05", 10, status=CameraStatus.OFFLINE),
            snapshot("1A06", None),
            snapshot("1A07", 10, observed=False),
            snapshot("1A08", 41),
            snapshot("1A09", 10, occupancy_room_id="room_9a99"),
        ])
        results = execute_query_plan(source, parse_assistant_query("available rooms"))
        self.assertEqual([item.name for item in results], ["1A01"])
        self.assertEqual(source.calls, 1)

    def test_filters_and_available_capacity_are_calculated_from_trusted_values(self):
        source = _Source([
            snapshot("1A01", 8, capacity=40, floor=1),
            snapshot("1B01", 4, capacity=20, floor=1),
            snapshot("2A01", 5, capacity=50, floor=2),
            snapshot("1A09", 1, capacity=50, floor=1, building="Engineering Annex"),
        ])
        plan = parse_assistant_query(
            "available rooms in the University Building on first floor in A Block below 30% for 25 people"
        )
        results = execute_query_plan(source, plan)
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.name, "1A01")
        self.assertEqual(result.occupancy_percentage, 20)
        self.assertEqual(result.available_capacity, 32)
        self.assertEqual(result.status, CameraStatus.ONLINE)
        self.assertEqual(result.observed_at, NOW)

    def test_engine_does_not_rank_or_apply_top_limit_before_module_five(self):
        source = _Source([
            snapshot("1A03", 30),
            snapshot("1A01", 4),
            snapshot("1A02", 12),
        ])
        results = execute_query_plan(source, parse_assistant_query("top one available room"))
        self.assertEqual([item.name for item in results], ["1A03", "1A01", "1A02"])

    def test_missing_reading_is_never_treated_as_zero(self):
        results = execute_query_plan(
            _Source([snapshot("1A01", None), snapshot("1A02", 0)]),
            parse_assistant_query("available rooms"),
        )
        self.assertEqual([(item.name, item.occupancy) for item in results], [("1A02", 0)])

    def test_database_repository_uses_one_joined_read_and_enforces_feed_freshness(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = create_engine(f"sqlite:///{(Path(directory) / 'assistant.db').as_posix()}")
            Base.metadata.create_all(engine)
            sessions = sessionmaker(engine, expire_on_commit=False)
            now = datetime.now(timezone.utc)
            with sessions.begin() as db:
                for index, (name, enabled, age) in enumerate((
                    ("1A01", True, 1), ("1A02", False, 1), ("1A03", True, 120),
                ), start=1):
                    room_id, camera_id = f"room_{name.lower()}", f"cam_{index:03d}"
                    timestamp = now.isoformat()
                    db.add(RoomRow(
                        room_id=room_id, name=name, capacity=40, building="University Building",
                        floor=1, behavior_profile="study_room", created_at=timestamp, updated_at=timestamp,
                    ))
                    db.add(CameraRow(
                        camera_id=camera_id, room_id=room_id, enabled=enabled,
                        stale_after_seconds=10, created_at=timestamp, updated_at=timestamp,
                    ))
                    db.add(CameraStateRow(
                        camera_id=camera_id, raw_occupancy=5, occupancy=5, status="online",
                        observed_at=(now - timedelta(seconds=age)).isoformat(), updated_at=timestamp,
                    ))

            statement_count = 0
            def count_statement(*_):
                nonlocal statement_count
                statement_count += 1
            event.listen(engine, "before_cursor_execute", count_statement)
            source = DatabaseOccupancyRepository(sessions)
            snapshots = source.list_assistant_snapshots()
            event.remove(engine, "before_cursor_execute", count_statement)
            self.assertEqual(statement_count, 1)
            self.assertEqual(
                [(item.room.name, item.camera_enabled, item.is_fresh) for item in snapshots],
                [("1A01", True, True), ("1A02", False, True), ("1A03", True, False)],
            )
            results = execute_query_plan(source, parse_assistant_query("available rooms"))
            self.assertEqual([item.name for item in results], ["1A01"])
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
