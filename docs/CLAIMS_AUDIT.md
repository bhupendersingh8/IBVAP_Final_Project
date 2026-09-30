# TCVIAF / IBVAP Claims Audit & Pitch Guidance
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines  
**Branch**: `feature/tcvf-assurance-layer`  
**Preserved Baseline**: Commit `25c05eba437058b07873ee9aba822ae173fdf1d2`  
**Audit Date**: September 30, 2026  

---

## 1. Executive Guidelines

This document establishes the authoritative evidentiary baseline for all presentations, jury demonstrations, technical evaluations, and pitch materials for the IBVAP platform.

### Core Truth Principles:
1. **Never claim an algorithm or metric without reproducible repository evidence.**
2. **Never claim a security property stronger than what the code actually provides** (e.g., use "tamper-evident", never "tamper-proof").
3. **Always distinguish controlled synthetic test results from real-world field performance.**
4. **All performance claims must cite the exact benchmark script, hardware platform, and input configuration.**

---

## 2. Detailed Claims Audit Table

---

### Claim 1: Secured Edge Pipeline Throughput & Latency

- **CLAIM**: The secured vision assurance pipeline maintains real-time throughput on local edge hardware.
- **STATUS**: **VERIFIED**
- **CODE EVIDENCE**: `benchmarks/run_benchmark.py`, `main_pipeline.py`
- **TEST EVIDENCE**: Benchmark harness execution
- **BENCHMARK EVIDENCE**: `benchmarks/results/latest.json`
  - Raw Baseline: **14.94 ms** mean latency (**66.92 FPS**)
  - Secured Assurance Pipeline: **18.13 ms** mean latency (**53.69 FPS**)
  - Hardware: Intel Core i7 / NVIDIA GeForce RTX 5050 Laptop GPU (CUDA 12.8)
  - Input: 50 frames @ 640x640 synthetic RGB, 10 warmup frames
- **ALLOWED PITCH WORDING**:
  - *"The secured assurance pipeline achieves a measured throughput of 53.69 FPS (18.13 ms latency) on local RTX 5050 GPU compute, comfortably exceeding standard CCTV frame rate requirements (25–30 FPS)."*
  - *"Inference with active provenance binding introduces +3.19 ms (+21.4%) latency overhead compared to the raw baseline."*
- **FORBIDDEN / OVERCLAIMED WORDING**:
  - ❌ *"Guaranteed >60 FPS in deployment."* (Secured pipeline runs at 53.69 FPS, not >60 FPS).
  - ❌ *"Sub-12 ms end-to-end latency."* (Measured latency is 18.13 ms).
  - ❌ *"Zero overhead security."* (Security has a measured +3.19 ms / +21.4% computational cost).

---

### Claim 2: Cryptographic Hashing and Persistence Latency

- **CLAIM**: Inference provenance hashing adds negligible overhead to frame processing.
- **STATUS**: **VERIFIED**
- **CODE EVIDENCE**: `services/assurance/inference_provenance.py:compute_provenance_hash()`, `crypto_ledger.py:commit_event()`
- **TEST EVIDENCE**: `test_inference_provenance.py`
- **BENCHMARK EVIDENCE**: `benchmarks/results/latest.json`
  - Canonicalization & Hashing: **0.562 ms**
  - Database Persistence (SQLite commit): **5.554 ms**
- **ALLOWED PITCH WORDING**:
  - *"Inference provenance canonicalization and dual-layer hashing executes in 0.562 ms on CPU."*
  - *"Ledger persistence adds 5.55 ms during event commit, decoupled from non-alert background frames to preserve real-time streaming."*
- **FORBIDDEN / OVERCLAIMED WORDING**:
  - ❌ *"CUDA-accelerated asynchronous SHA-256."* (Hashing executes on CPU via standard `hashlib`).
  - ❌ *"Total cryptographic overhead is under 2 ms."* (Hashing is 0.56 ms, but total overhead including database persistence is +3.19 ms).

---

### Claim 3: Controlled Fault-Injection Tamper Detection

- **CLAIM**: The platform detects unauthorized modifications to input pixels, model weights, inference parameters, and outputs.
- **STATUS**: **VERIFIED (Within Controlled Test Harness)**
- **CODE EVIDENCE**: `benchmarks/run_fault_injection.py`, `services/assurance/inference_provenance.py:verify_provenance_record()`
- **TEST EVIDENCE**: `test_inference_provenance.py` (Mutations 1–17)
- **BENCHMARK EVIDENCE**: `benchmarks/results/fault_injection_latest.json`
  - **17 / 17 controlled mutation cases detected** (100.0% detection rate in controlled battery)
