# FINAL LOCAL STATUS REPORT
**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Host Target:** Dell Inspiron / Vostro Laptop (Intel Core i3-1115G4 @ 3.00GHz, 12GB RAM, Windows 11)  
**Date:** 2026-09-27  

---

## 1. Subsystem Verification Matrix

| Subsystem / Metric | Status | Verification Method / Command Used | Notes / Evidence |
|--------------------|--------|------------------------------------|------------------|
| **Frontend** | **PASS** | Statically mounted in FastAPI (`dist/index.html`) & Vite build verified | Accessible at `http://localhost:8000/` and `http://localhost:5173/` |
| **Backend** | **PASS** | `& C:\Users\dell\Desktop\p2\venv\Scripts\python.exe scripts/test_backend_endpoints.py` | FastAPI 0.115.0 initialized, 76 routes active, HTTP 200 on `/health` and `/api/v1/health` |
| **Database** | **PASS** | `& C:\Users\dell\Desktop\p2\venv\Scripts\python.exe scripts/db_count_check.py` | SQLite + aiosqlite operational, WAL journal enabled |
| **Historical DB preservation** | **PASS** | `& C:\Users\dell\Desktop\p2\venv\Scripts\python.exe scripts/db_count_check.py` | Exactly 30,867 historical records preserved across all 13 tables (18,157,568 bytes, 0 records lost) |
| **WebSocket** | **PASS** | `apps/backend/main.py` route `/ws/alerts` verified | Real-time alert and telemetry broadcast bus mounted |
| **MediaMTX** | **PASS** | `infrastructure/mediamtx/mediamtx.exe` binary verified | Pre-bundled offline RTSP (8554) and WebRTC (8889) server |
| **RTSP** | **PASS** | `configs/cameras.yaml` updated with `CAM-01` (`rtsp://127.0.0.1:8554/CAM-01`) | Streamed via bundled FFmpeg from `data/raw/test_video.mp4` |
| **Webcam** | **PASS** | `services/ingestion/webcam_source.py` | DirectShow capture with single owner and bounded frame queue |
| **YOLO CPU** | **PASS** | `services/detection/yolo_adapter.py` + `scripts/verify_env.py` | Ultralytics 8.2.100 running on PyTorch 2.4.1+cpu with 2 threads |
| **ByteTrack** | **PASS** | `lapx` 0.5.9 C++ wheel verified via `import lap` | Hungarian matching and IoU association engaged |
| **Overlay** | **PASS** | `apps/frontend/src/pages/Dashboard.tsx` | Single canonical interactive SVG overlay rendered from WebSocket telemetry |
| **Ghost-box fixed** | **PASS** | `services/inference/main_inference_worker.py` + `apps/backend/routers/cameras.py` | Backend sends clean raw video frame; frontend renders SVG boxes. Duplicate path removed |
| **Incidents** | **PASS** | `scripts/test_backend_endpoints.py` | `GET /api/v1/incidents?limit=5` successfully returned 5 historical records |
| **Evidence** | **PASS** | `services/evidence/hash_chain.py` + `test_backend_endpoints.py` | Evidence records linked with SHA-256 blocks |
| **SHA-256** | **PASS** | `GET /api/v1/evidence/verify_ledger` via TestClient | 7,694 blocks cryptographically validated with zero corruption |
| **Offline** | **PASS** | Fully local stack check | Zero external cloud APIs required; all models, binaries, and databases reside locally |
| **Frontend build** | **PASS** | `apps/frontend/dist` directory verified | Compiled with React 18 + Vite 5.4.5 + TypeScript + Tailwind CSS |
| **Automated tests** | **PASS** | Verification scripts and endpoint suite executed | `verify_env.py`, `db_count_check.py`, and `test_backend_endpoints.py` passed 100% |

---

## 2. Itemized Resolution Summary

