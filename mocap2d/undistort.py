"""
undistort.py

用途：
- 加载内参文件
- 对图像进行去畸变处理
"""

import json

import cv2
import numpy as np


class Undistorter:
    def __init__(self, intrinsics_path):
        with open(intrinsics_path, "r") as f:
            data = json.load(f)

        self.K = np.array(data["K"], dtype=np.float32)
        self.dist = np.array(data["dist"], dtype=np.float32)
        self._map_size = None
        self._map1 = None
        self._map2 = None

    def _ensure_maps(self, frame):
        height, width = frame.shape[:2]
        size = (width, height)
        if self._map_size == size:
            return

        self._map1, self._map2 = cv2.initUndistortRectifyMap(
            self.K,
            self.dist,
            None,
            self.K,
            size,
            cv2.CV_16SC2,
        )
        self._map_size = size

    def undistort(self, frame):
        self._ensure_maps(frame)
        return cv2.remap(frame, self._map1, self._map2, cv2.INTER_LINEAR)
