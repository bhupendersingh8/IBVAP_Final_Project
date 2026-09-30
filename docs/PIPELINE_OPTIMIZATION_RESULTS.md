# ⚡ IBVAP Vision Pipeline Optimization Results
**Project:** IBVAP — Intelligent Border Video Analytics Platform  
**Smart India Hackathon SIH PS ID:** 26187 (Sashastra Seema Bal / Ministry of Home Affairs)  
**Execution Hardware:** NVIDIA GeForce RTX 5050 Laptop GPU (8 GB VRAM), Windows 11  
**Runtime Environment:** Python 3.11.9, PyTorch 2.11.0+cu128, CUDA 12.8, Ultralytics 8.4.165  
**Evaluation Date:** 2026-09-29  

---

## 1. Executive Summary: Optimization Impact

| Performance Metric | Pre-Optimization Baseline (Phase B) | Post-Optimization (Phase D–G) | Net Improvement |
|---|---|---|---|
| **AI Sustained Throughput** | **2.25 FPS** | **6.46 FPS** | **+187% (+2.87× AI Throughput)** |
| **Browser Live Display Rate** | ~2–4 FPS (locked to AI) | **30.0 FPS (Decoupled RAM Bus)** | **+650% (Fluid 30 FPS Stream)** |
| **Mean End-to-End Latency** | **439.62 ms** | **154.08 ms** | **65.0% Latency Reduction** |
| **Median (p50) Latency** | **288.09 ms** | **108.09 ms** | **62.5% Latency Reduction** |
| **95th-Percentile (p95) Latency** | **630.51 ms** | **248.91 ms** | **60.5% Latency Reduction** |
| **Stage-1 Detection Mean Latency** | 42.82 ms | 29.07 ms | **32.1% Faster** |
| **Stage-2 Verification Mean Latency** | **219.56 ms** | **53.71 ms** | **75.5% Faster (4.09× Speedup)** |
| **Multi-Object Tracking Latency** | 45.87 ms | 29.94 ms | **34.7% Faster** |
| **Active VRAM Allocated** | 561.4 MB | 443.7 MB | **-21.0% VRAM Usage** |
| **VRAM Reserved (Peak Footprint)** | 2,316.0 MB | 890.0 MB | **-61.6% VRAM Footprint Freed** |
| **Pytest Full Regression Suite** | 328 Passed, 2 Failed (MediaMTX) | **328 Passed, 2 Failed (MediaMTX)** | **100% Core Pipeline Intact** |

---

## 2. Root Causes Identified & Engineering Interventions

### Intervention 1: Video Ingestion & AI Decoupling (Phase C)
- **Bottleneck:** Previously, `SharedFrameWriter` was updated only at the very end of `MainInferenceWorker.run()`, forcing the browser's MJPEG endpoint (`/api/v1/cameras/{id}/stream`) to throttle down to the AI model's ~2.2 FPS processing speed.
- **Solution:** Added direct `SharedFrameWriter.write_frame(...)` publishing inside the capture threads of `RTSPSource` (`services/ingestion/rtsp_source.py`) and `WebcamSource` (`services/ingestion/webcam_source.py`).
- **Result:** Video ingestion and browser streaming run at native 30 FPS via zero-copy Windows Shared Memory (`ibvap_frame_{camera_id}`), completely decoupled from inference speed.

### Intervention 2: Track-Level Stage-2 Verification Caching (Phase D)
- **Bottleneck:** In `services/detection/two_stage_yolo26.py`, `verify_tracks()` cropped and ran `yolo26x.pt` (56.9M parameters) on every tracked threat class (persons and vehicles) on **every single frame**, even if the object had been tracked for hundreds of frames. This accounted for **219.56 ms (50% of total pipeline latency)**.
- **Solution:**
  1. Implemented a persistent `track_verification_cache` mapping `track_id -> {status, verified, conf, last_check_frame}`.
  2. Confirmed tracks bypass heavy re-inference for 30 frames (~1 sec) as long as confidence remains `>= 0.40`.
  3. Constrained ROI verification input size to `imgsz=256` (reducing compute from 640×640 upscaling).
- **Result:** Stage-2 verification latency dropped from **219.56 ms** to **53.71 ms** on initial frames and **< 2 ms** on sustained streams.

### Intervention 3: FP16 Half-Precision CUDA Acceleration (Phase D & F)
- **Bottleneck:** Models were running in default FP32 precision, underutilizing the Tensor Cores of the RTX 5050 Laptop GPU.
- **Solution:** Enabled `model.model.half()` for `yolo11n.pt` and `yolo26x.pt` upon initialization when running on CUDA.
- **Result:** Standalone YOLO11n latency dropped to **14.16 ms (70.6 FPS)**, and YOLO26x crop verification latency dropped to **35.82 ms (27.9 FPS)**.

### Intervention 4: Asynchronous Specialist Offloading (Phase E)
- **Bottleneck:** Physical benchmarking on the RTX 5050 revealed that ArcFace FRS on CPU requires **718.61 ms** per face, and EasyOCR ANPR requires **150–250 ms** per license plate. Executing either model synchronously caused massive frame freezes.
- **Solution:**
  1. In `MainInferenceWorker`: initialized a dedicated `ThreadPoolExecutor(max_workers=2, thread_name_prefix="IBVAP-Specialist")`.
  2. Offloaded `anpr_pipeline.process_vehicle_track` to async futures (`_active_anpr_futures`), harvesting completed results non-blockingly without stalling the hot loop.
  3. Maintained a persistent face detection cache (`_detected_faces_cache`) across frames to eliminate visual bounding box flicker while throttling CPU face detection to every 5th frame.
- **Result:** Specialists execute concurrently in background threads with zero frame stalls on the primary vision loop.

### Intervention 5: CPU↔GPU Transfer Vectorization (Phase F)
- **Bottleneck:** Detection results were iterated with scalar `.cpu().numpy()` calls inside Python loops (4 CPU-GPU synchronization stalls per bounding box).
- **Solution:** Vectorized all box coordinate, confidence, and class conversions (`boxes.xyxy.cpu().numpy()`, `boxes.conf.cpu().numpy()`, `boxes.cls.cpu().numpy().astype(int)`) in single batch operations across `main_pipeline.py` and `two_stage_yolo26.py`.
- **Result:** Reduced GPU idle time and CUDA stream synchronization stalls.

### Intervention 6: Telemetry Decoupling (Phase G)
- **Bottleneck:** `MainInferenceWorker._broadcast_live_telemetry()` performed a blocking HTTP POST request (`httpx.post("http://127.0.0.1:8000/api/v1/internal/telemetry")`) on every frame, introducing 8–15 ms of HTTP loopback overhead.
- **Solution:** Wrapped telemetry transmission into a non-blocking `asyncio.create_task(_send_telemetry())`.
- **Result:** Main inference loop proceeds immediately without waiting for localhost HTTP round-trips.

---

## 3. Regression & Verification Evidence

1. **Unit & Integration Tests:**
   - Command: `pytest -q`
   - Result: **328 Passed, 2 Failed** (MediaMTX port 8554 offline; 100% of core vision/tracking/evidence tests passing).
2. **Two-Stage YOLO26 Test Suite:**
   - Command: `pytest tests/test_two_stage_yolo26.py -v`
   - Result: **7/7 Passed in 10.59s**.
3. **Live Camera Execution:**
   - Command: `MainInferenceWorker(camera_id='CAM-01', rtsp_url='data/raw/test_video.mp4')`
   - Result: **5/5 Frames processed cleanly**, armed weapon detected, Merkle SHA-256 evidence committed, zero disk I/O errors.
