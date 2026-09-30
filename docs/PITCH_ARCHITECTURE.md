# TCVIAF / IBVAP Pitch-Ready Architecture Specification
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines  
**Platform**: IBVAP (Integrity-Bound Vision Assurance Platform)  
**Branch**: `feature/tcvf-assurance-layer`  
**Preserved Baseline**: Commit `25c05eba437058b07873ee9aba822ae173fdf1d2`  
**Document Status**: Pitch-Ready & Production-Aligned (Grounded in Verified Code)  

---

## 1. System Architecture Overview

The **Trustworthy Computer Vision Integrity Assurance Framework (TCVIAF)** implemented in **IBVAP** establishes an end-to-end chain of trust for edge surveillance systems. It cryptographically binds raw sensor data, model weights, and inference outputs to prevent silent tampering, uncurated data poisoning, and unauthorized automated decisions.

```
                     ┌──────────────────────────────────────────────┐
                     │            RAW VIDEO INPUT SOURCES           │
                     │    RTSP Cameras / Local MP4 / Video Queues   │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │     STAGE 1: INGESTION & SHARED MEMORY       │
                     │  • Threaded Video Queue (Leak-Free Drops)    │
                     │  • 8-Second In-Memory Ring Buffer (270 f)    │
                     │  • Seqlock Shared Memory Frame Transport     │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │    STAGE 2: PHOTOMETRIC RESTORATION          │
                     │  • Luminance V-Channel Check (Lux < 40.0)    │
                     │  • Zero-DCE++ Neural Curve Estimator (<10ms) │
                     │  • CLAHE Dynamic Contrast Fallback           │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │  STAGE 3: DETECTION & PERSISTENT TRACKING    │
                     │  • Primary Detector: YOLO11n (CUDA FP16)     │
                     │  • Persistent Tracker: ByteTrack (Vel/Angle) │
                     │  • Two-Stage YOLO26x Cascade Verifier        │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │   STAGE 4: CONDITIONAL SPECIALIST ANALYTICS  │
                     │  • MobileSAM Camouflage Segmentation (ROIs)  │
                     │  • ArcFace Biometrics (Async Thread Pool)    │
                     │  • EasyOCR / ANPR Plates (Async Thread Pool) │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │   STAGE 5: PERIMETER TRIPWIRE & PROVENANCE   │
                     │  • Virtual Fence Tripwire Crossing Check     │
                     │  • 8-Field Cryptographic Canonicalization    │
                     │  • Dual Classical-Quantum Hybrid Commitment  │
                     │  • Monotonic Sequence & Nonce Generation     │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │   STAGE 6: CRYPTOGRAPHIC EVIDENCE LEDGER     │
                     │  • Millisecond SHA-256 Frame Byte Digest     │
                     │  • Sequential Hash Chaining (Tamper-Evident) │
                     │  • Binary Merkle Tree Root Computation       │
                     │  • DuckDB / SQLite Append-Only Local Store   │
                     │  • Deferred 8-Second Forensic Video Export   │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │     STAGE 7: AUDIT, GOVERNANCE & C4ISR UI    │
                     │  • FastAPI REST Endpoints & WebSockets       │
                     │  • React Tactical Dashboard (Air-Gap Mode)   │
                     │  • ACCEPT / REVIEW / QUARANTINE Lifecycle    │
                     │  • Immutable Human Override Audit Trail      │
                     │  • Section 65B Audit Certificate Export      │
                     └──────────────────────────────────────────────┘
```

---

## 2. Decoupled Architecture Subsystems

To maintain sustained real-time video throughput (**53.69 FPS**) without dropping frames, the architecture strictly decouples **high-frequency runtime execution** from **heavy offline assurance checks**.

