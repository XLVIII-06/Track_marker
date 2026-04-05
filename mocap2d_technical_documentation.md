# Mocap2D Technical Documentation / Mocap2D 技术文档

## 1. Project Overview / 项目概述

**中文**

本项目是一个基于单目视频的二维运动捕捉系统，主要用于识别视频中的高亮反光球，并将它们的图像坐标转换为真实平面坐标。系统适用于需要在一个平面内跟踪多个反光标记点的场景，例如动物运动实验、平面行为分析、简单动作捕捉和实验场地定位。

系统当前的核心能力包括：

- 使用棋盘格图像完成相机内参标定
- 对视频帧做去畸变处理
- 自动检测每一帧中最亮的若干个反光点
- 使用 `trackpy` 完成跨帧关联，生成稳定的 `particle_id`
- 通过单应矩阵将像素坐标转换为真实平面坐标，单位为毫米
- 输出结构化 CSV 结果
- 输出带可视化标注的视频，便于人工核查

**English**

This project is a monocular 2D motion capture system designed to detect bright reflective markers in video frames and convert their image coordinates into real-world planar coordinates. It is suitable for applications that require tracking multiple reflective points on a plane, such as animal locomotion experiments, planar behavioral analysis, simple motion capture, and laboratory scene localization.

The current system provides the following core capabilities:

- Camera intrinsic calibration using chessboard images
- Frame undistortion based on calibrated intrinsics
- Automatic detection of the brightest reflective markers in each frame
- Cross-frame association with `trackpy` to generate stable `particle_id`
- Pixel-to-world planar coordinate conversion using homography, in millimeters
- Structured CSV export
- Annotated output video for visual verification

## 2. Intended Readers / 适用读者

**中文**

本说明面向两类读者：

- 非技术人员：希望了解系统在做什么、输入输出是什么、如何运行
- 技术人员：希望了解模块划分、数据流、参数含义、局限性和扩展方向

**English**

This document is intended for two groups of readers:

- Non-technical users who want to understand what the system does, what goes in and out, and how to run it
- Technical users who need module details, data flow, parameter meanings, limitations, and extension ideas

## 3. What the System Does / 系统做什么

**中文**

可以把这个系统理解为一条处理流水线：

1. 先用棋盘格完成相机标定
2. 再用棋盘格图像完成平面标定，得到像素平面到真实平面的映射关系
3. 然后把实验视频输入系统
4. 系统会自动找到反光球，判断每一帧里哪个点属于哪个轨迹
5. 最后输出每个点在每一帧中的像素坐标和真实坐标，并生成一个带标记的视频

**English**

The system can be understood as a processing pipeline:

1. Calibrate the camera using chessboard images
2. Calibrate the planar mapping using a chessboard image to compute pixel-to-world transformation
3. Feed an experiment video into the system
4. The system detects reflective markers and associates them across frames
5. It outputs pixel coordinates, real-world coordinates, and an annotated video

## 4. Repository Structure / 代码结构

```text
Track_marker/
├─ mocap2d/
│  ├─ calibration_intrinsics.py
│  ├─ undistort.py
│  ├─ calibration_homography.py
│  ├─ transform.py
│  ├─ detection.py
│  ├─ tracking.py
│  └─ pipeline.py
└─ mocap2d_technical_documentation.md
```

### 4.1 Module Summary / 模块摘要

| File | 中文说明 | English Description |
|---|---|---|
| `calibration_intrinsics.py` | 用棋盘格图片标定相机内参和畸变参数 | Calibrates camera intrinsics and lens distortion from chessboard images |
| `undistort.py` | 根据内参对图像或视频帧做去畸变 | Undistorts images or frames using saved intrinsics |
| `calibration_homography.py` | 用棋盘格图像计算平面单应矩阵 `H` | Computes planar homography `H` from a chessboard image |
| `transform.py` | 将像素坐标转换为真实平面坐标 | Converts pixel coordinates into world-plane coordinates |
| `detection.py` | 检测每一帧中最亮的反光点 | Detects the brightest reflective markers in each frame |
| `tracking.py` | 使用 `trackpy` 做跨帧关联 | Performs cross-frame linking with `trackpy` |
| `pipeline.py` | 串联整个系统并输出结果 | Orchestrates the full pipeline and exports results |

## 5. End-to-End Workflow / 完整工作流

