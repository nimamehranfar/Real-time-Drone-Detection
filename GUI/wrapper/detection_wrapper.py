"""
Detection Wrapper
Runs drone_detection.py as a subprocess and captures alert/warning events
"""

import subprocess
import threading
import queue
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Callable
import time


class DroneDetector:
    """Wrapper for drone_detection.py that captures events without modifying the original script"""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.output_queue = queue.Queue()
        self.is_running = False
        self.alert_callback: Optional[Callable[[str], None]] = None
        self.warning_callback: Optional[Callable[[str], None]] = None
        
        # Configuration
        self.config = {
            'VIDEO_PATH': '',
            'CASCADED_ROI_CONFIRM_MODE': 'None',
            'TEMPORAL_ROI_PROP_ENABLED': True,
            'SHOW_GATE': False,
            'SHOW_TROI': False,
            'SHOW_CASCADE': False,
            'TOPLEFT_LOG_MODE': 'windows_big',
            'SAVE_VIDEO': False,
            'SAVE_ALERT_WINDOW_FRAMES': True,
            'WARNING_COOLDOWN_S': 3.0,
            'ALERT_COOLDOWN_S': 3.0,
            'INFER_FPS': 5,
        }
        
        # State tracking
        self.last_warning_count = 0
        self.last_alert_count = 0
        self.warning_active = False
        self.alert_active = False
        
    def set_config(self, config: Dict[str, Any]):
        """Update configuration"""
        self.config.update(config)
        
    def set_alert_callback(self, callback: Callable[[str], None]):
        """Set callback for alert events"""
        self.alert_callback = callback
        
    def set_warning_callback(self, callback: Callable[[str], None]):
        """Set callback for warning events"""
        self.warning_callback = callback
    
    def _create_modified_script(self) -> str:
        """Create a temporary modified version of drone_detection.py with config overrides"""
        # Read original script - go up to project root first
        # From GUI/wrapper/ -> ES_Drone_Detection/
        wrapper_file = Path(__file__).absolute()
        project_root = wrapper_file.parent.parent.parent
        script_path = project_root / 'drone_detector' / 'drone_detection.py'
        
        print(f"[DEBUG] Wrapper file: {wrapper_file}")
        print(f"[DEBUG] Project root: {project_root}")
        print(f"[DEBUG] Looking for script at: {script_path}")
        print(f"[DEBUG] Script exists: {script_path.exists()}")
        
        if not script_path.exists():
            raise FileNotFoundError(f"Could not find drone_detection.py at {script_path}")
        
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Build configuration overrides
        overrides = []
        
        if self.config.get('VIDEO_PATH'):
            overrides.append(f'VIDEO_PATH = "{self.config["VIDEO_PATH"]}"')
        
        overrides.append(f'CASCADED_ROI_CONFIRM_MODE = "{self.config["CASCADED_ROI_CONFIRM_MODE"]}"')
        overrides.append(f'TEMPORAL_ROI_PROP_ENABLED = {self.config["TEMPORAL_ROI_PROP_ENABLED"]}')
        overrides.append(f'SHOW_GATE = {self.config["SHOW_GATE"]}')
        overrides.append(f'SHOW_TROI = {self.config["SHOW_TROI"]}')
        overrides.append(f'SHOW_CASCADE = {self.config["SHOW_CASCADE"]}')
        overrides.append(f'TOPLEFT_LOG_MODE = "{self.config["TOPLEFT_LOG_MODE"]}"')
        overrides.append(f'SAVE_VIDEO = {self.config["SAVE_VIDEO"]}')
        overrides.append(f'SAVE_ALERT_WINDOW_FRAMES = {self.config["SAVE_ALERT_WINDOW_FRAMES"]}')
        overrides.append(f'WARNING_COOLDOWN_S = {self.config["WARNING_COOLDOWN_S"]}')
        overrides.append(f'ALERT_COOLDOWN_S = {self.config["ALERT_COOLDOWN_S"]}')
        overrides.append(f'INFER_FPS = {self.config["INFER_FPS"]}')
        
        # Disable the live window since we're using the web UI
        overrides.append('SHOW_WINDOW = False')
        
        # Insert overrides after imports but before main logic
        # Find a good insertion point (after the last config constant)
        insertion_point = content.find('def xywh_to_xyxy')
        if insertion_point == -1:
            insertion_point = content.find('class TemporalContinuity')
        
        if insertion_point != -1:
            override_block = '\n# === CONFIG OVERRIDES FROM WRAPPER ===\n'
            override_block += '\n'.join(overrides)
            override_block += '\n# === END CONFIG OVERRIDES ===\n\n'
            
            content = content[:insertion_point] + override_block + content[insertion_point:]
        
        # Save to temporary file
        temp_script = Path(__file__).parent / 'temp_drone_detection.py'
        with open(temp_script, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(temp_script)
    
    def _monitor_output(self):
        """Monitor subprocess output for events"""
        while self.is_running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                    
                line = line.decode('utf-8', errors='ignore').strip()
                
                # Store in queue for debugging
                if line:
                    self.output_queue.put(line)
                    print(f"[SUBPROCESS] {line}")  # Debug output
                
                # Parse output for event counts
                # Look for patterns like: "Events: Warning=X  Alert=Y" or "Events: Warning=X Alert=Y"
                if 'Events:' in line and ('Warning=' in line or 'Alert=' in line):
                    try:
                        # Extract the part after "Events:"
                        events_part = line.split('Events:')[1].strip()
                        
                        # Parse warning count
                        if 'Warning=' in events_part:
                            warning_str = events_part.split('Warning=')[1].split()[0]
                            warning_count = int(warning_str)
                            
                            if warning_count > self.last_warning_count:
                                print(f"[EVENT] New WARNING detected! Count: {self.last_warning_count} -> {warning_count}")
                                self.last_warning_count = warning_count
                                self.warning_active = True
                                if self.warning_callback:
                                    self.warning_callback("Warning: Possible drone detected")
                        
                        # Parse alert count  
                        if 'Alert=' in events_part:
                            alert_str = events_part.split('Alert=')[1].split()[0]
                            alert_count = int(alert_str)
                            
                            if alert_count > self.last_alert_count:
                                print(f"[EVENT] New ALERT detected! Count: {self.last_alert_count} -> {alert_count}")
                                self.last_alert_count = alert_count
                                self.alert_active = True
                                if self.alert_callback:
                                    self.alert_callback("ALERT: Drone confirmed!")
                    
                    except (ValueError, IndexError) as e:
                        print(f"[ERROR] Failed to parse event line: {line} - {e}")
                
            except Exception as e:
                print(f"Error monitoring output: {e}")
                break
    
    def start(self) -> bool:
        """Start the detection process"""
        if self.is_running:
            return False
        
        try:
            # Create modified script
            script_path = self._create_modified_script()
            
            # Start subprocess
            self.process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1
            )
            
            self.is_running = True
            self.last_warning_count = 0
            self.last_alert_count = 0
            self.warning_active = False
            self.alert_active = False
            
            # Start output monitoring thread
            monitor_thread = threading.Thread(target=self._monitor_output, daemon=True)
            monitor_thread.start()
            
            return True
            
        except Exception as e:
            print(f"Error starting detection: {e}")
            return False
    
    def stop(self):
        """Stop the detection process"""
        self.is_running = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            finally:
                self.process = None
        
        # Clean up temp script
        temp_script = Path(__file__).parent / 'temp_drone_detection.py'
        if temp_script.exists():
            try:
                temp_script.unlink()
            except:
                pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return {
            'is_running': self.is_running,
            'warning_active': self.warning_active,
            'alert_active': self.alert_active,
            'warning_count': self.last_warning_count,
            'alert_count': self.last_alert_count,
        }
    
    def dismiss_alert(self):
        """Dismiss current alert/warning"""
        self.warning_active = False
        self.alert_active = False


