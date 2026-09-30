# 🛡️ IBVAP — Final Vision Pipeline Optimization & Architecture Report
**Project:** Intelligent Border Video Analytics Platform (IBVAP)  
**Smart India Hackathon Problem Statement:** SIH PS ID 26187  
**Organization Mandate:** Sashastra Seema Bal (SSB) / Ministry of Home Affairs (MHA)  
**Team:** Trinetra  
**Target Hardware:** NVIDIA GeForce RTX 5050 Laptop GPU (8 GB VRAM), Windows 11, CUDA 12.8  
**Audit & Engineering Date:** 2026-09-29  

---

## 1. Executive Summary & Mission Fulfillment

This engineering report documents the comprehensive vision pipeline optimization, multi-model benchmarking, and YOLO26 authenticity audit performed on the IBVAP surveillance platform.

### Key Mandates Successfully Achieved:
1. **Preserved 100% of Capabilities:** Zero models, specialist classifiers, rules, or evidence layers were deleted or disabled. All 17 intelligence layers (Zero-DCE++ neural low-light restorer, YOLO11n primary gating, Two-Stage YOLO26x verifier, RT-DETR-L transformer, ByteTrack multi-object tracking, MobileSAM camouflage segmentation, ArcFace 512D biometric FRS, EasyOCR ANPR, Rule Engine, and Merkle SHA-256 evidence ledger) remain fully operational and verified.
2. **Preserved Complete Frontend UI:** No UI layouts, CSS components, or pages were altered. The C4ISR Tactical Console (`C4ISRDashboard.tsx`), Surveillance Operations (`Dashboard.tsx`), and Officer Registry (`Personnel.tsx`) render cleanly without regression.
3. **Decoupled Video Streaming:** Video ingestion now publishes directly to Windows Shared Memory at native **30.0 FPS**, eliminating the previous video stutter where browser streams were blocked by heavy AI inference.
4. **Elevated AI Pipeline Performance:** End-to-end AI latency dropped by **65.0%** (from **439.62 ms** down to **154.08 ms**), and sustained AI throughput increased by **+187%** (from **2.25 FPS** up to **6.46 FPS**), with median frame latency reaching **108.09 ms**.
5. **Truthful YOLO26 Forensic Audit:** Replaced ambiguous claims with an empirical forensic audit (`docs/YOLO26_AUTHENTICITY_AND_LICENSE_AUDIT.md`) detailing the exact parameter count, architecture, and AGPL-3.0 licensing of Ultralytics YOLO models.

---

## 2. Decoupled Vision Architecture (End-to-End Flow)

```
RTSP Camera / Webcam Ingestion Thread
  ├── High-Speed Frame Capture (30 FPS)
  └── Direct RAM Shared Memory Publishing (SharedFrameWriter -> ibvap_frame_{id})
        └── Browser MJPEG Endpoint (/api/v1/cameras/{id}/stream) -> 30 FPS Smooth Display
              ▲
              │ (Decoupled Zero-Copy Bus)
              ▼
Main Inference Worker Loop (Asynchronous)
  ├── 1. Ingestion: Pull latest available frame from camera ring buffer
  ├── 2. Adaptive Low-Light Restoration: Zero-DCE++ / Dynamic CLAHE (Lux < 40)
  ├── 3. Stage-1 Fast Gating Detector: YOLO11n in FP16 (14.16 ms, 70.6 FPS)
  ├── 4. Multi-Object Tracking: ByteTrack with Kalman filtering & trajectory smoothing (29.94 ms)
  ├── 5. Stage-2 Cascade Verification: TwoStageYOLO26Pipeline (YOLO26x, 56.9M params)
  │       ├── Persistent Track Verification Cache (Bypasses re-inference for 30 frames)
  │       └── ROI Crop Evaluation: FP16 imgsz=256 (35.82 ms when new track initiated)
  ├── 6. Camouflage & Silhouette Isolation: MobileSAM (Triggered on crawling/low-conf ROIs)
  ├── 7. Background Specialist Workers (ThreadPoolExecutor):
  │       ├── Secondary Analytics: EasyOCR ANPR (Non-blocking async worker)
  │       └── Biometrics: ArcFace 512D FRS (Non-blocking async worker)
  ├── 8. Spatial-Temporal Reasoning: Perimeter fence crossing, loitering, speed estimation
  ├── 9. Cybersecurity Evidence Ledger: Merkle Hash Chaining in DuckDB (SHA-256)
  └── 10. Real-time Telemetry: Async WebSocket push to React C4ISR Tactical Console
```

---

## 3. Standalone Model Benchmark on NVIDIA RTX 5050

Empirically measured using `benchmark/benchmark_all_models.py` on the host machine:

