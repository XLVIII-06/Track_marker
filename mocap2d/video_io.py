"""
Video input/output helpers for the 2D mocap pipeline.
"""

from pathlib import Path

import cv2


def open_video(video_path):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")
    return cap


def get_video_properties(cap):
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps <= 0:
        fps = 30.0

    return fps, width, height, frame_count


def extract_frame(video_path, frame_index=0):
    if frame_index < 0:
        raise ValueError("frame_index must be non-negative.")

    cap = open_video(video_path)
    try:
        _, _, _, frame_count = get_video_properties(cap)
        if frame_count > 0 and frame_index >= frame_count:
            raise ValueError(
                f"frame_index {frame_index} is outside the video frame range 0..{frame_count - 1}."
            )

        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
        ret, frame = cap.read()
        if not ret:
            raise RuntimeError(f"Could not read frame {frame_index} from video: {video_path}")

        return frame
    finally:
        cap.release()


def open_video_writer(output_path, codec, fps, size):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*codec),
        fps,
        size,
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer: {output_path}")
    return writer
