from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path


@dataclass(frozen=True)
class OccupancyRecord:
    camera_id: str
    timestamp: str
    raw_occupancy: int
    stable_occupancy: int
    processing_ms: float
    inference_ms: float
    source_fps: float | None
    sampled_fps: float
    dropped_frames: int

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


class JsonlSink:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.path.open("a", encoding="utf-8")

    def write(self, record: OccupancyRecord) -> None:
        self._stream.write(record.to_json() + "\n")
        self._stream.flush()

    def close(self) -> None:
        self._stream.close()


def timestamp_now(timestamp: float | None = None) -> str:
    if timestamp is None:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")
    return datetime.fromtimestamp(timestamp, timezone.utc).astimezone().isoformat(timespec="milliseconds")
