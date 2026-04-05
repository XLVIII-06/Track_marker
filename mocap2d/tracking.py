"""
tracking.py

用途：
- 使用 trackpy 对跨帧检测结果做关联
- 将 trackpy 的粒子编号映射为固定的 particle_id = 0..num_markers-1
- 为缺失检测补齐 NaN，便于后续导出和可视化
"""

import numpy as np
import pandas as pd

try:
    import trackpy as tp
except ImportError:  # pragma: no cover - depends on local environment
    tp = None


TRACKING_COLUMNS = [
    "frame",
    "particle_id",
    "u",
    "v",
    "area",
    "brightness",
    "mean_intensity",
    "max_intensity",
    "trackpy_particle",
    "detected",
]


def _ensure_trackpy_available():
    if tp is None:
        raise ImportError(
            "trackpy is required for marker linking. Install it with 'pip install trackpy'."
        )


def _empty_tracking_dataframe(num_frames, num_markers):
    rows = []
    for frame_idx in range(num_frames):
        for particle_id in range(num_markers):
            rows.append(
                {
                    "frame": frame_idx,
                    "particle_id": particle_id,
                    "u": np.nan,
                    "v": np.nan,
                    "area": np.nan,
                    "brightness": np.nan,
                    "mean_intensity": np.nan,
                    "max_intensity": np.nan,
                    "trackpy_particle": np.nan,
                    "detected": False,
                }
            )

    return pd.DataFrame(rows, columns=TRACKING_COLUMNS)


def link_markers(
    detections,
    num_frames,
    num_markers=5,
    search_range=50,
    memory=5,
):
    if num_markers <= 0:
        raise ValueError("num_markers must be a positive integer.")

    if num_frames < 0:
        raise ValueError("num_frames must be non-negative.")

    _ensure_trackpy_available()

    detections_df = pd.DataFrame(detections).copy()
    if detections_df.empty:
        return _empty_tracking_dataframe(num_frames=num_frames, num_markers=num_markers)

    required_columns = {"frame", "u", "v"}
    missing_columns = required_columns - set(detections_df.columns)
    if missing_columns:
        raise ValueError(f"Missing detection columns: {sorted(missing_columns)}")

    working = detections_df.rename(columns={"u": "x", "v": "y"}).copy()
    working = working.sort_values(["frame", "x", "y"]).reset_index(drop=True)

    linked = tp.link(
        working,
        search_range=search_range,
        memory=memory,
    )

    track_summary = (
        linked.groupby("particle")
        .agg(
            track_length=("frame", "size"),
            first_frame=("frame", "min"),
            mean_x=("x", "mean"),
            mean_y=("y", "mean"),
        )
        .reset_index()
    )

    selected_tracks = (
        track_summary.sort_values(
            ["track_length", "first_frame", "mean_x", "mean_y", "particle"],
            ascending=[False, True, True, True, True],
        )
        .head(num_markers)
        .sort_values(["first_frame", "mean_x", "mean_y", "particle"])
        .reset_index(drop=True)
    )

    track_mapping = {
        row["particle"]: particle_id
        for particle_id, row in selected_tracks.iterrows()
    }

    filtered = linked[linked["particle"].isin(track_mapping)].copy()
    filtered["particle_id"] = filtered["particle"].map(track_mapping).astype(int)
    filtered = filtered.rename(columns={"x": "u", "y": "v", "particle": "trackpy_particle"})

    value_columns = [
        "u",
        "v",
        "area",
        "brightness",
        "mean_intensity",
        "max_intensity",
        "trackpy_particle",
    ]

    frame_particle_index = pd.MultiIndex.from_product(
        [range(num_frames), range(num_markers)],
        names=["frame", "particle_id"],
    )

    completed = (
        filtered[["frame", "particle_id"] + value_columns]
        .drop_duplicates(subset=["frame", "particle_id"], keep="first")
        .set_index(["frame", "particle_id"])
        .reindex(frame_particle_index)
        .reset_index()
    )

    completed["detected"] = completed["u"].notna()
    completed = completed[TRACKING_COLUMNS]
    return completed
