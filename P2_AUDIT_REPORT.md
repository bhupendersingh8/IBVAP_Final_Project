# IBVAP — P2 MASTER AUDIT REPORT
**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**SIH Problem Statement:** 26187  
**Target Host:** Dell Laptop (Intel Core i3 11th Gen - 2C/4T, 12 GB RAM, Integrated Intel UHD Graphics, No NVIDIA GPU)  
**Storage:** 58.8 GB Free on C:  
**Node.js / npm:** v25.9.0 / 11.12.1  
**Audit Date:** 2026-09-27  

---

## EXECUTIVE SUMMARY

A comprehensive non-destructive audit of the entire `P2` folder (`C:\Users\dell\Desktop\p2`) was conducted. The project has a solid architectural core (FastAPI backend, React/Vite dashboard, OpenCV ingestion, YOLOv8/ByteTrack tracking, temporal rules, SQLite database, and SHA-256 evidence ledger), but suffers from four critical systemic issues that currently prevent out-of-the-box local operation on this Dell machine:
1. **Broken Python Virtual Environment:** The bundled `venv/` is hardcoded to an external path (`C:\Users\kissa\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13...`) from the machine where it was packaged. The Dell host has Python 3.14/3.15 installed, but lacks Python 3.11 which is required for stable PyTorch/OpenCV/ByteTrack CPU wheels.
2. **Duplicate Bounding Box Rendering (The "Ghost Box" Bug):** The backend OpenCV worker renders and burns bounding boxes directly into `live_annotated_{camera_id}.jpg`, which is streamed via MJPEG, while the frontend `Dashboard.tsx` concurrently renders SVG bounding boxes from WebSocket telemetry on top of the same stream, causing severe double-boxing and visual jitter.
3. **Ghost / Nested Directory Bloat:** There is an entire duplicate project directory nested at `IBVAP_Final_Project/IBVAP_Final_Project` (containing an extra 13MB database, duplicate video, and MediaMTX binary), alongside macOS archive metadata (`__MACOSX/`), a 172MB GPU-only TensorRT engine (`yolov8n.engine`), and duplicate weights.
4. **Configuration Inconsistencies:** `configs/cameras.yaml` is missing `CAM-01` (the primary simulation camera used across all scripts), `apps/backend/config.py` references a non-existent weights path (`../../ml/models/weights/yolov8n.pt`), and `main_inference_worker.py` lacks `import json` at module level.

---

## DETAILED AUDIT CATEGORIES

### A. WORKING (Verified Functional)
- **Frontend Build Pipeline:** React 18.3.1 + TypeScript + Vite 5.4.5 + TailwindCSS builds into `apps/frontend/dist` with 0 errors (verified in 39s).
- **Offline Infrastructure Binaries:**
  - `infrastructure/ffmpeg/bin/ffmpeg.exe`, `ffplay.exe`, `ffprobe.exe` are pre-bundled Windows binaries.
  - `infrastructure/mediamtx/mediamtx.exe` and `mediamtx.yml` are pre-bundled Windows binaries capable of local RTSP (8554) and WebRTC (8889) streaming without internet.
- **Pure Python Cryptographic Auth Engine:** `apps/backend/auth/jwt_auth.py` and `rbac.py` use standard library `hmac`, `hashlib`, `base64`, requiring no external cryptography wheels.
- **Evidence Integrity Hash Chain:** `services/evidence/hash_chain.py` deterministically links incidents with SHA-256 blocks without external blockchain dependencies.
- **Rule Engine & Temporal Event Engine:** `services/rules/temporal_event_engine.py` and `rule_engine.py` implement explainable multi-frame validation for Zone Intrusion, Loitering, Direction Violation, Night Movement, and Repeated Entry.
- **Bounded Frame Queue:** `services/ingestion/frame_buffer.py` implements a non-blocking queue with `drop_oldest` policy to prevent memory leaks during slow inference.
- **Shared Memory IPC Bus:** `services/ingestion/shared_frame_buffer.py` implements atomic Seqlock over Python `multiprocessing.shared_memory.SharedMemory` for zero-disk-I/O frame delivery between worker and FastAPI.
- **Historical Database:** `data/ibvap_dev.db` (18.1 MB) contains valid schema and 7,708 recorded events/incidents, 7,694 evidence records, and 7,694 hash chain blocks.

