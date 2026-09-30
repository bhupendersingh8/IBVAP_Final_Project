# IBVAP P1 Automation & Single-Command Workflow Setup

This document describes the automated execution and verification framework for the **Intelligent Border Video Analytics Platform (IBVAP)** (SIH PS-26187).

It enables a **Zero Repeated Approval / Single-Command Demonstration & Acceptance Workflow** designed for evaluators, judges, and operators.

---

## 1. Overview & Objectives

In automated and evaluation scenarios, operators should not need to manually approve dozens of separate commands, shell executions, server launches, and test scripts.

The IBVAP Master Controller orchestrates the entire operational stack through a unified command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ibvap.ps1 demo
```

Running this **single command** executes the complete automated cycle:
1. **Clean & Reset**: Purges previous test incidents and evidence snapshots for clean state.
2. **Ensure Services**: Inspects specific processes, ports, and health endpoints (MediaMTX, FFmpeg, FastAPI Backend, Inference Worker, Vite Dev Server) and starts only missing services without duplicating processes.
3. **Launch Browser**: Opens the live dashboard in the user's default browser (`http://localhost:5173`).
4. **Browser & AI Acceptance Suite**: Runs automated headless Microsoft Edge via Playwright to verify video rendering, live AI person detection, tracking, zone overlay, real-time alert generation, camera failure & auto-recovery, WebSocket reconnection, and incident deduplication.
5. **Report Generation**: Automatically outputs the formal evaluation matrix and captures 9 evidence screenshots into `docs/evidence/p1/`.

---

## 2. Prerequisites & Safe Local Configuration

The automation framework strictly operates within standard Windows user-space permissions without bypassing operating system security, Windows Defender, UAC, or network boundaries:

1. **Operating System**: Windows 10/11 (AMD64 / ARM64).
2. **Browser**: Microsoft Edge (`channel="msedge"`). No external Chromium binary downloads are performed.
3. **Python Environment**: Python 3.11+ / 3.14 with required dependencies (`playwright`, `websockets`, `fastapi`, `ultralytics`, `opencv-python`, `structlog`).
4. **Media Stack**:
   - MediaMTX binary placed in `infrastructure/mediamtx/mediamtx.exe` (Ports: RTSP 8554, WebRTC 8889, API 9997).
   - FFmpeg 9.0.1 installed via WinGet.
5. **Authorized Test Asset**: `data/raw/test_video.mp4` (local authorized video replay).

---

## 3. Master CLI Reference (`scripts/ibvap.ps1`)

The master controller script provides standard administration verbs:

| Command | Action | Description |
| :--- | :--- | :--- |
| `.\scripts\ibvap.ps1 demo` | **Full Autonomous Demo** | Cleans environment, ensures stack, launches browser, executes acceptance suite, and outputs evidence report. |
| `.\scripts\ibvap.ps1 start` | **Ensure Services** | Checks and starts MediaMTX, FFmpeg, Backend, Worker, and Frontend with readiness polling. |
| `.\scripts\ibvap.ps1 stop` | **Stop Services** | Gracefully terminates all background IBVAP processes using exact WMI process matching. |
| `.\scripts\ibvap.ps1 restart` | **Restart Services** | Stops and relaunches all stack components cleanly. |
| `.\scripts\ibvap.ps1 status` | **Inspect Status** | Displays running/stopped status and PIDs of all 5 stack services. |
| `.\scripts\ibvap.ps1 test` | **Automated Acceptance** | Runs the Playwright/Edge test suite directly and generates screenshots. |
| `.\scripts\ibvap.ps1 audit` | **Stability Audit** | Runs the 2-minute continuous runtime stability audit recording FPS and disconnects. |
| `.\scripts\ibvap.ps1 clean` | **Reset Database** | Clears demonstration incidents, events, and evidence files. |

---

## 4. Automated Testing Architecture

### A. Non-Intrusive State Inspection (`window.__IBVAP_TEST_STATE__`)
To avoid fragile DOM scraping or CSS selector brittleness, `Dashboard.tsx` exposes runtime test telemetry directly to the window context:
- `videoPlaying`: Boolean confirming video viewport activity.
- `activeTracks`: Integer count of active tracks tracked by the inference worker.
- `tracks`: Array of live tracks with bounding boxes, confidence, class, and trajectory history.
- `cameraStatus`: Health state of CAM-01 (`ONLINE`, `CONNECTING`, `DEGRADED`, `OFFLINE`).
- `websocketStatus`: WebSocket connection state (`CONNECTED`, `RECONNECTING`, `DISCONNECTED`).
- `fps`: Current measured inference frames per second.
- `zones`: Array of active authoritative restricted zone IDs.

### B. Controlled Fault Injection
1. **Camera Failure & Auto-Recovery**:
   - Terminating the FFmpeg publisher causes MediaMTX to signal unpublishing on path `CAM-01`.
   - The inference worker detects frame unavailability, transitions camera health to `DEGRADED`/`RECONNECTING`, and periodically updates telemetry.
   - Restarting FFmpeg restores the stream; the worker automatically resumes frame ingestion and AI detection.
2. **WebSocket Interruption & Auto-Recovery**:
   - The test invokes `window.__IBVAP_WS_DISCONNECT__()`.
   - The client immediately transitions to `RECONNECTING` and initiates exponential backoff reconnects.
   - Upon reconnection, telemetry resumes streaming without user intervention or page reload.

### C. Transition-Based Incident Deduplication
- Alerts are generated strictly on spatial boundary transitions (`ZONE_ENTRY`), rather than continuous presence (`ZONE_PRESENCE`).
- A 15-second per-track cooldown prevents alert flooding when a tracked person remains inside the restricted zone.

---

## 5. Evidence Artifacts Directory

During automated acceptance runs, screenshots are captured to `docs/evidence/p1/`:
- `01_dashboard_loaded.png`
- `02_live_video.png`
- `03_person_tracking.png`
- `04_zone_overlay.png`
- `05_live_alert.png`
- `06_camera_reconnecting.png`
- `07_camera_recovered.png`
- `08_websocket_reconnecting.png`
- `09_websocket_recovered.png`

The formal acceptance log is written to `docs/P1_AUTOMATED_ACCEPTANCE_REPORT.md`.
