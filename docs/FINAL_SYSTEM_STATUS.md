# IBVAP Final System Status & Pre-Demo Freeze Audit

**Milestone**: Monday SIH Demonstration Freeze  
**Date**: 2026-09-05 21:00 UTC  
**Environment**: Windows 11 AMD64, Intel Core i3 (CPU-Only Mode), 12GB RAM  
**Repository**: `C:\Users\dell\Projects\IBVAP`  

---

## 1. Verified Working Functionality

- **Video Ingestion Layer**:
  - Live Mobile IP Camera (`PHONE-CAM-01`) verified reachable at `http://10.63.26.249:8080/video` via direct MJPEG and low-latency FFmpeg RTSP relay.
  - Perimeter CCTV Simulation (`CAM-01`) continuously replayed via MediaMTX at `rtsp://127.0.0.1:8554/CAM-01` and WebRTC at `http://127.0.0.1:8889/CAM-01/`.
- **Inference & Computer Vision Pipeline**:
  - Ultralytics YOLOv8n detector loaded in CPU-only mode.
  - Persistent Class-Aware Tracking (`FallbackIoUTracker` / ByteTrack) maintaining track IDs, velocity vectors, and trajectory history.
  - Class preservation: Standard `class_name="person"` and `class_name="vehicle"` with vehicle subclasses (`car`, `truck`, `bus`, `motorcycle`).
- **Spatial Rule Engine**:
  - Ray-casting polygon containment strictly evaluated at the **bottom-center ground contact point** (`x=(x1+x2)/2, y=y2`), eliminating upper-body false alarms.
  - Directional `ZONE_ENTRY` transition alerts with 15-second per-track deduplication cooldowns.
- **Evidence & Cryptographic Integrity**:
  - Atomic snapshot persistence to `data/evidence/` with SHA-256 integrity hash.
  - **Local Cryptographic Hash Chain Ledger** (`evidence_hash_chain`) linking every event cryptographically to the prior block's hash.
- **Incident Lifecycle Management**:
  - 4-state workflow (`NEW` -> `ACKNOWLEDGED` -> `INVESTIGATING` -> `RESOLVED`) supported in backend SQLite/FastAPI and frontend React UI.
- **Frontend Dashboard**:
  - React 18 + TypeScript + Vite operations dashboard compiling with 0 errors (`npm run build`).
  - Viewport-synchronized SVG overlays showing bounding boxes, track IDs, trajectory trails, and authoritative restricted zone polygons.
  - Dedicated multi-camera switcher (`PHONE-CAM-01` and `CAM-01`).

---

## 2. Regression Test Suite

- **Pytest**: **54 of 54 tests PASSED** in 4.41s across all modules:
  - `tests/test_tracking.py`: 34 passed
  - `tests/test_anpr.py`: 9 passed
  - `tests/test_detection.py`: 4 passed
  - `tests/test_hash_chain.py`: 4 passed
  - `tests/test_rules.py`: 3 passed
- **Frontend**: Vite production build succeeded cleanly (`dist/assets/index-D5K1SUS8.js`).

---

## 3. Honest Real-World Constraints Disclosure

1. **Plate Recognition**: Real license plates in wide-angle perimeter CCTV test footage (592x360) are sub-pixel (<35px). The system honestly flags them as `UNREADABLE` / `NOT_VERIFIED` rather than hallucinating synthetic text.
2. **CPU Execution Envelope**: YOLOv8n runs CPU-only on Intel Core i3 at 12–18 FPS. The display feed is decoupled to guarantee smooth operator rendering.
3. **No Blockchain / Military Claims**: The evidence ledger is a local tamper-evident SHA-256 hash chain; no cryptocurrency or decentralized blockchain overhead is present.
