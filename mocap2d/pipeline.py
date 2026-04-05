"""
pipeline.py

用途：
- 串联整个 2D 动作捕捉流程
    视频 -> 去畸变 -> 亮点检测 -> trackpy 跨帧关联 -> 坐标转换 -> 保存 CSV -> 输出标注视频
"""

import argparse

import cv2
import numpy as np
import pandas as pd

try:
    from .detection import detect_markers
    from .tracking import link_markers
    from .transform import CoordinateTransformer
    from .undistort import Undistorter
except ImportError:
    from detection import detect_markers
    from tracking import link_markers
    from transform import CoordinateTransformer
    from undistort import Undistorter


def _open_video(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")
    return cap


def _get_video_properties(cap):
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps <= 0:
        fps = 30.0

    return fps, width, height, frame_count


def _compute_world_coordinates(tracking_df, transformer):
    tracking_df = tracking_df.copy()
    tracking_df["X_mm"] = np.nan
    tracking_df["Y_mm"] = np.nan

    valid_rows = tracking_df["u"].notna() & tracking_df["v"].notna()
    for index in tracking_df.index[valid_rows]:
        X_mm, Y_mm = transformer.pixel_to_world(
            tracking_df.at[index, "u"],
            tracking_df.at[index, "v"],
        )
        tracking_df.at[index, "X_mm"] = float(X_mm)
        tracking_df.at[index, "Y_mm"] = float(Y_mm)

    return tracking_df


def _build_overlay_lines(frame_idx, frame_rows, num_markers):
    lines = [f"Frame {frame_idx}"]
    frame_rows = frame_rows.set_index("particle_id")

    for particle_id in range(num_markers):
        if particle_id in frame_rows.index:
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


def _draw_markers(frame, frame_rows, colors):
    for _, row in frame_rows.iterrows():
        if not bool(row["detected"]):
            continue

        center = (int(round(row["u"])), int(round(row["v"])))
        particle_id = int(row["particle_id"])
        color = colors[particle_id % len(colors)]

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


def _write_annotated_video(
    video_path,
    intrinsics_path,
    tracking_df,
    output_video,
    num_markers,
    codec="mp4v",
):
    cap = _open_video(video_path)
    fps, width, height, _ = _get_video_properties(cap)

    writer = cv2.VideoWriter(
        output_video,
        cv2.VideoWriter_fourcc(*codec),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open video writer: {output_video}")

    undistorter = Undistorter(intrinsics_path)
    frame_groups = {
        frame_idx: rows.copy()
        for frame_idx, rows in tracking_df.groupby("frame", sort=True)
    }

    colors = [
        (0, 255, 0),
        (0, 255, 255),
        (255, 255, 0),
        (255, 0, 255),
        (0, 128, 255),
        (255, 128, 0),
        (128, 255, 0),
        (255, 0, 128),
    ]

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = undistorter.undistort(frame)
        frame_rows = frame_groups.get(frame_idx)
        if frame_rows is None:
            frame_rows = pd.DataFrame(columns=tracking_df.columns)

        frame = _draw_markers(frame, frame_rows, colors)
        overlay_lines = _build_overlay_lines(frame_idx, frame_rows, num_markers)
        frame = _draw_overlay(frame, overlay_lines)
        writer.write(frame)
        frame_idx += 1

    writer.release()
    cap.release()


def run_pipeline(
    video_path,
    intrinsics_path,
    homography_path,
    output_csv="output.csv",
    output_video="annotated_output.mp4",
    num_markers=5,
    detection_threshold=200,
    detection_min_area=5.0,
    detection_max_area=None,
    blur_kernel_size=5,
    track_search_range=50,
    track_memory=5,
    video_codec="mp4v",
):
    if num_markers <= 0:
        raise ValueError("num_markers must be a positive integer.")

    cap = _open_video(video_path)
    _, _, _, frame_count = _get_video_properties(cap)

    undistorter = Undistorter(intrinsics_path)
    transformer = CoordinateTransformer(homography_path)

    detections = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = undistorter.undistort(frame)
        frame_detections = detect_markers(
            frame,
            num_markers=num_markers,
            threshold=detection_threshold,
            min_area=detection_min_area,
            max_area=detection_max_area,
            blur_kernel_size=blur_kernel_size,
            return_metadata=True,
        )

        for detection in frame_detections:
            detections.append(
                {
                    "frame": frame_idx,
                    **detection,
                }
            )

        frame_idx += 1

    cap.release()
    num_frames = frame_idx if frame_idx > 0 else frame_count

    tracking_df = link_markers(
        detections=detections,
        num_frames=num_frames,
        num_markers=num_markers,
        search_range=track_search_range,
        memory=track_memory,
    )
    tracking_df = _compute_world_coordinates(tracking_df, transformer)

    tracking_df.to_csv(output_csv, index=False)
    _write_annotated_video(
        video_path=video_path,
        intrinsics_path=intrinsics_path,
        tracking_df=tracking_df,
        output_video=output_video,
        num_markers=num_markers,
        codec=video_codec,
    )

    print("Saved CSV:", output_csv)
    print("Saved annotated video:", output_video)
    return tracking_df


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Run the full mocap2d pipeline on a video."
    )
    parser.add_argument("--video", required=True, help="Input video path.")
    parser.add_argument(
        "--intrinsics-path",
        required=True,
        help="Path to intrinsics.json.",
    )
    parser.add_argument(
        "--homography-path",
        required=True,
        help="Path to homography.json.",
    )
    parser.add_argument(
        "--output-csv",
        default="output.csv",
        help="Path to save tracking results CSV.",
    )
    parser.add_argument(
        "--output-video",
        default="annotated_output.mp4",
        help="Path to save the annotated output video.",
    )
    parser.add_argument(
        "--num-markers",
        type=int,
        default=5,
        help="Number of reflective markers to track.",
    )
    parser.add_argument(
        "--detection-threshold",
        type=int,
        default=200,
        help="Grayscale threshold for bright marker detection.",
    )
    parser.add_argument(
        "--detection-min-area",
        type=float,
        default=5.0,
        help="Minimum blob area to keep during detection.",
    )
    parser.add_argument(
        "--detection-max-area",
        type=float,
        default=None,
        help="Optional maximum blob area to keep during detection.",
    )
    parser.add_argument(
        "--blur-kernel-size",
        type=int,
        default=5,
        help="Gaussian blur kernel size used before thresholding.",
    )
    parser.add_argument(
        "--track-search-range",
        type=float,
        default=50,
        help="Maximum per-frame displacement for trackpy linking.",
    )
    parser.add_argument(
        "--track-memory",
        type=int,
        default=5,
        help="Number of frames trackpy keeps a marker alive during temporary misses.",
    )
    parser.add_argument(
        "--video-codec",
        default="mp4v",
        help="FourCC codec used for annotated video output.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_pipeline(
        video_path=args.video,
        intrinsics_path=args.intrinsics_path,
        homography_path=args.homography_path,
        output_csv=args.output_csv,
        output_video=args.output_video,
        num_markers=args.num_markers,
        detection_threshold=args.detection_threshold,
        detection_min_area=args.detection_min_area,
        detection_max_area=args.detection_max_area,
        blur_kernel_size=args.blur_kernel_size,
        track_search_range=args.track_search_range,
        track_memory=args.track_memory,
        video_codec=args.video_codec,
    )
