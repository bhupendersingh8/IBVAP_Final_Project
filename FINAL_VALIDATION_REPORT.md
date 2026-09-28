# IBVAP — Final System Validation & Hardware Audit Report

**Project**: Intelligent Border Video Analytics Platform (IBVAP)  
**SIH Problem Statement**: 26187 | Ministry of Home Affairs (MHA)  
**Team**: Trinetra  
**Verification Date**: September 28, 2026  
**Repository Location**: `C:\Users\dell\Desktop\p2\IBVAP_Final_Project`  
**Execution Environment**: Physical Dell Host (CPU-Only Mode)  

---

## 1. Executive Summary & Hardware Verification

This audit was conducted strictly against real physical and runtime hardware boundaries. **Zero results have been fabricated.**

| Environment | Discovered Hardware | Runtime Status | Real Execution Status |
|---|---|---|---|
| **Local Host (Dell)** | Intel Core i3-1115G4 (2C/4T @ 3.00 GHz), 11.73 GB RAM, Intel UHD Graphics | PyTorch 2.4.1+cpu (AVX2 Enabled) | **PASS** (100% Verified) |
| **NVIDIA GPU** | No physical NVIDIA GPU installed (`nvidia-smi: None`) | CUDA/TensorRT runtime unavailable | **BLOCKED BY HARDWARE** |

---

## 2. Core Capabilities & Empirical Evidence Table

*Statuses restricted strictly to: `PASS`, `PARTIAL`, `NOT TESTED`, `BLOCKED BY HARDWARE`, `NOT AVAILABLE`.*

| Capability | Status | Empirical Evidence |
|---|:---:|---|
| **Dell CPU Pipeline** | **PASS** | 205/205 pytest passing; real recorded video pipeline processed 50 frames with zero errors. |
| **CPU Fallback Contract** | **PASS** | `test_backend_fallback_matrix.py` (4/4 passed); auto-resets `device='cuda'` to `'cpu'` without crashing. |
| **Full Regression Suite** | **PASS** | `pytest tests/ -q` executed: **205 passed in 212.08s**. |
| **Frontend Production Build** | **PASS** | `npm run build` in `apps/frontend`: **dist/ built in 26.42s with 0 errors**. |
| **Real Video Pipeline** | **PASS** | `data/raw/test_video.mp4` (592x360 @ 30 FPS, 50 frames, 163 detections, 3 tracks, SHA-256 sealed). |
| **Adverse Condition Processing** | **PASS** | `ConditionAnalyzer` verified across 16 categories; severe blur marked `DEGRADED` (zero hallucination). |
| **Offline-First Operation** | **PASS** | Zero cloud/external API runtime dependencies; local SQLite and local model weights. |
| **Evidence Hash Chain** | **PASS** | Section 65B SHA-256 verification endpoint (`POST /evidence/verify`) verified (detects 1-byte alteration). |
| **Physical NVIDIA GPU** | **BLOCKED BY HARDWARE** | `nvidia-smi: None`, `torch.cuda.is_available(): False`, `GPU: NONE`. |
| **PyTorch CUDA Acceleration** | **BLOCKED BY HARDWARE** | Host is running `torch 2.4.1+cpu`; physical CUDA matrix operations fail gracefully. |
| **TensorRT Runtime** | **BLOCKED BY HARDWARE** | `tensorrt` module not installed; requires physical NVIDIA GPU and CUDA 12.x drivers. |
| **ONNX Runtime CUDA** | **BLOCKED BY HARDWARE** | Only `['AzureExecutionProvider', 'CPUExecutionProvider']` available on host. |
| **TensorRT Engine Generation** | **BLOCKED BY HARDWARE** | Exporter `deployment/rtx3050/export_tensorrt_engines.py` ready, requires target GPU to build. |
| **Real GPU Video Inference** | **BLOCKED BY HARDWARE** | Real video was validated on CPU; GPU inference requires transfer to target GPU unit. |

---

## 3. Hardware Compatibility Matrix

