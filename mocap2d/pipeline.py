"""
End-to-end 2D marker mocap pipeline.

Flow:
video -> homography calibration -> undistortion -> marker detection ->
track linking -> pixel-to-world transform -> CSV/video outputs.
"""

import argparse
from pathlib import Path

import numpy as np

try:
    from tqdm import tqdm
except ImportError as exc:
    raise ImportError("tqdm is required for progress output. Install it with 'pip install tqdm'.") from exc

try:
    from .calibration_homography import (
        DEFAULT_PATTERN_SIZE,
        DEFAULT_SQUARE_SIZE,
        calibrate_homography_from_video,
    )
    from .detection import detect_markers
    from .output import save_tracking_csv, write_annotated_video
    from .roi import resolve_roi
    from .tracking import link_markers
    from .transform import CoordinateTransformer
    from .undistort import Undistorter
    from .video_io import extract_frame, get_video_properties, open_video
except ImportError:
    from calibration_homography import (
        DEFAULT_PATTERN_SIZE,
        DEFAULT_SQUARE_SIZE,
        calibrate_homography_from_video,
    )
    from detection import detect_markers
    from output import save_tracking_csv, write_annotated_video
    from roi import resolve_roi
    from tracking import link_markers
    from transform import CoordinateTransformer
    from undistort import Undistorter
    from video_io import extract_frame, get_video_properties, open_video


def compute_world_coordinates(tracking_df, transformer):
    tracking_df = tracking_df.copy()
    tracking_df["X_mm"] = np.nan
    tracking_df["Y_mm"] = np.nan

    valid_rows = tracking_df["u"].notna() & tracking_df["v"].notna()
    for index in tracking_df.index[valid_rows]:
        X_mm, Y_mm = transformer.pixel_to_world(
            tracking_df.at[index, "u"],
            tracking_df.at[index, "v"],
        )
        tracking_df.at[index, "X_mm"] = float(X_mm)
        tracking_df.at[index, "Y_mm"] = float(Y_mm)

    return tracking_df


