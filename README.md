# Real-time Drone Detection (Video-based)

A desktop demo app built around a **single-class YOLO detector for drone detection**. It processes video streams with **stride-based inference**, draws a real-time overlay in an **OpenCV window**, and triggers **warning / alert** events with cooldown handling.

This project is not just a raw detector wrapper. It adds a decision layer around YOLO with three main mechanisms:

- **Temporal ROI Propagation**: reuse valid detections from the previous inference step to generate up to **3 square ROIs** for the next step
- **Cascaded ROI Confirmation**: optional second-pass YOLO verification for ambiguous detections
- **Temporal Continuity**: an IoU-based continuity gate across consecutive inference frames for warning/alert stability

The detector was trained on a large mixed drone dataset with hard-negative background suppression and achieved strong test performance on unseen data:
- **Precision:** 97.8%
- **Recall:** 91.5%
- **mAP@50:** 95.1%
- **Average speed per image:** 0.7 ms preprocessing, 1.4 ms inference, 0.1 ms postprocessing  
These values are reported in the project report’s held-out test evaluation and model comparison sections.

---

## At a Glance

### Core idea
This system is designed for **real-time video-based drone detection**, where raw frame-by-frame detections alone are not enough. The project combines:
- a trained YOLO drone detector,
- temporal reasoning across inference frames,
- ROI-based spatial restriction,
- optional cascaded verification,
- and warning/alert decision logic.

The report explicitly states that the system is a **demonstrative detector emphasizing real-time behavior, temporal decision logic, and inference-aware performance accounting**, rather than a benchmark framework.

### Main reported result
The trained **YOLOv26n** model achieved the following on the held-out test split:

| Metric | Value |
|---|---:|
| Precision | 97.8% |
| Recall | 91.5% |
| mAP@50 | 95.1% |
| Preprocessing time | 0.7 ms / image |
| Inference time | 1.4 ms / image |
| Postprocessing time | 0.1 ms / image |

### Why this matters
The report compares this model to several public GitHub drone detection implementations and shows that this project’s detector achieves the best overall balance between **recall**, **precision**, and **latency** among those compared models.

---

## Performance Comparison with Public GitHub Drone Detection Models

**Table 3.3** from the report, rebuilt here as a Markdown table.

| Model (GitHub) | Precision | Recall | mAP@50 | Inference Time (ms / image) |
|---|---:|---:|---:|---:|
| **Our YOLOv26n** | **97.8%** | **91.5%** | **95.1%** | **2.2** |
| FardadDadboud Drone YOLOv5 Detector | 92.4% | 55.4% | 75.3% | 23.3 |
| MohiteYash Drone yolo v11 | 49.1% | 33.4% | 31.8% | 1.4 |
| doguilmak Drone-Detection-YOLOv11x | 39.6% | 23.5% | 21.5% | 27.8 |

### Key takeaway
The main advantage is not just high precision. It is the combination of:
- **very high recall** for a safety-oriented detector,
- **low total latency** suitable for real-time video,
- and support for extra logic such as ROI propagation and cascaded verification without making the system unusable in practice. 

---

## Project Figures

<p align="center">
  <img src="/imgs/latex_imgs/TROI.jpeg" alt="Temporal ROI Propagation" width="48%" />
  <img src="/imgs/latex_imgs/TC.jpeg" alt="Temporal Continuity" width="48%" />
</p>

<p align="center">
  <em>
    Figures Left and Right are Conceptual illustration of Temporal ROI Propagation and IoU-based Temporal Continuity. Detections at inference frame t generate spatial ROIs that restrict inference at frame t+1; if no valid detections are available, the system falls back to full-frame inference. Temporal continuity accepts a detection when the overlap between consecutive bounding boxes exceeds the threshold (IoU &gt; 0.1); otherwise, the continuity chain is reset.
  </em>
</p>
---

## Small-Object Alert Reliability

The project explicitly separates **warning** and **alert** behavior for very small detections. Detections below a minimum area can still contribute to warnings, but not all of them are allowed to trigger alerts. The report shows that recall drops sharply for small bounding boxes, which is why the alert pipeline uses area-based gating.