### 5.1 High-Level Flow / 高层流程

```text
Chessboard images
    -> Intrinsic calibration
    -> intrinsics.json

Chessboard plane image
    -> Homography calibration
    -> homography.json

Experiment video
    -> Undistortion
    -> Bright marker detection
    -> Track linking with trackpy
    -> Pixel-to-world transform
    -> CSV results + annotated video
```

### 5.2 Data Flow / 数据流

**中文**

- `calibration_intrinsics.py` 输出 `intrinsics.json`
- `calibration_homography.py` 输出 `homography.json`
- `pipeline.py` 读取视频、`intrinsics.json` 和 `homography.json`
- `detection.py` 输出每帧候选点的坐标和亮度信息
- `tracking.py` 将候选点链接成连续轨迹，并补全缺失帧
- `transform.py` 将像素坐标转成真实坐标
- `pipeline.py` 输出 `output.csv` 和 `annotated_output.mp4`

**English**

- `calibration_intrinsics.py` produces `intrinsics.json`
- `calibration_homography.py` produces `homography.json`
- `pipeline.py` reads the video plus both calibration files
- `detection.py` outputs frame-wise candidate coordinates and intensity metadata
- `tracking.py` links detections into trajectories and fills missing frames
- `transform.py` converts pixel coordinates to real-world coordinates
- `pipeline.py` writes `output.csv` and `annotated_output.mp4`

## 6. Dependencies / 依赖环境

**中文**

建议的 Python 依赖如下：

```bash
pip install opencv-python numpy pandas trackpy scipy
```

其中：

- `opencv-python` 用于图像处理、视频读写和标定
- `numpy` 用于矩阵和数组计算
- `pandas` 用于组织和导出结果表格
- `trackpy` 用于跨帧轨迹关联
- `scipy` 是 `trackpy` 常见依赖

**English**

Recommended Python dependencies:

```bash
pip install opencv-python numpy pandas trackpy scipy
```

These libraries are used for:

- `opencv-python`: image processing, video I/O, and calibration
- `numpy`: matrix and array operations
- `pandas`: tabular result management and CSV export
- `trackpy`: cross-frame marker linking
- `scipy`: commonly required by `trackpy`

## 7. Usage Guide / 使用说明

### 7.1 Step 1: Camera Intrinsic Calibration / 第一步：相机内参标定

**中文**

该步骤用于估计相机的内参矩阵 `K` 和畸变参数 `dist`。如果相机、镜头、焦距、分辨率没有变化，通常可以重复使用一次标定结果。

当前脚本在直接运行时默认读取工作目录下的 `chessboard_images/*.jpg`：

```bash
python mocap2d/calibration_intrinsics.py
```

如果需要更灵活的调用，也可以在 Python 中导入函数：

```python
from mocap2d.calibration_intrinsics import calibrate_intrinsics

calibrate_intrinsics(
    image_folder="chessboard_images",
    pattern_size=(8, 6),
    square_size=10.0,
    save_path="intrinsics.json",
)
```

**English**

This step estimates the camera intrinsic matrix `K` and distortion coefficients `dist`. If the camera, lens, focal setting, and resolution remain unchanged, the result can usually be reused.

When run directly, the script reads `chessboard_images/*.jpg` from the current working directory:

```bash
python mocap2d/calibration_intrinsics.py
```

For more flexible usage, you can also call the function from Python:

```python
from mocap2d.calibration_intrinsics import calibrate_intrinsics

calibrate_intrinsics(
    image_folder="chessboard_images",
    pattern_size=(8, 6),
    square_size=10.0,
    save_path="intrinsics.json",
)
```

### 7.2 Step 2: Planar Homography Calibration / 第二步：平面单应标定

**中文**

该步骤用于建立“像素坐标 -> 实验平面坐标”的映射关系。当前实现采用棋盘格自动识别，不需要人工点选像素点。

典型用法：

```bash
python mocap2d/calibration_homography.py --image chessboard_plane.jpg --pattern-cols 8 --pattern-rows 6 --square-size 10.0 --save-path homography.json --intrinsics-path intrinsics.json
```

说明：

- `pattern-cols` 和 `pattern-rows` 表示棋盘格内角点数，不是黑白格数量
- `square-size` 是每个小格子的实际边长，单位为毫米
- 如果提供 `intrinsics.json`，脚本会先对图片去畸变，再计算 `H`