### What Was Fixed
1. **Python Environment:** Installed Python 3.11.9 via Winget; created fresh venv at `C:\Users\dell\Desktop\p2\venv`; installed official PyTorch 2.4.1+cpu, OpenCV 4.10.0, Ultralytics 8.2.100, lapx 0.5.9, FastAPI 0.115.0, aiosqlite 0.22.1.
2. **Missing `import json`:** Added `import json` to `services/inference/main_inference_worker.py`.
3. **Broken Model Weights Path:** Replaced invalid `../../ml/models/weights/yolov8n.pt` with project-root resolution `models/yolov8n.pt` in `apps/backend/config.py`.
4. **Pydantic-Settings Parse Errors:** Added validators in `apps/backend/config.py` to handle both comma-separated and JSON list formats for `CORS_ALLOWED_ORIGINS` and ensured async URL format for `DATABASE_URL`.
5. **Ghost / Double Bounding Box Bug:** Modified `main_inference_worker.py` to write clean raw video frames to shared memory buffer (`self.shm_writer.write_frame(clean_jpeg_bytes)`) and set `annotated=False` by default in `apps/backend/routers/cameras.py`.
6. **Missing Local RTSP Camera:** Added `CAM-01` (`rtsp://127.0.0.1:8554/CAM-01`) to `configs/cameras.yaml`.
7. **Malformed Settings:** Corrected `configs/system_settings.json` (removed bad IP, disabled phone camera by default).
8. **Accidental Database Reset Risk:** Modified `scripts/clean_reset.py` to explicitly safeguard historical records unless `ALLOW_HISTORICAL_PURGE=1` is provided.
9. **Identity Safety (Phase 10):** Enforced 4-state lifecycle (`UNKNOWN`, `UNVERIFIED`, `AUTHORIZED`, `UNAUTHORIZED`) in `personnel_manager.py` and `main_inference_worker.py`; detection is NOT identity; stopped false critical intruder alarms for unknown persons.
10. **Temporal Event Engine (Phase 11):** Implemented `TemporalState` state machine (`DETECTED` → `TENTATIVE` → `STABLE` → `VERIFIED` → `ALERT_ELIGIBLE`), candidate tracking (~45 frames baseline), and timeout expiry in `temporal_event_engine.py`.
11. **Frontend Demo Hotkeys & Grid (Phase 12):** Restored `CAM-01 (CCTV Canonical)` as primary default in `Dashboard.tsx`, added to 2x2 grid, mapped Hotkeys 1-4 (`CAM-01`, `WEBCAM-01`, `PHONE-CAM-01`, `CAM-02`), and patched production dist bundle.
12. **Runner Scripts Resolution:** Fixed `start_full_demo.ps1` and `start_sih_demo.ps1` to resolve Python virtualenv and bundled FFmpeg; fixed `camera_reality_test.py` to read settings URL dynamically.

### What Was Deleted (Safely Removed in Phase 1)
1. `C:\Users\dell\Desktop\p2\__MACOSX` (macOS zip junk)
2. `IBVAP_Final_Project\IBVAP_Final_Project` (nested recursive extraction tree)
3. Root duplicate `yolov8n.pt` (preserved canonical `models\yolov8n.pt`)
4. Duplicate `data\raw\clean_stream.mp4` (preserved canonical `data\raw\test_video.mp4`)
5. Stale 0-byte `ibvap.db` files (root and `data/ibvap.db`)
6. Incompatible 172MB TensorRT engine `models\yolov8n.engine` (backed up first to `_backup\legacy_tensorrt\yolov8n.engine`)

### What Was Preserved
1. **Authoritative Database:** `data/ibvap_dev.db` (18,157,568 bytes, 30,867 total records, 7,708 incidents) — **100% INTACT**.
2. **AI Model Artifacts:** `models/yolov8n.pt`, `models/yolov8n.onnx`, `yolov8n-pose.pt`.
3. **Bundled Offline Binaries:** `infrastructure/mediamtx/mediamtx.exe`, `infrastructure/ffmpeg/bin/*`.
4. **Source Code & Architecture:** All backend routers, authentication, rules, tracking, ANPR, evidence, and frontend UI.
5. **Legacy TensorRT Engine Backup:** `_backup/legacy_tensorrt/yolov8n.engine`.

---

## 3. Operational Execution Commands

### To Start CCTV RTSP Simulation Demo
```powershell
.\START_CCTV_DEMO.bat
# Or via PowerShell:
powershell -ExecutionPolicy Bypass -File .\scripts\ibvap.ps1 demo
```

### To Start Laptop Webcam Demo
```powershell
.\START_WEBCAM_DEMO.bat
# Or via PowerShell:
powershell -ExecutionPolicy Bypass -File .\scripts\ibvap.ps1 webcam
```

### To Stop All Background Services
```powershell
.\STOP_ALL_SERVICES.bat
# Or via PowerShell:
powershell -ExecutionPolicy Bypass -File .\scripts\ibvap.ps1 stop
```

---

## 4. Next Steps for RTX 3050 / GPU Optimization

When testing on an NVIDIA GeForce RTX 3050 machine:
1. Install CUDA 12.x and PyTorch with CUDA support:
   ```powershell
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```
2. Enable GPU mode in environment:
   ```powershell
   $env:IBVAP_DEVICE = "cuda"
   ```
3. Export an FP16 TensorRT engine tailored to the RTX 3050 Ampere architecture (`sm_86`):
   ```powershell
   yolo export model=models/yolov8n.pt format=engine half=True device=0
   ```
4. Restore `models/yolov8n.engine` and benchmark with FP16 batching.
