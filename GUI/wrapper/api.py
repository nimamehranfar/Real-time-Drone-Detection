"""
FastAPI backend for drone detection.
Streams video via WebSocket, REST API for controls.
"""

import asyncio
import base64
import cv2
import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wrapper import DroneDetector, CommunicationModule

app = FastAPI(title="Drone Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
system = DroneDetector()
is_streaming = False
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
    cascade_trigger_conf: Optional[float] = None
    cascade_accept_conf: Optional[float] = None
    roi_size: Optional[int] = None


# Status
@app.get("/api/status")
async def get_status():
    status = system.get_status()
    status['is_streaming'] = is_streaming
    status['esp32_connected'] = system.comm.connected if system.comm else False
    return status


# Source endpoints
@app.post("/api/source/file")
async def open_file(data: FileSource):
    if system.video.open_file(data.path):
        system.video_fps = system.video.fps
        system.update_stride()
        return {"success": True, "frames": system.video.total_frames}
    raise HTTPException(400, "Failed to open file")


@app.post("/api/source/webcam")
async def open_webcam():
    if system.video.open_webcam(0):
        system.video_fps = system.video.fps or 30
        system.update_stride()
        return {"success": True}
    raise HTTPException(400, "Failed to open webcam")


@app.post("/api/source/youtube")
async def open_youtube(data: YouTubeSource):
    if system.video.open_youtube(data.url):
        system.video_fps = system.video.fps
        system.update_stride()
        return {"success": True, "frames": system.video.total_frames}
    raise HTTPException(400, "Failed to download YouTube video")


# Control endpoints
@app.post("/api/control/start")
async def start_detection():
    global is_streaming
    system.start()
    is_streaming = True
    return {"success": True}


@app.post("/api/control/stop")
async def stop_detection():
    global is_streaming
    system.stop()
    is_streaming = False
    return {"success": True}


@app.post("/api/control/seek")
async def seek_video(data: dict):
    frames = data.get("frames", 0)
    if system.video.cap:
        current = int(system.video.cap.get(1))
        new_pos = max(0, current + frames)
        if system.video.total_frames > 0:
            new_pos = min(new_pos, system.video.total_frames - 1)
        system.video.cap.set(1, new_pos)
        return {"success": True, "frame": new_pos}
    raise HTTPException(400, "No video loaded")


# Settings endpoints
@app.get("/api/settings")
async def get_settings():
    return system.get_settings()


@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate):
    updates = {k: v for k, v in settings.dict().items() if v is not None}
    system.update_settings(updates)
    return {"success": True, "settings": system.get_settings()}


# Alert endpoints
@app.post("/api/alert/dismiss")
async def dismiss_alert():
    system.dismiss_alert()
    return {"success": True}


@app.post("/api/alert/cooldown")
async def set_cooldown(seconds: float = 3.0):
    system.alert_cooldown = max(0, seconds)
    return {"success": True, "cooldown": seconds}


# Device endpoint
@app.post("/api/device")
async def set_device(device: str = "cpu"):
    if device not in ["cpu", "gpu", "cuda"]:
        raise HTTPException(400, "Device must be 'cpu' or 'gpu'")
    try:
        actual_device = "cuda" if device == "gpu" else device
        system.set_device(actual_device)
        return {"success": True, "device": device}
    except Exception as e:
        raise HTTPException(400, f"Failed to switch to {device}: {str(e)}")


@app.get("/api/device")
async def get_device():
    return {"device": system.device}


# ESP32 endpoint
@app.post("/api/esp32/connect")
async def connect_esp32(data: ESP32Connect):
    system.set_comm(data.address)
    if system.comm and system.comm.test_connection():
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


# WebSocket for video streaming
@app.websocket("/ws/video")
async def video_stream(websocket: WebSocket):
    await websocket.accept()
    active_clients.append(websocket)
    
    try:
        import time
        last_frame_time = 0
        target_fps = 20  # Reduced from 25 to prevent lag spikes
        
        while True:
            if is_streaming and system.video.is_opened():
                current_time = time.time()
                elapsed = current_time - last_frame_time
                if elapsed < 1/target_fps:
                    await asyncio.sleep(1/target_fps - elapsed)
                    continue
                
                ret, frame = system.video.read_frame()
                if ret:
                    last_frame_time = time.time()
                    
                    # Process frame
                    annotated, confirmed = system.process_frame(frame)
                    
                    # Resize for streaming
                    resolution = QUALITY_PRESETS.get(stream_quality)
                    if resolution is not None:
                        preview = cv2.resize(annotated, resolution)
                    else:
                        preview = annotated
                    
                    # Encode as JPEG (lower quality for smoother streaming)
                    _, buffer = cv2.imencode('.jpg', preview, [cv2.IMWRITE_JPEG_QUALITY, 60])
                    b64 = base64.b64encode(buffer).decode('utf-8')
                    
                    # Send frame + stats
                    await websocket.send_json({
                        "type": "frame",
                        "data": b64,
                        "stats": {
                            "fps": round(system.stats['current_fps'], 1),
                            "frame": system.frame_idx,
                            "detections": len(confirmed),
                            "alerts": system.stats['total_alerts'],
                            "warnings": system.stats.get('total_warnings', 0)
                        },
                        "alert_active": system.alert_active,
                        "warning_active": system.warning_active,
                        "new_detections": []
                    })
                else:
                    await asyncio.sleep(0.05)
            else:
                await asyncio.sleep(0.1)
                
    except WebSocketDisconnect:
        active_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
