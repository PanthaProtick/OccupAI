from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


def _load_tracker_args(path: str | Path) -> SimpleNamespace:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to load the ByteTrack configuration") from exc
    with Path(path).open(encoding="utf-8") as stream:
        values = yaml.safe_load(stream) or {}
    values.pop("tracker_type", None)
    # Ultralytics expects these fields as attributes. Keep track_buffer explicit and configurable.
    return SimpleNamespace(**values, with_reid=False)


class PerCameraTrackerManager:
    """Own one ByteTrack instance per camera; IDs never cross camera boundaries."""

    def __init__(self, camera_ids: list[str], tracker_config: str | Path, input_fps: float) -> None:
        from ultralytics.trackers.byte_tracker import BYTETracker

        args = _load_tracker_args(tracker_config)
        self._tracker_class = BYTETracker
        self._tracker_args = args
        self._input_fps = input_fps
        # Recent Ultralytics releases removed BYTETracker's frame_rate parameter;
        # keep the compatibility fallback for the older project environments.
        self._trackers = {camera_id: self._new_tracker() for camera_id in camera_ids}

    def _new_tracker(self) -> Any:
        try:
            return self._tracker_class(self._tracker_args)
        except TypeError:
            return self._tracker_class(self._tracker_args, frame_rate=max(1, round(self._input_fps)))

    def reset(self, camera_id: str) -> None:
        if camera_id not in self._trackers:
            raise KeyError(f"unknown camera: {camera_id}")
        self._trackers[camera_id] = self._new_tracker()

    def update(
        self, camera_id: str, boxes: object, frame: object
    ) -> tuple[int, list[int], list[tuple[float, float, float, float, int]]]:
        if camera_id not in self._trackers:
            raise KeyError(f"unknown camera: {camera_id}")
        tracks = self._trackers[camera_id].update(boxes, frame)
        if isinstance(tracks, np.ndarray):
            # Current Ultralytics returns [x1,y1,x2,y2,track_id,score,class,idx].
            ids = [int(track_id) for track_id in tracks[:, 4]] if len(tracks) else []
            observations = [
                (float(row[0]), float(row[1]), float(row[2]), float(row[3]), int(row[4]))
                for row in tracks
            ]
            return len(ids), ids, observations
        active = [track for track in tracks if getattr(track, "is_activated", True)]
        ids = [int(track.track_id) for track in active]
        observations = []
        for track in active:
            box = getattr(track, "tlbr", None)
            if box is None:
                x, y, width, height = track.tlwh
                box = (x, y, x + width, y + height)
            observations.append((*[float(value) for value in box], int(track.track_id)))
        return len(ids), ids, observations
