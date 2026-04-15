# Real-time Drone Detection (Video-based)

A desktop demo app built around a **single-class YOLO detector (drone)**.  
It runs detection on a video, draws a real-time overlay in an **OpenCV window**, and triggers **warning / alert** events with cooldowns.

It also supports (configurable) logic for:

- **Temporal ROI Propagation**: reuse prior detections to generate up to 3 square ROIs (full-frame coordinates)
- **Cascaded ROI Confirmation**: optional second-pass YOLO verification (no extra rectangles drawn; log-only)
- **Temporal Continuity**: decision-only continuity gate between consecutive *inference* frames (affects warning/alert hit counting only)

Outputs are written to a per-run folder and a single shared CSV (append-only across runs).


## Files

- `drone_detection.py` — the demo detector (core logic + OpenCV rendering + outputs)
- `drone_detection_gui.py` — modern desktop GUI runner (Qt / PySide6) for configs + event log  
  (video still shows in the OpenCV window; the GUI has **no preview section**)


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
