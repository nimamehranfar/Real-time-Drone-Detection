"""
Communication Module
Sends HTTP requests to ESP32 to control display and buzzer.
Supports two alert types: DRONE (display + buzzer) and WARNING (display only)
"""

import requests
from datetime import datetime


class CommunicationModule:
    """
    Sends HTTP requests to ESP32 to control display and buzzer.
    
    Alert Types:
    - DRONE: Shows on OLED display AND activates buzzer
    - WARNING: Shows on OLED display only (no buzzer)
    """
    
    def __init__(self, esp32_address: str = "http://drone-alert.local:5000"):
        self.esp32_address = esp32_address
        self.connected = False
        self.last_error = None
        
    def test_connection(self) -> bool:
        """Test connection to ESP32"""
        try:
            response = requests.get(f"{self.esp32_address}/status", timeout=2)
            self.connected = response.status_code == 200
            return self.connected
        except Exception as e:
            self.last_error = str(e)
            self.connected = False
            return False
            
    def send_drone_alert(self, message: str = "Drone detected!") -> bool:
        """
        Send DRONE alert - activates OLED display AND buzzer
        
        Args:
            message: Alert message to display on OLED
        """
        try:
            response = requests.post(
                f"{self.esp32_address}/alert/drone",
                json={
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                },
                timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def send_warning_alert(self, message: str = "Warning!") -> bool:
        """
        Send WARNING alert - shows on OLED display only (no buzzer)
        
        Args:
            message: Warning message to display on OLED
        """
        try:
            response = requests.post(
                f"{self.esp32_address}/alert/warning",
                json={
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                },
                timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def clear_alert(self) -> bool:
        """Clear any active alert on ESP32"""
        try:
            response = requests.post(
                f"{self.esp32_address}/alert/clear",
                timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            self.last_error = str(e)
            return False
            
    def activate_buzzer(self, message: str = "Drone detected!") -> bool:
        """
        Activate buzzer on ESP32 (legacy method, calls send_drone_alert)
        """
        return self.send_drone_alert(message)
            
    def deactivate_buzzer(self) -> bool:
        """Deactivate buzzer on ESP32"""
        try:
            response = requests.post(
                f"{self.esp32_address}/buzzer/off",
                json={'timestamp': datetime.now().isoformat()},
                timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def send_warning(self) -> bool:
        """Send warning (display only, no buzzer)"""
        return self.send_warning_alert("Warning: Possible drone")
    
    def send_alert(self) -> bool:
        """Send alert (display + buzzer)"""
        return self.send_drone_alert("ALERT: Drone confirmed!")
            
    def get_status(self) -> dict:
        """Get status from ESP32"""
        try:
            response = requests.get(f"{self.esp32_address}/status", timeout=2)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.last_error = str(e)
        return {
            'connected': False, 
            'buzzer_active': False,
            'drone_detected': False,
            'warning_active': False
        }
