# GSD Project Specification: IBVAP (SIH-26187)
## Intelligent Border Video Analytics Platform

### 1. Executive Summary & Objective
IBVAP is an edge-optimized, military-grade tactical border video analytics platform designed for the Smart India Hackathon (SIH Problem Statement 26187). It converts legacy and tactical CCTV/PTZ/Thermal camera feeds into real-time situational awareness streams with cryptographic data integrity.

### 2. Core Architecture
- **Inference Engine**: Ultralytics YOLOv8/YOLO11 with TensorRT FP16 acceleration targeting NVIDIA RTX 3050 / RTX 5050 hardware profiles.
- **ANPR Subsystem**: Real-time license plate detection and OCR with high-accuracy character recognition (EasyOCR / PaddleOCR).
- **Out-of-Distribution (OOD) & Integrity Testing**:
  - Mahalanobis Distance covariance scoring on latent embeddings.
  - k-Nearest Neighbor (kNN) density conformity evaluation.
  - Cleanlab label quality and annotation inversion auditing.
- **Cryptographic Assurance & Evidence Binding**:
  - Immutable Merkle tree-based video evidence ledger (`crypto_ledger.py` / DuckDB / SQLite).
  - Post-Quantum Cryptography (PQC) readiness: Winternitz One-Time Signatures (WOTS+-SHAKE256).
- **Presentation & Operations Dashboard**:
  - React 18 + Vite + TailwindCSS + Material Symbols operations console with real-time RTSP/WebRTC streams and live integrity auditing.

### 3. Key Non-Functional Requirements
- **Latency**: Sub-35ms end-to-end inference per camera stream on NVIDIA GPU.
- **Multi-Stream**: Concurrent ingestion of up to 4 tactical RTSP streams via MediaMTX.
- **Offline Reliability**: Air-gapped deployment capability with pre-bundled wheels and local model weights.
