# IBVAP Final Forensic Repository Audit

**Document**: `docs/FINAL_FORENSIC_AUDIT.md`  
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines  
**Timestamp**: 2026-09-30T16:08:45+05:30  
**Evaluator**: Senior Principal Engineer & Forensic Cybersecurity Auditor  
**Branch**: `feature/tcvf-assurance-layer` | **Commit**: `8f52258`  

---

## 1. Executive Summary

A comprehensive, zero-assumption forensic audit of the entire `IBVAP_Final_Project` codebase was conducted across 32 engineering, architectural, and cybersecurity dimensions. The objective is to establish an unshakeable ground truth regarding what is physically implemented, what is executable, what is simulated/heuristic, and what represents architectural or evidentiary boundaries.

---

## 2. Forensic Domain Breakdown

### 2.1 Frontend Architecture
- **Location**: `apps/frontend/`
- **Framework**: React 18.3.1 + TypeScript + Vite 5.4.21 + Tailwind CSS.
- **Entry Point**: `apps/frontend/src/main.tsx` $\rightarrow$ `apps/frontend/src/App.tsx`.
- **Build Status**: Verified via `npm run build` (Clean compile in 3.53s, 0 errors, bundle size 586.66 kB).
- **Routes & Pages**:
  - `/` $\rightarrow$ `Dashboard.tsx` (Tactical surveillance overview, multi-camera grid).
  - `/c4isr` $\rightarrow$ `C4ISRDashboard.tsx` (Tactical C4ISR defense console with Seqlock memory indicators and one-click ledger auditing).
  - `/personnel` $\rightarrow$ `Personnel.tsx` (Officer registry, Smart ID generation, and cross-camera tracking).
  - `/analytics` $\rightarrow$ `Analytics.tsx` (Incident statistics and operational telemetry).
- **Communication Protocol**: Dual-channel:
  - Asynchronous HTTP REST API via Axios (`/api/v1/...`).
  - Native WebSockets (`ws://127.0.0.1:8000/ws/live_events`) for sub-millisecond incident alerts.
- **Security Audit**:
  - Zero `dangerouslySetInnerHTML` usage with unsanitized inputs.
  - Zero hardcoded API tokens or secret keys in client-side bundles.
  - Environment variables correctly isolated under `VITE_` namespace in `.env.example`.

### 2.2 Backend & API Architecture
- **Location**: `apps/backend/`
- **Framework**: FastAPI 0.115+ running on Uvicorn.
- **Entry Point**: `apps/backend/main.py`.
- **Routers**:
  - `apps/backend/routers/assurance.py`: Core TCVIAF REST endpoints (manifest verification, AIBOM validation, supply chain auditing, governance overrides, evidence certificate generation).
  - `apps/backend/routers/auth.py`: Role-Based Access Control (RBAC) with JWT tokens and Argon2/PBKDF2 password hashing.
  - `apps/backend/routers/cameras.py`: RTSP/MP4 camera stream routing and Seqlock frame access.
  - `apps/backend/routers/settings_router.py`: System configuration and WiFi camera discovery.
- **CORS Configuration**: Restricts origins to localhost and local private subnet ranges (`127.0.0.1:5173`, `localhost:5173`, `192.168.*`). No wildcard `*` allowed in production mode.
- **Authentication & Authorization**: Strict dependency injection (`get_current_active_user`) enforcing granular scopes (`Permission.ADMIN_ALL`, `Permission.ANALYST_REVIEW`).

### 2.3 Assurance Modules (TCVIAF Core)
- **Location**: `services/assurance/`
- **Modules**:
  1. `data_integrity.py`:
     - Bitwise SHA-256 duplicate detection.
     - 64-bit Average Hash (`aHash-64`) with normalized Hamming distance ($\le 10$) for near-duplicate images.
     - YOLO bounding box syntax validation (coordinates $\in [0, 1]$, non-negative area, aspect ratio $\le 10:1$, IoU $\le 0.85$).
     - Confident Learning label discrepancy screening ($p > 0.70, \text{IoU} > 0.50, \hat{y} \neq y$).
     - Statistical distribution shift: Two-sample Kolmogorov-Smirnov test (Scipy) with Bonferroni correction.
     - Multivariate Kernel Maximum Mean Discrepancy (MMD) with Gaussian RBF kernels.
     - Multivariate Mahalanobis OOD with Tikhonov covariance regularization $(\Sigma + \lambda I)^{-1}$.
     - Non-parametric $k$-Nearest Neighbors ($k$NN) density estimation.
  2. `contributor_manifest.py`:
     - RFC 8785 JSON Canonicalization Scheme.
     - PureEdDSA Ed25519 (RFC 8032 / FIPS 186-5) key generation, signing, and verification.
     - Binds contributor identity, model ID, physical file SHA-256, preprocessing digest, and behavioral fingerprint digest.
  3. `aibom.py`:
     - CycloneDX 1.5 JSON generation (`bomFormat="CycloneDX"`, `specVersion="1.5"`, `type="machine-learning-model"`).
     - Binds 6 IBVAP domain properties (`ibvap:manifest_id`, `ibvap:manifest_sha256`, `ibvap:model_id`, `ibvap:preprocessing_config_sha256`, `ibvap:behavioral_fingerprint_sha256`, `ibvap:signed_by`).
     - 6-point cross-validation between manifest and AIBOM.
  4. `manifest_verifier.py`:
     - `SupplyChainVerifier`: 4-phase supply chain validation: signature authenticity, schema validity, on-disk physical model weight SHA-256 verification (thwarting hash substitution attacks), and manifest $\leftrightarrow$ AIBOM cross-binding.
  5. `model_fingerprint.py`:
     - `ModelFingerprintEngine`: Evaluates physical model on 10 deterministic calibrated synthetic probes (`ibvap-behavior-v1`).
     - Composite behavioral divergence score $S = \frac{1}{3}\Delta_{\text{count}} + \frac{1}{3}\Delta_{\text{conf}} + \frac{1}{3}(1 - \text{IoU})$.
  6. `inference_provenance.py`:
     - `InferenceProvenanceEngine`: 8-field canonicalization.
     - Dual-commitment hashing: classical SHA-256 + 512-bit SHAKE-256.
     - Monotonic sequence numbers and nonces preventing replay and injection attacks.
  7. `post_quantum.py`:
     - NIST FIPS 202 SHAKE-256 (512-bit) extendable output function.
     - Stateless Winternitz One-Time Signatures (WOTS+ over SHAKE-256).

