# IBVAP ENVIRONMENT RECORD
**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Host:** Dell Inspiron / Vostro (Intel Core i3-1115G4 @ 3.00GHz, 2C/4T, 12 GB RAM, Integrated Intel UHD Graphics, No Discrete GPU)  
**Target Environment:** Local CPU-First Virtual Environment  
**Virtual Environment Path:** `C:\Users\dell\Desktop\p2\venv`  
**Date Created/Verified:** 2026-09-27  

---

## 1. Core Runtime Versions

| Component | Version | Build / Details | Verification Status |
|-----------|---------|-----------------|---------------------|
| **Python** | 3.11.9 | 64-bit AMD64 (installed via Winget to `AppData\Local\Programs\Python\Python311`) | PASS |
| **pip** | 24.0 | Default venv installer | PASS |
| **PyTorch** | 2.4.1+cpu | Prebuilt Official CPU Wheel (`download.pytorch.org/whl/cpu`) | PASS |
| **TorchVision** | 0.19.1+cpu | Prebuilt Official CPU Wheel | PASS |
| **CUDA Available** | False | CPU execution strictly verified | PASS |
| **OpenCV** | 4.10.0.84 | `opencv-python` headless/GUI prebuilt wheel | PASS |
| **Ultralytics (YOLOv8)** | 8.2.100 | Official YOLOv8n detector library | PASS |
| **Lap (lapx)** | 0.5.9 | Prebuilt C++ linear assignment wheel for ByteTrack association | PASS |
| **FastAPI** | 0.115.0 | High performance ASGI web framework | PASS |
| **Uvicorn** | 0.30.6 | ASGI production server | PASS |
| **SQLAlchemy** | 2.0.35 | Async ORM | PASS |
| **AioSQLite** | 0.22.1 | Asynchronous SQLite driver for FastAPI | PASS |
| **Pydantic** | 2.9.0 | Data validation & schemas | PASS |
| **Pydantic-Settings** | 2.5.2 | Environment and settings management | PASS |
| **Structlog** | 24.4.0 | Structured JSON/Console logging | PASS |
| **Pytest** | 9.1.1 | Automated test framework | PASS |
| **Pytest-Asyncio** | 1.4.0 | Async test fixtures | PASS |
| **Psutil** | 7.2.2 | System resource monitoring | PASS |
| **Node.js** | v25.9.0 | Frontend build tool | PASS |
| **npm** | 11.12.1 | Package manager | PASS |

---

## 2. Bundled Native Binaries

- **MediaMTX:** `infrastructure/mediamtx/mediamtx.exe` (v1.9.0 Windows amd64)
- **FFmpeg:** `infrastructure/ffmpeg/bin/ffmpeg.exe`, `ffplay.exe`, `ffprobe.exe` (Windows amd64 build)

---

## 3. Acceleration Capability (Optional)

- Default mode: `IBVAP_DEVICE=cpu`
- Optional mode: `IBVAP_DEVICE=cuda` (configured for later NVIDIA GeForce RTX 3050 testing)
- TensorRT engine backup preserved: `_backup/legacy_tensorrt/yolov8n.engine`
