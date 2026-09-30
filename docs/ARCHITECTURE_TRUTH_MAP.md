# IBVAP Architecture Truth Map & Subsystem Separation Audit

**Document**: `docs/ARCHITECTURE_TRUTH_MAP.md`  
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines  
**Timestamp**: 2026-09-30T16:09:15+05:30  
**Evaluator**: Senior Principal Systems Architect & Cybersecurity Reviewer  

---

## 1. Subsystem Boundaries & Separation Principle

The IBVAP architecture strictly decouples **presentation**, **API coordination**, **high-frequency inference**, **assurance validation**, and **cryptographic persistence**. 

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PRESENTATION LAYER                                     │
│  React 18.3.1 + TypeScript + Tailwind CSS (Vite SPA @ localhost:5173)                  │
│  Pages: Dashboard, C4ISRDashboard, Personnel, Analytics                                │
│  Modals: LedgerAuditModal (One-Click Chain Verification & Certificate Inspection)       │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTP REST (Axios) + Native WebSocket
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              API COORDINATION LAYER                                    │
│  FastAPI Application (Uvicorn ASGI Server @ localhost:8000)                            │
│  Routers: assurance.py, auth.py, cameras.py, settings_router.py                        │
│  Security Boundary: RBAC Token Validation, Strict Origin Whitelisting, Param Schemas   │
└───────────────────┬─────────────────────────────────────────────────┬──────────────────┘
                    │                                                 │
                    ▼ Direct In-Memory Call                           ▼ Subprocess / Stream
┌─────────────────────────────────────────┐       ┌─────────────────────────────────────────┐
│     TCVIAF ASSURANCE ENGINE LAYER       │       │        CV INGESTION & ML WORKERS        │
│  • DataIntegrity (aHash, YOLO Syntax)   │       │  • ThreadedVideoSource (RTSP / MP4)     │
│  • ContributorManifest (Ed25519)        │       │  • RollingRingBuffer (8s RAM Window)    │
│  • AIBOM (CycloneDX 1.5 JSON Binding)   │       │  • SharedFrameWriter (Seqlock Memory)   │
│  • ModelFingerprint (ibvap-behavior-v1) │       │  • YOLO11n + ByteTrack (CUDA FP16)      │
│  • InferenceProvenance (Dual Hash)      │       │  • Two-Stage YOLO26x Cascade Verifier   │
│  • DistributionShift (KS & Kernel MMD)  │       │  • MobileSAM / ArcFace / EasyOCR        │
└───────────────────┬─────────────────────┘       └───────────────────┬─────────────────────┘
                    │                                                 │
                    │ Trigger On Threat / Breach / Assurance Audit    │
                    ▼                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          CRYPTOGRAPHIC LEDGER & EVIDENCE STORE                         │
│  CryptoEvidenceLedger (DuckDB / SQLite Fallback @ evidence_ledger.sqlite3)             │
│  • Sequential SHA-256 Merkle Hash Chaining                                             │
│  • Incremental Binary Merkle Tree Root Calculation                                     │
│  • BSA 2023 Section 63 / Sec 65B Electronic Evidence Certificate Export                 │
│  • Forensic 8-Second Video Clip Harvester (Deferred MP4 Export)                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Truth Matrix