- **ALLOWED PITCH WORDING**:
  - *"In a controlled 17-scenario fault-injection battery, the provenance verification engine successfully detected 17 out of 17 simulated mutations, including 1-byte pixel changes, weight swaps, confidence score tampering, coordinate alteration, sequence gaps, and replay attacks."*
- **FORBIDDEN / OVERCLAIMED WORDING**:
  - ❌ *"100% detection rate against all real-world adversarial attacks."* (This is an engineering validation test with known mutations, not a statistical field trial).
  - ❌ *"Unhackable / bulletproof tamper protection."* (Hash chains provide tamper evidence, not physical or cryptographic prevention).

---

### Claim 4: Cryptographic Ledger Chain-of-Custody

- **CLAIM**: Video evidence and inference outputs are cryptographically bound into an append-only ledger complying with Indian Evidence Act Section 65B.
- **STATUS**: **VERIFIED**
- **CODE EVIDENCE**: `crypto_ledger.py:CryptoEvidenceLedger`, `crypto_ledger.py:export_audit_certificate()`
- **TEST EVIDENCE**: `test_defense_pipeline_and_ledger.py`, `test_clip_ledger_integration.py`
- **BENCHMARK EVIDENCE**: Embedded DuckDB / SQLite schema with SHA-256 Merkle hash chaining
- **ALLOWED PITCH WORDING**:
  - *"The platform implements an append-only, tamper-evident cryptographic hash chain that binds raw frame bytes, model digests, bounding boxes, and timestamps into an immutable sequence."*
  - *"Generates Section 65B-compliant audit certificates with verified sequence height and binary Merkle root."*
- **FORBIDDEN / OVERCLAIMED WORDING**:
  - ❌ *"Decentralized blockchain vault."* (The system is a high-speed local cryptographic hash chain, NOT a distributed blockchain).
  - ❌ *"Tamper-proof evidence."* (Use 'tamper-evident'; an attacker with local OS root who rewrites the entire disk cannot be stopped by software alone).
  - ❌ *"Guaranteed court-admissible non-repudiation."* (The system produces technical evidence certificates meeting Section 65B requirements; legal admissibility is determined by the court).

---

### Claim 5: Out-of-Distribution & Distribution Shift Detection

- **CLAIM**: The system detects uncurated data, distribution drift, and out-of-distribution feature anomalies.
- **STATUS**: **VERIFIED**
- **CODE EVIDENCE**: `services/assurance/data_integrity.py` (`check_ood()`, `check_ood_mahalanobis()`, `check_ood_knn_density()`, `check_distribution_shift()`, `check_distribution_shift_mmd()`)
- **TEST EVIDENCE**: `test_data_integrity.py`, `test_advanced_ood_and_mmd.py` (18 tests passing)
- **BENCHMARK EVIDENCE**: Mathematical formulations with Bonferroni correction and Chi-square critical values
- **ALLOWED PITCH WORDING**:
  - *"Detects distribution shift via univariate two-sample Kolmogorov-Smirnov tests and multivariate Kernel Maximum Mean Discrepancy (MMD) with Gaussian RBF kernels."*
  - *"Supports both centroid-distance heuristic, multivariate Mahalanobis distance with regularized covariance inversion, and non-parametric kNN feature density for OOD identification."*
  - *"Requires an enrolled reference baseline; conservatively reports NO_REFERENCE_BASELINE in cold-start scenarios rather than fabricating confidence."*
- **FORBIDDEN / OVERCLAIMED WORDING**:
  - ❌ *"97.8% OOD detection accuracy."* (Uncalibrated heuristic/statistical tests; no real-world accuracy percentage is claimed).
  - ❌ *"Bayesian deep uncertainty estimation."* (Uses empirical statistical distance metrics, not Bayesian neural networks).

---

### Claim 6: Active Label Quality & Dataset Assurance

