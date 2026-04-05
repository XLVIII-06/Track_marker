"""
detection.py

用途：
- 检测画面中的高亮反光点
- 默认返回最亮的 num_markers 个候选点
- 可选返回检测元数据，供跨帧关联和可视化使用
"""

import cv2
import numpy as np


def detect_markers(
    frame,
    num_markers=5,
    threshold=200,
    min_area=5.0,
    max_area=None,
    blur_kernel_size=5,
    return_metadata=False,
):
    if num_markers <= 0:
        raise ValueError("num_markers must be a positive integer.")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if blur_kernel_size and blur_kernel_size > 1:
        if blur_kernel_size % 2 == 0:
            blur_kernel_size += 1
        gray = cv2.GaussianBlur(gray, (blur_kernel_size, blur_kernel_size), 0)

    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        if max_area is not None and area > max_area:
            continue

        mask = np.zeros_like(gray, dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, color=255, thickness=-1)

        intensity_values = gray[mask > 0]
        if intensity_values.size == 0:
            continue

        moments = cv2.moments(contour)
        if moments["m00"] != 0:
            center_x = moments["m10"] / moments["m00"]
            center_y = moments["m01"] / moments["m00"]
        else:
            x, y, w, h = cv2.boundingRect(contour)
            center_x = x + w / 2.0
            center_y = y + h / 2.0

        detections.append(
            {
                "u": float(center_x),
                "v": float(center_y),
                "area": float(area),
                "brightness": float(np.sum(intensity_values)),
                "mean_intensity": float(np.mean(intensity_values)),
                "max_intensity": float(np.max(intensity_values)),
            }
        )

    detections.sort(
        key=lambda item: (
            item["brightness"],
            item["max_intensity"],
            item["area"],
        ),
        reverse=True,
    )
    detections = detections[:num_markers]

    if return_metadata:
        return detections

    return [(item["u"], item["v"]) for item in detections]
