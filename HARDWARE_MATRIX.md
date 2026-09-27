# IBVAP HARDWARE COMPATIBILITY & DEPLOYMENT MATRIX
**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Host Target:** Dell Core i3-1115G4, 12GB RAM, Windows 11 (Current Development Machine)  
**Scope:** Edge Patrol Laptop to Sovereign Command Cluster  

---

## 1. Hardware Tiers Overview

IBVAP is designed with a **modular compute contract**. The same software codebase scales from single-core CPU laptops in remote border observation posts to multi-GPU high-availability military command centers.

```
TIER 1 (Dell Laptop CPU) ──► TIER 2 (RTX 3050 Field Unit) ──► TIER 3 (Jetson Embedded)
                                                                       │
TIER 5 (Sovereign Cloud HQ) ◄──────────────── TIER 4 (Sector HQ Multi-GPU)
```

---

## 2. Hardware Tier Specifications

### Tier 1: Host Edge Laptop (Current Dell Target)
- **Processor:** Intel Core i3-1115G4 (2 Cores, 4 Threads, 3.00 GHz base, 4.10 GHz boost)
- **Memory:** 12 GB DDR4 RAM
- **GPU:** Intel UHD Graphics (Integrated, Shared Memory)
- **Operating System:** Windows 11 Home 64-bit
- **Power Envelope:** 15W–28W TDP
- **Active Role:** Local CCTV simulation (`CAM-01`), built-in webcam capture (`WEBCAM-01`), CPU-first YOLOv8n detection, ByteTrack tracking, Haar face verification, SHA-256 evidence hashing, and local React dashboard.

### Tier 2: Tactical Mobile Patrol Unit
- **Processor:** Intel Core i7-12700H or AMD Ryzen 7 6800H (8–14 Cores)
- **Memory:** 16 GB to 32 GB DDR5 RAM
- **GPU:** NVIDIA GeForce RTX 3050 / RTX 4060 Laptop GPU (4 GB / 8 GB GDDR6)
- **Compute Stack:** CUDA 12.4, TensorRT 10.3 (FP16), cuDNN 9
- **Active Role:** 4 concurrent 1080p RTSP feeds, YOLOv8s at 120 FPS, FastSAM segmentation, AdaFace ArcFace recognition.

### Tier 3: Edge Embedded Forward Operating Base (FOB)
- **Compute Unit:** NVIDIA Jetson Orin Nano (8 GB) or Jetson Orin NX (16 GB)
- **AI Performance:** 40 to 100 TOPS INT8
- **Power Envelope:** 7W to 25W (Solar/Battery compatible)
- **Compute Stack:** JetPack 6.0, DeepStream 7.0, TensorRT, V4L2 hardware video decoder
- **Active Role:** Remote solar-powered perimeter fence mast; autonomous edge inference and intermittent satellite telemetry relay.

### Tier 4: Tactical Sector Command Server
- **Processor:** Dual AMD EPYC 7763 or Intel Xeon Gold 6338 (64 Cores)
- **Memory:** 128 GB to 256 GB ECC DDR4/DDR5
- **GPU:** 2x NVIDIA RTX 6000 Ada or 2x NVIDIA L40S (48 GB VRAM each)
- **Storage:** 16 TB NVMe RAID-10 for tamper-evident video evidence vaults
- **Active Role:** 32 concurrent 4K border streams, VideoMAE v2 video understanding, ViTPose++ sniper/crawling pose classification, multi-camera track handover.

### Tier 5: Central Sovereign Cloud Command (HQ)
- **Compute Cluster:** 8x NVIDIA A100 / H100 80GB SXM5 NVLink Node
- **Networking:** 400 Gbps InfiniBand
- **Active Role:** Qwen2.5-VL 72B strategic incident synthesis, Krutrim Sovereign LLM multi-lingual battleground reporting, nationwide intelligence correlation.

---

## 3. Model Deployment Allocation by Tier

| Model Category | Tier 1 (Dell i3 CPU) | Tier 2 (RTX 3050 Laptop) | Tier 3 (Jetson Orin) | Tier 4 (Sector HQ) | Tier 5 (Cloud Cluster) |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Primary Detection** | YOLOv8n (CPU) | YOLOv8s (TensorRT) | YOLOv8n (DeepStream) | D-FINE / RT-DETRv3 | Grounding DINO 1.5 Pro |
| **Segmentation** | Bounding Box Crop | FastSAM (FP16) | MobileSAM | EfficientSAM | SAM 2.1 Video Foundation |
| **Tracking** | ByteTrack (lapx) | BoT-SORT (GMC) | ByteTrack (C++) | Deep OC-SORT | MeMOTR Long-Term Memory |
| **Face & Identity** | Haar + 4-State | AdaFace IR100 | InsightFace | TransFace | XCloud Multi-View PTZ |
| **Restoration** | Adaptive CLAHE | Zero-DCE++ | SCI Enhancer | Retinexformer | DiffLL Diffusion |
| **Pose & Posture** | YOLOv8n-pose | RTMPose-s | RTMPose-m | ViTPose++ / MMPose | Sapiens 1B Foundation |
| **Anomaly Engine** | Heuristic Rules | PyOD Ensemble | MNAD Normality | Anomalib PatchCore | STAEformer Autoencoder |
| **Tactical Reasoner**| Rule Copilot | Florence-2 (INT8) | PaliGemma 2 (Edge) | Qwen2.5-VL 7B | Qwen2.5-VL 72B / Krutrim |
| **Evidence Ledger** | Local SQLite SHA256| Local SQLite SHA256| Signed Edge Vault | Distributed Ledger | Sovereign National Vault |
