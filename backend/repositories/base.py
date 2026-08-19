from __future__ import annotations

from datetime import datetime
from typing import Protocol

from backend.models import HistoryMetric, HistoryPoint, HistoryRange, Occupancy, Room, RoomView


class OccupancyRepository(Protocol):
    generated_at: datetime

    def list_rooms(self) -> list[Room]: ...

    def get_room(self, room_id: str) -> RoomView | None: ...

    def list_occupancy(self) -> list[Occupancy]: ...

    def get_occupancy(self, camera_id: str) -> Occupancy | None: ...

    def get_history(
        self,
        room_id: str,
        history_range: HistoryRange,
        metric: HistoryMetric,
    ) -> list[HistoryPoint] | None: ...
