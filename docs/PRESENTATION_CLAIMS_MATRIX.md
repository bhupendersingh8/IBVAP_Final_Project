# TCVIAF / IBVAP — Presentation Claims Matrix
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance  
**Audit Date**: September 30, 2026  
**Branch**: `feature/tcvf-assurance-layer`  
**Purpose**: Maps every presentation-facing claim to its executable evidence. No claim exists without verified code + test.

---

## Claim/Evidence Status Legend

| Symbol | Meaning |
|:---:|:---|
| ✅ | Claim is accurate and backed by executable test |
| ⚠️ | Claim required terminology correction (fixed in this audit) |
| ❌ | Claim was unsupported or overclaimed (removed/corrected) |

---

## Data Integrity Claims

| # | Presentation Claim | Actual Algorithm | Code Location | Test Evidence | Status |
|:---:|:---|:---|:---|:---|:---:|
| 1 | Exact duplicate detection via SHA-256 | `hashlib.sha256(raw_bytes)` full-image digest | `data_integrity.py:check_duplicates()` | `test_data_integrity.py::test_exact_duplicate_detection` | ✅ |
| 2 | Near-duplicate detection via 64-bit Average Hash (aHash-64) | `compute_ahash()`: 8×8 grayscale downsample → mean threshold → 64-bit binary hash, Hamming distance ≤ 10 | `data_integrity.py:compute_ahash()`, `compute_hamming_distance()` | `test_data_integrity.py::test_perceptual_near_duplicate_detection` | ⚠️ Function was named `compute_phash` — renamed to `compute_ahash` (the algorithm is aHash, not pHash) |
| 3 | YOLO label coordinate geometry validation | Checks `x,y,w,h ∈ [0,1]`, non-negative area, class ID bounds | `data_integrity.py:check_label_integrity()` | `test_data_integrity.py::test_yolo_label_anomaly_detection` | ✅ |
| 4 | Centroid-Distance Anomaly Indicator (OOD) with 3σ heuristic | Euclidean distance from feature centroid, threshold = μ + 3σ | `data_integrity.py:check_ood()` (method='centroid_distance') | `test_data_integrity.py::test_ood_with_deterministic_reference_baseline` | ✅ |
| 5 | Two-sample Kolmogorov-Smirnov distribution shift | Per-channel 1D KS test with Bonferroni correction (α=0.05/k) | `data_integrity.py:check_distribution_shift()` (method='ks') | `test_data_integrity.py::test_distribution_shift_ks_detection` | ✅ |
| 6 | Multivariate Mahalanobis Distance OOD | Regularized covariance matrix inversion (Σ + λI)⁻¹, Chi-Square critical values | `data_integrity.py:check_ood_mahalanobis()` | `test_advanced_ood_and_mmd.py::test_mahalanobis_ood_detection` | ✅ |
| 7 | kNN Feature Density OOD | k-Nearest Neighbors Euclidean density vs 95th percentile of intra-reference | `data_integrity.py:check_ood_knn_density()` | `test_advanced_ood_and_mmd.py::test_knn_ood_detection` | ✅ |
| 8 | Kernel Maximum Mean Discrepancy (MMD) shift | Unbiased U-statistic with Gaussian RBF kernel, median bandwidth heuristic, permutation test | `data_integrity.py:check_distribution_shift_mmd()` | `test_advanced_ood_and_mmd.py::test_kernel_mmd_shift_detection` | ✅ |
| 9 | Active Label Quality (Cleanlab-inspired) | Aspect ratio >10:1, area anomaly, IoU>0.85 collision, confident label flip (p>0.70, IoU>0.50, ŷ≠y) | `data_integrity.py:check_label_quality()` | `test_label_quality_assurance.py` (4 tests) | ✅ |

## Model Integrity Claims

| # | Presentation Claim | Actual Algorithm | Code Location | Test Evidence | Status |
|:---:|:---|:---|:---|:---|:---:|
| 10 | Behavioral Model Fingerprinting (`ibvap-behavior-v1` probe battery) | N=10 deterministic seeded synthetic probes (lighting, contrast, geometry), composite divergence score S ∈ [0,1] | `model_fingerprint.py:ModelFingerprintEngine` | `test_behavioral_fingerprint.py` (14 tests) | ✅ |
| 11 | Model weight digest verification | SHA-256 of on-disk `.pt` file bytes | `model_fingerprint.py:compute_weight_digest()` | `test_behavioral_fingerprint.py::test_model_identity_mismatch_detected` | ✅ |

## Inference Provenance Claims

| # | Presentation Claim | Actual Algorithm | Code Location | Test Evidence | Status |
|:---:|:---|:---|:---|:---|:---:|
| 12 | Cryptographic inference provenance binding (8-field) | SHA-256 of canonical (frame hash + model ID + weight digest + preprocessing config + inference config + sorted output + timestamp + sequence + nonce) | `inference_provenance.py:InferenceProvenanceEngine` | `test_inference_provenance.py` (29 tests) | ✅ |
| 13 | Merkle hash chaining (tamper-evident) | Sequential: Hᵢ = SHA256(Hᵢ₋₁ ‖ digest(Recordᵢ)), monotonic sequence, 16-byte random nonce | `inference_provenance.py:verify_provenance_chain()` | `test_inference_provenance.py::test_chain_integrity_verification` | ✅ |
| 14 | 17-scenario fault-injection battery (controlled mutation detection) | 17 mutation cases: pixel, hash, weights, model ID, preprocessing, config, class, confidence, bbox, timestamp, sequence, nonce, previous hash, substitution, replay, chain break, valid | `benchmarks/run_fault_injection.py` | `fault_injection_latest.json`: 17/17 PASS | ✅ |
| 15 | Replay attack detection | Nonce uniqueness check + monotonic sequence validation + timestamp freshness | `inference_provenance.py:verify_provenance_chain()` | `test_inference_provenance.py::test_replay_attack_detection` | ✅ |

