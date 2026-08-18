from __future__ import annotations

import cv2


class OccupancyVisualizer:
    """Optional OpenCV viewer for demonstrations and manual inspection."""

    def __init__(self, display_width: int = 960) -> None:
        self.display_width = display_width
        self.quit_requested = False

    def show(
        self,
        camera_id: str,
        frame: object,
        observations: list[tuple[float, float, float, float, int]],
        raw_occupancy: int,
        stable_occupancy: int,
        processing_ms: float,
    ) -> None:
        annotated = frame.copy()
        for x1, y1, x2, y2, track_id in observations:
            top_left = (int(x1), int(y1))
            bottom_right = (int(x2), int(y2))
            cv2.rectangle(annotated, top_left, bottom_right, (0, 220, 0), 2)
            cv2.putText(
                annotated,
                f"ID:{track_id}",
                (top_left[0], max(20, top_left[1] - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 220, 0),
                2,
                cv2.LINE_AA,
            )

        cv2.putText(
            annotated,
            f"{camera_id}  Raw: {raw_occupancy}  Stable: {stable_occupancy}  "
            f"processing: {processing_ms:.1f} ms",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )
        height, width = annotated.shape[:2]
        scale = self.display_width / width
        display = cv2.resize(
            annotated,
            (self.display_width, max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
        cv2.imshow(f"Occupancy - {camera_id}", display)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            self.quit_requested = True

    def close(self) -> None:
        cv2.destroyAllWindows()