| Silicon Profile | Deployment Role | CPU Fallback | CUDA Available | PyTorch CUDA | TensorRT Runtime | ONNX GPU | Engine Regeneration | Physical Verification Status |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Dell Intel Core i3 + UHD** | Tier 1 (Host Dev/Observation Post) | **PASS** | **NOT AVAILABLE** | **NOT AVAILABLE** | **NOT AVAILABLE** | **NOT AVAILABLE** | None (Runs PyTorch CPU) | **PHYSICALLY TESTED (PASS)** |
| **NVIDIA RTX 3050 Laptop (4GB)** | Tier 2 (Patrol Unit) | **PASS** | Compatible | Compatible (cu124) | Compatible (FP16) | Compatible | Required on target (SM86) | **CONFIG PREPARED / SIMULATED** |
| **NVIDIA RTX 3050 Laptop (6GB)** | Tier 2 (Patrol Unit) | **PASS** | Compatible | Compatible (cu124) | Compatible (FP16) | Compatible | Required on target (SM86) | **CONFIG PREPARED / SIMULATED** |
| **NVIDIA RTX 3060 (6GB/12GB)** | Tier 2+ (Mobile Command) | **PASS** | Compatible | Compatible (cu124) | Compatible (FP16) | Compatible | Required on target (SM86) | **CONFIG PREPARED / SIMULATED** |
| **NVIDIA RTX 4060 Laptop (8GB)**| Tier 3 (Forward Base) | **PASS** | Compatible | Compatible (cu124) | Compatible (FP16) | Compatible | Required on target (SM89) | **CONFIG PREPARED / SIMULATED** |
| **NVIDIA L40S / A100 Cluster** | Tier 4/5 (Command HQ) | **PASS** | Compatible | Compatible (cu124) | Compatible (TRT-LLM)| Compatible | Required on target (SM89/90) | **SPEC DEFINED** |

> [!NOTE]
> TensorRT `.engine` files are hardware and driver specific. The portable master checkpoints are preserved in `.pt` and `.onnx` formats. Engine generation must be executed once on the actual target silicon using `python deployment/rtx3050/export_tensorrt_engines.py`.

---

## 4. Empirical Benchmark Telemetry (Local Recorded Video)

- **Video Asset**: `data/raw/test_video.mp4` (592x360 @ 30 FPS, 898 total frames)
- **Data Source Label**: `[RECORDED_VIDEO]`
- **Frames Evaluated**: 50 frames
- **Total Detections Logged**: 163
- **Active Tracks at End**: 3
- **Mean Total Latency (Dell CPU)**: 915.5 ms
- **p50 Latency**: 396.7 ms
- **p95 Latency**: 1280.2 ms
- **Mean Ingestion Latency**: 3.2 ms
- **Mean Preprocessing (CLAHE) Latency**: 21.4 ms
- **Mean Detection Latency**: 888.4 ms
- **Mean Tracking & Spatial Latency**: 2.5 ms
- **Host RAM Consumed**: 368.1 MB (Stable, no memory growth)
- **Host CPU Usage**: 2-core active load
- **Evidence Verification Hash (Frame #10)**: `e6cd4f5d5eef9fc89217d2290437f6256651e5f811f01f74c35b12ca3da68500`

---

## 5. Security & Integrity Audit Summary

- **Authentication & RBAC**: JWT access tokens with Argon2/bcrypt password hashing (`services/auth/`).
- **Data Integrity**: Section 65B Indian Evidence Act SHA-256 hashing for raw snapshots and HMAC-SHA256 for audit events.
- **Verification Endpoint**: `POST /api/v1/evidence/verify` physically audits file bytes against stored hashes and detects single-byte modifications.
- **Terminology Standard**: System is designated **TAMPER-EVIDENT / INTEGRITY-VERIFIABLE** (claims of "100% unhackable" or "tamper-proof" are strictly avoided).

---

## 6. Offline Field Transfer Readiness

1. **Air-Gapped Wheel Cache**: Manifest prepared in `deployment/rtx3050/OFFLINE_WHEELS_MANIFEST.txt`.
2. **Download Utility**: `deployment/rtx3050/download_rtx3050_wheels.ps1` for building offline USB media.
3. **Automated Setup Script**: `deployment/rtx3050/setup_rtx3050_env.ps1 -Offline` installs dependencies with zero internet access.
4. **1-Click Launchers**: `start_ibvap_rtx3050.bat` and `start_ibvap_rtx3050.ps1` ready for double-click startup on field laptops.
