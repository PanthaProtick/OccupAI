import unittest
from datetime import datetime, timezone
import time
from unittest.mock import patch

from model_server.model_state import LatestOccupancyStore
from model_server.occupancy import OccupancyRecord


def record(camera_id: str, timestamp: str, raw: int = 4, stable: int = 5) -> OccupancyRecord:
    return OccupancyRecord(camera_id, timestamp, raw, stable, 1.0, 1.0, None, 3.0, 0)


class LatestOccupancyStoreTests(unittest.TestCase):
    def test_initial_cameras_are_offline(self) -> None:
        store = LatestOccupancyStore(["camera_01"])
        self.assertEqual(store.snapshot()["camera_01"]["status"], "offline")

    def test_update_preserves_latest_only_state(self) -> None:
        store = LatestOccupancyStore(["camera_01"])
        now = time.time()
        timestamp = datetime.fromtimestamp(now, timezone.utc).isoformat()
        store.update(record("camera_01", timestamp, raw=4, stable=5))
        with patch("model_server.model_state.time.time", return_value=now):
            state = store.camera_snapshot("camera_01")
        self.assertEqual(state["raw_occupancy"], 4)
        self.assertEqual(state["occupancy"], 5)
        self.assertEqual(state["status"], "online")

    def test_old_state_becomes_stale(self) -> None:
        store = LatestOccupancyStore(["camera_01"], stale_after_seconds=10.0)
        now = time.time()
        timestamp = datetime.fromtimestamp(now, timezone.utc).isoformat()
        store.update(record("camera_01", timestamp))
        with patch("model_server.model_state.time.time", return_value=now + 11.0):
            self.assertEqual(store.camera_snapshot("camera_01")["status"], "stale")

    def test_unknown_camera_is_not_in_store(self) -> None:
        store = LatestOccupancyStore(["camera_01"])
        self.assertIsNone(store.camera_snapshot("camera_99"))


if __name__ == "__main__":
    unittest.main()
