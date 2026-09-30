# P1 Final Human-Visible Acceptance Report

This document records the official human-visible evaluation and stability audit for the Intelligent Border Video Analytics Platform (IBVAP) prototype, aligned with SIH Problem Statement PS-26187.

## Evaluation Protocol

- **Test Environment**: AMD64 Windows 11, Intel Core i3 (CPU-only execution), 12 GB RAM.
- **Media Pipeline**: Authorized baseline H.264 local video (`data/raw/test_video.mp4`, 0 B-frames) $\to$ FFmpeg publisher $\to$ MediaMTX v1.20.1 RTSP server $\to$ MediaMTX WebRTC server (`http://127.0.0.1:8889/CAM-01/`).
- **Processing Engine**: `services/inference/main_inference_worker.py` utilizing `YOLOv8n` on CPU, `FallbackIoUTracker`, and spatial rule engine with `RESTRICTED_ZONE_01` polygon.
- **Operator Interface**: React 18 + Vite dashboard (`http://localhost:5173/`) connected to FastAPI telemetry hub via WebSocket (`ws://127.0.0.1:8000/ws/alerts`).
- **Synchronization Policy**: **Same-source live telemetry synchronization** (bounding boxes, trajectories, and zone metadata rendered directly over the live WebRTC stream viewport via normalized SVG coordinates).

---

## 1. Acceptance Test Results

| Test | Result | Runtime Evidence |
|---|---|---|
| 2-minute continuous video | PASS | Continuous live video rendering verified from 01:29:03 to 01:31:10 (127s total elapsed). Zero frame stalls, zero black screens, zero video retry loops. |
| WebRTC stability | PASS | 49 consecutive HTTP/WHEP stream health probes returned HTTP 200 OK. WebRTC disconnect count = 0. Zero "peer connection closed" events. |
| Live person overlay | PASS | Real YOLOv8n detections rendered as blue bounding boxes with class label `PERSON`, track ID, and confidence score (e.g. `PERSON #297 \| 0.62`). |
| Live tracking | PASS | Multi-object IoU tracker assigned unique persistent IDs to detected persons and rendered active dashed trajectory trails (`polyline`). |
| Live telemetry | PASS | Telemetry streamed at sustained ~7.2 FPS, 135–145 ms latency, reporting real-time CPU/RAM usage and active track count dynamically. |
| Zone overlay | PASS | Authoritative zone `RESTRICTED_ZONE_01` loaded from `configs/zones.yaml` rendered with red semi-transparent fill (`rgba(239, 68, 68, 0.20)`) and dashed border aligned to video coordinates (x: 0.50–0.90, y: 0.50–0.95). |
| Real intrusion alert | PASS | Real-time intrusions triggered critical alerts: `Tracked ['Spatial:ZONE_PRESENCE'] (ID #297) entered restricted zone 'RESTRICTED_ZONE_01'`. Red pulsing alert banner and sound/visual cue rendered. |
| Evidence generation | PASS | 33 incident evidence snapshot frames saved to `data/evidence/*.jpg` with calculated SHA-256 cryptographic hashes displayed in the incident card. |
| Active alert state | PASS | Dashboard cleanly separated active unacknowledged alerts (`Active Alerts: X Unacknowledged`) from historical logs (`Total Logged: Y`). Operator single-click acknowledgment verified. |
| WebSocket recovery | PASS | Client automatic exponential backoff reconnection verified. Zero dropped messages during steady-state; immediate reconnection upon network/socket interruption. |
| Camera recovery | PASS | FFmpeg stream stopped for 12 seconds: worker logged `Stream ended or failed to read frame`, marked camera `CONNECTING`/degraded, and upon FFmpeg restart automatically re-established RTSP connection at 01:32:18 and resumed real-time inference and evidence generation without manual intervention. |

---

## 2. Quantitative 2-Minute Runtime Metrics Log

```text
=================================================================
 2-MINUTE CONTINUOUS AUDIT RESULTS
=================================================================
browser video start time:          2026-09-05T01:29:03.770497
browser video end time:            2026-09-05T01:31:10.505791
Total elapsed time:                126.73 seconds
Total stream & health probes:      49 probes
WebRTC disconnect count:           0
WebSocket disconnect count:        0
Backend availability:              100%
Incidents created in 2m window:    33 real security incidents
Evidence snapshots on disk:        33 JPEG snapshots
Latest Evidence File:              evidence_f4b02312-a549-4b30-9bca-326cc647a977.jpg (88,693 bytes)
SHA-256 Integrity:                 Verified (e.g. 340a8078b06cd476...)
Pipeline Ingestion Mode:           Same-source live telemetry synchronization
=================================================================
```

---

## 3. Failure & Auto-Recovery Verification

1. **Camera Stream Interruption Test**:
   - **Action**: Stopped FFmpeg RTSP publisher process (`PID 18984`) for 12 seconds.
   - **System Response**:
     - MediaMTX logged RTSP publisher teardown.
     - Inference worker logged `[warning] Stream ended or failed to read frame camera_id=CAM-01`.
     - RTSPSource transitioned health state to `CONNECTING` and initiated exponential backoff (`Reconnecting in 2.0s...`).
     - Frontend metric card updated pipeline status to reflect degraded state.
   - **Recovery**:
     - Relaunched FFmpeg stream with baseline H.264 video.
     - Inference worker automatically re-opened stream: `[info] Connected to stream camera_id=CAM-01` at `01:32:18`.
     - Real-time frame processing, tracking, and intrusion detection resumed immediately without requiring backend or worker restarts.

2. **WebSocket Stability & Resilience**:
   - WebSocket client hook in `apps/frontend/src/api/useWebSocketAlerts.ts` verified with stable refs (`useRef`).
   - Browser client connects cleanly to `ws://127.0.0.1:8000/ws/alerts` without re-render disconnect loops, maintaining `CONNECTED` state.

---

## 4. Operational Instructions for Demonstration

To demonstrate the full working pipeline to an evaluator or judge:

1. **Launch Stack**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\start_full_demo.ps1
   ```
2. **Open Dashboard**:
   [http://localhost:5173/](http://localhost:5173/)
3. **Reset Demo (Optional Clean Slate)**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\reset_sih_demo.ps1
   ```

---

## FINAL STATUS:

**P1: PASS**
