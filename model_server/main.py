from __future__ import annotations

import argparse
from pathlib import Path
import time

from .camera_source import CameraSource
from .detector import SharedPersonDetector
from .occupancy import JsonlSink
from .scheduler import run_scheduler
from .tracker_manager import PerCameraTrackerManager
from .visualizer import OccupancyVisualizer


def load_config(path: str | Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required; install project dependencies first") from exc
    with Path(path).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the multi-camera occupancy checkpoint")
    parser.add_argument("--config", default="model_server/config/cameras.yaml")
    parser.add_argument("--log", default="model_server/logs/occupancy.jsonl")
    parser.add_argument("--display", action="store_true", help="show annotated camera windows; press q to stop")
    args = parser.parse_args()
    config = load_config(args.config)
    camera_configs = config["cameras"]
    cameras = [
        CameraSource(
            item["camera_id"],
            item["source"],
            loop=item.get("loop", config.get("loop_videos", False)),
        )
        for item in camera_configs
    ]
    detector = SharedPersonDetector(config["model"], config["imgsz"], config["device"], config["confidence"])
    trackers = PerCameraTrackerManager(
        [camera.camera_id for camera in cameras], config["tracker_config"], config["sample_fps"]
    )
    sink = JsonlSink(args.log)
    visualizer = OccupancyVisualizer() if args.display else None
    for camera in cameras:
        camera.start()
    started = time.monotonic()
    try:
        run_scheduler(
            cameras,
            detector,
            trackers,
            sink,
            config["sample_fps"],
            visualizer,
            config.get("stabilization_window_seconds", 2.0),
        )
    finally:
        for camera in cameras:
            camera.stop()
        sink.close()
        if visualizer is not None:
            visualizer.close()
    duration = max(time.monotonic() - started, 1e-9)
    for camera in cameras:
        stats = camera.stats()
        print(f"{camera.camera_id}: captured={stats['captured_frames']} dropped={stats['dropped_frames']} duration={duration:.1f}s")
        if camera.error:
            print(f"{camera.camera_id}: {camera.error}")


if __name__ == "__main__":
    main()
