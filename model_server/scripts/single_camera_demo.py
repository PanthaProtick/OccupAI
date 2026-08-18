from ultralytics import YOLO
import cv2

# -----------------------------
# Configuration
# -----------------------------

VIDEO_PATH = "model_server/videos/test5.mp4"
MODEL_PATH = "model_server/models/yolo11m.pt"

CONFIDENCE = 0.25
IMAGE_SIZE = 960
DISPLAY_WIDTH = 900


# -----------------------------
# Load model
# -----------------------------

model = YOLO(MODEL_PATH)


# -----------------------------
# Start tracking
# -----------------------------

results = model.track(
    VIDEO_PATH,
    classes=[0],                 # 0 = person
    tracker="model_server/config/bytetrack_custom.yaml",
    conf=CONFIDENCE,
    imgsz=IMAGE_SIZE,
    device=0,
    stream=True,
)


# -----------------------------
# Create resizable window
# -----------------------------

cv2.namedWindow("Occupancy", cv2.WINDOW_NORMAL)


# -----------------------------
# Process frames
# -----------------------------

try:
    for result in results:
        frame = result.orig_img
        raw_count = 0

        if result.boxes.id is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            track_ids = result.boxes.id.int().cpu().tolist()
            raw_count = len(track_ids)

            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = map(int, box)

                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(
                    frame,
                    f"ID:{track_id}",
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                )

        cv2.putText(
            frame,
            f"Raw: {raw_count}",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )

        height, width = frame.shape[:2]
        scale = DISPLAY_WIDTH / width
        display_frame = cv2.resize(
            frame,
            (DISPLAY_WIDTH, int(height * scale)),
            interpolation=cv2.INTER_AREA,
        )

        cv2.imshow("Occupancy", display_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    cv2.destroyAllWindows()
