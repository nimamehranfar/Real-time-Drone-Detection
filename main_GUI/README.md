# Drone Detection System

A real-time drone detection application using YOLOv8, FastAPI, and React.

## Features

- **Real-time Detection**: Supports video files, webcam, and YouTube URLs.
- **Advanced Logic**:
  - **Temporal ROI Propagation**: Tracks drones across frames for efficiency.
  - **Cascaded Verification**: Double-checks small detections to reduce false positives.
  - **Warning & Alert Logic**: N-of-M window consistency checks (e.g., 9 out of 10 frames).
- **Modern UI**: React-based interface with dark/light mode, fullscreen video, and cumulative statistics.
- **Persistence**: Settings and alerts are saved automatically.
- **Hardware Integration**: Optional ESP32 buzzer support for physical alerts.

## Project Structure

```
├── api.py                    # FastAPI backend (controls detection loop)
├── run_app.py                # Main application launcher (Backend + Frontend)
├── requirements.txt          # Python dependencies
├── settings.json             # Persistent application settings
├── ui/                       # React Frontend source code
├── working/
│   ├── drone_detection.py    # Core logic (YOLO inference, state machine)
│   ├── drone_detection_gui.py # Standalone GUI implementation 
│   └── demo_outputs/         # Saved detection videos
├── yolo26n_trained/          # Custom YOLO model weights & training results
│   └── weights/              # Model weights
└── runs/                     # YOLOv8 inference logs (auto-generated)
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js & npm (for the frontend)

### Installation

1.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Install Frontend Dependencies**:
    ```bash
    cd ui
    npm install
    cd ..
    ```

### Running the App

The easiest way to run the full stack (Backend + Frontend) is:

```bash
python run_app.py
```

This will:
1.  Start the FastAPI backend on port 8000.
2.  Start the React frontend on port 5173.
3.  Automatically open your browser to `http://localhost:5173`.

## Usage

1.  **Select Source**: Choose "Video File" or "YouTube" from the UI.
2.  **Control**: Use Play/Pause/Stop buttons.
3.  **Settings**: Click the gear icon to adjust YOLO confidence, ROI size, and alert sensitivities.
4.  **Fullscreen**: Toggle fullscreen mode for immersive monitoring.

## Troubleshooting

-   **"Backend not ready"**: Ensure you have installed all Python requirements.
-   **"WinError 123"**: Fixed in latest version (YouTube filenames are now safer).
-   **Port Conflicts**: The app attempts to clear ports 8000 and 5173 on startup. If issues persist, check other running services.