**English**

This step establishes the mapping from pixel coordinates to planar experiment coordinates. The current implementation automatically detects chessboard corners, so no manual clicking is required.

Typical usage:

```bash
python mocap2d/calibration_homography.py --image chessboard_plane.jpg --pattern-cols 8 --pattern-rows 6 --square-size 10.0 --save-path homography.json --intrinsics-path intrinsics.json
```

Notes:

- `pattern-cols` and `pattern-rows` refer to the number of inner corners, not the number of black and white squares
- `square-size` is the real edge length of one chessboard square, in millimeters
- If `intrinsics.json` is provided, the image is undistorted before computing `H`

### 7.3 Step 3: Run the Full Pipeline / 第三步：运行完整动捕流程

**中文**

完整流程会读取实验视频，对每帧进行去畸变、亮点检测、跨帧关联、坐标变换，并输出 CSV 与标注视频。

典型命令：

```bash
python mocap2d/pipeline.py --video video.mp4 --intrinsics-path intrinsics.json --homography-path homography.json --output-csv output.csv --output-video annotated_output.mp4 --num-markers 5
```

**English**

The full pipeline reads an experiment video, performs undistortion, bright marker detection, cross-frame association, and coordinate transformation, then exports a CSV file and an annotated video.

Typical command:

```bash
python mocap2d/pipeline.py --video video.mp4 --intrinsics-path intrinsics.json --homography-path homography.json --output-csv output.csv --output-video annotated_output.mp4 --num-markers 5
```

## 8. Module Principles / 模块原理

### 8.1 `calibration_intrinsics.py`

**中文**

该模块通过多张棋盘格图片调用 OpenCV 的相机标定接口，估计相机内参矩阵和畸变系数，并保存为 JSON 文件。

核心原理：

- 棋盘格在现实世界中的格点坐标是已知的
- 图像中的角点位置通过 `cv2.findChessboardCorners` 检测得到
- OpenCV 根据多组“世界点-图像点”对应关系估计相机参数

**English**

This module uses multiple chessboard images and OpenCV camera calibration routines to estimate the intrinsic matrix and distortion coefficients, then saves them as JSON.

Core principle:

- Chessboard corner coordinates in the real world are known
- Image corner locations are detected with `cv2.findChessboardCorners`
- OpenCV estimates camera parameters from multiple world-to-image correspondences

### 8.2 `undistort.py`

**中文**

该模块负责加载内参文件并对图像做去畸变，保证后续检测和坐标变换建立在更准确的图像几何基础上。

**English**

This module loads the intrinsic parameters and undistorts frames so that later detection and coordinate transformation operate on geometrically corrected images.

### 8.3 `calibration_homography.py`

**中文**

该模块通过棋盘格图像自动检测内角点，构造图像坐标和真实平面坐标之间的对应关系，并计算单应矩阵 `H`。

核心原理：

- 棋盘格角点在图像中可检测
- 棋盘格角点在真实平面中的坐标可根据格长自动生成
- 通过 `cv2.getPerspectiveTransform` 或 `cv2.findHomography` 计算平面映射矩阵

注意事项：

- 这里得到的是“图像平面到某一个参考平面”的变换
- 真实坐标系的原点和方向由棋盘格排列定义
- 该方法适用于所有目标点基本落在同一平面上的场景

**English**

This module automatically detects chessboard inner corners, builds correspondences between image coordinates and real planar coordinates, and computes the homography matrix `H`.

Core principle:

- Chessboard corners can be detected in the image
- Their real-world planar coordinates can be generated from the chessboard geometry
- `cv2.getPerspectiveTransform` or `cv2.findHomography` computes the planar mapping

Important notes:

- The result is a transformation from the image plane to a reference physical plane
- The real coordinate origin and axis directions are defined by the chessboard layout
- This approach is valid when the tracked targets remain on or near the same plane

### 8.4 `detection.py`

**中文**

该模块负责在单帧内寻找最亮的若干个反光点。当前策略是：

1. 将彩色图像转为灰度图
2. 进行高斯模糊，降低噪声
3. 使用阈值分割提取高亮区域
4. 查找连通轮廓
5. 计算每个轮廓的中心、面积和亮度
6. 按亮度从高到低排序，保留前 `num_markers` 个点

检测输出不只是坐标，还包含：

