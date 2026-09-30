# JUDGE EVIDENCE INDEX — SIH26228 TCVIAF / IBVAP
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines  
**Platform**: IBVAP — Integrity-Bound Vision Assurance Platform  
**Branch**: `feature/tcvf-assurance-layer`  
**Preserved Baseline**: Commit `25c05eba437058b07873ee9aba822ae173fdf1d2`  
**Audit Date**: September 30, 2026

---

## Quick Navigation

| Section | What It Proves |
|:---|:---|
| [1. Data Integrity](#1-data-integrity-assurance) | Training/validation data is verified for duplicates, corruption, OOD, and label quality |
| [2. Model Integrity](#2-model-behavioral-fingerprinting) | Model weights and behavior are cryptographically bound and drift-detectable |
| [3. Inference Provenance](#3-inference-provenance--tamper-detection) | Every inference output is tamper-evident with 8-field cryptographic binding |
| [4. Post-Quantum Readiness](#4-post-quantum-cryptographic-readiness) | Hash-based signatures immune to quantum computing threats |
| [5. Governance](#5-analyst-governance-lifecycle) | Human-in-the-loop disposition lifecycle with immutable audit trail |
| [6. Performance](#6-performance-benchmark) | Assurance overhead measured and documented |
| [7. Fault Injection](#7-fault-injection-battery) | 17 controlled tampering scenarios all detected |
| [8. Test Coverage](#8-automated-test-coverage) | 76 assurance tests + 396 total repository tests passing |

---

## 1. Data Integrity Assurance

### What it does
Detects corrupted, poisoned, duplicate, or out-of-distribution training/validation data before it enters the pipeline.

### Evidence files
| Check | Algorithm | Code | Test |
|:---|:---|:---|:---|
| Exact duplicates | SHA-256 full-image digest | [`data_integrity.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/data_integrity.py) | [`test_data_integrity.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/tests/test_data_integrity.py) |
| Near-duplicates | 64-bit Average Hash (aHash-64) + Hamming distance ≤ 10 | [`data_integrity.py:compute_ahash()`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/data_integrity.py#L54) | `test_data_integrity.py::test_perceptual_near_duplicate_detection` |
| Label integrity | YOLO coordinate geometry validation (x,y,w,h ∈ [0,1]) | [`data_integrity.py:check_label_integrity()`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/data_integrity.py) | `test_data_integrity.py::test_yolo_label_anomaly_detection` |
| Centroid-distance OOD | Euclidean distance from feature centroid, 3σ threshold | [`data_integrity.py:check_ood()`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/data_integrity.py) | `test_data_integrity.py::test_ood_with_deterministic_reference_baseline` |
| Mahalanobis OOD | Regularized covariance (Σ+λI)⁻¹, Chi-Square critical values | [`data_integrity.py:check_ood_mahalanobis()`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/data_integrity.py) | `test_advanced_ood_and_mmd.py::test_mahalanobis_ood_detection` |
| kNN density OOD | k-Nearest Neighbors Euclidean density, 95th percentile threshold | [`data_integrity.py:check_ood_knn_density()`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/data_integrity.py) | `test_advanced_ood_and_mmd.py::test_knn_ood_detection` |
| KS distribution shift | Two-sample KS per channel, Bonferroni α=0.05/k | [`data_integrity.py:check_distribution_shift()`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/data_integrity.py) | `test_data_integrity.py::test_distribution_shift_ks_detection` |
| Kernel MMD shift | Gaussian RBF kernel, median bandwidth, permutation test | [`data_integrity.py:check_distribution_shift_mmd()`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/data_integrity.py) | `test_advanced_ood_and_mmd.py::test_kernel_mmd_shift_detection` |
| Active label quality | Aspect ratio, area, IoU collision, confident learning label flip | [`data_integrity.py:check_label_quality()`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/data_integrity.py) | `test_label_quality_assurance.py` (4 tests) |

### Limitations declared
- Centroid-distance assumes spherical distribution
- Mahalanobis assumes unimodal elliptical distribution, requires N ≥ 3
- kNN sensitive to high-dimensional sparsity
- KS tests independent 1D marginals only; requires N ≥ 10
- MMD requires N ≥ 10 per distribution
- Cold-start: system reports `NO_REFERENCE_BASELINE` when no baseline exists

---

## 2. Model Behavioral Fingerprinting

### What it does
Detects whether a model behaves differently from its registered reference, even when filenames/metadata appear unchanged.

### Evidence files
| Component | Code | Test |
|:---|:---|:---|
| Probe battery (`ibvap-behavior-v1`, N=10 synthetic patterns) | [`model_fingerprint.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/model_fingerprint.py) | [`test_behavioral_fingerprint.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/tests/test_behavioral_fingerprint.py) (14 tests) |
| Weight digest (SHA-256 of `.pt` file) | `model_fingerprint.py:compute_weight_digest()` | `test_behavioral_fingerprint.py::test_model_identity_mismatch_detected` |
| Human override isolation | Automated fingerprint NEVER overwrites analyst disposition | `test_behavioral_fingerprint.py::test_analyst_override_preserved_against_model_anomaly` |

### Limitations declared
- Evaluates output-level behavioral drift, not internal neuron activations
- Requires offline baseline enrollment

---

## 3. Inference Provenance & Tamper Detection

### What it does
Cryptographically binds every inference record to 8 fields: input hash, model ID, weight digest, preprocessing config, inference config, output, timestamp, sequence/nonce.

### Evidence files
| Component | Code | Test |
|:---|:---|:---|
| 8-field provenance binding | [`inference_provenance.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/inference_provenance.py) | [`test_inference_provenance.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/tests/test_inference_provenance.py) (29 tests) |
| Merkle hash chaining | `inference_provenance.py:verify_provenance_chain()` | 17/17 fault-injection scenarios |
| Runtime integration | [`main_pipeline.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/main_pipeline.py) (provenance hook) | Verified via benchmark harness |
| Replay detection | Nonce uniqueness + monotonic sequence + timestamp freshness | `test_inference_provenance.py::test_replay_attack_detection` |

### Terminology: TAMPER-EVIDENT, not tamper-proof
Hash chains provide evidence of tampering. An attacker with OS root who rewrites the database AND all exported certificates simultaneously cannot be stopped by software alone.

---

## 4. Post-Quantum Cryptographic Readiness

### What it does
Provides quantum-resistant hash primitives and one-time signatures alongside classical SHA-256.

### Evidence files
| Component | Algorithm | Code | Test |
|:---|:---|:---|:---|
| SHAKE-256 digest | FIPS 202, 512-bit output (256-bit Grover resistance) | [`post_quantum.py:compute_shake256_digest()`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/post_quantum.py) | `test_post_quantum_crypto.py::test_shake256_digest_properties` |
| Hybrid commitment | SHA256(SHA256(m) ‖ SHAKE256(m,64)) | `post_quantum.py:compute_hybrid_hash_commitment()` | `test_post_quantum_crypto.py::test_hybrid_hash_commitment` |
| WOTS+ signatures | Winternitz w=16, 67 chains, pure hash-based | `post_quantum.py:WOTSPlusSHAKE256` | `test_post_quantum_crypto.py::test_wots_plus_keypair_and_signing` |

### Important qualification
This is a **pure-Python implementation following the WOTS+ mathematical construction**. It is NOT a NIST-certified library. The security argument is: hash-based signatures rely exclusively on hash collision/preimage resistance and are immune to Shor's algorithm.

---

## 5. Analyst Governance Lifecycle

### What it does
Enforces human-in-the-loop oversight with three-tier disposition (ACCEPT / REVIEW / QUARANTINE) and immutable audit trail.

### Evidence files
| Component | Code | Test |
|:---|:---|:---|
| Governance disposition | `data_integrity.py:recommend_governance_disposition()` | [`test_analyst_governance.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/tests/test_analyst_governance.py) (2 tests) |
| API endpoints | `assurance.py` router | `test_analyst_governance.py::test_api_governance_endpoints` |
| Immutable `governance_audit` table | `crypto_ledger.py` schema | Verified via ledger audit |

---

## 6. Performance Benchmark

### Measured on physical hardware (NOT simulated)
| Metric | Value | Source |
|:---|:---|:---|
| Hardware | NVIDIA GeForce RTX 5050 Laptop GPU, CUDA 12.8 | [`latest.json`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/benchmarks/results/latest.json) |
| Baseline mean latency | 14.94 ms (66.9 FPS) | `latest.json` |
| Secured mean latency | 18.13 ms (53.7 FPS) | `latest.json` |
| Assurance overhead | +3.19 ms (+21.4%) | `latest.json` |
| Provenance hashing | 0.562 ms | `latest.json` |
| SQLite ledger commit | 5.554 ms | `latest.json` |
| Evaluation: 50 frames @ 640×640 synthetic RGB, 10 warmup | — | `latest.json` |

**Operational significance**: Secured pipeline at 53.7 FPS exceeds real-time CCTV requirements (25–30 FPS).

---

## 7. Fault-Injection Battery

### 17 controlled mutation scenarios — 17/17 detected

Detailed results: [`fault_injection_latest.json`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/benchmarks/results/fault_injection_latest.json)

| # | Mutation | Detection Code | Result |
|:---:|:---|:---|:---:|
| 1 | Pixel byte modified | INPUT_TAMPERING_DETECTED | ✅ |
| 2 | Input hash modified | PROVENANCE_HASH_MISMATCH | ✅ |
| 3 | Model weights swapped | MODEL_TAMPERING_DETECTED | ✅ |
| 4 | Model ID changed | MODEL_NAME_MISMATCH | ✅ |
| 5 | Preprocessing resolution altered | PREPROCESSING_TAMPERING_DETECTED | ✅ |
| 6 | Confidence threshold altered | CONFIG_TAMPERING_DETECTED | ✅ |
| 7 | Class label modified | OUTPUT_TAMPERING_DETECTED | ✅ |
| 8 | Confidence score modified | OUTPUT_TAMPERING_DETECTED | ✅ |
| 9 | Bounding box coords modified | OUTPUT_TAMPERING_DETECTED | ✅ |
| 10 | Timestamp modified | PROVENANCE_HASH_MISMATCH | ✅ |
| 11 | Sequence ID modified | PROVENANCE_HASH_MISMATCH | ✅ |
| 12 | Nonce modified | PROVENANCE_HASH_MISMATCH | ✅ |
| 13 | Previous hash broken | PROVENANCE_HASH_MISMATCH | ✅ |
| 14 | Entire record substituted | SEQ_2_PROVENANCE_HASH_MISMATCH | ✅ |
| 15 | Replay (duplicate nonce) | PROVENANCE_REPLAY_DETECTED | ✅ |
| 16 | Chain break (linkage broken) | PROVENANCE_CHAIN_MISMATCH | ✅ |
| 17 | Valid untampered record | VERIFIED | ✅ |

**Important qualification**: This is a **controlled test harness** with known mutation inputs. It validates the detection mechanisms work correctly under laboratory conditions — it does NOT claim 100% detection of all adversarial attacks in the wild.

---

## 8. Automated Test Coverage

### Focused Assurance Tests (76/76 passing)
| Test File | Count | Focus |
|:---|:---:|:---|
| `test_data_integrity.py` | 12 | Duplicates, near-dupes, labels, OOD, KS shift |
| `test_analyst_governance.py` | 2 | Governance lifecycle + API |
| `test_behavioral_fingerprint.py` | 14 | Probe battery, weight digest, human override |
| `test_inference_provenance.py` | 29 | 8-field binding, tampering, replay, chain |
| `test_advanced_ood_and_mmd.py` | 6 | Mahalanobis, kNN, Kernel MMD |
| `test_label_quality_assurance.py` | 6 | Aspect ratio, area, collision, label flip |
| `test_post_quantum_crypto.py` | 6 | SHAKE-256, hybrid commitment, WOTS+ |
| `test_airgap_and_offline_integrity.py` | 1 | Socket interception air-gap verification |

### Full Repository (396 passed, 2 known environment failures)
- 2 failures: `test_cctv_discovery.py` tests requiring active MediaMTX RTSP daemon on port 8554

### Preserved Baseline
- Branch `ibvap-preserved-base` → commit `25c05eba437058b07873ee9aba822ae173fdf1d2` ✅
- Tag `ibvap-original-final` → commit `25c05eba437058b07873ee9aba822ae173fdf1d2` ✅

---

## Repository Structure (Assurance Layer)

```
services/assurance/
├── data_integrity.py          # All data-level checks (duplicates, OOD, shift, labels)
├── model_fingerprint.py       # Behavioral model fingerprinting
├── inference_provenance.py    # 8-field cryptographic binding + Merkle chain
└── post_quantum.py            # SHAKE-256, hybrid commitment, WOTS+

crypto_ledger.py               # SHA-256 Merkle Hash Chain + DuckDB/SQLite ledger
main_pipeline.py               # Runtime integration (provenance hook)

apps/backend/routers/assurance.py  # REST API for all assurance capabilities

benchmarks/
├── run_benchmark.py           # Performance overhead measurement
├── run_fault_injection.py     # 17-scenario mutation battery
└── results/
    ├── latest.json            # Benchmark numbers
    └── fault_injection_latest.json  # Fault injection results

tests/
├── test_data_integrity.py
├── test_analyst_governance.py
├── test_behavioral_fingerprint.py
├── test_inference_provenance.py
├── test_advanced_ood_and_mmd.py
├── test_label_quality_assurance.py
├── test_post_quantum_crypto.py
└── test_airgap_and_offline_integrity.py
```
