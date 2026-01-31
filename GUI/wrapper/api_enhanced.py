"""
Enhanced FastAPI backend for drone detection with wrapper integration
"""

import asyncio
import base64
import cv2
import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wrapper.detection_wrapper import DetectionSystem
from wrapper.communication import CommunicationModule

app = FastAPI(title="Drone Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
system = DetectionSystem()
active_clients: list[WebSocket] = []

# Stream quality settings
QUALITY_PRESETS = {
    "360p": (640, 360),
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": None
}
stream_quality = "480p"


# Request models
class FileSource(BaseModel):
    path: str

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


# Status
@app.get("/api/status")
async def get_status():
    status = system.get_status()
    return {
        "connected": True,
        "is_streaming": status.get('is_running', False),
        "alert_active": status.get('alert_active', False),
        "warning_active": status.get('warning_active', False),
        "esp32_connected": status.get('esp32_connected', False),
        "alert_count": status.get('alert_count', 0),
        "warning_count": status.get('warning_count', 0),
    }


# Source endpoints
@app.post("/api/source/file")
async def open_file(data: FileSource):
    """Set video file path (will be used when detection starts)"""
    if not os.path.exists(data.path):
        raise HTTPException(400, f"File not found: {data.path}")
    
    system.detector.set_config({'VIDEO_PATH': data.path})
    return {"success": True, "path": data.path}


@app.post("/api/source/webcam")
async def open_webcam():
    """Webcam not supported in headless mode"""
    raise HTTPException(400, "Webcam not supported. Please use file input.")


@app.post("/api/source/youtube")
async def open_youtube(data: dict):
    """YouTube download not supported in this wrapper"""
    raise HTTPException(400, "YouTube not supported. Please download video first and use file input.")


# Control endpoints
@app.post("/api/control/start")
async def start_detection(background_tasks: BackgroundTasks):
    """Start detection process"""
    video_path = system.detector.config.get('VIDEO_PATH')
    if not video_path:
        raise HTTPException(400, "No video file selected. Use /api/source/file first.")
    
    if not os.path.exists(video_path):
        raise HTTPException(400, f"Video file not found: {video_path}")
    
    # Start in background
    success = system.start(
        video_path=video_path,
        esp32_address=system.comm.esp32_address
    )
    
    if not success:
        raise HTTPException(500, "Failed to start detection")
    
    return {"success": True}


@app.post("/api/control/stop")
async def stop_detection():
    """Stop detection process"""
    system.stop()
    return {"success": True}


@app.post("/api/control/seek")
async def seek_video(data: dict):
    """Video seeking not supported in subprocess mode"""
    return {"success": False, "message": "Seek not supported in this mode"}


# Settings endpoints
@app.get("/api/settings")
async def get_settings():
    """Get current settings"""
    config = system.detector.config
    return {
        "cascade_mode": config.get('CASCADED_ROI_CONFIRM_MODE', 'None'),
        "temporal_roi_enabled": config.get('TEMPORAL_ROI_PROP_ENABLED', True),
        "infer_fps": config.get('INFER_FPS', 5),
        "show_gate": config.get('SHOW_GATE', False),
        "show_troi": config.get('SHOW_TROI', False),
        "show_cascade": config.get('SHOW_CASCADE', False),
        "log_mode": config.get('TOPLEFT_LOG_MODE', 'windows_big'),
        "save_video": config.get('SAVE_VIDEO', False),
        "save_alert_frames": config.get('SAVE_ALERT_WINDOW_FRAMES', True),
        "warning_cooldown": config.get('WARNING_COOLDOWN_S', 3.0),
        "alert_cooldown": config.get('ALERT_COOLDOWN_S', 3.0),
    }


@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate):
    """Update settings"""
    updates = {}
    
    if settings.cascade_mode is not None:
        updates['CASCADED_ROI_CONFIRM_MODE'] = settings.cascade_mode
    if settings.temporal_roi_enabled is not None:
        updates['TEMPORAL_ROI_PROP_ENABLED'] = settings.temporal_roi_enabled
    if settings.infer_fps is not None:
        updates['INFER_FPS'] = settings.infer_fps
    if settings.show_gate is not None:
        updates['SHOW_GATE'] = settings.show_gate
    if settings.show_troi is not None:
        updates['SHOW_TROI'] = settings.show_troi
    if settings.show_cascade is not None:
        updates['SHOW_CASCADE'] = settings.show_cascade
    if settings.log_mode is not None:
        updates['TOPLEFT_LOG_MODE'] = settings.log_mode
    if settings.save_video is not None:
        updates['SAVE_VIDEO'] = settings.save_video
    if settings.save_alert_frames is not None:
        updates['SAVE_ALERT_WINDOW_FRAMES'] = settings.save_alert_frames
    if settings.warning_cooldown is not None:
        updates['WARNING_COOLDOWN_S'] = settings.warning_cooldown
    if settings.alert_cooldown is not None:
        updates['ALERT_COOLDOWN_S'] = settings.alert_cooldown
    
    system.detector.set_config(updates)
    
    return {"success": True, "settings": await get_settings()}


# Alert endpoints
@app.post("/api/alert/dismiss")
async def dismiss_alert():
    """Dismiss current alert"""
    system.dismiss_alert()
    return {"success": True}


# ESP32 endpoint
@app.post("/api/esp32/connect")
async def connect_esp32(data: ESP32Connect):
    """Connect to ESP32"""
    system.comm.esp32_address = data.address
    if system.comm.test_connection():
        return {"success": True}
    raise HTTPException(400, "Failed to connect to ESP32")


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


# Device endpoint (not applicable in subprocess mode)
@app.post("/api/device")
async def set_device(device: str = "cpu"):
    """Device selection not supported in subprocess mode"""
    return {"success": True, "device": device, "message": "Device setting not available in this mode"}


@app.get("/api/device")
async def get_device():
    return {"device": "cpu"}


# WebSocket for status streaming (since we can't stream video from subprocess)
@app.websocket("/ws/video")
async def video_stream(websocket: WebSocket):
    """
    WebSocket for status updates
    Note: Video streaming not available when running drone_detection.py as subprocess
    """
    await websocket.accept()
    active_clients.append(websocket)
    
    try:
        last_status = {}
        
        while True:
            status = system.get_status()
            
            # Send status update
            await websocket.send_json({
                "type": "status",
                "stats": {
                    "fps": 0,  # Not available in subprocess mode
                    "frame": 0,
                    "detections": 0,
                    "alerts": status.get('alert_count', 0),
                    "warnings": status.get('warning_count', 0)
                },
                "alert_active": status.get('alert_active', False),
                "warning_active": status.get('warning_active', False),
            })
            
            await asyncio.sleep(0.5)  # Update every 500ms
                
    except WebSocketDisconnect:
        active_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