---

### B. BROKEN (Immediate Startup / Runtime Failures)
1. **Python Virtual Environment (`c:\Users\dell\Desktop\p2\venv`):**
   - Fails immediately on execution: `did not find executable at 'C:\Users\kissa\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe'`.
   - Cannot run `python`, `pytest`, `uvicorn`, or any script using the current venv.
2. **Missing Module-Level `import json` in `services/inference/main_inference_worker.py`:**
   - Line 120 calls `json.load(sf)` to load `system_settings.json`, but `json` is not imported at module level. The code only avoids crashing because of a bare `except Exception: pass`, which silently prevents user settings from ever applying.
3. **Broken Model Weights Path in `apps/backend/config.py`:**
   - Line 26 defines `DETECTION_MODEL_PATH = "../../ml/models/weights/yolov8n.pt"`. The directory `ml/models/weights` does NOT exist.
4. **Invalid System Settings Config:**
   - In `configs/system_settings.json`: `"phone_camera_url": "http://10.177.66.193.8080/VEDIO"` contains an invalid IP (missing colon) and misspelled path.
5. **Missing `CAM-01` in `configs/cameras.yaml`:**
   - The primary demo script and inference workers expect `CAM-01` (RTSP loop), but `cameras.yaml` only lists `CAM-02`, `CAM-03`, `CAM-04`, `WEBCAM-01`, `PHONE-CAM-01`.

---

### C. PARTIALLY WORKING
1. **Bounding Box & Overlay System:**
   - Backend burns bounding boxes onto the video frames using OpenCV in `main_inference_worker.py`.
   - Frontend overlays SVG bounding boxes from WebSocket telemetry in `Dashboard.tsx`.
   - Result: Users see two competing, jittery bounding boxes for every single object.
2. **Tracker Implementation:**
   - `bytetrack_adapter.py` exposes `ByteTrackAdapter`, but it is an alias for `FallbackIoUTracker` (pure IoU greedy matching). Kalman filtering / true ByteTrack association is not engaged unless `lapx` and ByteTrack dependencies are cleanly installed and loaded.
3. **Face / Personnel Authorization:**
   - `services/auth_personnel/personnel_manager.py` has pose landmark detection and SIFT matching logic, but runs on unverified thresholds and risks classifying unrecognized faces prematurely without explicit UNKNOWN states.
4. **ANPR Pipeline:**
   - `services/anpr/anpr_pipeline.py` has contour plate detection and multi-frame consensus logic, but `EasyOCREngine` downloads ~100MB model files on first run if not cached, which violates offline-first unless pre-warmed or disabled on CPU.

---

### D. DUPLICATE (Identified Redundancies)
1. **Nested Project Tree:** `C:\Users\dell\Desktop\p2\IBVAP_Final_Project\IBVAP_Final_Project` (contains duplicate `data/ibvap_dev.db`, `data/raw/clean_stream.mp4`, `infrastructure/mediamtx/mediamtx.exe`).
2. **Duplicate Model Weights:**
   - `C:\Users\dell\Desktop\p2\IBVAP_Final_Project\yolov8n.pt` (6.55 MB)
   - `C:\Users\dell\Desktop\p2\IBVAP_Final_Project\models\yolov8n.pt` (6.55 MB) - EXACT DUPLICATE.
3. **Duplicate Raw Video:**
   - `data/raw/clean_stream.mp4` (4.70 MB)
   - `data/raw/test_video.mp4` (4.70 MB) - EXACT DUPLICATE (identical byte length).
4. **Duplicate Batch Launchers:**
   - `C:\Users\dell\Desktop\p2\START_CCTV_DEMO.bat` and `C:\Users\dell\Desktop\p2\IBVAP_Final_Project\START_CCTV_DEMO.bat`.
