from __future__ import annotations

from dataclasses import dataclass
from threading import Lock, Thread
from time import monotonic, sleep
from typing import Optional

import cv2


@dataclass(frozen=True)
class FramePacket:
    frame: object
    captured_at: float
    sequence: int
    cycle: int


class CameraSource:
    """Continuously capture a source while retaining only its newest frame."""

    def __init__(self, camera_id: str, source: str, loop: bool = False) -> None:
        self.camera_id = camera_id
        self.source = source
        self.loop = loop
        self._lock = Lock()
        self._latest: Optional[FramePacket] = None
        self._sequence = 0
        self._dropped = 0
        self._ended = False
        self._error: Optional[str] = None
        self._source_fps: Optional[float] = None
        self._cycle = 0
        self._stop = False
        self._thread = Thread(target=self._capture_loop, name=f"capture-{camera_id}", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop = True
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def latest_frame(self) -> Optional[FramePacket]:
        with self._lock:
            return self._latest

    @property
    def ended(self) -> bool:
        with self._lock:
            return self._ended

    @property
    def error(self) -> Optional[str]:
        with self._lock:
            return self._error

    @property
    def source_fps(self) -> Optional[float]:
        with self._lock:
            return self._source_fps

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {"captured_frames": self._sequence, "dropped_frames": self._dropped}

    def _capture_loop(self) -> None:
        capture = cv2.VideoCapture(self.source)
        if not capture.isOpened():
            with self._lock:
                self._ended = True
                self._error = f"unable to open source: {self.source}"
            return

        source_fps = capture.get(cv2.CAP_PROP_FPS)
        frame_interval = 1.0 / source_fps if source_fps and source_fps > 0 else 0.0
        next_frame_at = monotonic()
        with self._lock:
            self._source_fps = source_fps if source_fps and source_fps > 0 else None

        try:
            while not self._stop:
                if frame_interval:
                    next_frame_at += frame_interval
                    remaining = next_frame_at - monotonic()
                    if remaining > 0:
                        sleep(remaining)
                ok, frame = capture.read()
                if not ok:
                    if not self.loop:
                        break
                    capture.release()
                    capture = cv2.VideoCapture(self.source)
                    if not capture.isOpened():
                        with self._lock:
                            self._error = f"unable to reopen source: {self.source}"
                        break
                    self._cycle += 1
                    next_frame_at = monotonic()
                    continue
                with self._lock:
                    self._sequence += 1
                    if self._latest is not None:
                        self._dropped += 1
                    self._latest = FramePacket(frame, monotonic(), self._sequence, self._cycle)
        except Exception as exc:  # keep other camera pipelines alive
            with self._lock:
                self._error = f"capture failed: {exc}"
        finally:
            capture.release()
            with self._lock:
                self._ended = True
