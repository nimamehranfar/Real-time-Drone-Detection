import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time

app = FastAPI(title="Mock ESP32")

# Enable CORS (so the frontend can talk to us directly if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# State
state = {
    "buzzer_active": False,
    "last_beep": 0
}

@app.get("/status")
def get_status():
    print(f"[{time.strftime('%H:%M:%S')}] GET /status - Connection Check")
    return {
        "connected": True,
        "buzzer_active": state["buzzer_active"],
        "ip": "127.0.0.1 (MOCK)",
        "rssi": -42
    }

@app.post("/buzzer/on")
def buzzer_on():
    state["buzzer_active"] = True
    print("\n" + "="*40)
    print(f"[{time.strftime('%H:%M:%S')}] 🚨 BUZZER ACTIVATED! (Beep! Beep! Beep!)")
    print("="*40 + "\n")
    return {"success": True, "buzzer_active": True}

@app.post("/buzzer/off")
def buzzer_off():
    state["buzzer_active"] = False
    print(f"\n[{time.strftime('%H:%M:%S')}] 🔕 Buzzer Deactivated")
    return {"success": True, "buzzer_active": False}

@app.post("/test")
def test_buzzer():
    print(f"\n[{time.strftime('%H:%M:%S')}] 🔊 TEST BEEP REQUESTED")
    return {"success": True, "message": "Buzzer tested"}

if __name__ == "__main__":
    print("Starting Mock ESP32 Server...")
    print("Simulating hardware on port 5000")
    uvicorn.run(app, host="0.0.0.0", port=5000)