5. **Duplicate / Stale Database Files:**
   - `C:\Users\dell\Desktop\p2\data\ibvap_dev.db` (217 KB)
   - `C:\Users\dell\Desktop\p2\IBVAP_Final_Project\ibvap.db` (0 bytes)
   - `C:\Users\dell\Desktop\p2\IBVAP_Final_Project\data\ibvap.db` (0 bytes)
   - `C:\Users\dell\Desktop\p2\IBVAP_Final_Project\data\ibvap_dev.db` (18.1 MB - CANONICAL ACTIVE DATABASE).

---

### E. UNUSED / DEAD CODE CANDIDATES
1. `__MACOSX/` directories across `Desktop\p2` (macOS zip extraction metadata files `._*`).
2. `models/yolov8n.engine` (172.4 MB): Hardware-specific TensorRT engine compiled for an external NVIDIA GPU, completely non-executable on Intel Core i3.
3. `scripts/poc_tensorrt_deepstream.py` (15 KB): Prototype script requiring Linux DeepStream `.so` libraries.
4. `scripts/evaluate_10m_parameters.py`, `scripts/evaluate_1m_parameters.py`, `scripts/evaluate_10k_parameters.py`: Benchmarking scripts unreferenced by the primary runtime.
5. `ml/models/rtdetr_seg.py` (18 KB): Experimental RT-DETR model definition unreferenced in the main inference pipeline.

---

### F. DANGEROUS TO DELETE (Must Be Preserved)
1. `data/ibvap_dev.db` (18.1 MB): Authoritative SQLite database with all 7,708 historical events, incidents, and audit trails.
2. `infrastructure/ffmpeg/bin/*` & `infrastructure/mediamtx/*`: Required local binaries for offline RTSP video simulation.
3. `models/yolov8n.pt` and `yolov8n-pose.pt`: Active AI model weights for YOLOv8 detection and facial landmark pose.
4. `models/yolov8n.onnx`: Hardware-agnostic ONNX export.
5. `apps/backend/`: Entire backend API source code.
6. `apps/frontend/`: Entire dashboard source code.
7. `services/`: Ingestion, detection, tracking, rules, evidence, and incident services.
8. `tests/`: Complete automated test suite.
9. `configs/`: System configurations (zones, cameras, settings).

---

### G. SAFE TO DELETE (Pending Phase 2 Approval)
1. `C:\Users\dell\Desktop\p2\__MACOSX` (entire folder).
2. `C:\Users\dell\Desktop\p2\IBVAP_Final_Project\IBVAP_Final_Project` (nested duplicate tree).
3. `C:\Users\dell\Desktop\p2\IBVAP_Final_Project\ibvap.db` (0-byte empty file).
4. `C:\Users\dell\Desktop\p2\IBVAP_Final_Project\data\ibvap.db` (0-byte empty file).
5. `C:\Users\dell\Desktop\p2\IBVAP_Final_Project\yolov8n.pt` (root duplicate; keep canonical `models/yolov8n.pt`).
6. `C:\Users\dell\Desktop\p2\IBVAP_Final_Project\models\yolov8n.engine` (172 MB incompatible GPU engine, saveable to external backup or deleted after logging).
7. Old Python 3.13 `.pyc` caches in `__pycache__` once a clean virtual environment is created.

---

### H. MISSING (Required for Complete Dell Setup)
1. **Clean Local Python 3.11 Environment:**
   - Host currently only has Python 3.14/3.15. Python 3.11 is required so that prebuilt CPU wheels (`torch 2.4.1+cpu`, `torchvision`, `ultralytics`, `opencv-python`, `lapx`, `fastapi`, `uvicorn`) install cleanly without compilation errors.
2. **`CAM-01` Entry in `configs/cameras.yaml`:**
   - Must specify `id: CAM-01`, `name: "Border Outpost 1 - Simulation"`, `rtsp_url: "rtsp://127.0.0.1:8554/CAM-01"`.

---

