"""
Reflective marker detection.
"""

import math

import cv2
import numpy as np


def _normalize_roi(roi, frame_shape):
    if roi is None:
        return None

    x, y, w, h = [int(value) for value in roi]
    frame_h, frame_w = frame_shape[:2]
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > frame_w or y + h > frame_h:
        raise ValueError(
            f"ROI {(x, y, w, h)} is outside the frame bounds {(frame_w, frame_h)}."
        )
    return x, y, w, h


def _circularity(contour):
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)
    if perimeter <= 0:
        return 0.0
    return float(4.0 * math.pi * area / (perimeter * perimeter))


def _local_background_mean(gray_roi, contour, local_bg_radius):
    x, y, w, h = cv2.boundingRect(contour)
    x0 = max(0, x - local_bg_radius)
    y0 = max(0, y - local_bg_radius)
    x1 = min(gray_roi.shape[1], x + w + local_bg_radius)
    y1 = min(gray_roi.shape[0], y + h + local_bg_radius)

    local_gray = gray_roi[y0:y1, x0:x1]
    local_mask = np.ones(local_gray.shape, dtype=np.uint8)
    shifted_contour = contour.copy()
    shifted_contour[:, 0, 0] -= x0
    shifted_contour[:, 0, 1] -= y0
    cv2.drawContours(local_mask, [shifted_contour], -1, color=0, thickness=-1)

    background_values = local_gray[local_mask > 0]
    if background_values.size == 0:
        return float(np.mean(local_gray))
    return float(np.mean(background_values))


def detect_markers(
    frame,
    num_markers=5,
    threshold=200,
    min_area=5.0,
    max_area=None,
    blur_kernel_size=5,
    roi=None,
    min_circularity=0.5,
    local_bg_radius=12,
    local_peak_weight=1.0,
    local_contrast_weight=2.0,
    return_metadata=False,
):
    if num_markers <= 0:
        raise ValueError("num_markers must be a positive integer.")

    if local_bg_radius < 0:
        raise ValueError("local_bg_radius must be non-negative.")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    normalized_roi = _normalize_roi(roi, frame.shape)
    if normalized_roi is not None:
        x_offset, y_offset, w, h = normalized_roi
        gray_roi = gray[y_offset : y_offset + h, x_offset : x_offset + w]
    else:
        x_offset, y_offset = 0, 0
        gray_roi = gray

    if blur_kernel_size and blur_kernel_size > 1:
        if blur_kernel_size % 2 == 0:
            blur_kernel_size += 1
        gray_roi = cv2.GaussianBlur(gray_roi, (blur_kernel_size, blur_kernel_size), 0)

    _, binary = cv2.threshold(gray_roi, threshold, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < min_area:
            continue

        if max_area is not None and area > max_area:
            continue

        circularity = _circularity(contour)
        if min_circularity is not None and circularity < min_circularity:
            continue

        mask = np.zeros_like(gray_roi, dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, color=255, thickness=-1)

        intensity_values = gray_roi[mask > 0]
        if intensity_values.size == 0:
            continue

        moments = cv2.moments(contour)
        if moments["m00"] != 0:
            center_x = moments["m10"] / moments["m00"] + x_offset
            center_y = moments["m01"] / moments["m00"] + y_offset
        else:
            x, y, w, h = cv2.boundingRect(contour)
            center_x = x + w / 2.0 + x_offset
            center_y = y + h / 2.0 + y_offset

        max_intensity = float(np.max(intensity_values))
        local_background = _local_background_mean(gray_roi, contour, local_bg_radius)
        local_contrast = max(0.0, max_intensity - local_background)
        score = float(
            max_intensity * local_peak_weight
            + local_contrast * local_contrast_weight
        )

        detections.append(
            {
                "u": float(center_x),
                "v": float(center_y),
                "area": area,
                "brightness": float(np.sum(intensity_values)),
                "mean_intensity": float(np.mean(intensity_values)),
                "max_intensity": max_intensity,
                "circularity": circularity,
                "local_contrast": local_contrast,
                "score": score,
            }
        )

    detections.sort(
        key=lambda item: (
            item["score"],
            item["local_contrast"],
            item["max_intensity"],
            -item["area"],
        ),
        reverse=True,
    )
    detections = detections[:num_markers]

    if return_metadata:
        return detections

    return [(item["u"], item["v"]) for item in detections]
