# IBVAP — Team Quick Setup & Run Guide

> **Intelligent Border Video Analytics Platform (SIH PS-26187 / MHA)**
> Fully local, offline-capable surveillance analytics software running on existing CCTV streams or local webcam.

---

## ⚡ Prerequisites & Verified Environment

Before you start, make sure your machine has:
1. **Python**: **Verified on Python 3.14.4** (Python 3.11+ compatible). Must be added to your system `PATH`.
2. **Node.js & npm**: **Verified on Node.js v25.9.0 & npm 11.12.1** (Node 18+ compatible).
3. **FFmpeg**: **Verified on FFmpeg 9.0.1** (required for local RTSP camera stream simulation via MediaMTX). Ensure `ffmpeg` is accessible in system `PATH`.

---

## 🚀 3-Minute Fast Setup

### Step 1: Clone or Unzip
Unzip `IBVAP.zip` to your project workspace (e.g. `C:\Users\<your-user>\Projects\IBVAP` or any directory). Open a **PowerShell** or Terminal window inside the root folder:
```powershell
cd IBVAP
```

### Step 2: Configure Environment
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
*(No edits are strictly needed for local testing — defaults are preconfigured for SQLite and localhost).*

### Step 3: Install Dependencies
```powershell
# Python Dependencies
pip install -r requirements\dev.txt
pip install -r requirements\ml.txt

# Frontend Dependencies
cd apps\frontend
npm install
cd ..\..
```

---

## 🎮 Running IBVAP

### Mode A: Standard CCTV Demo Mode (Recommended)
This runs the full IP CCTV surveillance simulation (MediaMTX RTSP Gateway + Backend + Vite Dashboard + FFmpeg Test Stream + AI Inference Worker):
```powershell
.\scripts\ibvap.ps1 demo
```
- Open browser: **`http://localhost:5173`**
- Watch real-time YOLOv8 detections, tracking, perimeter fencing, instant alerts, and SHA-256 evidence chain!

### Mode B: Laptop Webcam Adapter (Test with your own room/face)
Don't want to use the pre-recorded CCTV loop? Test AI person detection and zone intrusion live using your laptop webcam:
```powershell
.\scripts\ibvap.ps1 webcam
```
- Open browser: **`http://localhost:5173`**
- Click the **WEBCAM-01** card in the dashboard.
- Move in and out of the red restricted zone to trigger live intrusion alerts!

### Mode C: Stop All Services
```powershell
.\scripts\ibvap.ps1 stop
```

### Mode D: Clean Reset (Fresh Demo State)
Purge previous runtime operational database records and snapshot images:
```powershell
python scripts\clean_reset.py
```

---

## 🧪 Running Verification Tests

Run the full automated pytest suite (75/75 passing):
```powershell
pytest tests/ -q
```
Verify frontend build:
```powershell
cd apps\frontend
npm run build
```

---

## ❓ Troubleshooting

- **Port Conflict (8000 or 5173 already in use)**:
  Run `.\scripts\ibvap.ps1 stop` to terminate orphaned uvicorn/node processes.
- **Webcam permission blocked on Windows**:
  Ensure Windows Camera Privacy Settings allow desktop apps to access the camera.
- **No Video Stream on Dashboard**:
  Ensure MediaMTX binary or FFmpeg is running. You can check status anytime with:
  ```powershell
  .\scripts\ibvap.ps1 status
  ```