### I. NEEDS REFACTOR
1. **Overlay Rendering (Canonical Single-Path):**
   - Choose canonical rendering: Either have Backend stream raw video + Frontend SVG overlay, OR Backend stream annotated video with Frontend overlay disabled.
   - Recommended: Backend serves raw frames (`annotated=False` by default) for browser stream; Frontend renders the SVG overlay driven by WebSocket telemetry. This eliminates double bounding boxes, decouples video from inference FPS, and enables interactive click-to-inspect on boxes.
2. **Identity & Authorization States:**
   - Refactor `services/auth_personnel/personnel_manager.py` to ensure explicit four-state lifecycle: `UNKNOWN`, `UNVERIFIED`, `AUTHORIZED`, `UNAUTHORIZED`.
   - Never fabricate or guess identities if face features are weak or absent.
3. **Camera Pipeline Resilience:**
   - Ensure `WebcamSource` and `RTSPSource` handle disconnects and reconnects without locking `webcam:0`.

---

### J. NEEDS GPU (Optional Acceleration Mode)
- `models/yolov8n.engine` (TensorRT execution).
- NVIDIA NIM API / DeepStream pipelines in `services/nvidia/`.
- FP16 TensorRT inference.
*Note: All of these MUST remain strictly optional flags via `IBVAP_DEVICE=cpu`.*

---

### K. MUST WORK ON CPU (Dell Laptop Core Requirement)
- FastAPI backend on `http://127.0.0.1:8000`.
- React dashboard on `http://127.0.0.1:5173` or port 8000.
- MediaMTX local RTSP loop on port 8554.
- Bounded OpenCV video capture from local file (`data/raw/test_video.mp4`) and webcam (`webcam:0`).
- YOLOv8n object detection on CPU with input size 640 or 480.
- Fallback IoU tracker / ByteTrack tracking with stable IDs.
- Temporal rule validation (Zone Intrusion, Loitering, Repeated Entry).
- Incident generation & SQLite persistence.
- WebSocket alert and telemetry broadcast.
- SHA-256 evidence integrity hashing.
- Fully offline operation with no external internet or cloud calls required.

---

## 1. PROJECT STRUCTURE
```
C:\Users\dell\Desktop\p2\
├── venv\                          [BROKEN: user 'kissa' Python 3.13 pointer]
├── data\ibvap_dev.db              [Stale 217KB database copy]
├── __MACOSX\                      [Mac zip extraction junk]
├── START_CCTV_DEMO.bat
├── START_WEBCAM_DEMO.bat
├── STOP_ALL_SERVICES.bat
└── IBVAP_Final_Project\           [CANONICAL WORKSPACE]
    ├── apps\
    │   ├── backend\               [FastAPI, SQLite, WebSocket, Auth, Routers]
    │   └── frontend\              [React 18, Vite, Tailwind, TS Dashboard]
    ├── configs\                   [cameras.yaml, zones.yaml, settings.json]
    ├── data\
    │   ├── authorized_people\     [Face enrollment images & json]
    │   ├── evidence\              [Incident snapshots]
    │   ├── raw\                   [test_video.mp4, clean_stream.mp4]
    │   └── ibvap_dev.db           [18.1 MB SQLite database with 7708 incidents]
    ├── IBVAP_Final_Project\       [DUPLICATE NESTED FOLDER - 73 MB]
    ├── infrastructure\
    │   ├── ffmpeg\bin\            [ffmpeg.exe, ffplay.exe, ffprobe.exe]
    │   └── mediamtx\              [mediamtx.exe, mediamtx.yml]
    ├── ml\                        [Registry, dataset validators, training]
    ├── models\
    │   ├── yolov8n.pt             [PyTorch weights, 6.55 MB]
    │   ├── yolov8n.onnx           [ONNX export, 12.85 MB]
    │   ├── threat_yolov8n.pt      [Threat model weights, 6.25 MB]
    │   └── yolov8n.engine         [GPU TensorRT engine, 172.4 MB]
    ├── requirements\              [base.txt, dev.txt, ml.txt]
    ├── scripts\                   [ibvap.ps1, ensure_services.ps1, etc.]
    ├── services\                  [ingestion, detection, tracking, rules, etc.]
    ├── tests\                     [21 test suites]
    ├── yolov8n.pt                 [Duplicate of models/yolov8n.pt]
    └── yolov8n-pose.pt            [Pose/facial landmark model, 6.83 MB]
```

