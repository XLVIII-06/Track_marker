"""
Output helpers for tracking CSVs, debug images, and annotated videos.
"""

from pathlib import Path

import cv2
import pandas as pd

try:
    from tqdm import tqdm
except ImportError as exc:
    raise ImportError("tqdm is required for progress output. Install it with 'pip install tqdm'.") from exc

try:
    from .undistort import Undistorter
    from .video_io import get_video_properties, open_video, open_video_writer
except ImportError:
    from undistort import Undistorter
    from video_io import get_video_properties, open_video, open_video_writer


MARKER_COLORS = [
    (0, 255, 0),
    (0, 255, 255),
    (255, 255, 0),
    (255, 0, 255),
    (0, 128, 255),
    (255, 128, 0),
    (128, 255, 0),
    (255, 0, 128),
]


def save_tracking_csv(tracking_df, output_csv):
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    tracking_df.to_csv(output_csv, index=False)


def save_chessboard_debug_image(image, pattern_size, corners, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    preview = image.copy()
    cv2.drawChessboardCorners(preview, pattern_size, corners, True)
    ok = cv2.imwrite(str(output_path), preview)
    if not ok:
        raise RuntimeError(f"Could not save debug image: {output_path}")


def _build_overlay_lines(frame_idx, frame_rows, num_markers):
    lines = [f"Frame {frame_idx}"]
    frame_rows = frame_rows.set_index("particle_id")

    for particle_id in range(num_markers):
        if particle_id not in frame_rows.index:
            lines.append(f"ID {particle_id}: missing")
            continue

        row = frame_rows.loc[particle_id]
        if bool(row["detected"]):
            lines.append(
                "ID {pid}: uv=({u:.1f}, {v:.1f}) XY=({X:.1f}, {Y:.1f})".format(
                    pid=particle_id,
                    u=row["u"],
                    v=row["v"],
                    X=row["X_mm"],
                    Y=row["Y_mm"],
                )
            )
        else:
            lines.append(f"ID {particle_id}: missing")

    return lines


def _draw_overlay(frame, lines):
    overlay = frame.copy()
    margin = 10
    line_height = 20
    width = 520
    height = margin * 2 + line_height * len(lines)

    cv2.rectangle(overlay, (5, 5), (5 + width, 5 + height), (0, 0, 0), thickness=-1)
    frame = cv2.addWeighted(overlay, 0.45, frame, 0.55, 0)

    for index, line in enumerate(lines):
        origin = (margin + 5, margin + 20 + index * line_height)
        cv2.putText(
            frame,
            line,
            origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    return frame


def _draw_roi(frame, roi):
    if roi is None:
        return frame

    x, y, w, h = [int(value) for value in roi]
    cv2.rectangle(frame, (x, y), (x + w, y + h), (80, 80, 255), 1)
    return frame


def _draw_markers(frame, frame_rows):
    for _, row in frame_rows.iterrows():
        if not bool(row["detected"]):
            continue

        center = (int(round(row["u"])), int(round(row["v"])))
        particle_id = int(row["particle_id"])
        color = MARKER_COLORS[particle_id % len(MARKER_COLORS)]

        cv2.circle(frame, center, 8, color, 2)
        cv2.putText(
            frame,
            f"ID {particle_id}",
            (center[0] + 10, center[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )

    return frame


def write_annotated_video(
    video_path,
    intrinsics_path,
    tracking_df,
    output_video,
    num_markers,
    codec="mp4v",
    roi=None,
):
    cap = open_video(video_path)
    try:
        fps, width, height, frame_count = get_video_properties(cap)
        writer = open_video_writer(output_video, codec, fps, (width, height))
        undistorter = Undistorter(intrinsics_path)
        frame_groups = {
            frame_idx: rows.copy()
            for frame_idx, rows in tracking_df.groupby("frame", sort=True)
        }

        frame_idx = 0
        try:
            progress = tqdm(
                total=frame_count if frame_count > 0 else None,
                desc="Writing annotated video",
                unit="frame",
            )
            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    frame = undistorter.undistort(frame)
                    frame_rows = frame_groups.get(frame_idx)
                    if frame_rows is None:
                        frame_rows = pd.DataFrame(columns=tracking_df.columns)

                    frame = _draw_roi(frame, roi)
                    frame = _draw_markers(frame, frame_rows)
                    frame = _draw_overlay(
                        frame,
                        _build_overlay_lines(frame_idx, frame_rows, num_markers),
                    )
                    writer.write(frame)
                    frame_idx += 1
                    progress.update(1)
            finally:
                progress.close()
        finally:
            writer.release()
    finally:
        cap.release()
