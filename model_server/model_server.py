from __future__ import annotations

import os
from pathlib import Path
from threading import Event, Thread
from typing import Any

from .camera_source import CameraSource
from .detector import SharedPersonDetector
from .main import load_config
from .model_state import LatestOccupancyStore
from .occupancy import JsonlSink
from .scheduler import run_scheduler
from .tracker_manager import PerCameraTrackerManager
from .visualizer import OccupancyVisualizer


class ModelServerWorker:
    """Runs the CV pipeline independently from FastAPI request handling."""

    def __init__(
        self,
        config: dict[str, Any],
        state: LatestOccupancyStore,
        log_path: str | Path,
        display: bool = False,
    ) -> None:
        self.config = config
        self.state = state
        self.log_path = log_path
        self.display = display
        self.stop_event = Event()
        self._thread = Thread(target=self._run, name="occupancy-cv-worker", daemon=True)
        self.error: str | None = None

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=5.0)

    def _run(self) -> None:
        cameras = [
            CameraSource(
                item["camera_id"],
                item["source"],
                loop=item.get("loop", self.config.get("loop_videos", False)),
            )
            for item in self.config["cameras"]
        ]
        sink: JsonlSink | None = None
        visualizer = OccupancyVisualizer() if self.display else None
        try:
            detector = SharedPersonDetector(
                self.config["model"],
                self.config["imgsz"],
                self.config["device"],
                self.config["confidence"],
            )
            trackers = PerCameraTrackerManager(
                [camera.camera_id for camera in cameras],
                self.config["tracker_config"],
                self.config["sample_fps"],
            )
            sink = JsonlSink(self.log_path)
            for camera in cameras:
                camera.start()
            run_scheduler(
                cameras,
                detector,
                trackers,
                sink,
                self.config["sample_fps"],
                stabilization_window_seconds=self.config.get("stabilization_window_seconds", 2.0),
                visualizer=visualizer,
                stop_event=self.stop_event,
                on_update=self.state.update,
                on_camera_error=self.state.mark_offline,
            )
        except Exception as exc:
            self.error = str(exc)
            for camera in cameras:
                self.state.mark_offline(camera.camera_id)
        finally:
            for camera in cameras:
                camera.stop()
            if sink is not None:
                sink.close()
            if visualizer is not None:
                visualizer.close()


def create_model_server(
    config_path: str | Path | None = None,
    log_path: str | Path | None = None,
    stale_after_seconds: float | None = None,
    display: bool | None = None,
):
    from contextlib import asynccontextmanager
    from fastapi import FastAPI, HTTPException

    resolved_config = Path(
        config_path or os.getenv("OCCUPANCY_CONFIG", "model_server/config/cameras.yaml")
    )
    resolved_log = Path(log_path or os.getenv("OCCUPANCY_LOG", "model_server/logs/occupancy.jsonl"))
    config = load_config(resolved_config)
    camera_ids = [item["camera_id"] for item in config["cameras"]]
    stale_seconds = (
        stale_after_seconds
        if stale_after_seconds is not None
        else float(os.getenv("OCCUPANCY_STALE_AFTER_SECONDS", "10.0"))
    )
    state = LatestOccupancyStore(camera_ids, stale_seconds)
    display_enabled = (
        display
        if display is not None
        else os.getenv("OCCUPANCY_DISPLAY", "0").lower() in {"1", "true", "yes"}
    )
    worker = ModelServerWorker(config, state, resolved_log, display=display_enabled)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        worker.start()
        app.state.occupancy_worker = worker
        try:
            yield
        finally:
            worker.stop()

    app = FastAPI(title="Classroom Occupancy Model Server", lifespan=lifespan)

    @app.get("/occupancy")
    def get_occupancy() -> dict[str, dict[str, dict[str, Any]]]:
        return {"cameras": state.snapshot()}

    @app.get("/occupancy/{camera_id}")
    def get_camera_occupancy(camera_id: str) -> dict[str, Any]:
        camera_state = state.camera_snapshot(camera_id)
        if camera_state is None:
            raise HTTPException(status_code=404, detail=f"unknown camera: {camera_id}")
        return camera_state

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_model_server()