- `u`, `v`：像素坐标
- `area`：轮廓面积
- `brightness`：区域总亮度
- `mean_intensity`：平均灰度
- `max_intensity`：最大灰度

**English**

This module detects the brightest reflective markers within a single frame. The current strategy is:

1. Convert the image to grayscale
2. Apply Gaussian blur to reduce noise
3. Threshold the image to isolate bright regions
4. Find contours
5. Compute center, area, and brightness for each contour
6. Rank detections by brightness and keep the top `num_markers`

The detection output includes more than just coordinates:

- `u`, `v`: pixel coordinates
- `area`: contour area
- `brightness`: summed intensity over the region
- `mean_intensity`: average grayscale intensity
- `max_intensity`: maximum grayscale intensity

### 8.5 `tracking.py`

**中文**

该模块将每一帧的检测结果送入 `trackpy`，完成跨帧关联。它的目标是让同一个物理反光球在不同帧中保持同一个编号。

当前流程：

1. 把所有帧的检测结果整理成表格
2. 将 `u, v` 重命名为 `x, y` 以适配 `trackpy`
3. 使用 `tp.link` 做轨迹关联
4. 统计轨迹长度和起始帧
5. 选出最主要的 `num_markers` 条轨迹
6. 将 `trackpy` 的内部轨迹编号映射为固定的 `particle_id = 0, 1, 2, ...`
7. 对缺失帧补齐 `NaN`

这意味着：

- `particle_id` 是面向业务使用的固定编号
- `trackpy_particle` 是 `trackpy` 内部轨迹编号，仅用于调试或追踪

**English**

This module sends frame-wise detections into `trackpy` for cross-frame association. Its goal is to keep the same physical reflective sphere under the same ID across frames.

Current workflow:

1. Gather detections from all frames into a table
2. Rename `u, v` to `x, y` for `trackpy`
3. Use `tp.link` for trajectory linking
4. Summarize track length and first frame
5. Select the main `num_markers` trajectories
6. Map `trackpy` internal IDs to fixed `particle_id = 0, 1, 2, ...`
7. Fill missing frames with `NaN`

This means:

- `particle_id` is the user-facing stable marker ID
- `trackpy_particle` is the internal `trackpy` trajectory ID for debugging or inspection

### 8.6 `transform.py`

**中文**

该模块负责将像素点通过单应矩阵变换到真实平面坐标系中，输出 `(X_mm, Y_mm)`。

**English**

This module transforms pixel coordinates into real planar coordinates using the homography matrix and outputs `(X_mm, Y_mm)`.

### 8.7 `pipeline.py`

**中文**

该模块是系统主入口，负责把所有模块串起来。它做了两件核心事情：

- 第一遍读取视频，完成检测和轨迹关联数据的生成
- 第二遍读取视频，绘制标注并输出可视化视频

输出包括：

- 一个 CSV 文件
- 一个带标注的视频文件

**English**

This module is the main entry point that connects all components. It performs two core passes:

- First pass: read the video and generate detection and tracking data
- Second pass: read the video again and render the annotated output video

Outputs:

- One CSV file
- One annotated video file

## 9. Input and Output Files / 输入输出文件

### 9.1 Input Files / 输入文件

| File Type | 中文 | English |
|---|---|---|
| Chessboard images | 用于相机内参标定的棋盘格图片 | Chessboard images for intrinsic calibration |
| Plane chessboard image | 用于单应矩阵标定的平面棋盘格图片 | Planar chessboard image for homography calibration |
| Experiment video | 需要检测和跟踪反光球的视频 | Video containing reflective markers to detect and track |
| `intrinsics.json` | 相机内参文件 | Camera intrinsics file |
| `homography.json` | 平面映射文件 | Planar mapping file |

### 9.2 Output Files / 输出文件

| File | 中文 | English |
|---|---|---|
| `intrinsics.json` | 保存相机内参矩阵 `K` 和畸变参数 `dist` | Stores camera matrix `K` and distortion coefficients `dist` |
| `homography.json` | 保存单应矩阵 `H` 以及标定点 | Stores homography `H` and calibration points |
| `output.csv` | 保存每一帧每个点的像素与真实坐标 | Stores per-frame pixel and world coordinates |
| `annotated_output.mp4` | 保存带标记和坐标文字的视频 | Stores the annotated video with markers and coordinate text |

### 9.3 CSV Fields / CSV 字段说明

