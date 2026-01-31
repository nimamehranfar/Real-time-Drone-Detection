# Drone Detection System

Real-time drone detection using YOLO and an ESP32 alert system.

## Quick Start

### 1. Prerequisites
- Python 3.9+
- Node.js 18+
- npm

### 2. Setup (One-time)
```bash
python setup.py
```
This installs:
- PyTorch (CUDA if GPU detected, otherwise CPU)
- YOLO, OpenCV, FastAPI dependencies
- Frontend npm packages

### 3. Run
**Double-click `DroneDetect.bat`** or run:
```bash
python run_app.py
```

## Project Structure
```
├── model/            # Nima's core detection algorithms
├── wrapper/          # GUI wrapper and API layer
├── ui/               # React + Vite frontend
├── esp32/            # ESP32 alert firmware
├── yolo26n_trained/  # Pre-trained YOLO model weights
├── setup.py          # One-click installer
├── run_app.py        # Python launcher
└── DroneDetect.bat   # Windows launcher
```

## ESP32 Integration
See `esp32/` folder for the alert system firmware that works with this application.
