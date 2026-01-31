"""
Drone Detection System - Desktop Launcher
Double-click to start the app and open in browser.
"""
import subprocess
import time
import sys
import os
import webbrowser
import signal

# Prevent recursive spawning
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

processes = []

def cleanup(signum=None, frame=None):
    """Clean up all subprocesses"""
    print("\nShutting down...")
    for p in processes:
        try:
            p.terminate()
        except:
            pass
    sys.exit(0)

def main():
    print("=" * 50)
    print("   Drone Detection System")
    print("=" * 50)
    print()
    
    # Register cleanup handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Start backend
    print("[1/2] Starting backend server...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "wrapper.api:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    processes.append(backend)
    time.sleep(2)
    
    # Start frontend 
    print("[2/2] Starting frontend server...")
    frontend = subprocess.Popen(
        "npm run dev",
        cwd="ui",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    processes.append(frontend)
    time.sleep(3)
    
    # Open in default browser
    print()
    print("Opening app in browser...")
    webbrowser.open("http://localhost:5173")
    
    print()
    print("=" * 50)
    print("  App is running at: http://localhost:5173")
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    
    # Keep running until Ctrl+C
    try:
        while True:
            time.sleep(1)
            # Check if processes are still running
            if backend.poll() is not None or frontend.poll() is not None:
                print("A server stopped unexpectedly.")
                break
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()

if __name__ == "__main__":
    main()
