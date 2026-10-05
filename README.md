# TRINETRA / IBVAP — Trusted Computer Vision Integrity & Assurance Platform
**Smart India Hackathon 2026 — Problem Statement ID: SIH26228**  
**Theme**: Blockchain & Cybersecurity | **Organization**: Ministry of Defence / Indian Army DGIS  
**Reference Operational Workload**: Tactical Border Surveillance Platform (SIH26187 Reference Pipeline)

---

## 1. Project Purpose & Scope

Modern defence and edge video intelligence pipelines rely on deep learning models and multi-contributor datasets that are vulnerable to data poisoning, unauthorized weight substitution, configuration alteration, and output/telemetry manipulation.

**TRINETRA (IBVAP)** is an air-gapped, zero-cloud Computer Vision Integrity and Assurance Platform designed to mathematically enforce end-to-end chain-of-custody across the computer vision lifecycle:
- **Data Integrity**: Cryptographic commitment and spatial/geometric sanity checking for training and validation datasets.
- **Model Integrity**: Checkpoint verification against cryptographic digests, CycloneDX 1.5 AIBOM generation, and behavioral probe fingerprinting.
- **Inference Provenance**: Deterministic output canonicalization, sub-millisecond recursive Merkle hash chaining, and replay defense.
- **Operational Reference**: Deployed over a real, high-throughput tactical border surveillance sentry pipeline (multi-camera RTSP ingestion, low-light neural restoration, vehicle ANPR, and biometric verification).

---

## 2. Core Assurance Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TRINETRA ASSURANCE LAYERS                       │
└────────────────────────────────────────────────────────────────────────┘

  [ 1. Ingestion & Preprocessing ]
    RTSP / MediaMTX / Camera Stream ──► Rolling Ring Buffer (8s RAM Window)
                                    └──► Zero-DCE++ / Adaptive CLAHE Low-Light Gating

  [ 2. Primary Detection & Tracking ]
    YOLO11n / YOLOv8n (FP16 CUDA) ──► ByteTrack Multi-Object Tracker

  [ 3. Cascade Verifier & Specialists ]
    Two-Stage YOLO26x Verifier (Uncertain Conf 0.25-0.65)
    MobileSAM (Crawling/Camouflage) | ArcFace (FRS) | EasyOCR (ANPR) | Threat YOLO (Weapons)

  [ 4. SIH26228 Cryptographic Assurance Engine ]
    ├── Tactical Schema Remapping (services/tactical_mapper.py)
    ├── Output Canonicalization (Deterministic sort & 4-decimal bounding box normalization)
    ├── Anomaly / Tamper Detection (Inverted coords, out-of-bounds, invalid confidences)
    └── Recursive Merkle Hash Chaining:
          H_n = SHA256( H_{n-1} || FrameBytesHash || WeightHash || OutputDigest || Timestamp || Nonce )

  [ 5. Automated Governance Gate ]
    Evaluates evidence integrity and issues automated verdict:
    [ACCEPT] ──► Verified authentic frame and inference
    [REVIEW] ──► Distribution shift or borderline bounding box anomaly
    [QUARANTINE] ──► Hash mismatch, inverted geometry, weight swap, or replay detected

  [ 6. Evidence Archival & Real-Time Dispatch ]
    ├── DuckDB / SQLite Cryptographic Audit Ledger (crypto_ledger.py)
    ├── Automated 8-Second Forensic MP4 Harvesting ([t-5s, t+3s] on perimeter breach)
    ├── FastAPI Backend (Port 8000) & Non-blocking WebSocket (/ws/alerts)
    └── React Operations Dashboard (Port 5173: C4ISR Console & IntegrityPanel)
