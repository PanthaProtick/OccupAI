"""Simulated occupancy ingestion for cameras not backed by a real model server.

Uses the same deterministic behavior-profile curves as the mock data generator,
with live Gaussian noise, to produce realistic occupancy readings that flow
through the standard SerializedDatabaseWriter pipeline.
"""

from __future__ import annotations

import json
import random
import threading
import logging
import uuid
from datetime import datetime, timezone

from mock.occupancy_patterns import occupancy_at

from backend.ingestion import IngestionRecord, SerializedDatabaseWriter


logger = logging.getLogger(__name__)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class SimulatedCamera:
    """Configuration for a single simulated camera."""

    __slots__ = ("camera_id", "capacity", "behavior_profile")

    def __init__(self, camera_id: str, capacity: int, behavior_profile: str) -> None:
        self.camera_id = camera_id
        self.capacity = capacity
        self.behavior_profile = behavior_profile


class SimulatedIngestionService:
    """Generates realistic fake occupancy data for cameras without a physical feed.

    Runs a daemon thread that produces one reading per camera every
    ``tick_interval_seconds``.  Each reading uses the behavior-profile curve
    for the current wall-clock hour plus Gaussian noise, then feeds it through
    the shared ``SerializedDatabaseWriter`` so the rest of the system treats it
    identically to real model-server data.
    """

    def __init__(
        self,
        cameras: list[SimulatedCamera],
        writer: SerializedDatabaseWriter,
        tick_interval_seconds: float = 10.0,
        seed: int = 42,
    ) -> None:
        if not cameras:
            raise ValueError("At least one simulated camera is required")
        self.cameras = cameras
        self.writer = writer
        self.tick_interval_seconds = tick_interval_seconds
        self._rng = random.Random(seed)
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="simulated-ingestion", daemon=True,
        )
        self.last_error: str | None = None
        self._sequence = 0
        # Source event IDs are durable-idempotency keys.  A per-process
        # sequence alone repeats after a backend restart and would cause every
        # simulated reading to be rejected as an old duplicate.
        self._run_id = uuid.uuid4().hex
        self._drift_offsets: dict[str, float] = {c.camera_id: 0.0 for c in cameras}

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
        """Generate one round of simulated readings for all cameras."""
        results: dict[str, bool] = {}

        for camera in self.cameras:
            try:
                # Timestamp each reading when this camera is processed. A large
                # all-room simulation cycle must not make later/earlier cameras
                # appear stale merely because the cycle itself takes time.
                now = datetime.now(timezone.utc)
                fraction = occupancy_at(camera.behavior_profile, now, camera.camera_id)
                
                # Random walk drift for organic movement (people entering/leaving)
                drift_change = self._rng.choice([-2.0, -1.0, 0.0, 1.0, 2.0])
                new_drift = self._drift_offsets[camera.camera_id] * 0.85 + drift_change
                # Clamp drift to +/- 5% of capacity so it doesn't wander infinitely
                max_drift = camera.capacity * 0.05
                self._drift_offsets[camera.camera_id] = _clamp(new_drift, -max_drift, max_drift)
                
                base_val = camera.capacity * fraction + self._drift_offsets[camera.camera_id]
                
                noise = self._rng.gauss(0, camera.capacity * 0.02)
                raw = int(round(_clamp(base_val + noise, 0, camera.capacity)))
                
                stable_noise = self._rng.gauss(0, camera.capacity * 0.01)
                stable = int(round(_clamp(base_val + stable_noise, 0, camera.capacity)))

                self._sequence += 1
                record = IngestionRecord(
                    camera_id=camera.camera_id,
                    observed_at=now,
                    raw_occupancy=raw,
                    occupancy=stable,
                    status="online",
                    source_event_id=f"sim-{self._run_id}-{camera.camera_id}-{self._sequence}",
                    source_sequence=self._sequence,
                )
                results[camera.camera_id] = self.writer.ingest(record)
            except Exception as exc:
                logger.warning(json.dumps({
                    "event": "simulated_ingestion_failed",
                    "camera_id": camera.camera_id,
                    "error_type": type(exc).__name__,
                }, sort_keys=True))
                results[camera.camera_id] = False

        self.last_error = None
        return results

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception as exc:
                self.last_error = type(exc).__name__
                logger.warning(json.dumps({
                    "event": "simulated_ingestion_tick_failed",
                    "error_type": self.last_error,
                }, sort_keys=True))
            self._stop.wait(self.tick_interval_seconds)