### A. Real-Time Video Runtime Pipeline (Every Frame)
*Executes at video frame rate within [main_pipeline.py](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/main_pipeline.py):*
1. **Ingestion & Buffer**: `ThreadedVideoSource` captures raw frames into a bounded queue. Frames are simultaneously pushed to an in-memory `RollingRingBuffer` (preserving an 8-second forensic window: 5s pre-event + 3s post-event) and exposed to the UI via `SharedFrameWriter` using an atomic 32-byte Seqlock header.
2. **Restorative Preprocessing**: Evaluates average luminance in HSV color space. If luminance $< 40.0$, invokes `ZeroDCEPlusPlusRestorer` (depthwise separable curve estimation) to restore low-light details in sub-10ms.
3. **Primary Detection & Tracking**: Executes Ultralytics YOLO11n on CUDA FP16 at $640\times 640$. Bounding boxes are tracked across frames using ByteTrack.
4. **Stacked Two-Stage Verification**: If candidate detections have borderline confidence ($0.25 \le c \le 0.65$), they are cropped and re-verified by the heavy verifier (`yolo26x.pt`, 56.9M parameters). A 30-frame track cache prevents redundant inference on persistent objects.
5. **Conditional Specialist Analytics**:
   - **Camouflage Segmentation**: Targets with crawling aspect ratio ($\text{height}/\text{width} < 0.65$) or low confidence are passed to `MobileSAM` for pixel-level silhouette extraction.
   - **Asynchronous Biometrics & ANPR**: Facial crops and license plate crops are offloaded to background worker threads running `ArcFace` and `EasyOCR`, ensuring zero pipeline stalls.
6. **Perimeter Breach & Provenance Hook**: When a track crosses the virtual perimeter tripwire:
   - Computes SHA-256 digest of raw frame bytes.
   - Invokes `InferenceProvenanceEngine` to bind input hash, model ID, weight digest, NMS configs, sorted detections, sequence number, and nonce into an immutable record.
   - Commits event into `CryptoEvidenceLedger` with sequential hash chaining and incremental Merkle tree root recalculation.
   - Schedules deferred 8-second MP4 clip export via background thread pool.
   - Dispatches real-time WebSocket alert payload to the frontend.

---

### B. Offline & Batch Assurance Services (Ad-Hoc / Pipeline Ingestion)
*Executes during dataset curation, model enrollment, or scheduled audits via [data_integrity.py](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/data_integrity.py) and [model_fingerprint.py](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/model_fingerprint.py):*
1. **Training Data Integrity**:
   - **Exact Duplicates**: SHA-256 byte hashing detects identical images across multi-contributor uploads.
   - **Near-Duplicates**: 64-bit Average Hash (`aHash-64`) with normalized Hamming distance ($\le 10$) detects compressed, resized, or brightness-adjusted duplicate uploads.
   - **YOLO Coordinate Validation**: Validates coordinate syntax, normalized bounds ($x, y, w, h \in [0, 1]$), non-negative area, and class ID boundaries.
   - **Cleanlab-Inspired Label Quality**: Flags bounding box aspect ratio anomalies ($>10:1$), box collisions ($\text{IoU} > 0.85$), and Confident Learning label flipping ($p>0.70, \text{IoU}>0.50, \hat{y} \neq y$).
2. **Distribution Shift & Out-of-Distribution Monitoring**:
   - **Centroid-Distance OOD**: Lightweight Euclidean distance from enrolled feature centroid with $3\sigma$ threshold.
   - **Multivariate Mahalanobis OOD**: Covariance-aware distance with regularized inversion $(\Sigma + \lambda I)^{-1}$ and Chi-square ($\chi^2_d$) critical values.
   - **kNN Feature Density**: Non-parametric $k$-Nearest Neighbors density relative to reference cluster percentiles.
   - **Two-Sample KS Test**: Per-channel Kolmogorov-Smirnov test with Bonferroni correction ($\alpha = 0.05 / k$).
   - **Kernel MMD Joint Shift**: Multivariate two-sample unbiased MMD U-statistic with Gaussian RBF kernel, median bandwidth heuristic, and permutation testing.
3. **Behavioral Model Fingerprinting**:
   - Evaluates black-box candidate models against deterministic synthetic probe battery `ibvap-behavior-v1` ($N=10$ calibrated patterns testing contrast, illumination, and geometry).
   - Computes composite behavioral divergence score $S \in [0, 1]$ measuring count drift, confidence shift, and bounding box geometric deviation.
   - Detects trojaned weights, silent model swapping, and quantization degradation.
