from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True)
class DetectionResult:
    boxes: object
    inference_ms: float


class SharedPersonDetector:
    """One shared YOLO model used by all cameras."""

    def __init__(self, model_path: str, imgsz: int, device: str | int, confidence: float) -> None:
        from ultralytics import YOLO

        self.model = YOLO(model_path)
        self.imgsz = imgsz
        self.device = device
        self.confidence = confidence

    def detect(self, frame: object) -> DetectionResult:
        started = perf_counter()
        results = self.model.predict(
            source=frame,
            imgsz=self.imgsz,
            classes=[0],
            device=self.device,
            conf=self.confidence,
            verbose=False,
        )
        if not results:
            raise RuntimeError("YOLO returned no result for a frame")
        # ByteTrack performs NumPy operations internally. Keep YOLO inference on
        # CUDA, then transfer only the compact detection tensor to host memory
        # before handing it to the tracker.
        return DetectionResult(results[0].boxes.cpu(), (perf_counter() - started) * 1000.0)
