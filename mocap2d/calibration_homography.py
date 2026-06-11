"""
Homography calibration for mapping image pixels to planar world coordinates.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

try:
    from .output import save_chessboard_debug_image
    from .undistort import Undistorter
    from .video_io import extract_frame
except ImportError:
    from output import save_chessboard_debug_image
    from undistort import Undistorter
    from video_io import extract_frame


DEFAULT_PATTERN_SIZE = (11, 8)
DEFAULT_SQUARE_SIZE = 3.0


def compute_homography(image_points, world_points, save_path="homography.json"):
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

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return H


def build_world_points(pattern_size, square_size):
    world_points = np.zeros((pattern_size[0] * pattern_size[1], 2), np.float32)
    world_points[:, :2] = np.mgrid[0 : pattern_size[0], 0 : pattern_size[1]].T.reshape(-1, 2)
    world_points *= square_size
    return world_points


def find_chessboard_points(image, pattern_size):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    found, corners = cv2.findChessboardCorners(gray, pattern_size, None)

    if not found:
        raise RuntimeError(
            "Chessboard corners were not found. Check --homography-frame, "
            "--pattern-cols, --pattern-rows, --square-size, and lighting."
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
    return refined_corners


def calibrate_homography_from_frame(
    frame,
    pattern_size=DEFAULT_PATTERN_SIZE,
    square_size=DEFAULT_SQUARE_SIZE,
    save_path="homography.json",
    debug_image_path=None,
):
    refined_corners = find_chessboard_points(frame, pattern_size)
    image_points = refined_corners.reshape(-1, 2)
    world_points = build_world_points(pattern_size, square_size)

    H = compute_homography(image_points, world_points, save_path=save_path)

    if debug_image_path is not None:
        save_chessboard_debug_image(frame, pattern_size, refined_corners, debug_image_path)

    return H


def calibrate_homography_from_video(
    video_path,
    intrinsics_path,
    frame_index=0,
    pattern_size=DEFAULT_PATTERN_SIZE,
    square_size=DEFAULT_SQUARE_SIZE,
    save_path="homography.json",
    debug_image_path=None,
):
    frame = extract_frame(video_path, frame_index=frame_index)
    undistorter = Undistorter(intrinsics_path)
    undistorted_frame = undistorter.undistort(frame)

    return calibrate_homography_from_frame(
        undistorted_frame,
        pattern_size=pattern_size,
        square_size=square_size,
        save_path=save_path,
        debug_image_path=debug_image_path,
    )


def calibrate_homography_from_chessboard(
    image_path,
    pattern_size=DEFAULT_PATTERN_SIZE,
    square_size=DEFAULT_SQUARE_SIZE,
    save_path="homography.json",
    intrinsics_path=None,
    show_corners=False,
    debug_image_path=None,
):
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    if intrinsics_path is not None:
        image = Undistorter(intrinsics_path).undistort(image)

    refined_corners = find_chessboard_points(image, pattern_size)
    image_points = refined_corners.reshape(-1, 2)
    world_points = build_world_points(pattern_size, square_size)
    H = compute_homography(image_points, world_points, save_path=save_path)

    if debug_image_path is not None:
        save_chessboard_debug_image(image, pattern_size, refined_corners, debug_image_path)

    if show_corners:
        preview = image.copy()
        cv2.drawChessboardCorners(preview, pattern_size, refined_corners, True)
        cv2.imshow("homography_calibration", preview)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return H


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Compute homography from a chessboard image or a selected video frame."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--image", help="Path to a chessboard calibration image.")
    source.add_argument("--video", help="Path to a video containing a chessboard frame.")
    parser.add_argument(
        "--intrinsics-path",
        default=None,
        help="Path to intrinsics.json. Required when using --video; optional for --image.",
    )
    parser.add_argument(
        "--frame-index",
        "--homography-frame",
        type=int,
        default=0,
        help="Video frame index used for homography calibration.",
    )
    parser.add_argument(
        "--pattern-cols",
        type=int,
        default=DEFAULT_PATTERN_SIZE[0],
        help="Number of inner corners along the chessboard width.",
    )
    parser.add_argument(
        "--pattern-rows",
        type=int,
        default=DEFAULT_PATTERN_SIZE[1],
        help="Number of inner corners along the chessboard height.",
    )
    parser.add_argument(
        "--square-size",
        type=float,
        default=DEFAULT_SQUARE_SIZE,
        help="Chessboard square size in mm.",
    )
    parser.add_argument(
        "--save-path",
        default="homography.json",
        help="Path to save the computed homography JSON file.",
    )
    parser.add_argument(
        "--debug-image-path",
        default=None,
        help="Optional path to save a chessboard corner preview image.",
    )
    parser.add_argument(
        "--show-corners",
        action="store_true",
        help="Display detected corners when using --image.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    pattern_size = (args.pattern_cols, args.pattern_rows)

    if args.video:
        if args.intrinsics_path is None:
            raise SystemExit("--intrinsics-path is required when using --video.")
        calibrate_homography_from_video(
            video_path=args.video,
            intrinsics_path=args.intrinsics_path,
            frame_index=args.frame_index,
            pattern_size=pattern_size,
            square_size=args.square_size,
            save_path=args.save_path,
            debug_image_path=args.debug_image_path,
        )
    else:
        calibrate_homography_from_chessboard(
            image_path=args.image,
            pattern_size=pattern_size,
            square_size=args.square_size,
            save_path=args.save_path,
            intrinsics_path=args.intrinsics_path,
            show_corners=args.show_corners,
            debug_image_path=args.debug_image_path,
        )
