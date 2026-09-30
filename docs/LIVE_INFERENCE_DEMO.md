# IBVAP Live Real Inference Demo Guide

This document outlines the real, verified end-to-end pipeline of the **Intelligent Border Video Analytics Platform (IBVAP)** for SIH PS-26187.

---

## 1. End-to-End Pipeline Architecture

```
Authorized Local MP4 (data/raw/test_video.mp4)
      │
      ▼
FFmpeg Publisher (TCP Transport)
      │
      ▼
MediaMTX RTSP Server (rtsp://127.0.0.1:8554/CAM-01)
      │
      ▼
IBVAP RTSPSource & Frame Buffer (services/ingestion/rtsp_source.py)
      │
      ▼
DetectionEngine / YOLOv8n (services/detection/yolo_adapter.py)
      │
      ▼
FallbackIoUTracker (services/tracking/bytetrack_adapter.py)
      │
      ▼
RuleEngine / RESTRICTED_ZONE_01 (services/rules/rule_engine.py)
      │
      ▼
EventCorrelator (services/incidents/event_correlator.py)
      │
      ├───────────────────────┬───────────────────────┐
      ▼                       ▼                       ▼
SQLite Database        Evidence Snapshot       FastAPI WebSocket
(data/ibvap_dev.db)   (data/evidence/*.jpg)    (ws://127.0.0.1:8000/ws/alerts)
                             │                        │
                             └───────────┬────────────┘
                                         ▼
                                React Operations UI
                              (http://localhost:5173)
```

---

## 2. Prerequisites Verified

* **FFmpeg:** v9.0.1 Full Build (Gyan.FFmpeg)
* **MediaMTX:** v1.20.1 Windows AMD64 (`infrastructure/mediamtx/mediamtx.exe`)
* **AI Model:** `yolov8n.pt` local weights
* **Test Video:** `data/raw/test_video.mp4` (H.264/AAC, 30 fps, 592x360)

---

## 3. How to Start the Live Demo

Run the automated all-in-one demo runner:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_end_to_end.ps1
```

Or start the individual components sequentially in separate terminals:

### Step 1: Start MediaMTX Server
```powershell
.\infrastructure\mediamtx\mediamtx.exe infrastructure\mediamtx\mediamtx.yml
```

### Step 2: Publish Local Video to CAM-01
```powershell
$ffmpeg = (Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1).FullName
& $ffmpeg -re -stream_loop -1 -i "data\raw\test_video.mp4" -c copy -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:8554/CAM-01
```

### Step 3: Start FastAPI Backend
```powershell
$env:PYTHONPATH = "."
python -m uvicorn apps.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 4: Start Inference Worker (AI Engine)
```powershell
$env:PYTHONPATH = "."
python services\inference\main_inference_worker.py --camera CAM-01 --rtsp rtsp://127.0.0.1:8554/CAM-01
```
*(Add `--debug` to open an OpenCV window showing real bounding boxes, track IDs, and the restricted polygon boundary).*

### Step 5: Start React Frontend
```powershell
cd apps\frontend
npm run dev
```
Open **`http://localhost:5173`** in your browser.

---

## 4. Zone Configuration

The restricted polygon is defined in [configs/zones.yaml](file:///C:/Users/dell/Projects/IBVAP/configs/zones.yaml):

```yaml
zones:
  - zone_id: "RESTRICTED_ZONE_01"
    name: "Perimeter Sector Alpha"
    camera_id: "CAM-01"
    zone_type: "RESTRICTED_ZONE"
    enabled: true
    color: "#FF0000"
    points:
      - x: 0.50
        y: 0.50
      - x: 0.90
        y: 0.50
      - x: 0.90
        y: 0.95
      - x: 0.50
        y: 0.95
```

---

## 5. Verification Results (Actual Execution)

* **RTSP stream reading:** Live H.264 stream read via OpenCV / TCP.
* **Person Detections:** Real person bounding boxes detected with ~0.66 confidence.
* **Tracking:** Real persistent track IDs (e.g. ID #1, #2).
* **Zone Entry:** Fired when person center entered `RESTRICTED_ZONE_01`.
* **Database Record:** Real record inserted into SQLite (`data/ibvap_dev.db`).
* **Evidence Image:** Real frame captured, saved as JPEG with cryptographic SHA-256 hash.
* **WebSocket Push:** Broadcast sent with HTTP 200 to connected operators.
* **No Mock Data / No External Feeds:** Zero internet streaming or synthetic incident generators used.
