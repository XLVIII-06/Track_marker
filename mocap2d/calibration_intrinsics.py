"""
calibration_intrinsics.py

用途：
- 使用棋盘格图像进行相机内参标定
- 输出 K(内参)和 dist(畸变参数)
- 保存为 JSON 文件供后续使用

注意：
- 同一相机 + 同一镜头 + 同一焦距 + 同一分辨率 可复用
"""

import cv2
import numpy as np
import glob
import json

def calibrate_intrinsics(image_folder, pattern_size=(11,8), square_size=3.0, save_path="intrinsics.json"):
    # 准备棋盘格世界坐标
    objp = np.zeros((pattern_size[0]*pattern_size[1],3), np.float32)
    objp[:,:2] = np.mgrid[0:pattern_size[0],0:pattern_size[1]].T.reshape(-1,2)
    objp *= square_size  # 单位：mm

    objpoints = []
    imgpoints = []

    images = glob.glob(f"{image_folder}/*.jpg")

    for fname in images:
        img = cv2.imread(fname)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)

        if ret:
            objpoints.append(objp)
            imgpoints.append(corners)

    # 标定
    ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, gray.shape[::-1], None, None
    )

    # 保存
    data = {
        "K": K.tolist(),
        "dist": dist.tolist()
    }

    with open(save_path, "w") as f:
        json.dump(data, f, indent=4)

    print("Intrinsic calibration saved to", save_path)

if __name__ == "__main__":
    calibrate_intrinsics("F:\Tongji\Sci\Pictures\Tracking\calibration_intrinsics")  # chessboard_images folder should contain the calibration images of chessboard patterns.