class DetectionSystem:
    """High-level system coordinator"""
    
    def __init__(self):
        from .communication import CommunicationModule
        
        self.detector = DroneDetector()
        self.comm = CommunicationModule()
        
        # Wire up callbacks
        self.detector.set_alert_callback(self._on_alert)
        self.detector.set_warning_callback(self._on_warning)
    
    def _on_alert(self, message: str):
        """Handle alert event"""
        print(f"ALERT EVENT: {message}")
        # Send to ESP32
        self.comm.send_drone_alert(message)
    
    def _on_warning(self, message: str):
        """Handle warning event"""
        print(f"WARNING EVENT: {message}")
        # Send to ESP32 (display only, no buzzer)
        self.comm.send_warning_alert(message)
    
    def configure(self, config: Dict[str, Any]):
        """Configure the system"""
        self.detector.set_config(config)
    
    def start(self, video_path: str, esp32_address: str = "http://drone-alert.local:5000") -> bool:
        """Start detection"""
        # Configure
        self.detector.set_config({'VIDEO_PATH': video_path})
        
        # Connect to ESP32
        self.comm.esp32_address = esp32_address
        if not self.comm.test_connection():
            print(f"Warning: Could not connect to ESP32 at {esp32_address}")
        
        # Start detection
        return self.detector.start()
    
    def stop(self):
        """Stop detection"""
        self.detector.stop()
        self.comm.clear_alert()
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            **self.detector.get_status(),
            'esp32_connected': self.comm.connected,
        }
    
    def dismiss_alert(self):
        """Dismiss current alert"""
        self.detector.dismiss_alert()
        self.comm.clear_alert()