### Model Performance for Small Bounding-Box Areas

**Table 10.1** from the report, rebuilt here as a Markdown table.

| Area Threshold (px²) | Precision< | Recall< | F1< |
|---|---:|---:|---:|
| 100 | 0.938 | 0.411 | 0.571 |
| 225 | 0.966 | 0.716 | 0.822 |
| 400 | 0.962 | 0.792 | 0.869 |
| 625 | 0.962 | 0.804 | 0.876 |
| 900 | 0.964 | 0.820 | 0.886 |

### Alert gating used in the system
According to the report:
- **Direct alert acceptance:** bounding-box area **≥ 25 × 25 = 625 px²**
- **Cascade-assisted alert acceptance:** bounding-box area **≥ 15 × 15 = 225 px²** and confirmed by cascaded ROI confirmation
- **Below 225 px²:** warning-only, never allowed to contribute to the alert window

---

## Datasets Used in This Project

The final curated training corpus contains **172,022 images**, split into:
- **80% training**
- **10% validation**
- **10% test** 

### Primary drone detection datasets
These provide the positive drone samples used to train the detector:

1. **WOSDETC (Bird vs Drone)**  
   Video-based dataset containing birds and drones. One frame sampled every 2 frames. Drone instances kept as positives; birds treated as background.

2. **Anti-UAV-RGBT**  
   Multimodal dataset. Only the **visible-spectrum** images were retained; infrared was excluded. One frame extracted every 5 frames.

3. **DUT Anti-UAV**  
   Static image dataset with diverse drone appearances across environments and viewpoints.

4. **Anti-MUAV (Roboflow)**  
   Image-based dataset used to add drone shape and scale diversity, especially for small-object detection.

5. **MAV-VID**  
   Image dataset focused on micro aerial vehicles and challenging small-scale drone examples.

### False-positive suppression / background datasets
These were included as background-only or hard-negative data to reduce false detections, especially birds and urban motion artifacts.

1. **AirBird**  
   Bird-only dataset used to suppress avian false positives.

2. **BDD10K / BDD100K**  
   Large-scale driving dataset used to improve robustness against road scenes.  
   Note: the report text uses **BDD10K** in the dataset section and **BDD100K** in references.

3. **FBD-SV**  
   Bird-focused video dataset. One frame extracted every 3 frames.

4. **DETRAC / UA-DETRAC**  
   CCTV-style traffic and junction dataset used as background.  
   Note: the report uses both **DETRAC** and **UA-DETRAC** naming in different places.

5. **VIRAT**  
   Surveillance video dataset with human and vehicle interactions. One frame extracted every 3 frames.

### Why the dataset mix matters
The dataset was intentionally built to do two things:
- maximize drone appearance diversity across altitude, scale, background, and motion,
- suppress common false positives such as birds, traffic, and surveillance-scene motion.

---

## Training Setup

The final training configuration reported for the best-performing model is:

| Parameter | Value |
|---|---|
| Model Architecture | YOLOv26n |
| Dataset | Mixed Drone + Background Suppression |
| Image Size | 640 |
| Batch Size | 48 |
| Epochs | 70 |
| Initial Learning Rate (lr0) | 0.001 |
| Final LR Ratio (lrf) | 0.01 |
| Optimizer | AdamW |
| Weight Decay | 0.0005 |
| Warmup Epochs | 3 |
| Mosaic Augmentation | Enabled (disabled after epoch 50) |
| IoU Threshold | 0.7 |
| Mixed Precision (AMP) | Enabled |

Training was run on a **cloud-based NVIDIA RTX 3090 GPU**.

---

## How the Detection Pipeline Works

### 1) Stride-based inference
The detector does **not** run YOLO on every video frame. Instead, inference is executed every **N frames**, derived from `INFER_FPS` and the source video FPS. Non-inference frames reuse the last inference state. The report and current README both describe this as a core design rule.

### 2) Temporal ROI Propagation
At inference frame **t**, detections from the previous inference frame are used to generate square ROIs for frame **t+1**. Up to **3 ROIs** are generated, each with side length equal to the detector input size (**640 px**), and ROI generation excludes boxes below the area threshold used for ROI eligibility. If no valid ROI exists, the system falls back to full-frame inference.

