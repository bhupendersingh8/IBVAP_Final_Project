# IBVAP — Comprehensive Third-Party Software & Model License Manifest
**Project:** Intelligent Border Video Analytics Platform (IBVAP)  
**SIH Problem Statement:** PS-26187  
**Audit Standard:** Strict IP, Commercial Viability, and Dual-Use Defense Governance  
**Date:** September 2026  

---

## 1. Compliance Classification Taxonomy

Every software package, machine learning framework, model weight checkpoint, and dataset incorporated into or evaluated by IBVAP is assigned an explicit compliance status:

1. **`APPROVED`**: Permissive license (e.g. Apache 2.0, MIT, BSD-3, BSD-2) or approved commercial distribution rights. No restrictive copyleft or non-commercial research clauses. Safe for both open research and sovereign border deployment.
2. **`REVIEW_REQUIRED`**: Copyleft (e.g. AGPL-3.0, GPLv3) or dual-license models. Permitted in open-source hackathons and academic validation; requires commercial licensing or source disclosure for closed-source proprietary distribution.
3. **`REJECTED`**: Restrictive non-commercial licenses (e.g. CC-BY-NC 4.0, academic research-only agreements, proprietary unverified binary blobs). **Strictly excluded from production runtime.**

---

## 2. Core System & Infrastructure Libraries

| Component | Upstream Vendor / Maintainer | Version | Software License | Compliance Status | Operational & Redistribution Terms |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **MediaMTX** | AlertAvert / bluenviron | 1.20.1 | **MIT** | `APPROVED` | Permissive. Zero copyleft. Full binary redistribution permitted. |
| **FFmpeg (Core)** | FFmpeg Team | 7.x / 9.x | **LGPL-2.1+** | `APPROVED` | Dynamic linking permitted without source disclosure of parent application. |
| **FFmpeg (Gyan Full)** | Gyan.dev | 9.0.1 | **GPLv3** | `REVIEW_REQUIRED` | Contains x264/x265 GPL plugins. Suitable for SIH demo; switch to pure LGPL build for commercial binary distribution. |
| **FastAPI** | Sebastián Ramírez (tiangolo) | 0.139.2 | **MIT** | `APPROVED` | Permissive backend API framework. |
| **Uvicorn** | Encode Team | 0.51.0 | **BSD-3-Clause** | `APPROVED` | Permissive ASGI server. |
| **WebSockets** | Aymeric Augustin | 17.1 | **BSD-3-Clause** | `APPROVED` | Permissive real-time WebSocket protocol library. |
| **SQLAlchemy** | Mike Bayer | 2.0.52 | **MIT** | `APPROVED` | Permissive database ORM. |
| **PyTorch** | Linux Foundation / PyTorch | 2.14.0 | **BSD-3-Clause** | `APPROVED` | Permissive scientific tensor library. |
| **Torchvision** | PyTorch Foundation | 0.29.0 | **BSD-3-Clause** | `APPROVED` | Permissive computer vision vision utilities. |
| **OpenCV** | OpenCV Foundation | 4.10+ / 5.0 | **Apache-2.0** | `APPROVED` | Permissive computer vision and image math. |
| **NumPy** | NumPy Developers | 2.x | **BSD-3-Clause** | `APPROVED` | Permissive numerical array engine. |
| **Shapely** | GEOS / Toblerity | 2.1.2 | **BSD-3-Clause** | `APPROVED` | Permissive planar geometry and polygon calculations. |
| **Pydantic** | Samuel Colvin | 2.10+ | **MIT** | `APPROVED` | Permissive data validation and schema serialization. |
| **React** | Meta Platforms, Inc. | 18.3.1 | **MIT** | `APPROVED` | Permissive frontend user interface framework. |
| **Vite** | Evan You | 5.4.21 | **MIT** | `APPROVED` | Permissive frontend bundling engine. |
| **TailwindCSS** | Tailwind Labs | 3.4.17 | **MIT** | `APPROVED` | Permissive CSS utility framework. |

---

## 3. Artificial Intelligence Models & Checkpoints Matrix

| Model Identifier | Primary Task | Model Code License | Checkpoint / Weights License | Compliance Status | Redistribution & Governance Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **YOLOv8n / YOLO26n** | Primary 2D Detection | **AGPL-3.0** | AGPL-3.0 / Ultralytics Commercial | `REVIEW_REQUIRED` | Allowed for SIH and open research. Commercial edge delivery requires Ultralytics commercial OEM license. |
| **RF-DETR-L** | Benchmark Candidate Detector | **Apache-2.0** | Apache-2.0 | `APPROVED` | Permissive Apache-2.0 license. Validated candidate for open border deployment. |
| **ByteTrack** | Multi-Object Tracking | **Apache-2.0** | Apache-2.0 | `APPROVED` | Fully permissive. Zero copyleft. Core production tracking algorithm. |
| **OSNet-x0.25** | Person Re-Identification | **MIT** | MIT / BSD | `APPROVED` | Torchreid ultra-lightweight Re-ID architecture. Permissive edge model. |
| **RT-DETR-R18-Seg** | Event-Triggered Segmentation | **Apache-2.0** | Apache-2.0 | `APPROVED` | Open-source real-time transformer segmentation. Fully redistributable. |
| **EasyOCR (CRNN)** | ANPR Character Reading | **Apache-2.0** | Apache-2.0 | `APPROVED` | Permissive character recognition. Production baseline. |
| **PaddleOCR** | Multi-Language ANPR | **Apache-2.0** | Apache-2.0 | `APPROVED` | Permissive Apache-2.0 license. Clean commercial use. |
| **RTMPose / YOLOv8n-Pose** | Posture & Threat Pose | **Apache-2.0 / AGPL-3.0** | Apache-2.0 / AGPL | `APPROVED` / `REVIEW_REQUIRED` | Event-triggered keypoint estimation. |
| **Depth Anything 3 / v2** | Relative Monocular Depth | **Apache-2.0** | Apache-2.0 | `APPROVED` | Event-triggered spatial reasoning. Relative depth only. |
| **NVIDIA PeopleNet** | Specialized Human Detector | **NVIDIA AI Product** | NVIDIA NGC Terms | `APPROVED` (NVIDIA Only) | Free download from NGC; redistributable on NVIDIA edge platforms (RTX 3050 / Jetson). |
| **NVIDIA TrafficCamNet**| Specialized Vehicle Detector | **NVIDIA AI Product** | NVIDIA NGC Terms | `APPROVED` (NVIDIA Only) | Free download from NGC; locked to CUDA runtime. |
| **Non-commercial Academic Models (CC-BY-NC 4.0)** | Various Research Models | Various | **CC-BY-NC 4.0** | `REJECTED` | **Prohibited from IBVAP.** Any model under non-commercial restrictions is excluded to ensure production viability. |

---

## 4. Licensing Action Items & Verification Protocol

1. **Dual-License Detector Agility**: By wrapping primary detection behind the `DetectorBackend` abstraction, the platform can seamlessly run under `Apache-2.0` (RF-DETR-L) or `AGPL-3.0` (YOLOv8) via configuration without rewriting application code.
2. **Offline Weight Bundling**: All approved production weights (`yolo26n.pt`, `yolov8n-pose.pt`, `threat_yolov8n.pt`, `haarcascade_frontalface_default.xml`) are bundled locally within the project repository to guarantee 100% offline self-containment.
3. **Automated License Gate in CI/CD**: Staged dependencies are audited during git pre-commit to reject dependencies containing non-commercial or unlicensed clauses.
