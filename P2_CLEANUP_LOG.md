# P2 CLEANUP LOG
**Date:** 2026-09-27  
**Host:** Dell Laptop (Intel Core i3-1115G4, 12GB RAM, Windows)  
**Working Directory:** `C:\Users\dell\Desktop\p2\IBVAP_Final_Project`  

---

## 1. Baseline State & Pre-Cleanup Verification
- Canonical Database: `data/ibvap_dev.db` (18,157,568 bytes, 30,867 total records across 13 tables, including 7,708 events and 7,708 incidents) — **PRESERVED UNTOUCHED**.
- Incompatible TensorRT engine: `models/yolov8n.engine` (172,439,740 bytes) — copied to `_backup/legacy_tensorrt/yolov8n.engine` before deletion.

---

## 2. Safely Removed Items (Phase 1)
| Item | Type | Path | Size | Reason / Safe Verification |
|------|------|------|------|---------------------------|
| 1. `__MACOSX` | Directory | `C:\Users\dell\Desktop\p2\__MACOSX` | ~KB | macOS ZIP archive extraction metadata, unreferenced junk |
| 2. Nested duplicate tree | Directory | `IBVAP_Final_Project\IBVAP_Final_Project` | ~17 MB | Accidental recursive zip extraction containing duplicate older db and binaries |
| 3. Root duplicate model | File | `yolov8n.pt` (root) | 6,549,796 bytes | Exact duplicate of `models\yolov8n.pt` (preserved) |
| 4. Raw duplicate video | File | `data\raw\clean_stream.mp4` | 4,700,380 bytes | Exact duplicate of `data\raw\test_video.mp4` (preserved, 0 code references) |
| 5. Stale 0-byte databases | Files | `ibvap.db` (root) & `data\ibvap.db` | 0 bytes each | Empty placeholder files, 0 code references |
| 6. Incompatible TensorRT engine | File | `models\yolov8n.engine` | 172,439,740 bytes | Incompatible with Intel CPU; safely backed up to `_backup\legacy_tensorrt\` |

---

## 3. Preserved Canonical Files
- `data/ibvap_dev.db` (Canonical historical database with 7,708 events/incidents)
- `models/yolov8n.pt` (Canonical PyTorch YOLOv8 detection model)
- `models/yolov8n.onnx` (Canonical hardware-agnostic ONNX model)
- `yolov8n-pose.pt` (Canonical pose model)
- `data/raw/test_video.mp4` (Canonical RTSP test video)
- `infrastructure/ffmpeg/bin/*` (Bundled offline FFmpeg binaries)
- `infrastructure/mediamtx/*` (Bundled offline MediaMTX binary)
