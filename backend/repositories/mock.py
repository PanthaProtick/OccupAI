from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from backend.models import (
    CameraStatus,
    HistoryMetric,
    HistoryPoint,
    HistoryRange,
    Occupancy,
    Room,
    RoomView,
)


def _fixture_datetime(value: Any, location: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise FixtureError(f"Invalid {location} timestamp: {exc}") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise FixtureError(f"Invalid {location} timestamp: UTC offset required")
    return parsed


class FixtureError(RuntimeError):
    """Raised when mock fixtures are missing, malformed, or inconsistent."""


class MockOccupancyRepository:
    REQUIRED_FILES = ("rooms.json", "live_occupancy.json", "historical_api_views.json")

    def __init__(self, fixture_dir: Path) -> None:
        self.fixture_dir = fixture_dir
        self._assert_files_exist()
        rooms_payload = self._read_json("rooms.json")
        live_payload = self._read_json("live_occupancy.json")
        history_payload = self._read_json("historical_api_views.json")

        try:
            rooms = TypeAdapter(list[Room]).validate_python(rooms_payload["rooms"])
            self.generated_at = _fixture_datetime(rooms_payload["generated_at"], "rooms.generated_at")
        except (KeyError, ValueError, ValidationError) as exc:
            raise FixtureError(f"Invalid rooms.json: {exc}") from exc

        self._rooms = {room.room_id: room for room in rooms}
        self._rooms_by_camera = {room.camera_id: room for room in rooms}
        if len(self._rooms) != len(rooms) or len(self._rooms_by_camera) != len(rooms):
            raise FixtureError("Room IDs and camera IDs must each be unique")

        try:
            live_items = live_payload["cameras"]
            self._history_views = history_payload["views"]["range"]
            self.history_generated_at = _fixture_datetime(history_payload["generated_at"], "history.generated_at")
        except (KeyError, TypeError, ValueError) as exc:
            raise FixtureError(f"Invalid live/history fixture structure: {exc}") from exc

        if not isinstance(live_items, list):
            raise FixtureError("Invalid live_occupancy.json: cameras must be a list")

        self._occupancy: dict[str, Occupancy] = {}
        for item in live_items:
            self._add_live_item(item)

        missing = set(self._rooms_by_camera) - set(self._occupancy)
        unknown = set(self._occupancy) - set(self._rooms_by_camera)
        if missing or unknown:
            raise FixtureError(f"Camera mapping mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}")
        self._validate_history_views()

    def _assert_files_exist(self) -> None:
        missing = [name for name in self.REQUIRED_FILES if not (self.fixture_dir / name).is_file()]
        if missing:
            raise FixtureError(f"Missing fixture files in {self.fixture_dir}: {', '.join(missing)}")

    def _read_json(self, filename: str) -> dict[str, Any]:
        try:
            return json.loads((self.fixture_dir / filename).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FixtureError(f"Unable to read {filename}: {exc}") from exc

    def _add_live_item(self, item: dict[str, Any]) -> None:
        try:
            camera_id = item["camera_id"]
            room = self._rooms_by_camera[camera_id]
            raw_occupancy = int(item["occupancy"])
            status = CameraStatus(item["status"])
            updated_at = _fixture_datetime(item["updated_at"], "live.updated_at")
        except (KeyError, TypeError, ValueError, FixtureError) as exc:
            raise FixtureError(f"Invalid live occupancy item {item!r}: {exc}") from exc

        # Offline means no trustworthy display value. The raw value remains available
        # for diagnostics, keeping "unavailable" distinct from a real zero occupancy.
        display_occupancy = None if status is CameraStatus.OFFLINE else raw_occupancy
        percentage = None
        if display_occupancy is not None:
            percentage = round(min(display_occupancy / room.capacity * 100, 100.0), 2)

        try:
            occupancy = Occupancy(
                camera_id=camera_id, room_id=room.room_id, occupancy=display_occupancy,
                raw_occupancy=raw_occupancy, capacity=room.capacity,
                occupancy_percentage=percentage, status=status, updated_at=updated_at,
            )
        except ValidationError as exc:
            raise FixtureError(f"Invalid live occupancy item {item!r}: {exc}") from exc
        if camera_id in self._occupancy:
            raise FixtureError(f"Duplicate live occupancy camera ID: {camera_id}")
        self._occupancy[camera_id] = occupancy

    def _validate_history_views(self) -> None:
        maximum_counts = {HistoryRange.HOUR: 168, HistoryRange.DAY: 7, HistoryRange.WEEK: 1}
        expected_ranges = {item.value for item in HistoryRange}
        if not isinstance(self._history_views, dict) or set(self._history_views) != expected_ranges:
            raise FixtureError(f"History ranges must be exactly {sorted(expected_ranges)}")
        for history_range in HistoryRange:
            rooms = self._history_views.get(history_range.value)
            if not isinstance(rooms, dict) or set(rooms) != set(self._rooms):
                raise FixtureError(f"History room mappings are incomplete for range={history_range.value}")
            for room_id in self._rooms:
                try:
                    metrics = rooms[room_id]["metric"]
                except (KeyError, TypeError) as exc:
                    raise FixtureError(f"Invalid history structure for room={room_id}, range={history_range.value}") from exc
                if not isinstance(metrics, dict) or set(metrics) != {item.value for item in HistoryMetric}:
                    raise FixtureError(f"History metrics are incomplete for room={room_id}, range={history_range.value}")
                for metric in HistoryMetric:
                    try:
                        points = TypeAdapter(list[HistoryPoint]).validate_python(metrics[metric.value])
                    except ValidationError as exc:
                        raise FixtureError(
                            f"Invalid historical view for room={room_id}, range={history_range.value}, metric={metric.value}: {exc}"
                        ) from exc
                    if len(points) > maximum_counts[history_range]:
                        raise FixtureError(
                            f"History count exceeds {maximum_counts[history_range]} for room={room_id}, range={history_range.value}"
                        )
                    timestamps = [point.bucket_start for point in points]
                    if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
                        raise FixtureError(
                            f"History points must be uniquely ordered for room={room_id}, range={history_range.value}, metric={metric.value}"
                        )

    def list_rooms(self) -> list[Room]:
        return list(self._rooms.values())

    def get_room(self, room_id: str) -> RoomView | None:
        room = self._rooms.get(room_id)
        if room is None:
            return None
        occupancy = self._occupancy[room.camera_id]
        percentage = occupancy.occupancy_percentage
        intensity = None if percentage is None else self._intensity(percentage)
        return RoomView(
            **room.model_dump(),
            occupancy=occupancy.occupancy,
            raw_occupancy=occupancy.raw_occupancy,
            occupancy_percentage=percentage,
            intensity=intensity,
            status=occupancy.status,
            updated_at=occupancy.updated_at,
        )

    def list_occupancy(self) -> list[Occupancy]:
        return list(self._occupancy.values())

    def get_occupancy(self, camera_id: str) -> Occupancy | None:
        return self._occupancy.get(camera_id)

    def get_history(
        self,
        room_id: str,
        history_range: HistoryRange,
        metric: HistoryMetric,
    ) -> list[HistoryPoint] | None:
        if room_id not in self._rooms:
            return None
        try:
            raw_points = self._history_views[history_range.value][room_id]["metric"][metric.value]
            return TypeAdapter(list[HistoryPoint]).validate_python(raw_points)
        except (KeyError, TypeError, ValidationError) as exc:
            raise FixtureError(
                f"Invalid historical view for room={room_id}, range={history_range}, metric={metric}: {exc}"
            ) from exc

    @staticmethod
    def _intensity(percentage: float) -> str:
        if percentage < 25:
            return "Low"
        if percentage < 50:
            return "Moderate"
        if percentage < 80:
            return "Busy"
        return "Very Busy"