4. **Model Supply-Chain & Multi-Contributor Provenance**:
   - **Signed Contributor Manifests**: Multi-contributor model releases are encapsulated into RFC-8785 canonicalized JSON manifests signed with Ed25519 (RFC 8032) keys, binding model checkpoint SHA-256, model ID, architecture, preprocessing digest, and behavioral fingerprint digest.
   - **CycloneDX 1.5 AIBOM**: Exports offline AI Software Bill of Materials in CycloneDX 1.5 format (`type="machine-learning-model"`) with IBVAP extension properties.
   - **Multi-Check SupplyChainVerifier**: Performs 4-phase supply chain validation: signature authenticity, schema validation, physical model file SHA-256 verification (thwarting hash substitution attacks), and 6-point Manifest ↔ AIBOM cross-binding integrity.

---

### C. Cryptographic Evidence & Ledger Services
*Manages tamper-evident chain-of-custody in [crypto_ledger.py](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/crypto_ledger.py) and [post_quantum.py](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/post_quantum.py):*
1. **Sequential Hash Chaining**: Links each incident block to the preceding block hash:
   $$\text{Block } H_i = \text{SHA256}(H_{i-1} \parallel \text{frame\_hash} \parallel \text{timestamp} \parallel \text{camera\_id} \parallel \text{event\_type} \parallel \text{payload})$$
2. **Binary Merkle Tree Root**: Incrementally reduces historical block hashes into a single root digest, enabling compact mathematical integrity proofs.
3. **Dual Classical-Quantum Hybrid Commitment**: Combines classical SHA-256 (FIPS 180-4) with SHAKE-256 512-bit (FIPS 202) to guarantee 256 bits of collision resistance against Grover's quantum search algorithm.
4. **Post-Quantum Signatures**: Incorporates Winternitz One-Time Signatures (WOTS+ over SHAKE-256), a stateless hash-based signature scheme mathematically immune to Shor's algorithm.
5. **Section 65B Audit Certificate**: Exports verifiable JSON certificates with sequence heights, Merkle roots, and file digests for judicial compliance.

---

### D. Governance & Analyst Console
*Enforces human-in-the-loop oversight in [apps/backend/routers/assurance.py](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/apps/backend/routers/assurance.py) and [apps/frontend/src/pages/C4ISRDashboard.tsx](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/apps/frontend/src/pages/C4ISRDashboard.tsx):*
1. **Three-Tier Disposition Lifecycle**: Every assurance finding produces a recommended disposition: `ACCEPT`, `REVIEW`, or `QUARANTINE`.
2. **Human Override Isolation**: Automated models generate recommendations only. Authorised defense analysts can override any disposition. Automated algorithms are strictly prohibited from overwriting an analyst's decision.
3. **Immutable Governance Audit Log**: Every override is recorded in the `governance_audit` ledger table with analyst identity, timestamp, previous disposition, new disposition, and justification.
4. **Air-Gapped Operator Interface**: High-density tactical console displays live video grids, Seqlock memory stream health, SHA-256 block heights, and one-click ledger verification.

---

## 3. Physical Hardware Execution Profile

All performance metrics reflect empirical measurements conducted on local hardware via `benchmarks/run_benchmark.py`:

- **Operating System**: Windows 11 (Build 26200)
- **Host Processor**: Intel(R) Core(TM) i7-13650HX
- **Discrete GPU**: NVIDIA GeForce RTX 5050 Laptop GPU (CUDA 12.8 compute capability)
- **Primary Detector**: Ultralytics YOLO11n (`weights/yolo11n.pt`)
- **Evaluation Settings**: 50 frames @ $640\times 640$ synthetic RGB, 10 warmup frames

| Metric | Raw Baseline | Secured Pipeline | Overhead / Delta | Operational Significance |
| :--- | :---: | :---: | :---: | :--- |
| **Mean Latency** | **14.94 ms** | **18.13 ms** | **+3.19 ms (+21.4%)** | Frame time well within real-time limits ($<33.3\text{ ms}$). |
| **Throughput (FPS)** | **66.92 FPS** | **53.69 FPS** | **-19.7%** | Comfortably exceeds 25–30 FPS CCTV stream rate. |
| **Hashing & Canonicalization** | — | **0.562 ms** | — | Lightweight dual-layer hashing executes in sub-millisecond. |
| **Ledger Disk Persistence** | — | **5.554 ms** | — | Decoupled disk commit preserves live stream fluidity. |
| **Fault Injection Detection** | — | **17 / 17 (100.0%)** | — | Detected all simulated tampering scenarios in test harness. |