| Component | Physical Location | Technology | Core Responsibility | Called By | Calls | Input Data | Output Data | Security Boundary |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Frontend UI** | `apps/frontend/` | React 18, TypeScript, Tailwind | Renders live camera grids, Seqlock health, threat alerts, and audit modals | Operator Browser | Backend API & WebSocket | User actions, video feeds, alerts | DOM updates, audit requests | Client-side only; zero secrets stored; all actions validated on backend |
| **API Router** | `apps/backend/routers/` | FastAPI, Pydantic v2 | Exposes REST endpoints for assurance, RBAC auth, camera feeds, and settings | Frontend HTTP client | Assurance services, ML engine, Ledger | JSON payloads, multipart files, auth headers | JSON responses, stream frames | Enforces JWT token verification, RBAC permissions (`ADMIN_ALL`, `ANALYST_REVIEW`), CORS |
| **Inference Worker** | `main_pipeline.py`, `services/inference/` | Python 3.11, Ultralytics, PyTorch, CUDA | Ingests frames, executes YOLO11n detection, tracks objects via ByteTrack, triggers MobileSAM | Subprocess worker / CLI | Ingestion, Vision models, Ledger | Raw RTSP/MP4 frames | Bounding boxes, track vectors, masks | Runs strictly on local GPU compute; zero network outbound calls |
| **Data Integrity Engine** | `services/assurance/data_integrity.py` | Python, NumPy, Scipy, Pillow | Validates datasets: aHash near-duplicates, YOLO box geometry, label discrepancy | Assurance Router, CLI audit scripts | None (standalone math/logic) | Image files, YOLO annotation `.txt` files | Anomaly scores, duplicate pairs, validity reports | Read-only analysis; does not mutate source data |
| **Supply Chain Verifier** | `services/assurance/manifest_verifier.py` | Python, Cryptography (Ed25519) | Validates Ed25519 manifest signature, on-disk model SHA-256, CycloneDX AIBOM schema, and 6-point binding | Assurance Router (`/manifests/verify`), CLI | ContributorManifest, AIBOM | JSON manifest, AIBOM JSON, `.pt` model file | `CompleteSupplyChainReport` (`ACCEPT` / `QUARANTINE`) | Thwarts hash substitution attacks by reading raw model bytes from disk |
| **Model Fingerprinter** | `services/assurance/model_fingerprint.py` | Python, PyTorch, Ultralytics | Runs 10 calibrated synthetic probes (`ibvap-behavior-v1`) to compute composite divergence score $S \in [0, 1]$ | Assurance Router, enrollment pipeline | Ultralytics model instance | Model checkpoint, probe images | Behavioral divergence score, status | Sandboxed local inference on deterministic synthetic patterns |
| **Inference Provenance** | `services/assurance/inference_provenance.py` | Python, hashlib, Pydantic | Generates 8-field deterministic canonical record with dual SHA-256 + SHAKE-256 digests and nonces | `main_pipeline.py`, Assurance Router | CryptoLedger | Frame bytes, model digest, detections, config | `InferenceProvenanceRecord` | Nonce and sequence validation prevents replay and injection attacks |
| **Crypto Evidence Ledger** | `crypto_ledger.py` | DuckDB, SQLite3, hashlib | Immutable append-only storage with sequential hash chaining and binary Merkle tree root | Inference Worker, Provenance Engine, Assurance Router | DuckDB / SQLite disk engine | Event payloads, frame hashes, timestamps | Block IDs, Merkle roots, Section 63/65B certificates | Thread-locked ACID transactions; tamper-evident hash chaining |
| **Shared Memory Transport** | `services/ingestion/shared_frame_buffer.py` | Python `multiprocessing.shared_memory` | Transports raw frames between ingestion and web streaming using 32-byte atomic Seqlock | Ingestion thread, Camera Router | OS Shared Memory | Ingested numpy frame buffers | Memory-mapped buffer slice | Protected by monotonic sequence lock to eliminate torn frames |

---

## 3. Communication Pipeline Flow

```text
[Camera Sensor / MP4 Ingestion]
      │
      ▼
ThreadedVideoSource ──> RollingRingBuffer (In-Memory 8s Window)
      │
      ▼
SharedFrameWriter (32-byte Seqlock in Windows Named Shared Memory)
      │
      ├──> [Camera Router (/api/v1/cameras/{id}/stream)] ──> [React Frontend Live Grid]
      │
      ▼
[YOLO11n CUDA FP16 Detector] ──> [ByteTrack Object Tracker]
      │
      ▼ (Borderline Conf 0.25 - 0.65)
[Two-Stage YOLO26x Cascade Verifier] (30-Frame Cache)
      │
      ▼ (Crawling Aspect Ratio < 0.65)
[MobileSAM Silhouette Segmentation]
      │
      ▼ (Virtual Fence Breach / Perimeter Crossing)
[InferenceProvenanceEngine] ──> 8-Field Canonical Hash Binding (SHA-256 + SHAKE-256)
      │
      ▼
[CryptoEvidenceLedger] ──> Block Commit (DuckDB / SQLite Append-Only Hash Chain)
      │
      ├──> [WebSocket (/ws/live_events)] ──> [Operator Dashboard Alert Cards]
      │
      ▼
[Section 63 / 65B Electronic Evidence Certificate Generator]
```