### 3) Cascaded ROI Confirmation
The detector can optionally run a second-pass YOLO verification stage on selected detections. The report describes several cascade modes, including:
- **off**
- **triggered cascade** for small / low-confidence detections
- **always-on cascade**
- **alert-window cascade** based on average confidence over the alert window.

### 4) Temporal Continuity
Continuity is evaluated using bounding-box overlap between consecutive inference frames. A detection is treated as continuous only if:

**IoU(Bt−1, Bt) > 0.1** :

This continuity gate affects warning/alert decision stability and suppresses transient false positives.

### 5) Warning / Alert logic
Warning and alert events are based on a FIFO rolling window over inference frames. In the default configuration:
- **window size W = 10**
- **trigger threshold T = 9** :

Warnings are more permissive; alerts require stronger spatial and confidence conditions.

---

## Files

- `drone_detection.py` — the demo detector (core logic + OpenCV rendering + outputs)
- `drone_detection_gui.py` — desktop GUI runner (Qt / PySide6) for configs and event log

This matches the current repo README, which describes the GUI as a runner for configs and logs while video still renders in the OpenCV window. 

---

## Setup

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

If you want GPU acceleration, install a CUDA-matching PyTorch build (then install the requirements).


### 2) Set paths (in `drone_detection.py`)

At the top of `drone_detection.py`, set:

- `MODEL_WEIGHTS` — YOLO weights path
- `VIDEO_PATH` — input video path

**Annotation logic**
- `ANNOTATION_PATH_PRIMARY` (optional)
- Fallback is automatically: same as `VIDEO_PATH` but with `.txt` extension (same stem)

Example:
- `VIDEO_PATH = .../gopro_006.mp4`
- fallback annotation path becomes `.../gopro_006.txt`


## Run

### Option A — Run detector directly

```bash
python drone_detection.py
```

Controls (OpenCV window):
- `p` = pause/resume
- `q` or `ESC` = quit


### Option B — Run with GUI (recommended)

```bash
python drone_detection_gui.py
```

The GUI provides:
- Event log (WARNING / ALERT)
- Config panel (scrollable)
- Run button

The video still renders in the OpenCV window.


## Important toggles (in `drone_detection.py`)

### 1) Box persistence on non-inference frames

The detector runs YOLO on **stride-based inference frames** and reuses the last inference state on HOLD frames.

To control whether prediction rectangles stay visible on HOLD frames:

- `DRAW_PRED_BOXES_ON_HOLD_FRAMES = True`  
  Boxes persist between inference frames (stable UI)
- `DRAW_PRED_BOXES_ON_HOLD_FRAMES = False`  
  Boxes are drawn **only** on inference frames (HOLD frames show no prediction rectangles)

This affects **overlay drawing only**. Detection / event logic stays unchanged.

### 2) Live playback speed (OpenCV window pacing)

If the OpenCV display loop isn’t paced, playback can look **too fast** when inference is light.

Use:
- `PACE_LIVE_PLAYBACK_TO_SOURCE_FPS = True` to pace display to the input FPS
- `PLAYBACK_SPEED = 1.0` for normal speed (0.5 slow, 2.0 fast)

This changes **live display only** (output video encoding uses the writer FPS).


## Outputs

All outputs go under:

- `OUTPUT_ROOT = .../demo_outputs`

Per run, you get:
- a **unique output video** (if `SAVE_VIDEO=True`)
- a single shared CSV log (append-only across runs)
- optional saved frames for alert windows (10 frames) if `SAVE_ALERT_WINDOW_FRAMES=True`

The saved alert-window frames contain **only** the detected drone box (no logs/ROIs/gates).


## Notes

- This is a **demo detector**, not a benchmark framework.
- Stride-based inference is non-negotiable: YOLO runs every N frames (derived from `INFER_FPS` and source FPS).
- Cascaded confirmation must not draw its own rectangles (log-only).
- Temporal continuity affects only warning/alert hit counting and does **not** change P/R/F1 metrics.
