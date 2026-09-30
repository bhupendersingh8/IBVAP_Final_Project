# TCVIAF / IBVAP Authoritative Capability Matrix
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines  
**Platform**: IBVAP (Integrity-Bound Vision Assurance Platform)  
**Branch**: `feature/tcvf-assurance-layer`  
**Preserved Baseline**: Commit `25c05eba437058b07873ee9aba822ae173fdf1d2` (`ibvap-preserved-base`, `ibvap-original-final`)  
**Audit Date**: September 30, 2026  

---

## 1. Classification Taxonomy

Every capability in this matrix is strictly classified into one of five mutually exclusive engineering states:

- **IMPLEMENTED**: Fully coded, physically executable in the Python/CUDA environment, backed by passing automated tests, and accessible via runtime pipeline or REST API.
- **PARTIAL**: Executable code exists in the repository, but it is either optional, conditionally loaded, or not active in the primary runtime path by default.
- **REFERENCED ONLY**: Conceptual architectural documentation, configuration templates, or design references exist, but the underlying SDK, library, or neural weights are not installed or executable in this environment.
- **NOT IMPLEMENTED**: Feature was mentioned in conceptual pitch materials or theoretical proposals, but no code, configuration, or tests exist in the repository.
- **DEFERRED**: Intentionally excluded or deferred from edge deployment due to hardware, latency, privacy, or dependency constraints.

---

## 2. Capability Matrix

### 2.1 Data & Training Assurance (SIH26228 §2.2.1)

| Capability | Status | Implementation | Tests | Runtime / API | Evidence | Limitations |
| :--- | :---: | :--- | :--- | :---: | :--- | :--- |
| **Exact Duplicate Detection** | **IMPLEMENTED** | `services/assurance/data_integrity.py:check_duplicates()` | `test_data_integrity.py::test_exact_duplicate_detection` | API / Batch | SHA-256 full byte digest comparison | Invariant to compression or bitwise modifications; matches bit-identical images only. |
| **Perceptual Near-Duplicate Detection** | **IMPLEMENTED** | `services/assurance/data_integrity.py:compute_ahash()` | `test_data_integrity.py::test_perceptual_near_duplicate_detection` | API / Batch | 64-bit Average Hash (`aHash-64`) with Hamming distance $\le 10$ | Effective against mild compression and noise; ineffective against severe crops or $>15^\circ$ rotations. |
| **YOLO Label Integrity Validation** | **IMPLEMENTED** | `services/assurance/data_integrity.py:check_label_integrity()` | `test_data_integrity.py::test_yolo_label_anomaly_detection` | API / Batch | Validates $x, y, w, h \in [0, 1]$, non-negative area, class bounds, syntax errors | Structural coordinate boundary check; does not semantically re-label misclassified objects. |
| **Active Label Noise (Cleanlab-Inspired)** | **IMPLEMENTED** | `services/assurance/data_integrity.py:check_label_quality()` | `test_label_quality_assurance.py` (6 tests) | API / Batch | Bbox aspect ratio ($>10:1$), box collisions ($\text{IoU} > 0.85$), Confident Learning label flipping ($p>0.70, \text{IoU}>0.50, \hat{y} \neq y$) | Native heuristic algorithm inspired by Cleanlab principles; does not import the external `cleanlab` package. |
| **Centroid-Distance OOD Detection** | **IMPLEMENTED** | `services/assurance/data_integrity.py:check_ood()` (`method="centroid_distance"`) | `test_data_integrity.py::test_ood_with_deterministic_reference_baseline` | API / Batch | Euclidean distance from enrolled feature centroid with $3\sigma$ heuristic | Assumes spherical feature distribution; requires enrolled baseline ($N \ge 3$). |
| **Multivariate Mahalanobis OOD** | **IMPLEMENTED** | `services/assurance/data_integrity.py:check_ood_mahalanobis()` | `test_advanced_ood_and_mmd.py::test_mahalanobis_ood_detection` | API / Batch | Regularized covariance matrix inversion $(\Sigma + \lambda I)^{-1}$ with $\chi^2_d$ critical values | Assumes unimodal elliptical Gaussian feature distribution; sensitive to rank deficiency without regularization. |
| **k-Nearest Neighbors (kNN) Density OOD** | **IMPLEMENTED** | `services/assurance/data_integrity.py:check_ood_knn_density()` | `test_advanced_ood_and_mmd.py::test_knn_ood_detection` | API / Batch | Non-parametric $k$-NN Euclidean density vs. 95th percentile of intra-reference baseline | Sensitive to local cluster density variations and curse of dimensionality if embedding dimension is large. |
| **Two-Sample Kolmogorov-Smirnov Shift** | **IMPLEMENTED** | `services/assurance/data_integrity.py:check_distribution_shift()` (`method="ks"`) | `test_data_integrity.py::test_distribution_shift_ks_detection` | API / Batch | Per-feature 1D two-sample KS test using `scipy.stats.ks_2samp` with Bonferroni correction ($\alpha = 0.05 / k$) | Evaluates independent 1D marginal projections; requires minimum sample size $N \ge 10$. |
| **Kernel Maximum Mean Discrepancy (MMD)** | **IMPLEMENTED** | `services/assurance/data_integrity.py:check_distribution_shift_mmd()` | `test_advanced_ood_and_mmd.py::test_kernel_mmd_shift_detection` | API / Batch | Multivariate two-sample unbiased MMD U-statistic with Gaussian RBF kernel, median bandwidth, and permutation testing | Evaluates joint multivariate distributions; requires $N \ge 10$ samples per distribution. |
| **Neural Cleanse / Trigger Inversion** | **NOT IMPLEMENTED** | None | None | None | None | Requires iterative gradient backpropagation ($L_1$-norm trigger inversion) incompatible with edge inference. |
| **Spectral Signatures** | **NOT IMPLEMENTED** | None | None | None | None | Requires internal hidden representation covariance inspection; not implemented. |
| **CycloneDX 1.5 AIBOM Generator** | **IMPLEMENTED** | `services/assurance/aibom.py:generate_cyclonedx_aibom()` | `test_aibom.py` (11 tests) | API / CLI | CycloneDX 1.5 machine-learning-model BOM with IBVAP extensions and cross-binding verification | Follows CycloneDX 1.5 schema format; not certified by external commercial body. |

