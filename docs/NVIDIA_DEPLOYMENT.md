# NVIDIA Deployment Architecture

> **Current Status: PLANNED**
> No NVIDIA GPU is available on the current development machine (Intel Core i3, CPU-only).
> This document describes the deployment architecture and roadmap for NVIDIA GPU acceleration.
> No GPU benchmarks are reported — all performance figures will be measured on actual hardware.

---

## Overview

IBVAP is architected for progressive GPU acceleration:

```
Current (CPU)          →  Near-term (ONNX/OpenVINO)  →  Production (NVIDIA)
────────────────────────────────────────────────────────────────────────────
YOLOv8n + CPU           YOLOv8n ONNX export           TensorRT engine
RTSPSource              Same ingestion                 NVIDIA DeepStream 9.1
OpenCV decode           OpenCV / NVDECODE              NVDEC hardware decode
FallbackIoUTracker      Same or improved               DeepStream NvTracker
~3-5 FPS (i3 CPU)       ~10-15 FPS (estimate)          60-120+ FPS (target)
```

---

## NVIDIA DeepStream 9.1

DeepStream is NVIDIA's production streaming analytics SDK. DeepStream 9.1 provides:
- Hardware-accelerated video decode (NVDEC)
- Batched multi-stream inference (TensorRT)
- Multi-camera 3D tracking
- Camera calibration agentic skills
- Low-latency pipeline (GStreamer-based)
- Jetson + discrete GPU support

**IBVAP integration point:** Replace `RTSPSource + YOLOAdapter + FallbackIoUTracker`
with a DeepStream pipeline while keeping `RuleEngine`, `EventCorrelator`, `HashChainLedger`,
and `FastAPI` unchanged.

### DeepStream Pipeline Architecture (Target)

```
IP CCTV streams (N cameras)
        ↓
    NVIDIA NvUriSrcBin  (hardware RTSP decode / NVDEC)
        ↓
    NvStreammux         (batch N streams into one tensor)
        ↓
    NvInfer             (TensorRT engine — custom IBVAP model)
        ↓
    NvTracker           (multi-object tracking, multi-camera)
        ↓
    Python probe / IBVAP RuleEngine
        ↓
    EventCorrelator → Evidence → FastAPI → Dashboard
```

---

## NVIDIA TAO (Train, Adapt, Optimize)

TAO provides pretrained backbone models that can be fine-tuned for custom domains:
- **DetectNet_v2** / **YOLO-family** for object detection
- Fine-tuning on IBVAP border surveillance dataset
- Export to `.etlt` → TensorRT engine

**Workflow:**
```
IBVAP Dataset (ml/datasets/)
        ↓
TAO DetectNet_v2 fine-tuning  [requires NVIDIA GPU]
        ↓
Evaluation on held-out test set (ml/evaluation/)
        ↓
Export to ONNX / TensorRT engine
        ↓
Deploy via DeepStream NvInfer
```

---

## Model Conversion Flow

```
YOLOv8n (PyTorch .pt)
        ↓  ultralytics export format=onnx
YOLOv8n.onnx
        ↓  trtexec --onnx=model.onnx --saveEngine=model.trt [requires NVIDIA GPU]
model.trt  (TensorRT engine — FP16 or INT8)
        ↓  NvInfer in DeepStream pipeline
```

---

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | NVIDIA T4 / RTX 3060 | NVIDIA A30 / RTX 4090 |
| VRAM | 8 GB | 24 GB |
| CPU | Intel Xeon / Ryzen 7 | Intel Xeon Gold |
| RAM | 32 GB | 64 GB |
| Storage | 500 GB NVMe | 2 TB NVMe RAID |
| OS | Ubuntu 20.04 LTS | Ubuntu 22.04 LTS |
| Driver | NVIDIA ≥ 525 | NVIDIA ≥ 535 |
| CUDA | 11.8+ | 12.x |
| DeepStream | 9.1 | 9.1 |

**Edge / Jetson:**
- NVIDIA Jetson AGX Orin (64 GB) — primary edge target
- NVIDIA Jetson Orin NX (16 GB) — secondary edge target
- JetPack 6.x with DeepStream 9.1 Jetson edition

---

## Multi-Camera Architecture at Scale

```
                    ┌─────────────────────────────┐
                    │    DeepStream Node          │
                    │  (NVIDIA GPU Server)        │
  Camera 1 ────────►│                             │
  Camera 2 ────────►│  NvStreammux (batch)         │───► IBVAP RuleEngine
  Camera 3 ────────►│  NvInfer    (TensorRT)      │───► EventCorrelator
  Camera N ────────►│  NvTracker  (multi-cam)     │───► FastAPI (:8000)
                    │                             │
                    └─────────────────────────────┘
```

Expected capacity (unvalidated estimates, require actual benchmark):
- T4 GPU: ~16-32 cameras at 1080p 15fps (per NVIDIA reference)
- A30 GPU: ~64+ cameras

---

## Deployment Checklist (When GPU Hardware Available)

- [ ] Install Ubuntu 22.04 LTS on GPU server
- [ ] Install NVIDIA Driver ≥ 535
- [ ] Install CUDA 12.x
- [ ] Install DeepStream 9.1
- [ ] Convert YOLOv8n.pt → ONNX → TensorRT engine (`trtexec`)
- [ ] Configure DeepStream config (see `deployment/nvidia/deepstream_config_template.txt`)
- [ ] Run DeepStream pipeline validation
- [ ] Benchmark: FPS, latency, memory usage per camera count
- [ ] Integrate DeepStream output with IBVAP RuleEngine via Python probe
- [ ] Validate 54/54 regression tests on GPU-deployed system
- [ ] Document actual GPU benchmark results in `docs/PERFORMANCE_BENCHMARK.md`

---

## Benchmark Methodology (To be executed on real hardware)

When GPU hardware is available, measure:

| Metric | Tool | Condition |
|--------|------|-----------|
| Inference FPS | DeepStream perf_demo | 1/4/8/16 cameras |
| End-to-end latency | Event timestamp delta | Frame capture → alert |
| GPU utilization | nvidia-smi | Sustained load |
| VRAM usage | nvidia-smi | Peak load |
| CPU overhead | htop | During inference |
| Alert latency | WebSocket timestamp | Detection → dashboard |

**DO NOT report benchmark numbers without running this methodology on actual hardware.**

---

## Current CPU Baseline (Verified)

| Metric | Value | Condition |
|--------|-------|-----------|
| Inference FPS | ~3-5 fps | Intel Core i3, YOLOv8n, 640px |
| Latency | variable | CPU-bound |
| Cameras | 2 (CAM-01 + PHONE-CAM-01) | Sequential processing |

*CPU-only operation is the production fallback for edge deployments without GPU.*
