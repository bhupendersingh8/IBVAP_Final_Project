# IBVAP — Android Phone Live IP Camera Setup Guide

This guide describes how to connect an Android mobile device running an IP Webcam server as an active, real-time live camera source (`PHONE-CAM-01`) within the IBVAP platform.

---

## 1. Overview & Architecture

Instead of relying solely on simulated video clips, IBVAP supports ingesting live real-time footage from Android devices.

```
[ Android Phone: IP Webcam App ]
        │  (HTTP MJPEG: port 8080/video)
        ▼
[ Low-Latency FFmpeg Transcoding Relay ]
        │  (Downscales 1080p -> 640x360 @ 10 FPS, H.264 ultrafast)
        ▼
[ MediaMTX Local Media Server ]
        │
        ├── RTSP: rtsp://127.0.0.1:8554/PHONE-CAM-01  ──>  [ IBVAP AI Inference Worker ]
        │                                                     (YOLOv8 + IoU Tracking + Rules)
        │                                                              │
        └── WebRTC: http://127.0.0.1:8889/PHONE-CAM-01/                ▼
                    (Direct Browser Iframe in React)       [ WebSocket Telemetry & SQLite ]
```

---

## 2. Phone Application Setup

1. Install **IP Webcam** (by Pavel Khlebovich) or any standard MJPEG Android IP Camera app from Google Play or F-Droid.
2. Ensure both the **PC** and the **Android Phone** are connected to the same local Wi-Fi network.
3. Open the app and configure:
   - **Video resolution**: `1920x1080` (or `1280x720`).
   - **Quality**: `50% - 75%` (minimizes Wi-Fi jitter).
   - **Orientation**: `Landscape` (recommended for optimal detection geometry).
   - **Power management**: Ensure "Keep screen on" or background service mode is enabled to prevent Android OS doze/sleep from terminating sockets.
4. Scroll to the bottom and tap **Start Server**.
5. Note the displayed URL (typically `http://<phone_ip>:8080`).

---

## 3. Verified Endpoints

The Android IP Webcam server exposes the following endpoints:
- **Live Video Stream**: `http://<phone_ip>:8080/video` (Content-Type: `multipart/x-mixed-replace; boundary=...`, MJPEG).
- **Snapshot Frame**: `http://<phone_ip>:8080/shot.jpg` (Single JPEG frame).
- **Device Telemetry**: `http://<phone_ip>:8080/status.json` (Battery, orientation, sensors).
- **Hardware Torch Control**:
  - Turn Torch ON: `http://<phone_ip>:8080/enabletorch`
  - Turn Torch OFF: `http://<phone_ip>:8080/disabletorch`

---

## 4. Launching the Phone Stream in IBVAP

### Option A: Master Script (Recommended)
Run the master control script:
```powershell
.\scripts\ibvap.ps1 phone -PhoneUrl "http://10.63.26.249:8080/video"
```

### Option B: Dedicated Phone Script
Run the dedicated phone relay orchestrator:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\phone_camera_relay.ps1 -PhoneUrl "http://10.63.26.249:8080/video"
```

### Option C: Stopping Phone Relay & Worker
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\phone_camera_relay.ps1 -Stop
```

---

## 5. Viewing on the Dashboard

1. Open your browser: `http://localhost:5173`
2. Under **Active Camera Selection**, click the **PHONE-CAM-01** card.
3. The main video viewport immediately switches to the live WebRTC stream from your phone.
4. Real-time YOLO detections (people, cars, motorbikes) and persistent track IDs are drawn directly over the phone feed via synchronized SVG overlays.
5. If an object enters the phone's restricted zone (`PHONE_RESTRICTED_01`), a `RESTRICTED_ZONE_INTRUSION` alert is emitted, logged in SQLite, and saved with an SHA-256 evidence snapshot.

---

## 6. Performance & Hardware Considerations (Intel i3 / CPU-Only)

- **CPU Scaling**: The raw phone stream is 1080p. The FFmpeg relay downscales the stream to `640x360` with `-preset ultrafast -tune zerolatency`. This prevents CPU saturation on dual-core / quad-core i3 processors and maintains low glass-to-glass latency (< 250ms).
- **Wi-Fi Stability**: If Wi-Fi signal drops, the `RTSPSource` client automatically reconnects using exponential backoff without crashing the IBVAP pipeline.