---

### 2.2 Model Integrity & Authenticity (SIH26228 §2.2.2)

| Capability | Status | Implementation | Tests | Runtime / API | Evidence | Limitations |
| :--- | :---: | :--- | :--- | :---: | :--- | :--- |
| **Model Weight SHA-256 Digest** | **IMPLEMENTED** | `services/assurance/model_fingerprint.py:compute_weight_digest()` | `test_behavioral_fingerprint.py::test_model_identity_mismatch_detected` | **YES** (Tripwire Breach) | Hashing of on-disk `.pt` model checkpoint | Detects bitwise alterations of model weights; requires reference hash. |
| **Behavioral Model Fingerprinting** | **IMPLEMENTED** | `services/assurance/model_fingerprint.py:ModelFingerprintEngine` | `test_behavioral_fingerprint.py` (14 tests) | API / Batch | Evaluates deterministic probe battery `ibvap-behavior-v1` ($N=10$ synthetic stimuli) and calculates divergence score $S \in [0, 1]$ | Black-box behavioral test evaluating output drift across contrast/geometry/illumination; requires enrolled profile. |
| **Architecture & Preprocessing Binding** | **IMPLEMENTED** | `services/assurance/model_fingerprint.py:create_reference_fingerprint()` | `test_behavioral_fingerprint.py::test_preprocessing_config_change_alters_fingerprint_binding` | API / Batch | Cryptographically binds architecture ID, imgsz, and NMS configs into fingerprint digest | Detects unauthorized configuration changes. |
| **Offline Contributor Model Manifest** | **IMPLEMENTED** | `services/assurance/contributor_manifest.py:create_contributor_manifest()` | `test_contributor_manifest.py` (17 tests) | API / CLI | Deterministic RFC-8785 canonical manifest binding model, preprocessing, and behavioral fingerprints | Offline developer manifest; requires explicit contributor metadata. |
| **Ed25519 Contributor Signatures** | **IMPLEMENTED** | `services/assurance/contributor_manifest.py:sign_contributor_manifest()` | `test_contributor_manifest.py` (17 tests) | API / CLI | Asymmetric Ed25519 (RFC 8032) signing of canonical model manifests | Requires model contributor to hold private key; public key embedded in manifest. |
| **Manifest / AIBOM Integrity Binding** | **IMPLEMENTED** | `services/assurance/aibom.py:verify_manifest_aibom_binding()` | `test_aibom.py` | API / Service | Strict 6-point cross-verification of model SHA-256, preprocessing, fingerprint, and contributor IDs | Exposes tampering discrepancies between BOM document and signed developer manifest. |

---

### 2.3 Inference Provenance & Tamper Assurance (SIH26228 §2.2.3)