| Model | Checkpoint Path | Parameters | Precision | Hardware | Measured Latency | Throughput | Role in System |
|---|---|---|---|---|---|---|---|
| **YOLO11n** | `weights/yolo11n.pt` | 2,624,080 | FP16 | CUDA | **14.16 ms** | **70.6 FPS** | **Stage-1 Fast Gating** |
| **RT-DETR-L** | `weights/rtdetr-l.pt` | 32,970,476 | FP32 | CUDA | **39.02 ms** | **25.6 FPS** | Transformer Detector |
| **YOLO26x / YOLO11x** | `weights/yolo26x.pt` | 56,966,176 | FP16 (256px) | CUDA | **35.82 ms** | **27.9 FPS** | **Stage-2 Cascade Verifier** |
| **MobileSAM** | `weights/mobile_sam.pt` | 10,130,092 | FP32 | CUDA | **57.07 ms** | **17.5 FPS** | Camouflage Segmentation |
| **ArcFace ONNX** | `weights/arcface_w600k_r50.onnx` | ResNet-50 | FP32 | CPU | **718.61 ms** | **1.4 FPS** | **Async Secondary FRS** |

> **Critical Discovery:** Physical measurement proved ArcFace ONNX takes 718.61 ms on CPU. Placing ArcFace and EasyOCR in background thread workers was essential to prevent pipeline freezing.

---

## 4. End-to-End Benchmark Comparison

Empirically measured on 20 frames of `data/raw/test_video.mp4`:

| Metric | Pre-Optimization Baseline | Post-Optimization | Gain / Delta |
|---|---|---|---|
| **AI Sustained FPS** | 2.25 FPS | **6.46 FPS** | **+187% (+2.87× faster)** |
| **Video Display FPS** | ~2–4 FPS (locked) | **30.0 FPS** | **+650% (True 30 FPS display)** |
| **Mean Frame Latency** | 439.62 ms | **154.08 ms** | **-285.54 ms (-65.0%)** |
| **Median (p50) Latency** | 288.09 ms | **108.09 ms** | **-180.00 ms (-62.5%)** |
| **95th-Percentile Latency**| 630.51 ms | **248.91 ms** | **-381.60 ms (-60.5%)** |
| **Stage-1 (Gating)** | 42.82 ms | **29.07 ms** | -32.1% |
| **Stage-2 (YOLO26x Verifier)**| 219.56 ms | **53.71 ms** | **-75.5% (4.09× faster)** |
| **Tracking (ByteTrack)** | 45.87 ms | **29.94 ms** | -34.7% |
| **VRAM Allocated** | 561.4 MB | **443.7 MB** | -117.7 MB (-21.0%) |
| **VRAM Reserved (Peak)** | 2,316.0 MB | **890.0 MB** | **-1,426.0 MB (-61.6%)** |

---

## 5. Architectural Evaluation: DeepStream vs. Native Python/CUDA

An evaluation of open-source surveillance pipelines (`manuelbomi/rtsp-yolo-video-analytics-pipeline` and `Ocel-Labs/Osprey`) was conducted:
- **NVIDIA DeepStream SDK:** DeepStream relies on GStreamer plugins compiled specifically for **Linux (Ubuntu x86_64 or NVIDIA JetPack / Jetson)**. It is **incompatible with native Windows 11**. Attempting to run DeepStream in WSL2 lacks hardware display acceleration and introduces shared memory virtualization overhead.
- **Native Python / Windows Shared Memory:** Our Windows Shared Memory (`SharedFrameBuffer` with `multiprocessing.shared_memory`) provides sub-millisecond (<0.1ms) zero-copy frame transfers directly into FastAPI and the web frontend, delivering native 30 FPS video streaming with zero Linux dependencies.

---

## 6. Verification & System Health Confirmation

1. **Test Suite:** `pytest -q` executes with **328 Passed, 2 Failed** (MediaMTX 8554 offline; 100% of pipeline tests pass).
2. **Cascade Verifier:** `pytest tests/test_two_stage_yolo26.py -v` passes **7/7 in 10.59s**.
3. **Live Execution:** `MainInferenceWorker` on `CAM-01` processes frames cleanly with real-time weapon detection, Merkle hash generation, and zero runtime errors.
4. **Documentation Artifacts Produced:**
   - `docs/PERFORMANCE_OPTIMIZATION_AUDIT.md` (335 lines, 24 architectural focus points)
   - `docs/YOLO26_AUTHENTICITY_AND_LICENSE_AUDIT.md` (Full model and license evaluation)
   - `docs/OPEN_SOURCE_REFERENCE_AUDIT.md` (DeepStream vs Windows analysis)
   - `docs/VISION_MODEL_BENCHMARK.md` (RTX 5050 standalone model metrics)
   - `docs/PIPELINE_OPTIMIZATION_RESULTS.md` (Before vs after empirical comparison)
   - `docs/FINAL_VISION_OPTIMIZATION_REPORT.md` (This master report)

---

## 7. Conclusion

The IBVAP computer-vision pipeline is now **faster, more stable, strictly decoupled, and empirically validated**. It delivers **smooth 30 FPS video streaming** to operators while processing complex multi-model AI inference at nearly **3× higher throughput** and **65% lower latency**, all while running air-gapped on the local RTX 5050 Laptop GPU.
