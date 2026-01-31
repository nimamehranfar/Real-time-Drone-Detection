"""
Drone Detection System - One-Click Setup
Run this script on a new PC to install all dependencies.
Usage: python setup.py
"""
import subprocess
import sys
import os
import shutil

def run(cmd, cwd=None, check=True):
    """Run a command and print output"""
    print(f"  Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0 and check:
        print(f"  Error: {result.stderr}")
        return False
    return True

def check_nvidia_gpu():
    """Check if NVIDIA GPU is available"""
    try:
        result = subprocess.run("nvidia-smi", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            # Extract GPU name from output
            for line in result.stdout.split('\n'):
                if 'NVIDIA' in line and 'GeForce' in line or 'RTX' in line or 'GTX' in line:
                    print(f"  Found: {line.strip()}")
                    return True
            return True
        return False
    except:
        return False

def main():
    print("=" * 55)
    print("   Drone Detection System - Setup")
    print("=" * 55)
    print()
    
    # Check Python version
    print("[1/5] Checking Python version...")
    py_version = sys.version_info
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 9):
        print("  ERROR: Python 3.9+ required!")
        print(f"  Your version: {py_version.major}.{py_version.minor}")
        sys.exit(1)
    print(f"  Python {py_version.major}.{py_version.minor}.{py_version.micro} - OK")
    print()
    
    # Check for NVIDIA GPU
    print("[2/5] Detecting GPU...")
    has_nvidia = check_nvidia_gpu()
    if has_nvidia:
        print("  NVIDIA GPU detected - will install CUDA-enabled PyTorch")
    else:
        print("  No NVIDIA GPU found - will install CPU-only PyTorch")
    print()
    
    # Install PyTorch (with or without CUDA)
    print("[3/5] Installing PyTorch...")
    if has_nvidia:
        # Install CUDA 12.1 version
        run("pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121")
    else:
        # Install CPU version
        run("pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu")
    print()
    
    # Install other Python dependencies
    print("[4/5] Installing Python dependencies...")
    dependencies = [
        "ultralytics",           # YOLO
        "opencv-python",         # Video processing
        "fastapi",               # Backend API
        "uvicorn[standard]",     # ASGI server
        "websockets",            # WebSocket support
        "yt-dlp",                # YouTube support
        "numpy",                 # Array operations
        "requests",              # HTTP requests
        "pydantic",              # Data validation
    ]
    run(f"pip install {' '.join(dependencies)}")
    print()
    
    # Install npm dependencies
    print("[5/5] Installing frontend dependencies...")
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Frontend (now in ui/)
    ui_dir = os.path.join(project_dir, "ui")
    if os.path.exists(ui_dir):
        run("npm install", cwd=ui_dir)
    
    # Electron (now in ui/electron/)
    electron_dir = os.path.join(project_dir, "ui", "electron")
    if os.path.exists(electron_dir):
        run("npm install", cwd=electron_dir)
    print()
    
    # Verify installation
    print("=" * 55)
    print("   Verifying Installation")
    print("=" * 55)
    try:
        import torch
        cuda_status = "CUDA" if torch.cuda.is_available() else "CPU"
        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A"
        print(f"  PyTorch: {torch.__version__}")
        print(f"  Mode: {cuda_status}")
        print(f"  GPU: {gpu_name}")
    except Exception as e:
        print(f"  PyTorch check failed: {e}")
    
    print()
    print("=" * 55)
    print("   Setup Complete!")
    print("=" * 55)
    print()
    print("  To run the app:")
    print("    - Double-click DroneDetect.bat")
    print("    - Or run: python run_app.py")
    print()
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
