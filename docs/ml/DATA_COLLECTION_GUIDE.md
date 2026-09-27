# DATA_COLLECTION_GUIDE.md — Operational Frame Collection Guide

**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Tool:** `scripts/collect_dataset_frames.py`  
**Target Ingestion:** Existing IP CCTV Surveillance Camera Infrastructure  

---

## 1. Overview

The IBVAP Data Collection Pipeline extracts non-destructive, full-resolution frames from authorized video feeds (RTSP CCTV or local recorded MP4 files) and packages them into staging directories for annotation.

---

## 2. Execution Runbook

### 2.1 From Authorized CCTV Stream / MediaMTX Gateway

```powershell
python scripts/collect_dataset_frames.py `
    --input "rtsp://127.0.0.1:8554/CAM-01" `
    --output "dataset/staging/frames" `
    --fps 1.0 `
    --max-frames 100 `
    --source-id "CAM-01-SECTOR-ALPHA" `
    --source-type "cctv_rtsp"
```

### 2.2 From Recorded Field MP4 Footage

```powershell
python scripts/collect_dataset_frames.py `
    --input "data/raw/test_video.mp4" `
    --output "dataset/staging/frames" `
    --fps 1.0 `
    --source-id "CAM-01-RECORDING" `
    --source-type "video_file"
```

---

## 3. Metadata Manifest (`dataset/metadata/frames.jsonl`)

Every extracted frame is automatically cataloged in the JSON Lines manifest with:
- **`frame_id`**: Deterministic unique identifier (`<source_id>_f<frame_number>`).
- **`sha256`**: Cryptographic digest of the exact JPEG byte sequence.
- **`source_id`**: Sanitized camera name (credentials/passwords strictly masked).
- **`quality_status`**: `GOOD`, `LOW_QUALITY`, `DUPLICATE`, or `REJECTED`.
- **`lighting_condition`**: `DAY`, `NIGHT`, `LOW_LIGHT`, or `IR`.
- **`blur_score`**: Laplacian variance ($> 30.0$ threshold for sharp images).
- **`brightness` & `contrast`**: Mean pixel intensity and standard deviation.

---

## 4. Privacy & Security Rules

1. **Zero Public Leakage**: Raw surveillance video and staging frames are strictly gitignored.
2. **Credential Sanitization**: The collection script automatically strips user authentication tokens from RTSP URLs before logging or saving metadata.
