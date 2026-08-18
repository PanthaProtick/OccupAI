from __future__ import annotations

from datetime import datetime
from threading import RLock
import time
from typing import Any

from .occupancy import OccupancyRecord


class LatestOccupancyStore:
    """Thread-safe latest-only occupancy state for the API layer."""

    def __init__(self, camera_ids: list[str], stale_after_seconds: float = 10.0) -> None:
        if stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be greater than zero")
        self.stale_after_seconds = stale_after_seconds
        self._lock = RLock()
        self._states: dict[str, dict[str, Any]] = {
            camera_id: {
                "raw_occupancy": None,
                "occupancy": None,
                "updated_at": None,
                "status": "offline",
                "_updated_epoch": None,
            }
            for camera_id in camera_ids
        }

    def update(self, record: OccupancyRecord) -> None:
        updated_epoch = datetime.fromisoformat(record.timestamp).timestamp()
        with self._lock:
            state = self._states[record.camera_id]
            state.update(
                raw_occupancy=record.raw_occupancy,
                occupancy=record.stable_occupancy,
                updated_at=record.timestamp,
                status="online",
                _updated_epoch=updated_epoch,
            )

    def mark_offline(self, camera_id: str) -> None:
        with self._lock:
            if camera_id in self._states:
                self._states[camera_id]["status"] = "offline"

    def snapshot(self) -> dict[str, dict[str, Any]]:
        now = time.time()
        with self._lock:
            result: dict[str, dict[str, Any]] = {}
            for camera_id, state in self._states.items():
                public_state = {key: value for key, value in state.items() if not key.startswith("_")}
                updated_epoch = state["_updated_epoch"]
                if updated_epoch is not None and now - updated_epoch > self.stale_after_seconds:
                    public_state["status"] = "stale"
                result[camera_id] = public_state
            return result

    def camera_snapshot(self, camera_id: str) -> dict[str, Any] | None:
        return self.snapshot().get(camera_id)