当前 `pipeline.py` 导出的 CSV 一般包含以下列：

| Column | 中文说明 | English Description |
|---|---|---|
| `frame` | 帧序号 | Frame index |
| `particle_id` | 固定轨迹编号 | Fixed marker ID |
| `u` | 像素横坐标 | Pixel x-coordinate |
| `v` | 像素纵坐标 | Pixel y-coordinate |
| `area` | 亮斑面积 | Blob area |
| `brightness` | 亮斑总亮度 | Summed blob brightness |
| `mean_intensity` | 平均灰度 | Mean grayscale intensity |
| `max_intensity` | 最大灰度 | Maximum grayscale intensity |
| `trackpy_particle` | `trackpy` 内部编号 | Internal `trackpy` particle ID |
| `detected` | 本帧是否检测到 | Whether the marker was detected in this frame |
| `X_mm` | 真实平面 X 坐标 | Real-world planar X coordinate |
| `Y_mm` | 真实平面 Y 坐标 | Real-world planar Y coordinate |

如果某一帧某个点未检测到，对应坐标会写为 `NaN`。

If a marker is missing in a given frame, the corresponding coordinate fields are written as `NaN`.

## 10. Parameter Explanation / 参数解释

### 10.1 Detection Parameters / 检测参数

| Parameter | 中文说明 | English Description |
|---|---|---|
| `num_markers` | 需要保留的反光点数量，默认 5 | Number of reflective markers to keep, default 5 |
| `detection_threshold` | 灰度阈值，越高越严格 | Grayscale threshold, higher means stricter bright-point selection |
| `detection_min_area` | 最小轮廓面积，过滤噪点 | Minimum contour area used to reject tiny noise |
| `detection_max_area` | 最大轮廓面积，用于排除过大的高亮区域 | Maximum contour area used to reject overly large bright regions |
| `blur_kernel_size` | 模糊核大小，用于去噪 | Blur kernel size used for denoising |

### 10.2 Tracking Parameters / 关联参数

| Parameter | 中文说明 | English Description |
|---|---|---|
| `track_search_range` | 相邻帧允许的最大位移 | Maximum allowed displacement between consecutive frames |
| `track_memory` | 允许点短暂丢失的帧数 | Number of frames a marker may disappear temporarily |

### 10.3 Calibration Parameters / 标定参数

| Parameter | 中文说明 | English Description |
|---|---|---|
| `pattern_size` | 棋盘格内角点数量 `(cols, rows)` | Number of inner chessboard corners `(cols, rows)` |
| `square_size` | 棋盘格单个小格边长，单位 mm | Physical square size in millimeters |
| `intrinsics_path` | 相机内参文件路径 | Path to the intrinsic calibration file |
| `homography_path` | 单应矩阵文件路径 | Path to the homography file |

## 11. Typical Operating Procedure / 典型操作流程

**中文**

推荐实际操作顺序如下：

1. 用同一相机、同一分辨率拍摄多张棋盘格图片
2. 运行内参标定，生成 `intrinsics.json`
3. 在实验平面上放置棋盘格，拍一张标定图
4. 运行平面标定，生成 `homography.json`
5. 拍摄实验视频，确保反光球足够亮、背景高亮干扰尽量少
6. 运行 `pipeline.py`
7. 查看 `output.csv` 和 `annotated_output.mp4`
8. 如有误检或跳轨，调节检测阈值和 `trackpy` 参数后重新运行

**English**

The recommended operating order is:

1. Capture multiple chessboard images with the same camera and resolution
2. Run intrinsic calibration to generate `intrinsics.json`
3. Place a chessboard on the experimental plane and capture one calibration image
4. Run homography calibration to generate `homography.json`
5. Record the experiment video with sufficiently bright reflective markers and minimal bright background interference
6. Run `pipeline.py`
7. Review `output.csv` and `annotated_output.mp4`
8. If there are false detections or ID switches, adjust detection and `trackpy` parameters and rerun

## 12. Known Limitations / 已知局限

**中文**

