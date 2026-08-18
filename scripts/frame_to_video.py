import cv2
import glob
import os

# Change this to the folder containing your FRIDA JPG frames
frame_folder = "videos/FRIDA/Frames/Segment_2/Camera_1"

output_video = "videos/frida_segment2_cam1.mp4"

# Get all JPG files
frames = sorted(glob.glob(os.path.join(frame_folder, "*.jpg")))

if not frames:
    raise ValueError("No JPG frames found!")

# Read first frame
first_frame = cv2.imread(frames[0])

height, width = first_frame.shape[:2]

# FRIDA was captured at 1.5 FPS
fps = 1.5

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

video = cv2.VideoWriter(
    output_video,
    fourcc,
    fps,
    (width, height)
)

for frame_path in frames[:500]:
    frame = cv2.imread(frame_path)

    if frame is None:
        print(f"Could not read: {frame_path}")
        continue

    video.write(frame)

video.release()

print(f"Created: {output_video}")