"""
undistort.py

用途：
- 加载内参文件
- 对图像进行去畸变处理
"""

import cv2
import json
import numpy as np

class Undistorter:
    def __init__(self, intrinsics_path):
        with open(intrinsics_path, "r") as f:
            data = json.load(f)

        self.K = np.array(data["K"])
        self.dist = np.array(data["dist"])

    def undistort(self, frame):
        return cv2.undistort(frame, self.K, self.dist)