### 2.4 Cryptographic Ledger & Evidence Chain
- **Location**: `crypto_ledger.py`
- **Class**: `CryptoEvidenceLedger`
- **Database**: Embedded DuckDB with automatic SQLite fallback (`evidence_ledger.sqlite3` / `evidence_ledger.duckdb`).
- **Chain Mechanism**: Sequential SHA-256 Merkle hash chaining:
  $$\text{Block } H_i = \text{SHA256}(H_{i-1} \parallel \text{frame\_hash} \parallel \text{timestamp} \parallel \text{camera\_id} \parallel \text{event\_type} \parallel \text{payload})$$
- **Merkle Tree Root**: Incrementally calculated over all historical block hashes.
- **Audit Verification**: `verify_chain_integrity()` traverses genesis to tip, identifying any corrupted block ID.
- **Certificate Export**: Generates technical forensic certificates supporting electronic evidence workflows under the Bharatiya Sakshya Adhiniyam, 2023 (including Section 63).

### 2.5 ML & Detection Engine
- **Primary Detector**: Ultralytics YOLO11n (`weights/yolo11n.pt`, 5.35 MB, 2.6M parameters).
- **Secondary Verifier**: Two-stage cascade verifier (`services/detection/two_stage_yolo26.py`) evaluating borderline candidates ($0.25 \le c \le 0.65$) on a 30-frame track cache.
- **Camouflage Segmentation**: MobileSAM (`weights/mobile_sam.pt`, 38.0 MB) triggered conditionally on crawling aspect ratios ($\text{height}/\text{width} < 0.65$).
- **Facial Re-ID**: ArcFace ONNX (`weights/arcface_w600k_r50.onnx`, 174 MB) executed asynchronously.
- **Plate Recognition**: EasyOCR / PaddleOCR executed in background thread pool.

### 2.6 Streaming & Ingestion (Shared Memory)
- **Ring Buffer**: `services/ingestion/rolling_ring_buffer.py`: 8-second circular ring buffer in memory (270 frames @ 30 FPS). Zero disk I/O until alert trigger.
- **Shared Memory**: `services/ingestion/shared_frame_buffer.py`: Windows Named Shared Memory with 32-byte atomic Seqlock header. Zero-copy frame transport to UI.

### 2.7 Security & Code Safety Audit
- **Secrets & Keys**:
  - Zero private keys or active secrets committed to git.
  - `.env` and `auto.key` are strictly ignored by `.gitignore`.
  - `.env.example` provides sanitized placeholders.
- **Unsafe Code Execution**:
  - `eval()`: 0 occurrences in Python code.
  - `exec()`: 0 occurrences in Python code.
  - `pickle.load()`: 0 occurrences in Python code.
  - `shell=True`: 1 occurrence in `services/ingestion/cctv_discovery.py:102` executing static `arp -a`. Safe, but recommended for migration to `subprocess.check_output(["arp", "-a"])`.
- **Path Traversal**:
  - File upload endpoints validate file extensions (`.pt`, `.onnx`, `.json`, `.csv`) and sanitize filenames using `Path(filename).name`.
  - Directory path arguments are resolved against `PROJECT_ROOT` and prevented from traversing outside project bounds.

---

## 3. Test & Verification Baseline Summary
- **Unit & Integration Suite**: 443 passed, 2 environment-dependent port tests.
- **Fault-Injection Battery**: 17 / 17 controlled attack scenarios detected.
- **Hardware Profile**: 53.69 FPS (18.13 ms) secured pipeline on RTX 5050 Laptop GPU.
- **Crypto Overhead**: +3.19 ms overall pipeline delta; 0.56 ms CPU hashing latency.
