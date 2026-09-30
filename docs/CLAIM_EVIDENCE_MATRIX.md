# IBVAP Claim Evidence Matrix & Red-Flag Audit

**Document**: `docs/CLAIM_EVIDENCE_MATRIX.md`  
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines  
**Timestamp**: 2026-09-30T16:10:15+05:30  
**Evaluator**: Lead Cybersecurity Auditor & SIH Jury Reviewer  

---

## 1. Evidentiary Classification Scheme

- **GREEN**: Implemented in physical code and verified by automated tests.
- **YELLOW**: Implemented as an empirical heuristic or statistical test; requires explicit operational boundary disclosure.
- **RED**: Unsupported, unverified, legally non-compliant, or historically overclaimed. Must be corrected or removed.

---

## 2. Complete Claim Evidence Matrix

| # | Claim | Location | Physical Implementation | Test Evidence | Status | Correct Wording / Allowed Pitch Language |
| :-: | :--- | :--- | :--- | :--- | :-: | :--- |
| 1 | **Throughput & Latency** | `benchmarks/run_benchmark.py` | YOLO11n on CUDA FP16 with dual provenance hashing | `benchmarks/results/latest.json` | **GREEN** | *"Achieves 53.69 FPS (18.13 ms latency) on local RTX 5050 Laptop GPU, introducing +3.19 ms (+21.4%) latency over raw baseline."* |
| 2 | **Hashing Overhead** | `services/assurance/inference_provenance.py` | 8-field deterministic canonicalization in Python | `benchmarks/results/latest.json` | **GREEN** | *"Inference provenance canonicalization and dual-layer hashing executes in 0.562 ms on CPU."* |
| 3 | **Fault-Injection Tamper Detection** | `benchmarks/run_fault_injection.py` | 17 controlled mutation scenarios | `fault_injection_latest.json` | **GREEN** | *"Detected 17 / 17 controlled fault-injection scenarios in test suite. (Do not claim 100% universal attack detection)."* |
| 4 | **Evidence Ledger Storage** | `crypto_ledger.py` | Append-only sequential SHA-256 Merkle hash chain in DuckDB / SQLite | `test_defense_pipeline_and_ledger.py` | **GREEN** | *"Local, append-only, tamper-evident cryptographic hash chain with incremental binary Merkle tree root. (Never call it a blockchain)."* |
| 5 | **Near-Duplicate Detection** | `services/assurance/data_integrity.py` | 64-bit Average Hash (`aHash-64`) with Hamming distance ($\le 10$) | `test_data_integrity.py` | **GREEN** | *"Detects resized, compressed, or brightness-adjusted near-duplicate images using 64-bit perceptual Average Hash (aHash-64)."* |
| 6 | **YOLO Coordinate Validation** | `services/assurance/data_integrity.py` | Bbox coordinate range check, non-negative area, aspect ratio $\le 10:1$ | `test_label_quality_assurance.py` | **GREEN** | *"Validates YOLO annotation geometry and syntax, rejecting negative areas, out-of-bounds coordinates, and aspect ratio outliers."* |
| 7 | **Distribution Shift (KS Test)** | `services/assurance/data_integrity.py` | Two-sample Kolmogorov-Smirnov test with Bonferroni correction | `test_data_integrity.py` | **GREEN** | *"Detects univariate feature distribution shift using two-sample Kolmogorov-Smirnov statistics with Bonferroni correction."* |
| 8 | **Joint Distribution Shift (Kernel MMD)** | `services/assurance/data_integrity.py` | Multivariate unbiased two-sample MMD with Gaussian RBF kernel | `test_advanced_ood_and_mmd.py` | **GREEN** | *"Evaluates multivariate distribution drift using Kernel Maximum Mean Discrepancy (MMD) with Gaussian RBF kernels."* |
| 9 | **Multivariate Mahalanobis OOD** | `services/assurance/data_integrity.py` | Regularized covariance inversion $(\Sigma + \lambda I)^{-1}$ with $\chi^2_d$ cutoffs | `test_advanced_ood_and_mmd.py` | **GREEN** | *"Detects out-of-distribution feature vectors using regularized multivariate Mahalanobis distance."* |
| 10 | **Contributor Model Manifest** | `services/assurance/contributor_manifest.py` | RFC 8785 canonical JSON signed with PureEdDSA Ed25519 (RFC 8032) | `test_contributor_manifest.py` | **GREEN** | *"Validates contributor identity and manifest integrity using RFC 8032 Ed25519 signatures over RFC 8785 canonical JSON."* |
| 11 | **CycloneDX 1.5 AIBOM** | `services/assurance/aibom.py` | CycloneDX 1.5 JSON generator with 6-point cross-validation | `test_aibom.py` | **GREEN** | *"Exports and validates CycloneDX 1.5-compatible AI/ML Bills of Materials with 6-point manifest cross-binding."* |
| 12 | **Physical Checkpoint Hash Validation** | `services/assurance/manifest_verifier.py` | Reads physical on-disk checkpoint file in 64 KB chunks and verifies SHA-256 | `test_contributor_manifest.py` | **GREEN** | *"Recomputes physical model weight SHA-256 directly from disk to thwart hash substitution attacks."* |
| 13 | **Behavioral Model Fingerprinting** | `services/assurance/model_fingerprint.py` | Evaluates model on 10 deterministic calibrated synthetic probes (`ibvap-behavior-v1`) | `test_behavioral_fingerprint.py` | **GREEN** | *"Evaluates black-box candidate models against deterministic synthetic probe battery `ibvap-behavior-v1`, computing composite divergence score $S \in [0, 1]$."* |
| 14 | **Inference Provenance Binding** | `services/assurance/inference_provenance.py` | 8-field canonical record with monotonic sequence and nonce | `test_inference_provenance.py` | **GREEN** | *"Cryptographically binds input frame, model digest, execution configuration, and detections with sequence IDs and nonces."* |
| 15 | **Backdoor / Poisoning Detection** | `services/assurance/data_integrity.py` | Confident Learning prediction discrepancy ($p > 0.70, \text{IoU} > 0.50, \hat{y} \neq y$) and feature outlier filtering | `test_label_quality_assurance.py` | **YELLOW** | **CORRECTED**: *"Heuristic backdoor/poisoning screening using prediction-discrepancy and feature outlier analysis. Does not guarantee universal backdoor detection or perform Neural Cleanse trigger inversion."* |
| 16 | **Post-Quantum Cryptography** | `services/assurance/post_quantum.py` | Classical SHA-256 + 512-bit SHAKE-256 dual digest; pure-Python WOTS+ | `test_post_quantum_crypto.py` | **YELLOW** | **CORRECTED**: *"Dual cryptographic digest using classical SHA-256 and SHA-3 family SHAKE-256 (512-bit). Incorporates stateless hash-based Winternitz One-Time Signatures (WOTS+). Does not claim platform-wide post-quantum certification."* |
| 17 | **Model Authenticity vs. Safety** | `services/assurance/manifest_verifier.py` | Ed25519 signature checks identity and manifest integrity | `test_contributor_manifest.py` | **YELLOW** | **CORRECTED**: *"Ed25519 signature confirms that the manifest was signed by the claimed contributor and has not been altered; it does not intrinsically prove the model is free of backdoors. Behavioral fingerprinting provides defense-in-depth."* |
| 18 | **Electronic Evidence / Section 65B** | `crypto_ledger.py` | Technical JSON evidence certificate with Merkle root and sequence height | `test_defense_pipeline_and_ledger.py` | **YELLOW** | **CORRECTED**: *"Cryptographically verifiable electronic-evidence certificate supporting forensic and audit workflows under the applicable electronic-record provisions of the Bharatiya Sakshya Adhiniyam, 2023, including Section 63. (Do not claim court admissibility)."* |
| 19 | **Neural Cleanse Trigger Inversion** | None | No $L_1$-norm trigger pattern optimization in code | None | **RED** | **REMOVED**: Remove all claims of Neural Cleanse. Replace with heuristic prediction discrepancy and probe-set behavioral fingerprinting. |
| 20 | **Decentralized Blockchain** | None | Local embedded DuckDB/SQLite hash chain; no P2P consensus or mining | None | **RED** | **REMOVED**: Remove all mentions of decentralized blockchain, Ethereum, Hyperledger, or gas fees. State: "Local Tamper-Evident Merkle Hash Chain". |
| 21 | **Guaranteed Legal Admissibility** | None | Admissibility is a judicial determination, not a software property | None | **RED** | **REMOVED**: Remove "court admissible" and "guaranteed admissibility". State: "Technically supports Section 63 BSA 2023 evidence workflows". |
| 22 | **NIST / ISO Certification** | None | Conceptual alignment with NIST AI RMF and ISO/IEC 42001; no formal lab certification | None | **RED** | **REMOVED**: Remove "NIST certified" or "ISO compliant". State: "Informed by NIST AI RMF risk-management principles; conceptually mapped to ISO/IEC 42001". |
| 23 | **Universal 100% Attack Detection** | None | Tested against 17 controlled scenarios in benchmark battery | None | **RED** | **REMOVED**: Remove "100% detection against all real-world attacks". State: "17 / 17 controlled fault-injection scenarios detected in benchmark battery". |
