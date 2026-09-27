# IBVAP DEPLOYMENT GUIDE
**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Host Target:** Dell Laptop (Intel Core i3-1115G4, 12GB RAM, Windows 11)  
**Canonical Directory:** `C:\Users\dell\Desktop\p2\IBVAP_Final_Project`  

---

## 1. Quick Start Commands (Dell Local Machine)

### A. Launch Canonical CCTV Simulation Demo
Starts bundled MediaMTX RTSP server, loops `data/raw/test_video.mp4` via bundled FFmpeg onto `rtsp://127.0.0.1:8554/CAM-01`, starts FastAPI backend on port 8000 in CPU mode, and serves the React dashboard.
```cmd
cd C:\Users\dell\Desktop\p2\IBVAP_Final_Project
START_CCTV_DEMO.bat
```
*Or via PowerShell:*
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ibvap.ps1 demo
```

### B. Launch Laptop Webcam Demo
Engages DirectShow single-owner capture on `webcam:0`, runs CPU YOLOv8n + ByteTrack, and streams clean frames to `http://localhost:8000`.
```cmd
cd C:\Users\dell\Desktop\p2\IBVAP_Final_Project
START_WEBCAM_DEMO.bat
```
*Or via PowerShell:*
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ibvap.ps1 webcam
```

### C. Stop All Background Services
Cleanly terminates FFmpeg streams, MediaMTX RTSP daemon, Python inference workers, and Uvicorn backend.
```cmd
cd C:\Users\dell\Desktop\p2\IBVAP_Final_Project
STOP_ALL_SERVICES.bat
```
*Or via PowerShell:*
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ibvap.ps1 stop
```

---

## 2. Environment Configuration

The system uses `.env` located at `C:\Users\dell\Desktop\p2\IBVAP_Final_Project\.env`:

```env
# System Hardware Execution Device
IBVAP_DEVICE=cpu
# Optional: Set to 'cuda' when executing on RTX 3050 machine
# IBVAP_DEVICE=cuda

# Networking & Ports
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_PORT=5173
CORS_ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173","http://localhost:8000","http://127.0.0.1:8000"]

# Database (Canonical Historical SQLite with 30,867 records preserved)
DATABASE_URL=sqlite+aiosqlite:///./data/ibvap_dev.db

# MediaMTX & RTSP Configuration
MEDIAMTX_PATH=infrastructure/mediamtx/mediamtx.exe
FFMPEG_PATH=infrastructure/ffmpeg/bin/ffmpeg.exe
RTSP_BASE_URL=rtsp://127.0.0.1:8554

# AI Model Configuration
DETECTION_MODEL_PATH=models/yolov8n.pt
DETECTION_CONF_THRESHOLD=0.35
DETECTION_IOU_THRESHOLD=0.45
TEMPORAL_VALIDATION_FRAMES=45
```

---

## 3. Transitioning to NVIDIA RTX 3050 Laptop GPU

When moving this project to an NVIDIA GPU machine:

1. Install NVIDIA CUDA 12.x drivers.
2. Install PyTorch with CUDA 12.1 support into the virtual environment:
   ```powershell
   & C:\Users\dell\Desktop\p2\venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```
3. Set environment variable:
   ```powershell
   $env:IBVAP_DEVICE = "cuda"
   ```
4. Verify CUDA detection:
   ```powershell
   & C:\Users\dell\Desktop\p2\venv\Scripts\python.exe -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('Device Name:', torch.cuda.get_device_name(0))"
   ```
5. The `YOLOAdapter` and `AutonomousAIOrchestrator` will automatically engage FP16 CUDA half-precision inference without any code modifications. If CUDA initialization fails, it automatically falls back to CPU without crashing.

---

## 4. Air-Gapped Offline Deployment

IBVAP has **zero mandatory cloud dependencies**:
- **Offline Binaries:** Pre-bundled `infrastructure/mediamtx/mediamtx.exe` and `infrastructure/ffmpeg/bin/ffmpeg.exe`.
- **Offline Weights:** Pre-downloaded weights in `models/yolov8n.pt`, `models/yolov8n.onnx`, `yolov8n-pose.pt`.
- **Offline Database:** Self-contained SQLite database in `data/ibvap_dev.db`.
- **Offline Frontend:** Production React/Vite bundle pre-compiled in `apps/frontend/dist` and statically served by FastAPI at `http://127.0.0.1:8000`.