## 2. DETECTED TECH STACK
- **Backend:** Python, FastAPI 0.115.0, Uvicorn, SQLAlchemy 2.0.35, aiosqlite, Pydantic v2, Structlog.
- **Frontend:** Node.js, React 18.3.1, TypeScript 5.5.4, Vite 5.4.5, TailwindCSS 3.4.12, TanStack Query, Lucide React.
- **Video & Ingestion:** OpenCV 4.10, MediaMTX 1.8.4, FFmpeg, Python `multiprocessing.shared_memory`.
- **AI / Tracking:** Ultralytics YOLOv8n, PyTorch 2.4.1 (CPU), FallbackIoU / ByteTrack, SIFT / ORB, EasyOCR.
- **Database:** SQLite3 (`data/ibvap_dev.db`).
- **Security:** HMAC-SHA256 JWT, SHA-256 tamper-evident hash chain ledger.

## 3. CURRENT STARTUP COMMANDS
- Master PowerShell Orchestrator:
  `powershell -ExecutionPolicy Bypass -File ".\scripts\ibvap.ps1" demo`
- Manual Services:
  - MediaMTX: `.\infrastructure\mediamtx\mediamtx.exe .\infrastructure\mediamtx\mediamtx.yml`
  - RTSP Publisher: `.\infrastructure\ffmpeg\bin\ffmpeg.exe -re -stream_loop -1 -i "data\raw\test_video.mp4" -c copy -f rtsp rtsp://127.0.0.1:8554/CAM-01`
  - Backend: `uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000`
  - Worker: `python services\inference\main_inference_worker.py --camera CAM-01 --rtsp rtsp://127.0.0.1:8554/CAM-01`
  - Frontend: `npm run dev` (in `apps/frontend`) or browse `http://127.0.0.1:8000` (static mount)

## 4. CURRENT VERSIONS & HARDWARE SPECS
- **Operating System:** Windows 10/11 x64
- **CPU:** 11th Gen Intel(R) Core(TM) i3-1115G4 @ 3.00GHz (2 physical cores, 4 logical processors)
- **RAM:** 12.0 GB Physical RAM
- **GPU:** Integrated Intel UHD Graphics (No NVIDIA CUDA GPU)
- **Free Disk Space (C:):** 58.8 GB
- **Node.js:** v25.9.0
- **npm:** 11.12.1
- **Host Python:** Python 3.14.4 (C:\Python314), Python 3.15 (AppData)
- **Virtual Environment (`p2\venv`):** Broken reference to Python 3.13 on user `kissa`'s machine.

## 5. AI MODELS FOUND
1. `models/yolov8n.pt` (6.55 MB): YOLOv8 Nano COCO detection model.
2. `yolov8n.pt` (6.55 MB): Exact duplicate in root directory.
3. `models/yolov8n.onnx` (12.85 MB): Universal ONNX export for CPU/GPU.
4. `models/threat_yolov8n.pt` (6.25 MB): Fine-tuned weapon/threat detection weights.
5. `yolov8n-pose.pt` (6.83 MB): YOLOv8 Pose model for face landmarks and eye-blink anti-spoofing.
6. `models/yolov8n.engine` (172.4 MB): TensorRT engine compiled for NVIDIA GPU (incompatible with Dell CPU).
7. `services/detection/haarcascade_frontalface_default.xml` (0.93 MB): OpenCV Haar cascade for facial bounding boxes.

## 6. CAMERA / VIDEO SYSTEMS FOUND
1. **Local RTSP Simulation:** FFmpeg publishing `test_video.mp4` to MediaMTX server at `rtsp://127.0.0.1:8554/CAM-01`.
2. **Local USB/Laptop Webcam:** `WebcamSource` reading `webcam:0` via OpenCV.
3. **Phone RTSP / IP Camera:** Endpoint for Android IP Webcam / DroidCam (`http://<ip>:8554` or `:8080/video`).
4. **Inter-Process Video Streaming:** `SharedFrameWriter` / `SharedFrameReader` using Windows shared memory Seqlock buffer (`ibvap_frame_cam_01`).
5. **Browser Video Delivery:** FastAPI MJPEG streaming endpoint at `/api/v1/cameras/{camera_id}/stream`.

