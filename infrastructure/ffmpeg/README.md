# FFmpeg Suite Configuration for IBVAP

## Overview
FFmpeg is utilized by the Intelligent Border Video Analytics Platform (IBVAP) for:
1. Low-latency RTSP video simulation and feed injection (`data/raw/test_video.mp4` -> `rtsp://127.0.0.1:8554/CAM-01`).
2. Incident evidence video clip extraction and transcode operations.
3. Live camera and mobile phone RTSP ingestion.

> **Note on Binary Distribution:**  
> The precompiled Windows FFmpeg binaries (`ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe`) exceed 200 MB each (totalling > 600 MB) and are intentionally **excluded** from Git history in compliance with GitHub's 100 MB per-file limit.

---

## Installation on New Deployment Machine (Windows / RTX 5050)

On your target machine (e.g. NVIDIA GeForce RTX 5050 laptop), install FFmpeg system-wide using Windows Package Manager (`winget`):

```powershell
winget install Gyan.FFmpeg
```

Alternatively, download the official release build from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) and add its `bin` directory to your system `PATH`.

---

## Verification

Confirm that FFmpeg is accessible in your terminal:

```powershell
ffmpeg -version
ffprobe -version
```

---

## Application Path Fallback Architecture

IBVAP orchestration scripts (`scripts/start_sih_demo.ps1`, `scripts/ensure_services.ps1`, `scripts/start_full_demo.ps1`) implement automatic tiered resolution for FFmpeg:
1. **Tier 1 (Bundled Local):** `infrastructure/ffmpeg/bin/ffmpeg.exe` (if placed manually into the directory).
2. **Tier 2 (System PATH):** Standard global `ffmpeg` command on system PATH (via `winget` or manual install).
3. **Tier 3 (WinGet Package Cache):** Automatically discovers FFmpeg inside `$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg*`.

No modification of application source code or behavior is needed.