def resolve_homography_path(
    video_path,
    intrinsics_path,
    output_dir,
    homography_path=None,
    homography_frame=0,
    pattern_size=DEFAULT_PATTERN_SIZE,
    square_size=DEFAULT_SQUARE_SIZE,
    force_homography=False,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if homography_path is not None:
        homography_path = Path(homography_path)
        if not homography_path.exists():
            raise FileNotFoundError(f"Homography file not found: {homography_path}")
        return homography_path

    generated_path = output_dir / "homography.json"
    debug_image_path = output_dir / "homography_frame_corners.png"

    if generated_path.exists() and not force_homography:
        return generated_path

    calibrate_homography_from_video(
        video_path=video_path,
        intrinsics_path=intrinsics_path,
        frame_index=homography_frame,
        pattern_size=pattern_size,
        square_size=square_size,
        save_path=generated_path,
        debug_image_path=debug_image_path,
    )
    return generated_path


def collect_detections(
    video_path,
    intrinsics_path,
    num_markers=5,
    detection_threshold=200,
    detection_min_area=5.0,
    detection_max_area=None,
    blur_kernel_size=5,
    roi=None,
    min_circularity=0.5,
    local_bg_radius=12,
    local_peak_weight=1.0,
    local_contrast_weight=2.0,
):
    cap = open_video(video_path)
    try:
        _, _, _, frame_count = get_video_properties(cap)
        undistorter = Undistorter(intrinsics_path)
        detections = []
        frame_idx = 0

        progress = tqdm(
            total=frame_count if frame_count > 0 else None,
            desc="Detecting markers",
            unit="frame",
        )
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame = undistorter.undistort(frame)
                frame_detections = detect_markers(
                    frame,
                    num_markers=num_markers,
                    threshold=detection_threshold,
                    min_area=detection_min_area,
                    max_area=detection_max_area,
                    blur_kernel_size=blur_kernel_size,
                    roi=roi,
                    min_circularity=min_circularity,
                    local_bg_radius=local_bg_radius,
                    local_peak_weight=local_peak_weight,
                    local_contrast_weight=local_contrast_weight,
                    return_metadata=True,
                )

                for detection in frame_detections:
                    detections.append({"frame": frame_idx, **detection})

                frame_idx += 1
                progress.update(1)
        finally:
            progress.close()

        num_frames = frame_idx if frame_idx > 0 else frame_count
        return detections, num_frames
    finally:
        cap.release()


def prepare_roi(
    video_path,
    intrinsics_path,
    output_dir,
    roi=None,
    interactive_roi=True,
    force_roi=False,
):
    frame = extract_frame(video_path, frame_index=0)
    frame = Undistorter(intrinsics_path).undistort(frame)
    return resolve_roi(
        output_dir=output_dir,
        frame=frame,
        roi=roi,
        interactive_roi=interactive_roi,
        force_roi=force_roi,
    )


def run_pipeline(
    video_path,
    intrinsics_path,
    output_dir="outputs",
    homography_path=None,
    homography_frame=0,
    pattern_size=DEFAULT_PATTERN_SIZE,
    square_size=DEFAULT_SQUARE_SIZE,
    force_homography=False,
    num_markers=5,
    detection_threshold=200,
    detection_min_area=5.0,
    detection_max_area=None,
    blur_kernel_size=5,
    roi=None,
    interactive_roi=True,
    force_roi=False,
    min_circularity=0.5,
    local_bg_radius=12,
    local_peak_weight=1.0,
    local_contrast_weight=2.0,
    track_search_range=50,
    track_memory=5,
    video_codec="mp4v",
):
    if num_markers <= 0:
        raise ValueError("num_markers must be a positive integer.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "tracking.csv"
    output_video = output_dir / "annotated_output.mp4"

    print("Resolving homography...")
    resolved_homography_path = resolve_homography_path(
        video_path=video_path,
        intrinsics_path=intrinsics_path,
        output_dir=output_dir,
        homography_path=homography_path,
        homography_frame=homography_frame,
        pattern_size=pattern_size,
        square_size=square_size,
        force_homography=force_homography,
    )

    print("Resolving ROI...")
    resolved_roi, roi_path = prepare_roi(
        video_path=video_path,
        intrinsics_path=intrinsics_path,
        output_dir=output_dir,
        roi=roi,
        interactive_roi=interactive_roi,
        force_roi=force_roi,
    )

    print("Detecting markers...")
    detections, num_frames = collect_detections(
        video_path=video_path,
        intrinsics_path=intrinsics_path,
        num_markers=num_markers,
        detection_threshold=detection_threshold,
        detection_min_area=detection_min_area,
        detection_max_area=detection_max_area,
        blur_kernel_size=blur_kernel_size,
        roi=resolved_roi,
        min_circularity=min_circularity,
        local_bg_radius=local_bg_radius,
        local_peak_weight=local_peak_weight,
        local_contrast_weight=local_contrast_weight,
    )

    print("Linking tracks...")
    tracking_df = link_markers(
        detections=detections,
        num_frames=num_frames,
        num_markers=num_markers,
        search_range=track_search_range,
        memory=track_memory,
    )
    print("Computing world coordinates...")
    tracking_df = compute_world_coordinates(
        tracking_df,
        CoordinateTransformer(resolved_homography_path),
    )

    print("Writing outputs...")
    save_tracking_csv(tracking_df, output_csv)
    write_annotated_video(
        video_path=video_path,
        intrinsics_path=intrinsics_path,
        tracking_df=tracking_df,
        output_video=output_video,
        num_markers=num_markers,
        codec=video_codec,
        roi=resolved_roi,
    )

    print("Saved homography:", resolved_homography_path)
    print("Saved ROI:", roi_path)
    print("Saved CSV:", output_csv)
    print("Saved annotated video:", output_video)
    return tracking_df


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Run the full 2D marker mocap pipeline on a video."
    )
    parser.add_argument(
        "--video",
        default=r"F:\Tongji\Sci\Video\Tracking\DSCF8178.mov",
        # required=True,
        help="Input .mov/.mp4 video path.",
    )
    parser.add_argument(
        "--intrinsics-path",
        default=r"intrinsics.json",
        # required=True,
        help="Path to intrinsics.json.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for tracking.csv, annotated_output.mp4, and generated homography files.",
    )
    parser.add_argument(
        "--homography-path",
        default=None,
        help="Optional existing homography.json. If omitted, output-dir/homography.json is generated or reused.",
    )
    parser.add_argument(
        "--force-homography",
        action="store_true",
        help="Recompute output-dir/homography.json even if it already exists.",
    )
    parser.add_argument(
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
        "--num-markers",
        type=int,
        default=4,
        help="Number of reflective markers to track.",
    )
    parser.add_argument(
        "--detection-threshold",
        type=int,
        default=200,
        help="Grayscale threshold for bright marker detection.",
    )
    parser.add_argument(
        "--detection-min-area",
        type=float,
        default=5.0,
        help="Minimum blob area to keep during detection.",
    )
    parser.add_argument(
        "--detection-max-area",
        type=float,
        default=None,
        help="Optional maximum blob area to keep during detection.",
    )
    parser.add_argument(
        "--blur-kernel-size",
        type=int,
        default=5,
        help="Gaussian blur kernel size used before thresholding.",
    )
    parser.add_argument(
        "--roi",
        type=int,
        nargs=4,
        metavar=("X", "Y", "W", "H"),
        default=None,
        help="Detection ROI in undistorted full-frame coordinates.",
    )
    parser.add_argument(
        "--interactive-roi",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Select ROI interactively on each run unless --roi is provided. "
        "With --no-interactive-roi, use cached output-dir/roi.json if available.",
    )
    parser.add_argument(
        "--force-roi",
        action="store_true",
        help="Deprecated compatibility option. ROI is selected interactively by default.",
    )
    parser.add_argument(
        "--min-circularity",
        type=float,
        default=0.5,
        help="Minimum contour circularity for marker candidates.",
    )
    parser.add_argument(
        "--local-bg-radius",
        type=int,
        default=12,
        help="Radius around each blob used to estimate local background intensity.",
    )
    parser.add_argument(
        "--local-peak-weight",
        type=float,
        default=1.0,
        help="Weight for max intensity in local peak scoring.",
    )
    parser.add_argument(
        "--local-contrast-weight",
        type=float,
        default=2.0,
        help="Weight for local contrast in local peak scoring.",
    )
    parser.add_argument(
        "--track-search-range",
        type=float,
        default=50,
        help="Maximum per-frame displacement for trackpy linking.",
    )
    parser.add_argument(
        "--track-memory",
        type=int,
        default=5,
        help="Number of frames trackpy keeps a marker alive during temporary misses.",
    )
    parser.add_argument(
        "--video-codec",
        default="mp4v",
        help="FourCC codec used for annotated video output.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_pipeline(
        video_path=args.video,
        intrinsics_path=args.intrinsics_path,
        output_dir=args.output_dir,
        homography_path=args.homography_path,
        homography_frame=args.homography_frame,
        pattern_size=(args.pattern_cols, args.pattern_rows),
        square_size=args.square_size,
        force_homography=args.force_homography,
        num_markers=args.num_markers,
        detection_threshold=args.detection_threshold,
        detection_min_area=args.detection_min_area,
        detection_max_area=args.detection_max_area,
        blur_kernel_size=args.blur_kernel_size,
        roi=args.roi,
        interactive_roi=args.interactive_roi,
        force_roi=args.force_roi,
        min_circularity=args.min_circularity,
        local_bg_radius=args.local_bg_radius,
        local_peak_weight=args.local_peak_weight,
        local_contrast_weight=args.local_contrast_weight,
        track_search_range=args.track_search_range,
        track_memory=args.track_memory,
        video_codec=args.video_codec,
    )