## 7. GPU / CUDA / TENSORRT DEPENDENCIES FOUND
- `models/yolov8n.engine` (TensorRT engine).
- References to `libnvds_nvmultiobjecttracker.so` and `nvv4l2decoder` in `configs/nvidia_acceleration.yaml`.
- References to `.venv_gpu` in `apps/backend/routers/cameras.py`.
- NVIDIA NIM cloud API calls in `services/nvidia/nim_surveillance_agent.py`.
- `torch-2.14.0+cu126` in the broken Python 3.13 venv.
*All of these are either optional or can be cleanly set to CPU fallback.*

## 8. BROKEN COMPONENTS
- The `venv` virtual environment executable link.
- `apps/backend/config.py` model path (`../../ml/models/weights/yolov8n.pt`).
- Missing `import json` in `main_inference_worker.py` (line 120).
- `configs/cameras.yaml` missing `CAM-01`.
- `configs/system_settings.json` corrupted phone camera URL.
- Double bounding box rendering (Backend burning + Frontend SVG).

## 9. DUPLICATE / UNUSED CANDIDATES
- Nested folder: `IBVAP_Final_Project/IBVAP_Final_Project` (73 MB).
- Root file: `IBVAP_Final_Project/yolov8n.pt` (duplicate of `models/yolov8n.pt`).
- Root file: `data/raw/clean_stream.mp4` (duplicate of `test_video.mp4`).
- All `__MACOSX` folders.
- Incompatible 172MB `yolov8n.engine`.
- Empty 0-byte `.db` files: `ibvap.db` in root and `data/ibvap.db`.

## 10. CRITICAL RISKS
1. **Python Wheel Incompatibility on Host:**
   System has Python 3.14/3.15. PyTorch stable does not publish prebuilt Windows binary wheels for Python 3.14+ yet. Attempting to install PyTorch on Python 3.14 will fail with build/C++ compiler errors. Python 3.11 MUST be installed via winget or pyenv.
2. **Camera Hardware Contention:**
   If multiple processes or threads attempt to open `webcam:0` simultaneously on Windows, the DirectShow camera device locks and crashes. A single canonical capture process must own `webcam:0`.
3. **Data Loss Risk:**
   `data/ibvap_dev.db` contains 7,708 valid historical records and must be protected during cleanup.

## 11. RECOMMENDED REPAIR ORDER (Phases 1-19)
1. **Phase 1: Canonical Architecture Approval:** Establish single detection pipeline, single overlay system, and CPU-first architecture.
2. **Phase 2: Safe Project Cleanup:** Back up and remove only verified junk (`__MACOSX`, duplicate nested folder, empty 0-byte databases, duplicate video/weights).
3. **Phase 3 & 4: Dell Python 3.11 Environment Setup:** Install Python 3.11 via `winget`, create a fresh `venv`, and install CPU-compatible dependencies (`torch+cpu`, `ultralytics`, `fastapi`, `uvicorn`, `opencv-python`, etc.).
4. **Phase 5: Backend Repair:** Fix config paths, missing `json` import, and database URL alignment. Verify `http://127.0.0.1:8000/health`.
5. **Phase 6: Frontend Repair & Verification:** Confirm Vite build and verify frontend communication with FastAPI.
6. **Phase 7: Video Pipeline Stabilization:** Add `CAM-01` to `cameras.yaml`, verify MediaMTX RTSP loop and webcam access.
7. **Phase 8-11: AI Pipeline & Overlay Unification:** Fix duplicate bounding boxes by separating raw video stream from SVG metadata overlay. Ensure `UNKNOWN`/`UNVERIFIED` state flow for face matching.
8. **Phase 12-16: Verification & Reality Testing:** Run end-to-end integration tests (backend, frontend, SQLite, WebSocket, detection, tracking, rules, incidents, evidence hashing, offline resilience).