```

---

## 3. The Four Assurance Pillars (SIH26228)

### Pillar 1: Data Integrity
- **Exact & Near-Duplicate Detection**: Bit-exact SHA-256 deduplication and perceptual average hashing (aHash / dHash) to identify dataset contamination.
- **Annotation Geometry Auditing**: Automated validation of YOLO bounding boxes against inverted coordinates ($x_1 \ge x_2$), negative values, and out-of-bounds coordinates ($> 1.05$).
- **Dataset Commitment**: Hierarchical SHA-256 Merkle root calculation binding training datasets (`data_integrity.py`).

### Pillar 2: Model Supply-Chain Integrity
- **Cryptographic Checkpoint Binding**: Compares physical weights against expected SHA-256 checksums before loading into memory.
- **Signed Contributor Manifests**: Ed25519-signed contributor model manifests attributing supplier identity.
- **CycloneDX 1.5 AIBOM**: Machine-readable AI Software Bill of Materials (`services/assurance/aibom.py`).
- **Behavioral Fingerprinting**: Standardized probe inputs validating baseline output tensors before deployment.

### Pillar 3: Inference Provenance & Output Integrity
- **Deterministic Canonicalization**: Normalizes detection outputs into deterministically sorted JSON strings before hashing.
- **Recursive Merkle Chain**: Every processed frame produces an immutable block linking the previous block hash ($H_{n-1}$), raw frame hash, model weight hash, output detections digest, timestamp, and a cryptographic nonce.
- **Replay Protection**: Nonce verification, monotonic sequence enforcement, and timestamp freshness validation prevent replay attacks.

### Pillar 4: Distribution-Shift & Operational Assurance
- **Photometric Gating**: Real-time luminance monitoring dynamically activates Zero-DCE++ or Adaptive CLAHE when illumination drops below 40 lux.
- **Statistical Drift Monitoring**: Two-sample Kolmogorov-Smirnov (KS) test monitoring feature distribution shifts over sliding windows.
- **Automated Governance Decisions**:
  - `ACCEPT`: Fully verified frame, model checksum, and canonical output.
  - `REVIEW`: Minor distribution drift, marginal lighting, or low-confidence anomaly.
  - `QUARANTINE`: Cryptographic hash mismatch, inverted coordinates, unauthorized model substitution, or duplicate nonces.

---

## 4. Model & Component Taxonomy

| Component / Model | Purpose / Role | Implementation File | Status |
| :--- | :--- | :--- | :--- |
| **YOLO11n** | Primary 2D object detection (COCO 80 classes) | `weights/yolo11n.pt` (5.6 MB) | **ACTIVE** (Default continuous detector) |
| **YOLO26x Verifier** | Heavy cascade verifier (56.9M params) | `weights/yolo26x.pt` (118.6 MB) | **ACTIVE** (Gated on uncertain tracks) |
| **YOLO26n** | Stage-1 fast gating detector | `weights/yolo26n.pt` (5.5 MB) | **ACTIVE** (Two-stage cascade stack) |
| **YOLOv8n** | Lightweight baseline & zero-crash fallback | `yolov8n.pt` / `models/yolov8n.pt` | **ACTIVE** (Fallback detector) |
| **Threat YOLOv8n** | Dedicated firearm, weapon & explosive detector | `models/threat_yolov8n.pt` (6.5 MB) | **ACTIVE** (Gated specialist) |
| **MobileSAM** | Silhouette extraction on crawling/camouflaged targets | `weights/mobile_sam.pt` (40.7 MB) | **ACTIVE** (Event-triggered specialist) |
| **ArcFace-512D** | Facial biometric feature extractor (sub-12ms) | `weights/arcface_w600k_r50.onnx` (174.3 MB) | **ACTIVE** (Asynchronous background worker) |
| **EasyOCR** | Vehicle license plate recognition (CRAFT + CTC) | `.cache/.EasyOCR/model/` (98 MB) | **ACTIVE** (Asynchronous background worker) |
| **Zero-DCE++** | Deep dynamic curve estimation for low-light restoration | `ml/models/zero_dce.py` (PyTorch) | **ACTIVE** (Triggered when lux < 40) |
| **ByteTrack** | Multi-object association and trajectory tracking | `services/tracking/bytetrack_adapter.py` | **ACTIVE** (Core multi-target tracker) |
| **RT-DETR-L** | Real-time Transformer detector (Apache-2.0) | `weights/rtdetr-l.pt` (66.5 MB) | **OPTIONAL** (Selectable via `--model rtdetr-l`) |
| **YOLOv8n-Pose** | 17-keypoint human skeleton pose & EAR blink liveness | `models/pose/yolov8n-pose.pt` (6.8 MB) | **OPTIONAL** (Used in `personnel_manager.py`) |
| **FastSAM-s** | Fast CNN instance segmentation alternative | `models/segmentation/FastSAM-s.pt` | **EXPERIMENTAL / UNWIRED** |
| **MiDaS v2.1 Small** | Monocular relative depth estimation | `models/depth/midas_v21_small.pt` | **EXPERIMENTAL / UNWIRED** |
| **YOLOv10n / YOLOv8n-Seg** | NMS-free detection / YOLOv8 segmentation | `models/detection/` & `models/segmentation/`| **EXPERIMENTAL / UNWIRED** |
| **Post-Quantum Cryptography** | WOTS+ one-time signatures & SHAKE-256 commitments | `services/assurance/post_quantum.py` | **EXPERIMENTAL** (Algorithmic reference) |

---

## 5. Model Weights & Large Binaries (Downloadable Weights Architecture)

In accordance with edge deployment best practices, **large model weights and compiled binaries are intentionally excluded from normal Git history**. They are preserved locally on the edge host machine (`weights/`, `models/`, and `infrastructure/`) to ensure fast cloning times and prevent repository bloat.

- **Offline / Local Guarantee**: The operational pipeline remains completely unchanged. Once staged locally, all models run 100% offline with zero external network calls.
- **Acquisition Mechanism**: Model weights can be inspected, verified, or acquired using the included project utility:
  ```powershell
  python download_weights_and_datasets.py
  ```
  *(Downloads official upstream release checkpoints directly to `./weights/` or stages local fallback copies).*
- **Release Assets**: The project structure is prepared to support packaging these verified checkpoints as GitHub Release assets if hosted on an enterprise remote.

### Model Weights Registry & Verification

| Model | Purpose | Local Path | Required | Acquisition / Source |
| :--- | :--- | :--- | :---: | :--- |
| **YOLO11n** | Primary 2D Object Detection | `weights/yolo11n.pt` | **YES** | `python download_weights_and_datasets.py` (Ultralytics v8.3.0) |
| **YOLO26x** | Two-Stage Cascade Verifier | `weights/yolo26x.pt` | **YES** | `python download_weights_and_datasets.py` (Ultralytics v8.3.0) |
| **YOLO26n** | Two-Stage Fast Gating | `weights/yolo26n.pt` | **YES** | `python download_weights_and_datasets.py` (Ultralytics v8.3.0) |
| **Threat YOLOv8n** | Armed Weapon / Explosive Classifier | `models/threat_yolov8n.pt` | **YES** | Local Host / Project Maintainer Setup |
| **MobileSAM** | Silhouette & Camouflage Segmenter | `weights/mobile_sam.pt` | **YES** | `python download_weights_and_datasets.py` (ChaoningZhang/MobileSAM) |
| **ArcFace-512D** | Facial Biometric Embeddings (FRS) | `weights/arcface_w600k_r50.onnx` | **YES** | `python download_weights_and_datasets.py` (InsightFace Buffalo_L) |
| **EasyOCR** | Vehicle License Plate Recognition | `.cache/.EasyOCR/model/` | **YES** | Pre-cached locally / PyTorch Hub CRAFT+CTC |
| **Zero-DCE++** | Low-Light Neural Curve Estimation | `ml/models/zero_dce.py` | **YES** | Procedural PyTorch Architecture (Zero download needed) |
| **RT-DETR-L** | Real-Time Transformer Alternative | `weights/rtdetr-l.pt` | *Optional* | `python download_weights_and_datasets.py` (Ultralytics v8.3.0) |
| **YOLOv8n-Pose** | Skeleton Keypoint & Liveness (EAR) | `models/pose/yolov8n-pose.pt`| *Optional* | `scripts/download_all_weights.py` (Ultralytics v8.2.0) |
| **MiDaS v2.1** | Relative Monocular Depth | `models/depth/midas_v21_small.pt` | *Optional* | Download source must be configured by maintainer |
| **MediaMTX** | RTSP / WebRTC Stream Server | `infrastructure/mediamtx/mediamtx.exe` | **YES** | Pre-compiled edge binary / bluenviron/mediamtx release |

## 6. Benchmark Evidence & Validation

> [!NOTE]
> All benchmarks were measured under controlled, reproducible conditions logged in `docs/BENCHMARK_EVIDENCE.md` and machine-readable JSON logs (`benchmarks/results/latest.json`, `fault_injection_latest.json`).

### Test Environment
- **Host**: Intel Core i7-13650HX (16 Cores, 24 Threads), 16 GB RAM
- **GPU**: NVIDIA GeForce RTX 5050 / RTX 3050 Laptop GPU (CUDA 12.8, Driver 572.16)
- **Input**: 640×640 Synthetic RGB Surveillance Streams

### Verified Throughput & Overhead
- **Raw Baseline Pipeline** (YOLO11n + ByteTrack without assurance): **66.92 FPS** (14.94 ms mean latency)
- **Secured Assurance Pipeline** (YOLO11n + ByteTrack + Canonicalization + Merkle Hashing + SQLite Persistence): **53.69 FPS** (18.13 ms mean latency)
- **Computational Hashing Overhead**: **0.562 ms** per frame (active CPU provenance hashing)
- **Total Pipeline Overhead**: **+3.19 ms** (+21.36%), predominantly driven by disk I/O during ledger commits. Non-breaching background frames bypass disk writes, maintaining >60 FPS.

### Controlled Fault-Injection Battery (17 / 17 Passed)
Evaluated via `benchmarks/run_fault_injection.py` across 17 distinct attack vectors:
- Pixel / frame byte substitution: **FLAGGED TAMPERED** (`QUARANTINE`)
- Model weight substitution / unauthorized swap: **FLAGGED TAMPERED** (`QUARANTINE`)
- Preprocessing / resolution alteration: **FLAGGED TAMPERED** (`QUARANTINE`)
- Inference configuration / threshold alteration: **FLAGGED TAMPERED** (`QUARANTINE`)
- Bounding box geometry manipulation: **FLAGGED TAMPERED** (`QUARANTINE`)
- Detection class / confidence manipulation: **FLAGGED TAMPERED** (`QUARANTINE`)
- Timestamp / Sequence ID manipulation: **FLAGGED TAMPERED** (`QUARANTINE`)
- Nonce reuse / Replay injection: **FLAGGED REPLAY_DETECTED** (`QUARANTINE`)
- Chain linkage breaks: **FLAGGED CHAIN_BROKEN** (`QUARANTINE`)
- Valid authentic record: **FLAGGED VERIFIED** (`ACCEPT`)

---

## 7. Installation & Quick Start

### Prerequisites
- Windows 10/11 or Ubuntu 22.04 LTS
- Python 3.11 (64-bit)
- Node.js 18+ and npm (for frontend UI)
- NVIDIA GPU with CUDA 12.x support (CPU fallback fully supported)

### 1-Click Launch (NVIDIA RTX 3050 / Windows 11)
```powershell
# Run the complete production stack (MediaMTX + Backend + Frontend)
.\start_ibvap_rtx3050.bat
```

### Manual Service Launch

#### 1. Setup / Verify Local Model Weights (If Running Fresh)
```powershell
python download_weights_and_datasets.py
```

#### 2. Start RTSP Ingestion Server (MediaMTX)
```powershell
infrastructure\mediamtx\mediamtx.exe infrastructure\mediamtx\mediamtx.yml
```

#### 3. Start FastAPI Accelerated Backend
```powershell
# Activate Python 3.11 virtual environment
.\venv_rtx\Scripts\Activate.ps1

# Launch backend API on port 8000
python -m uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000
```

#### 4. Start Live Inference Worker
```powershell
# Runs primary YOLO11n + ByteTrack + Assurance Engine
python services\inference\main_inference_worker.py --camera CAM-01 --rtsp rtsp://127.0.0.1:8554/CAM-01
```

#### 5. Launch React Operations Dashboard
```powershell
cd apps\frontend
npm run dev
# Open http://localhost:5173 in browser
```

---

## 8. Known Boundaries & Limitations

1. **Controlled Battery Scope**: The 17/17 fault detection rate represents validation against a synthetic mutation test harness with specified attack vectors; it is not an empirical guarantee against uncharacterized zero-day adversarial attacks.
2. **Relative Monocular Depth**: While `midas_v21_small.pt` is present, it generates relative topological depth maps; physical ground-truth distance in meters requires a calibrated camera intrinsic matrix.
3. **Local Administrative Tamper Boundary**: Sequential Merkle chaining provides mathematical *tamper evidence*, not physical OS-level *tamper prevention*. If an attacker has local OS root privileges, exported Section 65B hash certificates verify external discrepancies.
4. **Air-Gapped Operation**: The system does not contact external cloud APIs or licensing servers at runtime; all models and dependencies must remain locally cached.
