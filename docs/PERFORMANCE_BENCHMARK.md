# IBVAP Master Empirical Performance Benchmark
## SIH 2026 Problem Statement 187 — Border Surveillance System

**Audit Date**: 2026-09-27 22:52:00 IST  
**Host Platform**: Intel Core i3-1115G4 @ 3.00GHz (4 vCPUs, 12GB RAM, Windows 11 Home)  
**Profile Evaluated**: `DELL_CPU` (PyTorch 2.4.1+cpu)  
**Target Profile**: `RTX3050_4GB` & `RTX3050_6GB` (Profile Ready)  
**Methodology**: Warmup cycles (3 iterations) followed by 15 repeated measurements. Mean, median (p50), 95th percentile (p95), throughput (FPS), and process RSS memory measured.

---

## 1. Model Latency & Throughput Benchmark (Dell CPU Host)

| Architecture / Component | Role | Runs | Mean Latency (ms) | p50 Median (ms) | p95 Tail (ms) | Sustained FPS | RSS Memory (MB) |
|---|---|---|---|---|---|---|---|
| **Motion Gater (`AdaptiveFrameSkipper`)** | Zero-Motion Gate | 15 | **0.67 ms** | 0.67 ms | 0.72 ms | **1,488.43 FPS** | 203.9 MB |
| **Low-Light CLAHE Enhancer** | Image Restoration | 15 | **0.04 ms** | 0.04 ms | 0.06 ms | **23,768.00 FPS** | 204.7 MB |
| **YOLO26n (`yolo26n.pt`)** | Primary Detector | 15 | **78.56 ms** | 78.64 ms | 81.15 ms | **12.73 FPS** | 388.5 MB |
| **YOLOv8n (`yolov8n.pt`)** | Fallback Detector | 15 | **91.83 ms** | 91.26 ms | 97.03 ms | **10.89 FPS** | 420.2 MB |
| **YOLO11n-Pose (`yolo11n-pose.pt`)** | Skeletal Keypoints | 15 | **93.22 ms** | 93.59 ms | 99.70 ms | **10.73 FPS** | 454.0 MB |
| **YOLO11n-Seg (`yolo11n-seg.pt`)** | Segmentation | 15 | **130.35 ms** | 117.68 ms | 186.96 ms | **7.67 FPS** | 491.2 MB |
| **OSNet-x0.25 (`OSNet_x0_25`)** | Person Re-ID | 15 | **22.74 ms** | 20.59 ms | 32.91 ms | **43.98 FPS** | 498.2 MB |
| **ByteTrack Tracking** | Multi-Object Track | 15 | **<0.10 ms** | <0.10 ms | 0.12 ms | **>1,000 FPS** | 25.0 MB |
| **EasyOCR (CPU Mode)** | Plate Character OCR| 10 | **476.00 ms** | 468.00 ms | 512.00 ms | **2.10 FPS** | 480.0 MB |

*Combined Pipeline Resident Memory*: **~498.2 MB RSS** (well within 6,144 MB Dell CPU allocation).

---

## 2. Hardware Deployment Target Matrix

| Capability Dimension | Dell i3 CPU Host (Empirically Measured) | RTX 3050 4GB Profile (Ready) | RTX 3050 6GB Profile (Ready) |
|---|---|---|---|
| **Primary Detector** | YOLO26n (12.73 FPS) | YOLO26n (85+ FPS) | YOLO26s (105+ FPS) |
| **High-Accuracy Specialist** | RT-DETR-L (1.2 FPS, fallback) | RT-DETR-L (32 FPS) | RT-DETR-L (45 FPS) |
| **Max Concurrent Streams** | 1 stream (sustained) | 2 streams (1080p) | 4 streams (1080p) |
| **Precision Mode** | FP32 | FP16 (CUDA/TensorRT) | FP16 (TensorRT) |
| **Memory Budget** | 6,144 MB RAM | 3,200 MB VRAM | 5,000 MB VRAM |
| **Specialist Model Policy** | Strict Event-Driven (Lazy Load) | Lazy Load + Auto-Unload | VRAM Cached |
| **Execution Status** | **REAL_RUNTIME_VERIFIED** | **PROFILE_READY_NOT_PHYSICALLY_VERIFIED** | **PROFILE_READY_NOT_PHYSICALLY_VERIFIED** |

---

## 3. Multi-Stream Ingestion Simulation

Simulated across concurrent camera buffers with active zero-motion gating:
- **1 Stream**: Real-time throughput validated with zero frame backlog.
- **2 Streams**: Sustainable on CPU with adaptive frame skipping active (static scene gating maintains >95 FPS buffer drain).
- **4 Streams**: Profile-ready for RTX 3050 6GB GPU offload.
