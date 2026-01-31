"""
Test script for detection wrapper
Tests the integration without needing the full UI
"""

import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wrapper.detection_wrapper import DetectionSystem


def test_detection_wrapper():
    """Test the detection wrapper"""
    
    print("=" * 60)
    print("Testing Drone Detection Wrapper")
    print("=" * 60)
    
    # Create system
    system = DetectionSystem()
    
    # Configure
    config = {
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
    
    system.configure(config)
    
    # Set video path (update this to your actual video)
    video_path = input("Enter video file path: ").strip()
    
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return
    
    # Set ESP32 address (optional)
    esp32_address = input("Enter ESP32 address (or press Enter for default): ").strip()
    if not esp32_address:
        esp32_address = "http://drone-alert.local:5000"
    
    print(f"\nStarting detection...")
    print(f"Video: {video_path}")
    print(f"ESP32: {esp32_address}")
    print("\nPress Ctrl+C to stop\n")
    
    # Start detection
    if not system.start(video_path, esp32_address):
        print("Failed to start detection!")
        return
    
    try:
        # Monitor status
        while True:
            status = system.get_status()
            
            print(f"\rRunning: {status['is_running']} | "
                  f"Warnings: {status['warning_count']} | "
                  f"Alerts: {status['alert_count']} | "
                  f"Warning Active: {status['warning_active']} | "
                  f"Alert Active: {status['alert_active']}",
                  end='', flush=True)
            
            time.sleep(1)
            
            # Stop if process finished
            if not status['is_running']:
                print("\n\nDetection completed!")
                break
                
    except KeyboardInterrupt:
        print("\n\nStopping detection...")
        system.stop()
        print("Stopped.")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    test_detection_wrapper()
