"""
FastAPI backend for drone detection.
Uses DroneDetector class from drone_detector.py 
"""

import asyncio
import base64
import cv2
import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Legacy Script
from working import drone_detection
import threading
import queue
import time
import json

app = FastAPI(title="Drone Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint for connection verification
@app.get("/api/health")
async def health_check():
    """Health check endpoint for startup verification."""
    return {"status": "ok", "service": "drone-detection-api"}

# Global state for Legacy Integration
detector_thread: Optional[threading.Thread] = None
stop_event = threading.Event()
pause_event = threading.Event()
# Queue for frames (producer=legacy script, consumer=websocket)
# We use a small maxsize to drop frames if WS is slow (simulates real-time)
frame_queue = queue.Queue(maxsize=2)
latest_stats = {}

# ESP32 state
esp32_address = "172.20.10.9:5000"

# Stream quality settings
QUALITY_PRESETS = {
    "360p": (640, 360),
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": None
}
stream_quality = "480p"

# Settings Persistence
# Settings Persistence
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


def load_settings():
    """Load settings from JSON and apply to drone_detection."""
    if not os.path.exists(SETTINGS_FILE):
        return
    
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        
        print(f"[INFO] Loading settings from {SETTINGS_FILE}: {data}")
        
        # Apply strict mapping because JSON keys match API keys (mostly), 
        # but apply_runtime_config needs CONSTANT_CASE names.
        
        # We reuse the logic from update_settings by creating a dummy update object?
        # Or just map manually.
        updates = {}
        # Map JSON keys (which match SettingsUpdate model) to Script Globals
        mapping = {
            "infer_fps": "INFER_FPS",
            "temporal_roi_enabled": "TEMPORAL_ROI_PROP_ENABLED",
            "show_gate": "SHOW_GATE",
            "show_troi": "SHOW_TROI",
            "show_cascade": "SHOW_CASCADE",
            "detect_conf": "DETECT_CONF",
            "cascade_mode": "CASCADED_ROI_CONFIRM_MODE",
            "warning_cooldown": "WARNING_COOLDOWN_S",
            "alert_cooldown": "ALERT_COOLDOWN_S",
            "save_video": "SAVE_VIDEO",
            "save_alert_frames": "SAVE_ALERT_WINDOW_FRAMES",
            "log_mode": "TOPLEFT_LOG_MODE",
            "roi_size": "ROI_SIZE",
            "cascade_trigger_conf": "CASCADE_TRIGGER_CONF",
            "cascade_accept_conf": "CASCADE_ACCEPT_CONF",
            "warning_window_size": "WARNING_WINDOW_FRAMES",
            "warning_require_hits": "WARNING_REQUIRE_HITS",
            "alert_window_size": "ALERT_WINDOW_FRAMES",
            "alert_require_hits": "ALERT_REQUIRE_HITS"
        }
        
        for json_key, script_key in mapping.items():
            if json_key in data:
                updates[script_key] = data[json_key]
                # Special case: Sync TROI conf
                if json_key == "detect_conf":
                    updates["TROI_DETECT_CONF"] = data[json_key]

        if updates:
            drone_detection.apply_runtime_config(**updates)
            
    except Exception as e:
        print(f"[ERROR] Failed to load settings: {e}")

def save_settings(new_data: dict):
    """Merge new_data into existing settings file."""
    try:
        current = {}
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                try:
                    current = json.load(f)
                except:
                    pass
        
        # Update current with new data
        current.update(new_data)
        
        with open(SETTINGS_FILE, "w") as f:
            json.dump(current, f, indent=2)
            
    except Exception as e:
        print(f"[ERROR] Failed to save settings: {e}")

# Load immediately on startup
load_settings()



def frame_callback_handler(frame, stats):
    """Called by legacy script for every frame (when headless)."""
    global latest_stats
    latest_stats = stats
    
    # Non-blocking put; if full, drop frame (real-time behavior)
    try:
        frame_queue.put_nowait((frame, stats))
    except queue.Full:
        pass

def init_detector_thread():
    """Start the legacy script in a separate thread."""
    global detector_thread, stop_event, pause_event, is_streaming
    
    if detector_thread and detector_thread.is_alive():
        return # Already running
        
    stop_event.clear()
    pause_event.clear()
    
    # reset queue
    with frame_queue.mutex:
        frame_queue.queue.clear()

    def run_wrapper():
        print("[INFO] Starting Legacy Drone Detection Script...")
        try:
            # We must ensure the script uses the selected video path if possible
            # The script uses a global VIDEO_PATH. We can inject it using apply_runtime_config
            if video_path and video_path != "webcam":
                drone_detection.apply_runtime_config(VIDEO_PATH=video_path)
                drone_detection.apply_runtime_config(VIDEO_PATH=video_path)
                
            # Inject ESP32 hooks
            def send_alert_real():
                if esp32_address:
                    try:
                        import requests
                        print(f"[ESP32] Sending POST /alert/drone to {esp32_address}...")
                        resp = requests.post(f"http://{esp32_address}/alert/drone", timeout=1.0)
                        print(f"[ESP32] ALERT Response: {resp.status_code} {resp.text}")
                    except Exception as e:
                        print(f"[ESP32] Failed to send ALERT: {e}")

            def send_warning_real():
                if esp32_address:
                    try:
                        import requests
                        print(f"[ESP32] Sending POST /alert/warning to {esp32_address}...")
                        resp = requests.post(f"http://{esp32_address}/alert/warning", timeout=1.0)
                        print(f"[ESP32] WARNING Response: {resp.status_code} {resp.text}")
                    except Exception as e:
                        print(f"[ESP32] Failed to send WARNING: {e}")

            drone_detection.send_alert_to_esp = send_alert_real
            drone_detection.send_warning_to_esp = send_warning_real
            
            drone_detection.main(
                headless=True,
                frame_callback=frame_callback_handler,
                stop_event=stop_event,
                pause_event=pause_event
            )
        except Exception as e:
            print(f"[ERROR] Script Crashed: {e}")
        finally:
            print("[INFO] Legacy Script Finished")
            is_streaming = False

    detector_thread = threading.Thread(target=run_wrapper, daemon=True)
    detector_thread.start()
    is_streaming = True



# Request models
class FileSource(BaseModel):
    path: str

class YouTubeSource(BaseModel):
    url: str

class ESP32Connect(BaseModel):
    address: str

class SettingsUpdate(BaseModel):
    cascade_mode: Optional[str] = None
    temporal_roi_enabled: Optional[bool] = None
    infer_fps: Optional[int] = None
    show_gate: Optional[bool] = None
    show_troi: Optional[bool] = None
    show_cascade: Optional[bool] = None
    log_mode: Optional[str] = None
    save_video: Optional[bool] = None
    save_alert_frames: Optional[bool] = None
    warning_cooldown: Optional[float] = None
    alert_cooldown: Optional[float] = None
    detect_conf: Optional[float] = None
    roi_size: Optional[int] = None
    # Window settings
    warning_window_size: Optional[int] = None
    warning_require_hits: Optional[int] = None
    alert_window_size: Optional[int] = None
    alert_require_hits: Optional[int] = None
    cascade_trigger_conf: Optional[float] = None
    cascade_accept_conf: Optional[float] = None

# Device setting (cpu/gpu)
current_device = "gpu"

@app.post("/api/device")
async def set_device(device: str = "cpu"):
    """Switch between CPU and GPU for inference."""
    global current_device
    if device not in ["cpu", "gpu"]:
        raise HTTPException(status_code=400, detail="Device must be 'cpu' or 'gpu'")
    
    current_device = device
    # In legacy mode, device is set at startup. 
    # To support dynamic switch, we would need to restart the thread.
    # For now, we accept the request to prevent UI error but log it.
    print(f"[WARN] Device switch to {device} requested. Restart detection to apply.")
    return {"device": device, "status": "ok"}


# Status
@app.get("/api/status")
async def get_status():
    global detector, is_streaming, video_cap
    if detector is None:
        return {
            "warning_active": False,
            "alert_active": False,
            "is_streaming": False,
            "video_loaded": False,
        }
    # Build status from detector state
    return {
        "warning_active": latest_stats.get("warning_active", False),
        "alert_active": latest_stats.get("alert_active", False),
        "warning_events": latest_stats.get("warning_events", 0),
        "alert_events": latest_stats.get("alert_events", 0),
        "is_streaming": is_streaming and (detector_thread and detector_thread.is_alive()),
        "video_loaded": True, # Legacy script handles its own loading
        "esp32_connected": esp32_address is not None,
        "total_frames": 0, # Script logic
        "frame_id": latest_stats.get("frame_id", 0),
    }


# Source endpoints
@app.post("/api/source/file")
async def open_file(data: FileSource):
    global video_cap, video_path, video_fps, total_frames, detector
    
    video_path = data.path
    # We delay start until 'start_detection' is called, OR we just set the path config
    # The script opens the video in main(). So we just set the path variable.
    # Note: If thread is running, we might need to restart it.
    
    if detector_thread and detector_thread.is_alive():
        stop_event.set()
        detector_thread.join(timeout=2.0)
    
    return {"success": True, "frames": 0, "fps": 0}


@app.post("/api/source/webcam")
async def open_webcam():
    global video_cap, video_path, video_fps, total_frames, detector
    
    # Webcam not fully supported in simple legacy wrapper without changing VIDEO_PATH to int(0)
    # Use path "0" or 0
    video_path = 0 
    
    if detector_thread and detector_thread.is_alive():
        stop_event.set()
        detector_thread.join(timeout=2.0)

    return {"success": True, "fps": 30}


@app.post("/api/source/youtube")
async def open_youtube(data: YouTubeSource):
    global video_cap, video_path, video_fps, total_frames, detector
    
    try:
        import yt_dlp
        
        ydl_opts = {
            'format': 'best[height<=720]',
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(data.url, download=False)
            stream_url = info['url']
        
        video_path = str(stream_url)
        
        if detector_thread and detector_thread.is_alive():
            stop_event.set()
            detector_thread.join(timeout=2.0)

        return {"success": True, "frames": 0, "fps": 0}
        
        return {"success": True, "frames": total_frames, "fps": video_fps}
    except ImportError:
        raise HTTPException(400, "yt-dlp not installed")
    except Exception as e:
        raise HTTPException(400, f"Failed to open YouTube: {str(e)}")


# Control endpoints
@app.post("/api/control/start")
async def start_detection():
    # Start the thread
    init_detector_thread()
    # Unpause if paused
    pause_event.clear()
    return {"success": True}


@app.post("/api/control/stop")
async def stop_detection():
    stop_event.set()
    return {"success": True}

@app.post("/api/control/pause")
async def pause_detection():
    if pause_event.is_set():
        pause_event.clear() # Resume
    else:
        pause_event.set() # Pause
    return {"success": True, "paused": pause_event.is_set()}


@app.post("/api/control/seek")
async def seek_video(data: dict):
    frames = data.get("frames", 0)
    
    # Pass seek request to legacy script via global
    # We use a RELATIVE seek global since absolute position is hard to sync without reading current
    drone_detection.REQUESTED_SEEK_REL = frames
    
    return {"success": True, "frames": frames}


@app.post("/api/control/reset")
async def reset_detection():
    """Reset detector state for replay."""
    global detector, video_cap
    if detector:
        detector.reset()
    if video_cap and video_cap.isOpened():
        video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    return {"success": True}


# Settings endpoints
@app.get("/api/settings")
async def get_settings():
    # Return subset of globals from script
    return {
        "infer_fps": drone_detection.INFER_FPS,
        "temporal_roi_enabled": drone_detection.TEMPORAL_ROI_PROP_ENABLED,
        "show_gate": drone_detection.SHOW_GATE,
        "show_troi": drone_detection.SHOW_TROI,
        "show_cascade": drone_detection.SHOW_CASCADE,
        "detect_conf": drone_detection.DETECT_CONF,
        "cascade_mode": drone_detection.CASCADED_ROI_CONFIRM_MODE,
        "warning_cooldown": drone_detection.WARNING_COOLDOWN_S,
        "alert_cooldown": drone_detection.ALERT_COOLDOWN_S,
        "save_video": drone_detection.SAVE_VIDEO,
        "save_alert_frames": drone_detection.SAVE_ALERT_WINDOW_FRAMES,
        "log_mode": drone_detection.TOPLEFT_LOG_MODE,
        "cascade_trigger_conf": drone_detection.CASCADE_TRIGGER_CONF,
        "cascade_accept_conf": drone_detection.CASCADE_ACCEPT_CONF,
        "roi_size": drone_detection.ROI_SIZE,
        "warning_window_size": drone_detection.WARNING_WINDOW_FRAMES,
        "warning_require_hits": drone_detection.WARNING_REQUIRE_HITS,
        "alert_window_size": drone_detection.ALERT_WINDOW_FRAMES,
        "alert_require_hits": drone_detection.ALERT_REQUIRE_HITS,
    }


@app.post("/api/settings")
@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate):
    # Map frontend keys to script globals (CAPS)
    updates = {}
    if settings.infer_fps is not None: updates["INFER_FPS"] = settings.infer_fps
    if settings.temporal_roi_enabled is not None: updates["TEMPORAL_ROI_PROP_ENABLED"] = settings.temporal_roi_enabled
    if settings.show_gate is not None: updates["SHOW_GATE"] = settings.show_gate
    if settings.show_troi is not None: updates["SHOW_TROI"] = settings.show_troi
    if settings.show_cascade is not None: updates["SHOW_CASCADE"] = settings.show_cascade
    if settings.detect_conf is not None: 
        updates["DETECT_CONF"] = settings.detect_conf
        # Sync TROI conf? User request "change playback settings appropriately"
        updates["TROI_DETECT_CONF"] = settings.detect_conf
        
    # Additional mappings
    if settings.cascade_mode is not None: updates["CASCADED_ROI_CONFIRM_MODE"] = settings.cascade_mode
    if settings.warning_cooldown is not None: updates["WARNING_COOLDOWN_S"] = settings.warning_cooldown
    if settings.alert_cooldown is not None: updates["ALERT_COOLDOWN_S"] = settings.alert_cooldown
    if settings.save_video is not None: updates["SAVE_VIDEO"] = settings.save_video
    if settings.save_alert_frames is not None: updates["SAVE_ALERT_WINDOW_FRAMES"] = settings.save_alert_frames
    if settings.log_mode is not None: updates["TOPLEFT_LOG_MODE"] = settings.log_mode
    if settings.roi_size is not None: updates["ROI_SIZE"] = settings.roi_size
    if settings.cascade_trigger_conf is not None: updates["CASCADE_TRIGGER_CONF"] = settings.cascade_trigger_conf
    if settings.cascade_accept_conf is not None: updates["CASCADE_ACCEPT_CONF"] = settings.cascade_accept_conf
    if settings.warning_window_size is not None: updates["WARNING_WINDOW_FRAMES"] = settings.warning_window_size
    if settings.warning_require_hits is not None: updates["WARNING_REQUIRE_HITS"] = settings.warning_require_hits
    if settings.alert_window_size is not None: updates["ALERT_WINDOW_FRAMES"] = settings.alert_window_size
    if settings.alert_require_hits is not None: updates["ALERT_REQUIRE_HITS"] = settings.alert_require_hits
    
    # Apply
    drone_detection.apply_runtime_config(**updates)

    # PERSIST: Save the values that were handled
    # We reconstruct a dict of {json_key: value} based on what was in 'settings'
    # 'settings' is a SettingsUpdate object, containing .exclude_unset=True equivalent?
    # We iterate typical keys.
    raw_dict = settings.dict(exclude_unset=True)
    if raw_dict:
        save_settings(raw_dict)
    
    # RELIABLE SETTINGS: Restart the detection thread if it's running
    if detector_thread and detector_thread.is_alive():
        print("Settings changed: Restarting detection thread...")
        stop_event.set()
        # Wait briefly for it to stop (it checks stop_event every frame)
        detector_thread.join(timeout=2.0)
        
        # Restart
        init_detector_thread()
        pause_event.clear() # Ensure we don't start paused
    
    return {"success": True, "settings": updates}


# Alert endpoints
@app.post("/api/alert/dismiss")
async def dismiss_alert():
    """
    GLOBAL SUPPRESSION: Clears BOTH warning AND alert states.
    
    This is NOT alert-only. It resets all detection windows and triggers
    cooldowns for both warning and alert levels. Use this as the single
    "dismiss all" action - do NOT add separate warning-only dismiss.
    """
    # Direct global reset for legacy script
    drone_detection.win_warning.clear()
    drone_detection.win_alert.clear()
    drone_detection.inference_rows.clear()
    drone_detection.warning_active = False
    drone_detection.alert_active = False

    # Reset cooldowns? Or Trigger cooldowns? User says "trigger cooldowns".
    # Actually "trigger cooldowns" means START the cooldown so it doesn't alert again immediately.
    # So we should set cooldown_left to max.
    drone_detection.warn_cooldown_left = drone_detection.warn_cooldown_frames
    drone_detection.alert_cooldown_left = drone_detection.alert_cooldown_frames
    
    # Also send clear to ESP32
    if esp32_address:
        try:
            import requests
            requests.post(f"http://{esp32_address}/alert/clear", timeout=1)
        except:
            pass
    return {"success": True}


# ESP32 endpoint
@app.post("/api/esp32/connect")
async def connect_esp32(data: ESP32Connect):
    global esp32_address
    try:
        import requests
        response = requests.get(f"http://{data.address}/status", timeout=2)
        if response.status_code == 200:
            esp32_address = data.address
            return {"success": True}
    except:
        pass
    raise HTTPException(400, "Failed to connect to ESP32")


@app.get("/api/esp32/status")
async def get_esp32_status():
    return {"connected": esp32_address is not None, "address": esp32_address}


# Stream quality
@app.post("/api/stream/quality")
async def set_stream_quality(quality: str = "480p"):
    global stream_quality
    if quality in QUALITY_PRESETS:
        stream_quality = quality
        return {"success": True, "quality": quality}
    raise HTTPException(400, f"Invalid quality. Options: {list(QUALITY_PRESETS.keys())}")


@app.get("/api/stream/quality")
async def get_stream_quality():
    return {"quality": stream_quality, "options": list(QUALITY_PRESETS.keys())}


# Send alert to ESP32
def send_esp32_alert(alert_type: str, message: str = ""):
    if esp32_address:
        try:
            import requests
            if alert_type == "alert":
                requests.post(f"http://{esp32_address}/alert/drone", 
                            json={"message": message}, timeout=0.5)
            elif alert_type == "warning":
                requests.post(f"http://{esp32_address}/alert/warning",
                            json={"message": message}, timeout=0.5)
            elif alert_type == "clear":
                requests.post(f"http://{esp32_address}/alert/clear", timeout=0.5)
        except:
            pass


# WebSocket for video streaming
@app.websocket("/ws/video")
async def video_stream(websocket: WebSocket):
    global detector, video_cap, is_streaming
    
    await websocket.accept()
    
    # Track alert state for ESP32
    last_alert_state = False
    last_warning_state = False
    
    try:
        import time
        last_frame_time = 0
        target_fps = 25
        
        while True:
            # Consumer: Get frame from queue
            try:
                # Wait for frame (timeout to allow check for disconnect)
                frame, stats = frame_queue.get(timeout=0.1)
                
                # Resize if needed (script handles visualization resizing? No, main() creates local `vis`)
                # Let's trust the script's visual output, maybe resize for bandwidth if large
                resolution = QUALITY_PRESETS.get(stream_quality)
                if resolution is not None:
                    preview = cv2.resize(frame, resolution)
                else:
                    preview = frame
                
                # Encode
                _, buffer = cv2.imencode('.jpg', preview, [cv2.IMWRITE_JPEG_QUALITY, 65])
                b64 = base64.b64encode(buffer).decode('utf-8')
                
                await websocket.send_json({
                        "type": "frame",
                        "data": b64,
                        "stats": stats, # Already formatted in callback
                        "alert_active": stats['alert_active'],
                        "warning_active": stats['warning_active'],
                })
                
            except queue.Empty:
                await asyncio.sleep(0.01)
                continue
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WS Error: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