- **CLAIM**: The data integrity layer identifies annotation corruptions, bounding box anomalies, and potential label flipping.
- **STATUS**: **VERIFIED**
- **CODE EVIDENCE**: `services/assurance/data_integrity.py:check_label_integrity()`, `check_label_quality()`
- **TEST EVIDENCE**: `test_label_quality_assurance.py` (6 tests passing)
- **BENCHMARK EVIDENCE**: Bbox aspect ratio ($>10:1$), box collisions ($\text{IoU} > 0.85$), Confident Learning prediction discrepancy ($p > 0.70, \text{IoU} > 0.50, \hat{y} \neq y_{\text{ann}}$)
- **ALLOWED PITCH WORDING**:
  - *"Validates YOLO coordinate geometry and syntax, detecting out-of-bounds coordinates and negative areas."*
  - *"Applies Cleanlab-inspired active label quality checks to flag extreme aspect ratio outliers, duplicate bounding box collisions, and high-confidence label flips."*
- **FORBIDDEN / OVERCLAIMED WORDING**:
  - ❌ *"Integrated Cleanlab / Confident Learning package."* (Implements native geometric and prediction-discrepancy heuristics inspired by Cleanlab; does not import the third-party `cleanlab` library).
  - ❌ *"Automated active learning dataset re-labeling."* (The module flags noisy annotations for human review; it does not automatically re-train or overwrite ground truth).

---

### Claim 7: Behavioral Model Fingerprinting

- **CLAIM**: The platform detects behavioral drift or model tampering even when weight files appear authentic.
- **STATUS**: **VERIFIED**
- **CODE EVIDENCE**: `services/assurance/model_fingerprint.py:ModelFingerprintEngine`
- **TEST EVIDENCE**: `test_behavioral_fingerprint.py` (14 tests passing)
- **BENCHMARK EVIDENCE**: 10-probe synthetic test battery (`ibvap-behavior-v1`) with composite divergence scoring
- **ALLOWED PITCH WORDING**:
  - *"Evaluates black-box behavioral model consistency using deterministic synthetic probe batteries across varying contrast, lighting, and geometric patterns."*
  - *"Computes a multi-metric behavioral divergence score $S \in [0, 1]$ measuring detection count drift, confidence shift, and bounding box geometric deviation."*
- **FORBIDDEN / OVERCLAIMED WORDING**:
  - ❌ *"Neural Cleanse backdoor trigger inversion."* (Does not perform $L_1$-norm trigger inversion or Trojan weight pruning).
  - ❌ *"Formal neuron activation verification."* (Evaluates black-box input-output behavioral distributions, not formal activation bounds).

---

### Claim 8: Post-Quantum Cryptographic Readiness

- **CLAIM**: The cryptographic ledger includes post-quantum resistant hash commitments and signatures.
- **STATUS**: **VERIFIED**
- **CODE EVIDENCE**: `services/assurance/post_quantum.py`, `crypto_ledger.py:1220`
- **TEST EVIDENCE**: `test_post_quantum_crypto.py` (6 tests passing)
- **BENCHMARK EVIDENCE**: NIST FIPS 202 SHAKE-256 (512-bit) + WOTS+ over SHAKE-256
- **ALLOWED PITCH WORDING**:
  - *"Incorporates classical-quantum hybrid hash commitments combining SHA-256 with 512-bit SHAKE-256 (providing 256 bits of collision resistance against Grover's algorithm)."*
  - *"Includes Winternitz One-Time Signatures (WOTS+ over SHAKE-256), a stateless hash-based signature scheme that relies purely on hash collision resistance and is immune to Shor's algorithm."*
  - *"Employs a two-tier signature architecture: WOTS+ over SHAKE-256 for high-frequency, quantum-resistant inference event commitments, and standard Ed25519 (RFC 8032) for offline contributor model manifest release provenance."*
  - *"Pure-Python implementation following the WOTS+ construction without external third-party C-dependencies."*
- **FORBIDDEN / OVERCLAIMED WORDING**:
  - ❌ *"NIST FIPS 205 certified implementation."* (The implementation mathematically follows the WOTS+ / SLH-DSA construction, but has not undergone formal NIST CAVP laboratory certification).
  - ❌ *"Post-quantum Ed25519."* (Ed25519 is classical elliptic-curve cryptography for offline model releases; WOTS+ provides post-quantum security for inference commitments).

---

### Claim 11: Contributor Model Manifest & Offline CycloneDX 1.5 AIBOM

