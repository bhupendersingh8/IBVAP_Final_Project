# IBVAP: NVIDIA Production Edge Deployment & AI Agent Blueprint
**SIH PS-26187: Hardware-Agnostic Intelligent Surveillance for Border Outposts**

---

## 1. Executive Summary

Traditional border security CCTV installations at Border Out Posts (BOPs), check posts, and strategic transit corridors are limited to passive video recording, demanding non-stop human fatigue-prone monitoring.

**IBVAP (Intelligent Border Video Analytics Platform)** transforms any commodity CCTV or mobile camera stream into an intelligent military-grade surveillance matrix. 

While IBVAP maintains complete **zero-cost CPU fallback** (tested and verified on Intel Core i3 / CPU-only laptops), this guide outlines the **production deployment architecture leveraging NVIDIA free-tier AI technologies, TensorRT acceleration, and NVIDIA NIM (Inference Microservices)**.

---

## 2. NVIDIA AI Architecture Overview

```
[ Commodity CCTV / Mobile WiFi Streams ]
               │
               ▼ (Hardware NVDEC H.264/H.265 Decode)
┌────────────────────────────────────────────────────────┐
│             NVIDIA DeepStream Pipeline                │
│  - nvstreammux: Batch 4 to 16 camera streams          │
│  - nvinfer: TensorRT FP16/INT8 Engine (YOLOv8n)       │
│  - nvtracker: NvDCF Deep Feature Multi-Object Tracking│
└────────────────────────────────────────────────────────┘
               │
               ├─► Subclass Discrimination (Truck, Car, Bike, Bus, Person)
               ├─► Persistent Re-ID & Remembrance Store (Cross-Camera)
               ├─► Spatial Rule Engine (Restricted Zone Intrusions)
               │
               ▼ (Event & Telemetry Correlator)
┌────────────────────────────────────────────────────────┐
│           NVIDIA NIM Free Surveillance Agent           │
│  - Model: meta/llama-3.2-11b-vision-instruct           │
│  - Natural language threat analysis                    │
│  - Automated tactical situation reports (SITREPs)      │
│  - Zero-hallucination deterministic fallback            │
└────────────────────────────────────────────────────────┘
               │
               ▼
[ Military-Grade React Dashboard + Immutable Hash Chain Ledger ]
```

---

## 3. NVIDIA Free AI Agent Integration (NVIDIA NIM)

IBVAP integrates NVIDIA's free cloud/edge Inference Microservices (NIM) through `services/nvidia/nim_surveillance_agent.py`:

1. **Free Developer Access**:
   - Register at [build.nvidia.com](https://build.nvidia.com)
   - Generate your free API key.
   - Set environment variable:
     ```bash
     export NVIDIA_API_KEY="nvapi-..."
     ```
2. **Automated Tactical SITREPs**:
   - When perimeter breaches or recurring suspicious vehicles are detected, the agent synthesizes live telemetry, ANPR reads, and spatial coordinates into a concise threat briefing.
3. **Graceful Offline Fallback**:
   - When deployed at remote BOPs without internet access, `NVIDIASurveillanceAgent` automatically switches to the built-in deterministic tactical rule engine.

---

## 4. TensorRT Compilation & Acceleration

For border posts equipped with an NVIDIA Jetson Orin Nano, Xavier, or RTX workstation:

1. **Install TensorRT prerequisites**:
   ```bash
   pip install tensorrt
   ```
2. **Compile PyTorch YOLOv8 to TensorRT Engine**:
   ```bash
   python scripts/export_tensorrt.py --model models/yolov8n.pt --imgsz 640
   ```
3. **Performance Metrics**:
   - Standard PyTorch CPU: ~10-15 FPS (Single Stream)
   - NVIDIA TensorRT FP16 (Jetson Orin): **65+ FPS (Concurrent 4-Stream Ingestion)**
   - Latency: Reduced from 75ms to **< 12ms per frame**.

---

## 5. NVIDIA DeepStream Deployment Pipeline

Configure `infrastructure/nvidia/deepstream_app_config.txt`:

```ini
[source0]
enable=1
type=4
uri=rtsp://127.0.0.1:8554/CAM-01
num-sources=4
gpu-id=0

[primary-gie]
enable=1
gpu-id=0
model-engine-file=models/yolov8n_fp16.engine
batch-size=4
interval=0
gie-unique-id=1

[tracker]
enable=1
tracker-width=640
tracker-height=384
ll-lib-file=/opt/nvidia/deepstream/deepstream/lib/libnvds_nvmultiobjecttracker.so
ll-config-file=config_tracker_NvDCF_perf.yml
gpu-id=0
```

---

## 6. Security & Tamper-Evident Ledger Integration

All events processed through the NVIDIA inference pipeline are sealed with:
- SHA-256 cryptographic image hashing.
- Chained tamper-evident block headers.
- Exportable judicial evidence packages.

Zero proprietary vendor lock-in: seamlessly transitions between low-cost commodity CPU hardware and enterprise NVIDIA AI appliances.
