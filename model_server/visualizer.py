from __future__ import annotations

import cv2


class OccupancyVisualizer:
    """Optional OpenCV viewer for demonstrations and manual inspection."""

    def __init__(self, display_width: int = 960, room_labels: dict[str, str] | None = None) -> None:
        self.display_width = display_width
        self.room_labels = dict(room_labels or {})
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

        height, width = annotated.shape[:2]
        scale = self.display_width / width
        display = cv2.resize(
            annotated,
            (self.display_width, max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
        # Draw after resizing so high-resolution footage cannot shrink the label.
        # A separate header keeps the room name readable without hiding people.
        room = self.room_labels.get(camera_id, camera_id)
        title = f"ROOM {room}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        title_scale = min(1.6, max(0.1, (self.display_width - 40) /
                                 cv2.getTextSize(title, font, 1.0, 3)[0][0]))
        display = cv2.copyMakeBorder(display, 116, 0, 0, 0, cv2.BORDER_CONSTANT, value=(24, 24, 24))
        cv2.putText(display, title, (20, 49), font, title_scale,
                    (255, 255, 255), 3, cv2.LINE_AA)
        details = f"Occupancy: {stable_occupancy}   Raw: {raw_occupancy}   {camera_id}"
        details_scale = min(0.85, max(0.1, (self.display_width - 40) /
                                   cv2.getTextSize(details, font, 1.0, 2)[0][0]))
        cv2.putText(display, details, (20, 94), font, details_scale,
                    (0, 230, 255), 2, cv2.LINE_AA)
        cv2.imshow(f"Room {room} - Occupancy - {camera_id}", display)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            self.quit_requested = True

    def close(self) -> None:
        cv2.destroyAllWindows()
