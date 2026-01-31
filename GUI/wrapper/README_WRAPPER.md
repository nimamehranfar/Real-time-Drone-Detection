# Drone Detection System - Wrapper Integration

## Overview

This wrapper connects your `drone_detection.py` script with the ESP32 hardware and web UI **without modifying the original detection code**.

## Architecture

```
┌─────────────────┐
│   Web UI        │ (React frontend)
└────────┬────────┘
         │ HTTP/WebSocket
┌────────▼────────┐
│   FastAPI       │ (api_enhanced.py)
└────────┬────────┘
         │
┌────────▼────────┐
│ DetectionSystem │ (detection_wrapper.py)
└───┬─────────┬───┘
    │         │
    │         └─────────┐
    │                   │
┌───▼──────────┐  ┌─────▼─────────┐
│drone_        │  │Communication  │
│detection.py  │  │Module         │
│(subprocess)  │  └───────┬───────┘
└──────────────┘          │
                    ┌─────▼─────┐
                    │  ESP32    │
                    └───────────┘
```

## How It Works

### 1. Configuration Injection

The wrapper (`detection_wrapper.py`) creates a temporary copy of `drone_detection.py` with configuration overrides injected. This allows the UI to control settings without modifying the original file.

### 2. Event Detection

The wrapper monitors the subprocess output for event messages:
- Parses log lines for "Warning=" and "Alert=" counters
- Detects when counts increase (new event occurred)
- Triggers callbacks to send events to ESP32

### 3. ESP32 Communication

When an event is detected:
- **Warning**: Calls `send_warning_alert()` → ESP32 shows on OLED only (no buzzer)
- **Alert**: Calls `send_drone_alert()` → ESP32 shows on OLED AND activates buzzer

## Files

### wrapper/detection_wrapper.py
- `DroneDetector`: Runs drone_detection.py as subprocess, monitors for events
- `DetectionSystem`: High-level coordinator connecting detector + ESP32

### wrapper/api_enhanced.py
- Enhanced FastAPI backend with all UI endpoints
- Integrates with DetectionSystem instead of direct detection

### wrapper/communication.py
- Already created by your friend
- Sends HTTP requests to ESP32

## UI Configuration Options

All these settings are exposed in the UI and passed to drone_detection.py:

| Setting | Type | Options | Default |
|---------|------|---------|---------|
| Video Path | string | file path | - |
| Cascade Mode | select | None, Cascade Low/Small, Cascade All, Alert-Window Cascade | None |
| Temporal ROI | toggle | True/False | True |
| Show Gate | toggle | True/False | False |
| Show TROI | toggle | True/False | False |
| Show Cascade | toggle | True/False | False |
| Log Mode | select | off, full, windows_big | windows_big |
| Save Video | toggle | True/False | False |
| Save Alert Frames | toggle | True/False | True |
| Warning Cooldown | number | seconds | 3.0 |
| Alert Cooldown | number | seconds | 3.0 |
| Inference FPS | number | 1-30 | 5 |

## Usage

### Start the system:

```bash
# Terminal 1: Start backend
cd GUI/wrapper
python api_enhanced.py

# Terminal 2: Start frontend
cd GUI/ui
npm run dev
```

### Or use the launcher:
```bash
python run_app.py
```

## Event Flow Example

1. User selects video in UI and clicks "Play"
2. UI sends config to `/api/settings` and `/api/source/file`
3. UI calls `/api/control/start`
4. Backend creates temp script with config overrides
5. Backend starts `drone_detection.py` as subprocess
6. Wrapper monitors subprocess output
7. When "Events: Warning=1" appears in output:
   - Wrapper detects count increase
   - Calls `comm.send_warning_alert("Warning: Possible drone")`
   - ESP32 receives HTTP POST to `/alert/warning`
   - ESP32 shows message on OLED (no buzzer)
8. When "Events: Alert=1" appears in output:
   - Wrapper detects count increase
   - Calls `comm.send_drone_alert("ALERT: Drone confirmed!")`
   - ESP32 receives HTTP POST to `/alert/drone`
   - ESP32 shows message on OLED AND activates buzzer

## Limitations

Because drone_detection.py runs as a subprocess:

1. **No video streaming**: The UI won't show the annotated video feed
   - Solution: Set `SAVE_VIDEO = True` and review output video after
   
2. **No seek control**: Can't jump to different frames
   - The video plays through from start to finish

3. **No real-time FPS**: Can't display current processing FPS
   - Check console logs or output video for performance

## Benefits

✅ **Zero modification** to drone_detection.py
✅ **Zero modification** to ESP32 code
✅ All UI configuration options work
✅ Alert and Warning events properly trigger ESP32
✅ Clean separation of concerns

## Alternative: Direct Integration

If you want video streaming and real-time control, you'd need to refactor `drone_detection.py` into a class-based API. But that violates your requirement of minimal changes.

## Troubleshooting

**Events not triggering:**
- Check console for subprocess output
- Ensure `TOPLEFT_LOG_MODE` includes event logging
- Verify ESP32 address is correct

**ESP32 not responding:**
- Test connection: `curl http://drone-alert.local:5000/status`
- Check network connectivity
- Try IP address instead of mDNS

**Detection not starting:**
- Verify video file path exists
- Check Python environment has all dependencies
- Look for errors in backend console
