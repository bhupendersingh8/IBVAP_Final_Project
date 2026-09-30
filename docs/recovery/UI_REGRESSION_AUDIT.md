# IBVAP Frontend & Video Pipeline Regression Audit

**Audit Date:** 2026-09-28  
**Target Repository:** `C:\Users\anmol\.gemini\antigravity\scratch\IBVAP_Final_Project`  
**Current Branch / Safety Checkpoint:** `recovery-before-ui-video-fix` (created from `master` at SHA `073e40a`)  
**Status:** DIAGNOSIS ONLY — CODE MODIFICATIONS PENDING APPROVAL

---

## 1. Executive Summary & Root Cause Analysis

A major regression occurred in the frontend user interface and live video streaming pipeline between commit `aa07e0f` and the current `HEAD` (`073e40a` / `16e1d40`).

1. **Frontend UI Replacement:**  
   In commit `9e256d1` ("complete cyber-tactical AI neon redesign") and commit `16e1d40` ("prepare complete IBVAP RTX 5050 migration snapshot"), the original rich, interactive, multi-layered operations dashboard (`Dashboard.tsx`, ~1,344 lines) and dynamic themed layout (`Layout.tsx`, ~571 lines) were replaced by a simplified generic VMS card layout (~311 lines). Key tactical features (Digital PTZ Zoom & Pan, SVG bounding-box overlays with track velocity and dwell time, Operator Feedback Modal, Target Inspector Drawer, Multi-Camera 2x2 Grid View, Theme Presets, Keyboard Shortcuts, and Audio Alerting) were discarded.
2. **Video Streaming Breakage:**  
   In `Cameras.tsx` (lines 284–287) of commit `16e1d40`, the video `src` for `CAM-01` was hardcoded to `http://127.0.0.1:8889/CAM-01` (an external MediaMTX WebRTC/HLS port that was not running). When this external request failed, an `onError` handler reassigned the image `src` to `/api/v1/cameras/CAM-01/snapshot`, which returned HTTP 404 (Not Found), permanently breaking the image element.
3. **Webcam vs CCTV Discrepancy:**  
   `WEBCAM-01` worked because `Cameras.tsx` left non-`CAM-01` cameras routed to the backend endpoint `/api/v1/cameras/${selectedCameraId}/stream`. The backend's `WebcamSource` opened physical laptop device index 0 directly via OpenCV. For `CAM-01`, however, the code bypassed the backend route and attempted to reach the non-existent MediaMTX port 8889.
4. **Backend Worker Prerequisite:**  
   The backend `/api/v1/cameras/{id}/stream` endpoint serves frames from in-memory SharedMemory (`SharedFrameReader`). If `services/inference/main_inference_worker.py` is not running to process the input stream and write to `SharedFrameWriter`, the backend stream returns placeholder frames (`[Connecting / Initializing...]`). In addition, `main_inference_worker.py` failed on startup due to a missing `services/evidence` module caused by a directory ignore pattern (`evidence/`) in `.gitignore`.

---

## 2. Forensic Git History Breakdown

| Commit SHA | Date | Description | Frontend Status |
| :--- | :--- | :--- | :--- |
| **`aa07e0f`** *(Target)* | Mon Sep 28 07:18:21 2026 | `fix(demo): update start_sih_demo.ps1 for Windows cmd npm invocation` | **LAST KNOWN WORKING ORIGINAL UI** (1,344-line interactive Dashboard, 5 themes, HUD SVG overlay, PTZ zoom, operator modals) |
| **`9e256d1`** | Mon Sep 28 07:25:52 2026 | `feat(ui): complete cyber-tactical AI neon redesign for SIH & SSB defense` | 1st Redesign: Reduced Dashboard to 699 lines, replaced layout styling with neon themes |
| **`1c401ac`** | Mon Sep 28 10:48:28 2026 | `feat(cv-upgrade): implement phases 0-30 next-gen computer vision upgrade` | 2nd Redesign: Refined cv-upgrade styling, 579-line Dashboard |
| **`16e1d40`** | Mon Sep 28 14:10:21 2026 | `chore(migration): prepare complete IBVAP RTX 5050 migration snapshot` | 3rd Redesign: Substituted generic VMS dashboard (311 lines), introduced port 8889 bug in `Cameras.tsx`, split pages into generic ANPR, Evidence, Reports, System tabs |
| **`073e40a`** *(Current)* | Mon Sep 28 15:35:10 2026 | `chore(repo): remove bundled ffmpeg binaries from git history` | Identical frontend to `16e1d40` |

---

## 3. Frontend Files Changed Across Redesigns

Comparing `aa07e0f` (Original) to `HEAD` (`073e40a`):