| Capability | Status | Implementation | Tests | Runtime / API | Evidence | Limitations |
| :--- | :---: | :--- | :--- | :---: | :--- | :--- |
| **8-Field Provenance Binding** | **IMPLEMENTED** | `services/assurance/inference_provenance.py:InferenceProvenanceEngine` | `test_inference_provenance.py` (29 tests) | **YES** (`main_pipeline.py:920`) | Binds input hash, model ID, weights SHA-256, config digest, prep digest, output digest, sequence ID, and nonce | Bound directly to tripwire perimeter breach events in the live pipeline. |
| **Sequential Hash Chaining** | **IMPLEMENTED** | `crypto_ledger.py:compute_block_hash()` | `test_inference_provenance.py::test_hash_chain_break_detection` | **YES** | Block hash links sequentially: $H_i = \text{SHA256}(H_{i-1} \parallel \text{frame\_hash} \parallel \text{timestamp} \parallel \dots)$ | **Tamper-evident**: Exposes breaks in sequence; does not prevent disk overwriting if attacker has OS root. |
| **Binary Merkle Tree Root** | **IMPLEMENTED** | `crypto_ledger.py:compute_merkle_root()` | `test_inference_provenance.py` | **YES** | Pairwise binary leaf reduction over block hashes | Incremental root recalculation over historical sequence. |
| **Replay & Nonce Tracking** | **IMPLEMENTED** | `services/assurance/inference_provenance.py:verify_provenance_chain()` | `test_inference_provenance.py::test_replay_attack_detection` | API / Audit | 16-byte random hex nonce (`secrets.token_hex(16)`) and monotonic sequence verification | Detects injected, re-ordered, or replayed records. |
| **Post-Quantum Hybrid Commitment** | **IMPLEMENTED** | `services/assurance/post_quantum.py:compute_hybrid_hash_commitment()` | `test_post_quantum_crypto.py::test_hybrid_hash_commitment` | **YES** | Classical-quantum hybrid digest: $\text{SHA256}(\text{SHA256}(m) \parallel \text{SHAKE256}(m, 64))$ | 256 bits of collision resistance against Grover's quantum search. |
| **Post-Quantum Signatures (WOTS+)** | **IMPLEMENTED** | `services/assurance/post_quantum.py:WOTSPlusSHAKE256` | `test_post_quantum_crypto.py::test_wots_plus_keypair_and_signing` | API / Cert | Winternitz one-time signature ($w=16$, 67 chains) over SHAKE-256 | Pure hash-based signature immune to Shor's algorithm; pure-Python implementation (not a certified NIST library). |
| **CUDA-Accelerated SHA-256** | **NOT IMPLEMENTED** | None | None | None | None | Hashing executes on CPU via standard `hashlib.sha256()` in sub-millisecond time. No CUDA SHA-256 kernel exists. |

---

### 2.4 Governance & Audit Logging (SIH26228 §2.2.4 & §2.2.5)

| Capability | Status | Implementation | Tests | Runtime / API | Evidence | Limitations |
| :--- | :---: | :--- | :--- | :---: | :--- | :--- |
| **Three-Tier Disposition** | **IMPLEMENTED** | `services/assurance/data_integrity.py:recommend_governance_disposition()` | `test_analyst_governance.py::test_governance_disposition_lifecycle` | **YES** | `ACCEPT`, `REVIEW`, `QUARANTINE` recommendation logic | Automated findings recommend; human analyst decides. |
| **Human Override Isolation** | **IMPLEMENTED** | `crypto_ledger.py` (`governance_audit` table) | `test_data_integrity.py::test_analyst_override_preserved_against_automated_recommendation` | **YES** | Automated algorithms NEVER overwrite an analyst override | Immutable audit trail stored with analyst ID, timestamp, and justification. |
| **Section 65B Audit Certificate** | **IMPLEMENTED** | `crypto_ledger.py:export_audit_certificate()` | `test_post_quantum_crypto.py::test_section_65b_cert_includes_pq_readiness` | API / CLI | Exports JSON audit certificate with sequence height, Merkle root, and PQ readiness | Provides legal evidence chain-of-custody for judicial proceedings. |
| **Air-Gapped Local Operation** | **IMPLEMENTED** | `tests/test_airgap_and_offline_integrity.py` | `test_airgap_and_offline_integrity.py::test_airgap_assurance_pipeline_execution` | **YES** | Operates strictly on local embedded DuckDB / SQLite with zero WAN network calls | Verified via socket interception test blocking external network access. |

---

### 2.5 Computer Vision & Edge Processing Pipeline

