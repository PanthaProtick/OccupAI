from __future__ import annotations

from dataclasses import dataclass
from threading import Event
from time import monotonic, sleep, time
from typing import Callable

from .camera_source import CameraSource
from .detector import SharedPersonDetector
from .occupancy import JsonlSink, OccupancyRecord, timestamp_now
from .stabilization import OccupancyStabilizer
from .tracker_manager import PerCameraTrackerManager
from .visualizer import OccupancyVisualizer


@dataclass
class CameraScheduleState:
    last_sample_at: float = 0.0
    last_sequence: int = 0
    processed_samples: int = 0
    first_sample_at: float | None = None
    last_cycle: int = -1


def run_scheduler(
    cameras: list[CameraSource],
    detector: SharedPersonDetector,
    trackers: PerCameraTrackerManager,
    sink: JsonlSink,
    sample_fps: float,
    visualizer: OccupancyVisualizer | None = None,
    stabilization_window_seconds: float = 2.0,
    stop_event: Event | None = None,
    on_update: Callable[[OccupancyRecord], None] | None = None,
    on_camera_error: Callable[[str], None] | None = None,
) -> None:
    if sample_fps <= 0:
        raise ValueError("sample_fps must be greater than zero")
    states = {camera.camera_id: CameraScheduleState() for camera in cameras}
    stabilizers = {
        camera.camera_id: OccupancyStabilizer(window_seconds=stabilization_window_seconds)
        for camera in cameras
    }
    interval = 1.0 / sample_fps
    cursor = 0

    while stop_event is None or not stop_event.is_set():
        made_progress = False
        now = monotonic()
        for _ in cameras:
            camera = cameras[cursor % len(cameras)]
            cursor += 1
            state = states[camera.camera_id]
            if now - state.last_sample_at < interval:
                continue
            packet = camera.latest_frame()
            if camera.error and on_camera_error is not None:
                on_camera_error(camera.camera_id)
            if packet is None or packet.sequence == state.last_sequence:
                continue

            if packet.cycle != state.last_cycle:
                # A looped file is a new camera sequence. Prevent the tracker
                # and stabilizer from associating the end with the beginning.
                trackers.reset(camera.camera_id)
                stabilizers[camera.camera_id] = OccupancyStabilizer(
                    window_seconds=stabilization_window_seconds
                )
                state.last_cycle = packet.cycle

            started = monotonic()
            try:
                detection = detector.detect(packet.frame)
                raw_count, _, observations = trackers.update(camera.camera_id, detection.boxes, packet.frame)
            except Exception as exc:
                # A source-specific failure must not stop the other cameras.
                state.last_sample_at = monotonic()
                state.last_sequence = packet.sequence
                print(f"{camera.camera_id}: sample failed: {exc}")
                continue
            state.last_sample_at = monotonic()
            state.last_sequence = packet.sequence
            state.processed_samples += 1
            state.first_sample_at = state.first_sample_at or state.last_sample_at
            elapsed = state.last_sample_at - state.first_sample_at if state.first_sample_at else 0.0
            sampled_fps = state.processed_samples / elapsed if elapsed > 0 else 0.0
            processing_ms = (monotonic() - started) * 1000.0
            sample_timestamp = time()
            stable_count = stabilizers[camera.camera_id].update(raw_count, timestamp=sample_timestamp)
            capture_stats = camera.stats()
            record = OccupancyRecord(
                camera_id=camera.camera_id,
                timestamp=timestamp_now(sample_timestamp),
                raw_occupancy=raw_count,
                stable_occupancy=stable_count,
                processing_ms=processing_ms,
                inference_ms=detection.inference_ms,
                source_fps=camera.source_fps,
                sampled_fps=sampled_fps,
                dropped_frames=capture_stats["dropped_frames"],
            )
            sink.write(record)
            if on_update is not None:
                on_update(record)
            if visualizer is not None:
                visualizer.show(
                    camera.camera_id,
                    packet.frame,
                    observations,
                    raw_count,
                    stable_count,
                    processing_ms,
                )
                if visualizer.quit_requested and stop_event is not None:
                    stop_event.set()
                if visualizer.quit_requested:
                    return
            made_progress = True

        if all(camera.ended for camera in cameras):
            # Allow the final latest frames to be consumed before exiting.
            if not made_progress and all(
                camera.latest_frame() is None
                or states[camera.camera_id].last_sequence == camera.latest_frame().sequence
                for camera in cameras
            ):
                return
        sleep(0.001 if made_progress else 0.01)