- **CLAIM**: The platform validates multi-contributor model supply-chain provenance through cryptographically signed contributor manifests and CycloneDX 1.5-compatible AIBOMs.
- **STATUS**: **VERIFIED**
- **CODE EVIDENCE**: `services/assurance/contributor_manifest.py`, `services/assurance/aibom.py`, `services/assurance/manifest_verifier.py`, `services/assurance/keygen.py`
- **TEST EVIDENCE**: `test_contributor_manifest.py` (17 tests), `test_aibom.py` (11 tests) — 28/28 tests passing
- **BENCHMARK EVIDENCE**: RFC-8785 JSON canonicalization, PureEdDSA Ed25519 (RFC 8032) signing, CycloneDX 1.5 BOM generation, 6-point manifest ↔ AIBOM cross-verification, and physical model file SHA-256 validation.
- **ALLOWED PITCH WORDING**:
  - *"Supports multi-contributor model release provenance using RFC 8785 canonicalized JSON manifests signed with standard Ed25519 (RFC 8032) public-key cryptography."*
  - *"Exports and validates offline CycloneDX 1.5-compatible AI Software Bill of Materials (AIBOM) with deep machine-learning model component metadata and IBVAP domain properties."*
  - *"The SupplyChainVerifier service performs end-to-end multi-check supply chain validation: signature authenticity, schema validity, on-disk physical model weight SHA-256 verification (thwarting hash substitution attacks), and cross-binding integrity between Manifest and AIBOM."*
- **FORBIDDEN / OVERCLAIMED WORDING**:
  - ❌ *"Official third-party CycloneDX certification."* (Produces JSON conforming to CycloneDX 1.5 schema; has not undergone external vendor certification).
  - ❌ *"C2PA hardware-embedded provenance."* (Cryptographic software binding of manifest, AIBOM, and weight files; not hardware-enclave C2PA camera sensor signing).

---

### Claim 9: Air-Gapped Edge Operation

- **CLAIM**: The platform operates fully autonomously at remote border outposts without internet connectivity.
- **STATUS**: **VERIFIED**
- **CODE EVIDENCE**: `tests/test_airgap_and_offline_integrity.py`, embedded DuckDB/SQLite
- **TEST EVIDENCE**: Automated socket interception test blocking external network access
- **BENCHMARK EVIDENCE**: Zero outbound WAN calls during inference, ledger commit, and assurance auditing
- **ALLOWED PITCH WORDING**:
  - *"Engineered for air-gapped, isolated edge deployment with zero cloud dependencies, zero external API calls, and local embedded database storage."*
- **FORBIDDEN / OVERCLAIMED WORDING**:
  - ❌ *"100% air-gapped guarantee."* (Software runs locally; air-gap integrity also requires physical facility and hardware security).
  - ❌ *"Integrated with cloud Bhashini / Sarvam AI / sovereign translation APIs."* (These are external cloud services that would violate air-gap constraints; they are deferred and NOT integrated).

---

### Claim 10: Ingestion & Shared-Memory Streaming

- **CLAIM**: Video frames are transported between ingestion workers and streaming endpoints with zero disk I/O.
- **STATUS**: **VERIFIED**
- **CODE EVIDENCE**: `services/ingestion/shared_frame_buffer.py:SharedFrameWriter`, `services/ingestion/rolling_ring_buffer.py`
- **TEST EVIDENCE**: `test_shared_frame_buffer.py` (3 tests), `test_rolling_ring_buffer.py`
- **BENCHMARK EVIDENCE**: 32-byte binary Seqlock header in Windows Shared Memory + 8-second circular ring buffer (270 frames @ 30 FPS)
- **ALLOWED PITCH WORDING**:
  - *"Employs an atomic Seqlock-style protocol over shared memory to prevent torn frames during inter-process streaming to the operator dashboard."*
  - *"Maintains an in-memory 8-second rolling ring buffer for zero-disk-I/O forensic clip harvesting upon incident detection."*
- **FORBIDDEN / OVERCLAIMED WORDING**:
  - ❌ *"POSIX shared memory."* (On Windows 11, the implementation uses Python `multiprocessing.shared_memory` which maps to Windows Named Shared Memory, NOT POSIX `shm_open`).
  - ❌ *"DeepStream NVDEC hardware pipeline."* (Uses multi-threaded OpenCV / PyAV ingestion in Python; DeepStream is not installed).