- 当前系统是二维平面系统，不是三维重建系统
- 单应矩阵方法要求目标点基本位于同一物理平面上
- 亮点检测依赖阈值，对环境光、曝光和背景高亮区域比较敏感
- 如果画面中存在比反光球更亮的干扰物，检测结果可能被误导
- `trackpy` 的关联效果依赖 `search_range` 和 `memory` 参数，需要根据运动速度调节
- 当反光点长时间遮挡、交叉或过于接近时，可能出现轨迹切换
- `calibration_intrinsics.py` 当前脚本入口较简单，直接运行时默认只读取 `chessboard_images/*.jpg`
- 当前结果主输出为 CSV，尚未内建更丰富的实验元数据管理
- 标注视频的左上角文字区域较固定，当点数较多时可能显得拥挤

**English**

- The current system is a 2D planar system, not a 3D reconstruction system
- Homography-based mapping assumes the tracked targets remain on approximately the same physical plane
- Bright-spot detection depends on thresholding and is sensitive to lighting, exposure, and bright background regions
- If brighter distractors exist in the scene, detection may select them instead of true markers
- `trackpy` performance depends on `search_range` and `memory`, which should be tuned to motion speed
- Long occlusions, marker crossings, or very close trajectories may cause ID switches
- The current `calibration_intrinsics.py` script entry point is simple and, when run directly, only reads `chessboard_images/*.jpg`
- CSV is the main structured output, and richer experiment metadata management is not yet built in
- The top-left annotation panel in the output video may become crowded when tracking many markers

## 13. Recommended Extensions / 后续扩展建议

**中文**

建议后续优先考虑以下扩展方向：

- 增加统一配置文件，例如 `config.yaml` 或 `config.json`
- 为 `calibration_intrinsics.py` 增加命令行参数接口
- 增加自动参数搜索或参数推荐功能
- 增加调试模式，导出二值化图和中间检测结果
- 在 `tracking.py` 中引入更强的轨迹平滑或预测机制，例如卡尔曼滤波
- 增加多种导出格式，例如 JSON、Excel 或 HDF5
- 增加简单图形界面，方便非技术人员操作
- 增加单元测试和示例数据，提升可维护性和可复现性
- 如果未来需要三维动捕，可考虑扩展为多相机标定与三角重建

**English**

The following extension directions are recommended:

- Add a unified configuration file such as `config.yaml` or `config.json`
- Add a command-line interface to `calibration_intrinsics.py`
- Add automatic parameter search or parameter recommendation
- Add a debug mode that exports binary masks and intermediate detection results
- Introduce stronger trajectory smoothing or prediction in `tracking.py`, such as a Kalman filter
- Add more export formats, such as JSON, Excel, or HDF5
- Add a simple GUI for non-technical users
- Add unit tests and sample datasets to improve maintainability and reproducibility
- If 3D motion capture is needed in the future, extend the system toward multi-camera calibration and triangulation

## 14. Troubleshooting / 常见排查建议

**中文**

- 如果棋盘格识别失败，先检查 `pattern-cols`、`pattern-rows` 和 `square-size` 是否正确
- 如果 `homography` 结果不合理，检查棋盘格是否确实放在实验平面上
- 如果检测不到反光球，降低 `detection_threshold` 或提高反光球亮度
- 如果误检太多，提高 `detection_threshold`，并设置更严格的面积过滤
- 如果轨迹经常断裂，提高 `track_memory`
- 如果轨迹经常串号，适当减小 `track_search_range`
- 如果输出视频写入失败，检查输出路径、编码器和 OpenCV 视频编解码支持情况

**English**

- If chessboard detection fails, first verify `pattern-cols`, `pattern-rows`, and `square-size`
- If homography results look wrong, verify that the chessboard was placed on the actual experiment plane
- If reflective markers are not detected, lower `detection_threshold` or increase marker brightness
- If there are too many false detections, raise `detection_threshold` and tighten area filtering
- If trajectories break too often, increase `track_memory`
- If IDs switch too often, decrease `track_search_range`
- If annotated video writing fails, check the output path, codec, and OpenCV video codec support

## 15. Summary / 总结

**中文**

Mocap2D 当前已经具备一个完整的二维动捕基础流程：标定、去畸变、亮点检测、跨帧关联、坐标变换、结果导出和可视化。它适合平面实验场景下的多反光点跟踪，并且已经为后续扩展留下了较清晰的模块边界。

**English**

Mocap2D already provides a complete baseline 2D motion capture workflow: calibration, undistortion, bright-marker detection, cross-frame association, coordinate transformation, result export, and visualization. It is well suited for multi-marker tracking in planar experiments and has a clear modular structure for future extension.
