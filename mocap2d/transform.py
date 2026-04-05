"""
transform.py

用途：
- 使用 homography 将像素坐标转换为真实平面坐标(mm)
"""

import cv2
import numpy as np
import json

class CoordinateTransformer:
    def __init__(self, homography_path):
        with open(homography_path, "r") as f:
            data = json.load(f)

        self.H = np.array(data["H"], dtype=np.float32)

    def pixel_to_world(self, u, v):
        pt = np.array([[[u, v]]], dtype=np.float32)
        world_pt = cv2.perspectiveTransform(pt, self.H)
        return world_pt[0][0]  # (X, Y)