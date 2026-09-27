# IBVAP — Model License, Redistribution & Operational Matrix
**Intelligent Border Video Analytics Platform**  
*Document Version: 1.0.0 — SIH 2026 PS-26187 Compliance*

---

## 1. Executive Summary

In adherence to Rule 4, Rule 8, and Phase 6 directives, every artificial intelligence model evaluated, implemented, or integrated into the IBVAP platform must be cataloged with its exact origin, version, legal license, redistribution terms, commercial usage parameters, and edge hardware VRAM footprint.

---

## 2. Comprehensive Model Matrix

| Model Identifier | Source / Hub | Version | License | Redistribution Rights | Commercial Use Terms | Runtime & VRAM (FP16) | Integration Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **YOLOv8n (Primary)** | Ultralytics / GitHub | `v8.4.142` (3.2M params) | AGPL-3.0 / Commercial Enterprise | Copyleft under AGPL; requires source disclosure if distributed | Allowed under AGPL-3.0 terms or commercial enterprise license | PyTorch CUDA: 141 MB<br>TensorRT: **355 MB** | **VERIFIED & BENCHMARKED** (105.04 FPS on RTX 3050) |
| **ByteTrack (Tracker)** | YOLOX Authors / Apache | `v1.0.0` | **Apache 2.0** | Permissive; attribution required | Fully permitted for commercial and defense deployments | Minimal CPU RAM (~15 MB) | **VERIFIED** in pipeline (`services/tracking/`) |
| **NVIDIA PeopleNet** | NVIDIA NGC (`tao/peoplenet`) | `deployable_v2.6.1` (DetectNet_v2) | **NVIDIA AI Product / NGC License** | Free download from NGC; weights redistributable only on NVIDIA edge hardware | Permitted on NVIDIA hardware (RTX/Jetson); cannot resell standalone weights | TensorRT Engine: ~280 MB VRAM | **INTEGRATED (Adapter Ready)** (`NvidiaTaoAdapter`) |
| **NVIDIA TrafficCamNet** | NVIDIA NGC (`tao/trafficcamnet`) | `deployable_v1.0` (ResNet-18) | **NVIDIA AI Product / NGC License** | Free download from NGC; locked to NVIDIA CUDA runtime | Permitted on NVIDIA hardware for traffic and surveillance edge outposts | TensorRT Engine: ~240 MB VRAM | **INTEGRATED (Adapter Ready)** (`NvidiaTaoAdapter`) |
| **NVIDIA LPDNet** (Plate Detect) | NVIDIA NGC (`tao/lpdnet`) | `deployable_v1.0` | **NVIDIA AI Product / NGC License** | Free download from NGC | Permitted on NVIDIA platforms for automated gate/checkpoint security | TensorRT Engine: ~180 MB VRAM | **PLANNED** (Specialist ROI) |
| **NVIDIA LPRNet** (Plate OCR) | NVIDIA NGC (`tao/lprnet_usa`) | `deployable_v1.0` | **NVIDIA AI Product / NGC License** | Free download from NGC | Permitted on NVIDIA platforms | TensorRT Engine: ~140 MB VRAM | **PLANNED** (Specialist ROI) |
| **EasyOCR / CRNN** (Fallback ANPR) | JaidedAI / GitHub | `v1.7.1` | **Apache 2.0** | Permissive; full redistribution | Fully permitted for commercial and government use | PyTorch CPU/CUDA: ~250 MB VRAM | **VERIFIED** in `services/anpr/` |
| **OpenCV CLAHE / Low-Light** | OpenCV.org | `v5.0.0` | **Apache 2.0** | Permissive; zero restrictions | Fully permitted | Deterministic CPU math (~5 MB) | **VERIFIED** in `services/ingestion/` |
| **NVIDIA NIM LLM** (Copilot) | NVIDIA Cloud / integrate.api | `llama-3.2-11b-vision` | **Llama 3.2 Community License** | Cloud API call; zero local weight distribution | Free tier evaluation / enterprise consumption terms | Zero local VRAM (Cloud API) | **OPTIONAL ONLY** (`services/nvidia/`) |

---

## 3. Licensing & Compliance Guidelines

1. **Local Edge Autonomy**: Core detection (`YOLOv8n` / `TensorRT` / `ByteTrack` / `RuleEngine`) contains **zero cloud dependencies** and operates 100% offline.
2. **NVIDIA NGC Models**: TAO models (PeopleNet, TrafficCamNet) are compiled to TensorRT engines (`.engine`) and executed natively on the host's **NVIDIA GeForce RTX 3050 Laptop GPU**.
3. **No Unlicensed Research Code**: Non-commercial academic weights with restrictive licenses (e.g. CC-BY-NC 4.0) are strictly excluded from production builds.
4. **VRAM Budget Compliance**: Peak VRAM with YOLOv8n TensorRT (355 MB) + CUDA Context (180 MB) + Ring Buffer (120 MB) remains under **660 MB**, leaving > 3.4 GB headroom on the 4 GB GPU.