| File Path | Status | Nature of Change |
| :--- | :--- | :--- |
| `apps/frontend/src/pages/Dashboard.tsx` | Modified | Truncated from 1,344 lines to 311 lines. Removed PTZ zoom, interactive SVG HUD, multi-cam grid, operator feedback, target inspector drawer. |
| `apps/frontend/src/components/layout/Layout.tsx` | Modified | Removed theme engine (Cyber Aurora, Ocean Cobalt, Emerald Defense, Sunset Recon, Radiant Light), keyboard shortcuts modal, dual clocks. Replaced with generic VMS gray sidebar. |
| `apps/frontend/src/pages/Cameras.tsx` | Modified | Hardcoded `http://127.0.0.1:8889/CAM-01` in primary viewport `<img>` tag and added 404 snapshot `onError` fallback. |
| `apps/frontend/src/pages/Incidents.tsx` | Modified | Rewritten into generic VMS table; removed interactive evidence inspection modals. |
| `apps/frontend/src/pages/Zones.tsx` | Modified | Zone geometry editor simplified and restyled. |
| `apps/frontend/src/pages/Settings.tsx` | Modified | Replaced full model registry/pipeline settings with basic VMS toggle cards. |
| `apps/frontend/src/index.css` | Modified | Replaced HUD corner borders, tactical animations, and theme variables with generic VMS palette. |
| `apps/frontend/src/main.tsx` | Modified | Added routes for `/evidence`, `/anpr`, `/reports`, `/system` instead of keeping core 5-tab tactical navigation. |
| `apps/frontend/src/components/ui/Badge.tsx` | Added | Added for generic VMS tables. |
| `apps/frontend/src/components/ui/StatusIndicator.tsx` | Added | Added for generic VMS tables. |
| `apps/frontend/src/pages/ANPR.tsx`, `Evidence.tsx`, `Reports.tsx`, `System.tsx` | Added | Split pages created during the generic VMS migration. |

---

## 4. Video Streaming Pipeline Trace

```
Recorded Video (data/raw/test_video.mp4) OR RTSP Feed OR Laptop Webcam (webcam:0)
        │
        ▼
[ Ingestion Layer: services/ingestion/rtsp_source.py OR webcam_source.py ]
        │
        ▼
[ Inference Worker: services/inference/main_inference_worker.py ]
  ├── YOLOv8n CUDA Inference (RTX 5050 ~8.6 ms latency)
  ├── ByteTrack / FallbackIoUTracker
  ├── Spatial RuleEngine & Zone Intrusion Logic
  ├── WebSocket Telemetry Broadcast -> ws://127.0.0.1:8000/ws
  └── Frame Publisher -> services/ingestion/shared_frame_buffer.py (SharedMemory: ibvap_frame_cam_01)
        │
        ▼
[ FastAPI Backend: apps/backend/routers/cameras.py ]
  └── GET /api/v1/cameras/{camera_id}/stream
      └── Reads SharedMemory (SharedFrameReader)
      └── Streams multipart/x-mixed-replace; boundary=frame (MJPEG @ 30 FPS)
        │
        ▼
[ Vite Dev Server: apps/frontend/vite.config.ts ]
  └── Proxies /api -> http://127.0.0.1:8000
        │
        ▼
[ Browser DOM: apps/frontend/src/pages/Dashboard.tsx / Cameras.tsx ]
  └── <img src="/api/v1/cameras/{id}/stream" />
```

### The Breakdown Points Identified:
1. **Broken `src` in `Cameras.tsx`:**  
   `src="http://127.0.0.1:8889/CAM-01"` bypassed the working backend proxy entirely.
2. **Broken `onError` in `Cameras.tsx` and `Dashboard.tsx`:**  
   Replaced stream with `/api/v1/cameras/{id}/snapshot`, which returned 404 because no snapshot route exists on that path.
3. **Inference Worker Crash:**  
   `main_inference_worker.py` failed to start due to `ModuleNotFoundError: No module named 'services.evidence'`. The `services/evidence/` directory was uncommitted due to `.gitignore` line 136 (`evidence/`).
4. **Missing Service Orchestration:**  
   The backend was running in isolation without the background frame publisher or RTSP simulator.

---

## 5. Minimal Restoration Strategy (Post-Approval)

To restore the original, working IBVAP UI and video feeds cleanly without modifying backend logic or architecture:

1. **Restore Original Frontend Source from `aa07e0f`:**
   ```bash
   git checkout aa07e0f -- apps/frontend/src/
   ```
   This restores the complete 1,344-line interactive `Dashboard.tsx`, multi-theme `Layout.tsx`, `index.css`, `Cameras.tsx`, `Incidents.tsx`, `Settings.tsx`, and `main.tsx`.
2. **Remove Unused Generic VMS Artifacts:**
   Clean untracked files added by `16e1d40` in `apps/frontend/src/pages/` (`ANPR.tsx`, `Evidence.tsx`, `Reports.tsx`, `System.tsx`) and `components/ui/`.
3. **Rebuild Frontend Bundle:**
   ```bash
   cd apps/frontend && npm run build
   ```
4. **Provide Missing `services/evidence` Implementation:**
   Implement `services/evidence/hash_chain.py` (`HashChainLedger`) and `services/evidence/retention_manager.py` (`EvidenceRetentionManager`) matching their unit tests in `tests/test_hash_chain.py` and `tests/test_evidence_retention.py`, and adjust `.gitignore` from `evidence/` to `/evidence/` or `/data/evidence/` so code under `services/` is never ignored.
5. **Verify Full Video Ingestion & Stream Delivery:**
   Execute `services/inference/main_inference_worker.py` with `test_video.mp4` / `CAM-01` and verify that `/api/v1/cameras/CAM-01/stream` renders live video and SVG overlays in the browser.

---

## 6. Risk Assessment

- **Backend / Database Risk:** **ZERO.** Backend routes, database tables, and WebSocket contracts at `HEAD` are completely backwards-compatible with `aa07e0f`.
- **Performance Risk:** **ZERO.** PyTorch CUDA `cu128` inference on the RTX 5050 operates at 115.74 FPS (8.64 ms latency), more than sufficient to drive the 30 FPS MJPEG stream and SVG HUD overlay.
- **Rollback Safety:** High. Branch `recovery-before-ui-video-fix` holds the complete current state before any code changes.
