"""
calibration_homography.py

用途：
- 根据图像中的标定点计算 homography 矩阵 H
- 用于像素坐标 -> 实验平面坐标(mm)
- 支持脚本直接运行，从棋盘格图像自动提取 image_points
"""

import argparse
import json

import cv2
import numpy as np


def compute_homography(image_points, world_points, save_path="homography.json"):
    """
    image_points: [(u, v), ...]
    world_points: [(X, Y), ...]，单位 mm
    """

    img_pts = np.array(image_points, dtype=np.float32)
    world_pts = np.array(world_points, dtype=np.float32)

    if len(img_pts) != len(world_pts):
        raise ValueError("image_points and world_points must have the same length.")

    if len(img_pts) < 4:
        raise ValueError("At least 4 point pairs are required to compute homography.")

    if len(img_pts) == 4:
        H = cv2.getPerspectiveTransform(img_pts, world_pts)
    else:
        H, _ = cv2.findHomography(img_pts, world_pts, method=0)

    if H is None:
        raise RuntimeError("Failed to compute homography.")

    data = {
        "H": H.tolist(),
        "image_points": img_pts.tolist(),
        "world_points": world_pts.tolist(),
    }

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print("Homography saved to", save_path)
    return H


def _build_world_points(pattern_size, square_size):
    world_points = np.zeros((pattern_size[0] * pattern_size[1], 2), np.float32)
    world_points[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
    world_points *= square_size
    return world_points


def _load_intrinsics(intrinsics_path):
    with open(intrinsics_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    K = np.array(data["K"], dtype=np.float32)
    dist = np.array(data["dist"], dtype=np.float32)
    return K, dist


def calibrate_homography_from_chessboard(
    image_path,
    pattern_size=(8, 6),
    square_size=10.0,
    save_path="homography.json",
    intrinsics_path=None,
    show_corners=False,
):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    if intrinsics_path is not None:
        K, dist = _load_intrinsics(intrinsics_path)
        image = cv2.undistort(image, K, dist)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    found, corners = cv2.findChessboardCorners(gray, pattern_size, None)

    if not found:
        raise RuntimeError(
            "Chessboard corners were not found. Check the image, pattern size, and lighting."
        )

    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        30,
        0.001,
    )
    refined_corners = cv2.cornerSubPix(
        gray,
        corners,
        winSize=(11, 11),
        zeroZone=(-1, -1),
        criteria=criteria,
    )

    image_points = refined_corners.reshape(-1, 2)
    world_points = _build_world_points(pattern_size, square_size)

    H = compute_homography(image_points, world_points, save_path=save_path)

    if show_corners:
        preview = image.copy()
        cv2.drawChessboardCorners(preview, pattern_size, refined_corners, found)
        cv2.imshow("homography_calibration", preview)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return H


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Compute homography from a chessboard calibration image."
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Path to the chessboard image used for homography calibration.",
    )
    parser.add_argument(
        "--pattern-cols",
        type=int,
        default=8,
        help="Number of inner corners along the chessboard width.",
    )
    parser.add_argument(
        "--pattern-rows",
        type=int,
        default=6,
        help="Number of inner corners along the chessboard height.",
    )
    parser.add_argument(
        "--square-size",
        type=float,
        default=10.0,
        help="Chessboard square size in mm.",
    )
    parser.add_argument(
        "--save-path",
        default="homography.json",
        help="Path to save the computed homography JSON file.",
    )
    parser.add_argument(
        "--intrinsics-path",
        default=None,
        help="Optional intrinsics JSON path used to undistort the image first.",
    )
    parser.add_argument(
        "--show-corners",
        action="store_true",
        help="Display the detected chessboard corners before exiting.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    calibrate_homography_from_chessboard(
        image_path=args.image,
        pattern_size=(args.pattern_cols, args.pattern_rows),
        square_size=args.square_size,
        save_path=args.save_path,
        intrinsics_path=args.intrinsics_path,
        show_corners=args.show_corners,
    )