## Post-Quantum Cryptography Claims

| # | Presentation Claim | Actual Algorithm | Code Location | Test Evidence | Status |
|:---:|:---|:---|:---|:---|:---:|
| 16 | SHAKE-256 (FIPS 202) 512-bit digest | `hashlib.shake_256(data).hexdigest(64)` — 64-byte output | `post_quantum.py:compute_shake256_digest()` | `test_post_quantum_crypto.py::test_shake256_digest_properties` | ✅ |
| 17 | Hybrid hash commitment (SHA-256 + SHAKE-256) | SHA256(SHA256(m) ‖ SHAKE256(m, 64)) | `post_quantum.py:compute_hybrid_hash_commitment()` | `test_post_quantum_crypto.py::test_hybrid_hash_commitment` | ✅ |
| 18 | WOTS+ one-time signatures over SHAKE-256 | Winternitz w=16, 67 chains of SHAKE-256, pure hash-based | `post_quantum.py:WOTSPlusSHAKE256` | `test_post_quantum_crypto.py::test_wots_plus_keypair_and_signing` | ✅ |
| 19 | "Category 5 (256-bit Grover)" quantum security | SHAKE-256 with 512-bit output provides 256-bit collision resistance against Grover's quantum search | `post_quantum.py` docstring + `crypto_ledger.py:export_audit_certificate()` | `test_post_quantum_crypto.py::test_pq_assurance_status` | ⚠️ Accurate for SHAKE-256 hash security; WOTS+ is hash-based (immune to Shor's). "FIPS 205" label is aspirational — our WOTS+ follows the construction but is NOT a certified NIST implementation. Corrected in docs. |

## Governance & Operational Claims

| # | Presentation Claim | Actual Algorithm | Code Location | Test Evidence | Status |
|:---:|:---|:---|:---|:---|:---:|
| 20 | Analyst governance lifecycle (ACCEPT/REVIEW/QUARANTINE) | Three-tier disposition with human override isolation. `governance_audit` table preserves immutable audit trail | `data_integrity.py:recommend_governance_disposition()`, `assurance.py` router | `test_analyst_governance.py` (2 tests) | ✅ |
| 21 | Air-gapped edge operation | Zero external WAN/cloud socket calls. DuckDB/SQLite local embedded storage | Full codebase (no `requests`, no cloud SDK calls in assurance path) | `test_airgap_and_offline_integrity.py::test_airgap_assurance_pipeline_execution` | ⚠️ Was "100% Air-Gapped" — corrected to "Air-Gapped Edge" (no system can guarantee 100% air-gap at software level alone) |

## Performance Claims

| # | Presentation Claim | Actual Measured Value | Source | Status |
|:---:|:---|:---|:---|:---:|
| 22 | Baseline mean latency | 14.94 ms (66.9 FPS) | `benchmarks/results/latest.json` | ✅ |
| 23 | Secured pipeline mean latency | 18.13 ms (53.7 FPS) | `benchmarks/results/latest.json` | ✅ |
| 24 | Assurance overhead | +3.19 ms (+21.4%) | `benchmarks/results/latest.json` | ✅ |
| 25 | Provenance hashing cost | 0.562 ms | `benchmarks/results/latest.json` | ✅ |
| 26 | Ledger persistence cost | 5.554 ms | `benchmarks/results/latest.json` | ✅ |

---

## Terminology Corrections Applied in This Audit

| Original Term | Corrected Term | Reason |
|:---|:---|:---|
| `compute_phash` (function name) | `compute_ahash` | Algorithm is aHash (Average Hash), not pHash (Perceptual Hash) |
| "100% Air-Gapped Edge Node" | "Air-Gapped Edge Node" | No software system can guarantee 100% air-gap without hardware enforcement |
| "Verifies SHA-256 evidence **blockchain** sequence" | "Verifies SHA-256 evidence **hash chain** sequence" | System is a sequential hash chain, not a distributed blockchain |
| "tamper-proof logging" | "tamper-evident logging" | Hash chains provide evidence of tampering, not prevention |
| "100% self-contained" | "self-contained" | Removed absolute qualifier |
| "Guaranteed zero-crash" | "Resilient zero-crash" | No software can guarantee zero crashes in all conditions |
| `"chain_mode": "blockchain_merkle"` | `"chain_mode": "merkle_hash_chain"` | Not a blockchain |
| `"task": "evidence_tamper_proofing"` | `"task": "evidence_tamper_detection"` | Tamper evidence, not tamper proof |
| "Evidence Tamper-Proofing" | "Evidence Tamper-Detection" | Consistent with tamper-evident terminology |

---

## Claims NOT Made (Explicitly Excluded)

The following capabilities are **NOT** claimed by this system:

1. ❌ No Mahalanobis distance without actual covariance matrix inversion — **Actually implemented** (`check_ood_mahalanobis()`)
2. ❌ No distributed blockchain — **Correct**: system uses local sequential hash chain
3. ❌ No post-quantum certified NIST implementation — **Correct**: WOTS+ follows the mathematical construction but is a pure-Python implementation, not a NIST-certified library
4. ❌ No cloud/external API dependencies — **Correct**: fully offline operation
5. ❌ No claimed detection accuracy percentages on real-world data — **Correct**: all numbers come from controlled synthetic benchmarks
6. ❌ No "tamper-proof" claim — **Correct**: system is tamper-evident
7. ❌ No facial recognition claims — **Correct**: deferred for privacy/compute