| Capability | Status | Implementation | Tests | Runtime / API | Evidence | Limitations |
| :--- | :---: | :--- | :--- | :---: | :--- | :--- |
| **Zero-DCE++ Low-Light Restoration** | **IMPLEMENTED** | `ml/models/zero_dce.py:ZeroDCEPlusPlusRestorer` | `test_neural_restoration_and_actions.py` | **YES** (`main_pipeline.py:680`) | 8-iteration depthwise separable curve estimation applied if mean luminance $< 40.0$ | Sub-10ms latency; preserves frame quality in severe low-light conditions. |
| **CLAHE Dynamic Contrast Fallback** | **IMPLEMENTED** | `ml/models/zero_dce.py:150` | `test_neural_restoration_and_actions.py` | Fallback | OpenCV CLAHE contrast enhancement | Fallback mode when neural restorer is disabled or running on constrained CPU. |
| **Primary Object Detection (YOLO11n)** | **IMPLEMENTED** | `main_pipeline.py:358` | `test_pipeline.py`, `test_detection.py` | **YES** | Ultralytics YOLO11n (`weights/yolo11n.pt`) on CUDA FP16 | Primary real-time detector (640x640). |
| **Two-Stage YOLO26x Cascade Verifier** | **IMPLEMENTED** | `services/detection/two_stage_yolo26.py` | `test_two_stage_yolo26.py` | **YES** (`main_pipeline.py:747`) | Fast gating (conf 0.25) with heavy verifier (`weights/yolo26x.pt`, 56.9M params) | Verifies borderline detections ($0.25 \le c \le 0.65$); cached for 30 frames. Note: architecture is YOLO11x. |
| **Multi-Object Tracking (ByteTrack)** | **IMPLEMENTED** | `main_pipeline.py:693` | `test_tracking.py` | **YES** | ByteTrack via `TrackerFactory` / Ultralytics wrapper | Tracks trajectories, velocities, and prone/crawling aspect ratios. |
| **BoT-SORT Tracker** | **PARTIAL** | `services/tracking/tracker_factory.py` | `test_trackers_diversity.py` | Optional | Supported via configuration (`tracker_type="botsort"`), but ByteTrack is default | Available for deployment; not active in default runtime configuration. |
| **Camouflage Segmentation (MobileSAM)** | **IMPLEMENTED** | `main_pipeline.py:763` | `test_pipeline.py` | **YES** | MobileSAM (`weights/mobile_sam.pt`) prompted on crawling or low-confidence ROIs | Generates pixel-level target silhouettes; cached for 30 frames per track to preserve FPS. |
| **Facial Biometrics (ArcFace)** | **IMPLEMENTED** | `main_pipeline.py:367`, `services/biometrics/` | `test_authorized_personnel.py` | Asynchronous | InsightFace ArcFace ONNX (`weights/arcface_w600k_r50.onnx`) | Dispatched asynchronously via `ThreadPoolExecutor` to prevent blocking the video stream. |
| **Plate Recognition (ANPR)** | **IMPLEMENTED** | `main_pipeline.py:368`, `services/anpr/` | `test_anpr.py` | Asynchronous | `ContourPlateDetector` + `EasyOCREngine` | Dispatched asynchronously via `ThreadPoolExecutor` on vehicle bounding boxes. |
| **Seqlock Shared-Memory Frame Transport** | **IMPLEMENTED** | `services/ingestion/shared_frame_buffer.py` | `test_shared_frame_buffer.py` (3 tests) | Auxiliary | `SharedFrameWriter` / `Reader` with 32-byte binary Seqlock header in Windows Shared Memory | Atomic frame buffer for zero-disk-I/O streaming to web UI; prevents torn frames. |
| **Rolling Forensic Ring Buffer** | **IMPLEMENTED** | `services/ingestion/rolling_ring_buffer.py` | `test_rolling_ring_buffer.py` | **YES** | In-memory 8-second temporal context window (`[t-5s, t+3s]`, 270 frames @ 30 FPS) | Harvests forensic MP4 clip + SHA-256 upon virtual tripwire breach. |
| **D-FINE DETR Model** | **DEFERRED** | None | None | None | None | Heavier Transformer architecture; deferred to prevent edge frame rate drops. |
| **NVIDIA DeepStream SDK** | **REFERENCED ONLY** | `configs/nvidia_acceleration.yaml`, `deployment/nvidia/` | None | None | Config templates and runbooks exist | DeepStream is Linux-only; evaluated and rejected for Windows 11 host in `docs/OPEN_SOURCE_REFERENCE_AUDIT.md`. |
| **NVIDIA TAO 7 / Cosmos VLM** | **NOT IMPLEMENTED** | None | None | None | None | Conceptual references in old documentation; no code or weights exist in repository. |
| **Bhashini / Kutumb / Sarvam AI** | **DEFERRED** | None | None | None | None | Cloud APIs violate air-gapped edge requirement; no active SDK integration exists. |
