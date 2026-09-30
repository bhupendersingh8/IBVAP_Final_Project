import subprocess
import sys
import time
import os
import webbrowser

def start_services():
    print("="*50)
    print(" Starting IBVAP Live Preview...")
    print("="*50)

    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = os.path.join(base_dir, "apps", "backend")
    frontend_dir = os.path.join(base_dir, "apps", "frontend")

    # Start Backend
    print("🚀 Starting FastAPI Backend (Port 8000)...")
    backend_process = subprocess.Popen(
        ["uvicorn", "main:app", "--reload", "--port", "8000"],
        cwd=backend_dir,
        shell=True
    )

    # Start Frontend
    print("🎨 Starting React Frontend (Port 5173)...")
    frontend_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        shell=True
    )

    print("\n⏳ Waiting for servers to initialize...")
    time.sleep(4)

    url = "http://localhost:5173"
    print(f"\n✅ All systems go! Opening browser at: {url}")
    webbrowser.open(url)

    try:
        print("\nPress Ctrl+C to stop both servers.")
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down IBVAP servers...")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(0)

if __name__ == "__main__":
    start_services()
