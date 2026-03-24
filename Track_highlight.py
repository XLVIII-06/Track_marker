#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Highlight the brightest reflective marker in each video frame.

This script:
- reads a video from a built-in path or --input
- finds bright blobs by thresholding
- keeps only the brightest blob in each frame
- draws the selected point on the frame
- writes an annotated output video
"""

import argparse
import math
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np


DEFAULT_INPUT_VIDEO = r"F:/Tongji/Sci/Video/VID_20260324_155114.mp4"
DEFAULT_OUTPUT_VIDEO = r"highlight_overlay.mp4"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find and draw the brightest reflective marker in each frame."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT_VIDEO, help="Path to input video.")
    parser.add_argument("--output_video", default=DEFAULT_OUTPUT_VIDEO, help="Path to annotated output video.")
    parser.add_argument("--threshold", type=int, default=220, help="Binary threshold for bright marker detection (0-255).")
    parser.add_argument("--blur", type=int, default=0, help="Gaussian blur kernel size; use odd integer, 0 to disable.")
    parser.add_argument("--min_area", type=float, default=50.0, help="Minimum contour area to keep.")
    parser.add_argument("--max_area", type=float, default=5000.0, help="Maximum contour area to keep.")
    parser.add_argument("--fps_out", type=float, default=0.0, help="Output video FPS; 0 means same as input.")
    parser.add_argument("--codec", default="mp4v", help="FourCC codec for output video, e.g. mp4v, XVID.")
    parser.add_argument("--show", action="store_true", help="Display live preview window.")
    parser.add_argument(
        "--roi",
        type=int,
        nargs=4,
        metavar=("X", "Y", "W", "H"),
        default=None,
        help="Optional ROI in input frame coordinates: x y w h",
    )
    return parser.parse_args()


def ensure_odd(n: int) -> int:
    if n <= 0:
        return 0
    return n if n % 2 == 1 else n + 1


def preprocess_gray(gray: np.ndarray, blur: int) -> np.ndarray:
    blur = ensure_odd(blur)
    if blur > 1:
        gray = cv2.GaussianBlur(gray, (blur, blur), 0)
    return gray


def circularity_from_contour(cnt: np.ndarray) -> float:
    area = cv2.contourArea(cnt)
    perim = cv2.arcLength(cnt, True)
    if perim <= 0:
        return 0.0
    return float(4.0 * math.pi * area / (perim * perim))


def open_video_writer(path: str, codec: str, fps: float, size: Tuple[int, int]) -> cv2.VideoWriter:
    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(path, fourcc, fps, size)
    if not writer.isOpened():
        raise RuntimeError(f"Failed to open video writer: {path}")
    return writer


def find_brightest_marker(
    gray_roi: np.ndarray,
    x_offset: int,
    y_offset: int,
    threshold: int,
    min_area: float,
    max_area: float,
) -> Optional[Tuple[int, int, float, float, float]]:
    _, binary = cv2.threshold(gray_roi, threshold, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_point = None
    best_score = -1.0

    for cnt in contours:
        area = float(cv2.contourArea(cnt))
        if area < min_area or area > max_area:
            continue

        circularity = circularity_from_contour(cnt)
        moments = cv2.moments(cnt)
        if moments["m00"] == 0:
            continue

        center_x = int(round(moments["m10"] / moments["m00"])) + x_offset
        center_y = int(round(moments["m01"] / moments["m00"])) + y_offset
        mask = np.zeros_like(gray_roi, dtype=np.uint8)
        cv2.drawContours(mask, [cnt], -1, 255, thickness=-1)
        _, max_val, _, max_loc = cv2.minMaxLoc(gray_roi, mask=mask)
        score = area * float(max_val) * max(circularity, 1e-6)

        if score > best_score:
            best_score = score
            best_point = (
                center_x,
                center_y,
                float(max_val),
                area,
                circularity,
            )

    return best_point


def draw_marker(
    frame: np.ndarray,
    frame_idx: int,
    point: Optional[Tuple[int, int, float, float, float]],
    roi: Optional[Tuple[int, int, int, int]],
) -> np.ndarray:
    vis = frame.copy()

    if roi is not None:
        x, y, w, h = roi
        cv2.rectangle(vis, (x, y), (x + w, y + h), (80, 80, 255), 1)

    if point is not None:
        x, y, brightness, area, circularity = point
        cv2.circle(vis, (x, y), 10, (0, 255, 0), 2)
        cv2.circle(vis, (x, y), 3, (0, 255, 0), -1)
        cv2.putText(
            vis,
            f"Best marker: ({x}, {y}) val={brightness:.0f} area={area:.0f} circ={circularity:.2f}",
            (20, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
    else:
        cv2.putText(
            vis,
            "Best marker: not found",
            (20, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 165, 255),
            2,
            cv2.LINE_AA,
        )

    cv2.putText(
        vis,
        f"Frame: {frame_idx}",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return vis


def main() -> int:
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] Input video not found: {input_path}")
        return 1

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {input_path}")
        return 1

    input_fps = cap.get(cv2.CAP_PROP_FPS)
    if not input_fps or input_fps <= 0:
        input_fps = 30.0

    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    roi = None
    if args.roi is not None:
        x, y, w, h = args.roi
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > frame_w or y + h > frame_h:
            print("[ERROR] ROI is outside the video frame.")
            cap.release()
            return 1
        roi = (x, y, w, h)

    fps_out = args.fps_out if args.fps_out and args.fps_out > 0 else input_fps
    writer = open_video_writer(args.output_video, args.codec, fps_out, (frame_w, frame_h))

    print("[INFO] Processing video and marking the brightest reflective point in each frame...")
    frame_idx = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = preprocess_gray(gray, blur=args.blur)

        if roi is not None:
            x, y, w, h = roi
            gray_roi = gray[y : y + h, x : x + w]
            x_offset, y_offset = x, y
        else:
            gray_roi = gray
            x_offset, y_offset = 0, 0

        point = find_brightest_marker(
            gray_roi=gray_roi,
            x_offset=x_offset,
            y_offset=y_offset,
            threshold=args.threshold,
            min_area=args.min_area,
            max_area=args.max_area,
        )

        vis = draw_marker(frame=frame, frame_idx=frame_idx, point=point, roi=roi)
        writer.write(vis)

        if args.show:
            cv2.imshow("Brightest Reflective Marker", vis)
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord("q"):
                print("[INFO] Interrupted by user.")
                break

        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"  processed {frame_idx}/{frame_count if frame_count > 0 else '?'} frames")

    cap.release()
    writer.release()
    if args.show:
        cv2.destroyAllWindows()

    print(f"[INFO] Saved annotated video to: {args.output_video}")
    print("[INFO] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
