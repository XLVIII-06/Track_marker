"""
ROI configuration helpers.
"""

import json
from pathlib import Path

import cv2


def normalize_roi(roi, frame_shape):
    if roi is None:
        return None

    x, y, w, h = [int(value) for value in roi]
    frame_h, frame_w = frame_shape[:2]
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > frame_w or y + h > frame_h:
        raise ValueError(
            f"ROI {(x, y, w, h)} is outside the frame bounds {(frame_w, frame_h)}."
        )
    return x, y, w, h


def load_roi(roi_path):
    roi_path = Path(roi_path)
    with open(roi_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return (
        int(data["x"]),
        int(data["y"]),
        int(data["w"]),
        int(data["h"]),
    )


def save_roi(roi, roi_path):
    x, y, w, h = [int(value) for value in roi]
    roi_path = Path(roi_path)
    roi_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "coordinate_system": "undistorted full-frame image coordinates",
    }
    with open(roi_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def select_roi_interactively(frame, window_name="Select ROI"):
    try:
        roi = cv2.selectROI(window_name, frame, showCrosshair=True, fromCenter=False)
        cv2.destroyWindow(window_name)
    except cv2.error as exc:
        raise RuntimeError(
            "Interactive ROI selection failed. Use --roi X Y W H in headless environments."
        ) from exc

    x, y, w, h = [int(value) for value in roi]
    if w <= 0 or h <= 0:
        raise RuntimeError("ROI selection was cancelled. Use --roi X Y W H or select a valid ROI.")
    return x, y, w, h


def resolve_roi(
    output_dir,
    frame,
    roi=None,
    interactive_roi=True,
    force_roi=False,
):
    roi_path = Path(output_dir) / "roi.json"

    if roi is not None:
        resolved = normalize_roi(roi, frame.shape)
        save_roi(resolved, roi_path)
        return resolved, roi_path

    if not interactive_roi:
        if roi_path.exists():
            resolved = normalize_roi(load_roi(roi_path), frame.shape)
            return resolved, roi_path
        raise RuntimeError(
            f"ROI is required. Pass --roi X Y W H or enable interactive ROI selection. "
            f"No cached ROI found at: {roi_path}"
        )

    try:
        resolved = normalize_roi(select_roi_interactively(frame), frame.shape)
        save_roi(resolved, roi_path)
        return resolved, roi_path
    except RuntimeError as exc:
        if roi_path.exists():
            print(f"Interactive ROI selection failed; using cached ROI: {roi_path}")
            resolved = normalize_roi(load_roi(roi_path), frame.shape)
            return resolved, roi_path
        raise RuntimeError(
            "Interactive ROI selection failed and no cached ROI exists. "
            "Use --roi X Y W H in headless environments."
        ) from exc
