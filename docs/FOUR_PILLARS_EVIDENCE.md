# IBVAP — Four Pillars of Integrity Assurance
## Evidence, Specification, and Verification Map

**Project**: IBVAP (Integrity-Bound Vision Assurance Platform)  
**SIH Problem Statement**: SIH26228 (Blockchain & Cybersecurity)  
**Target Category**: Multi-Contributor Computer Vision Assurance  
**Repository Branch**: `feature/tcvf-assurance-layer`  

---

## Executive Summary

IBVAP decouples inference capability from inference integrity. Rather than treating raw neural network detections as ground truth, the platform wraps the complete computer vision lifecycle in a four-pillar assurance framework:

```
+---------------------------------------------------------------------------------------+
|                                  IBVAP TRUST ENGINE                                   |
+---------------------------+---------------------------+-------------------------------+
| 1. DATA TRUST             | 2. MODEL TRUST            | 3. INFERENCE TRUST            |
| - Average/Diff Hash       | - Ed25519 Manifests       | - Recursive SHA-256 Chains    |
| - OOD Feature Distance    | - CycloneDX AIBOM (v1.5)  | - SHAKE-256 Canonicalization  |
| - Confident Learning      | - Behavioral Probing      | - Nonce & Sequence Replay     |
| - Merkle Dataset Tree     | - Bit-Flip Sensitivity    | - Sub-3.2ms Overhead          |
+---------------------------+---------------------------+-------------------------------+
|                                  4. GOVERNANCE TRUST                                  |
| - Tri-State Verdict (ACCEPT / REVIEW / QUARANTINE)                                   |
| - Append-Only DuckDB / SQLite Evidence Ledger                                         |
| - Electronic Evidence Certificates under Bharatiya Sakshya Adhiniyam, 2023          |
+---------------------------------------------------------------------------------------+
```

---

## 1. Data Trust

### 1.1 Objective
Ensure training, fine-tuning, and operational surveillance frames are authentic, free from unauthorized label corruption, and non-redundant.

### 1.2 Implemented Capabilities & Algorithms

| Capability | Module & Implementation | Algorithmic Mechanism | Verification Test |
| :--- | :--- | :--- | :--- |
| **Near-Duplicate Detection** | [`services/assurance/data_integrity.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/data_integrity.py) | **Average Hash (aHash)** & **Difference Hash (dHash)**. Frames are downscaled to 8x8 grayscale, mean-thresholded into a 64-bit integer. Near duplicates detected when Hamming Distance $\le 10$ bits. | `tests/test_data_integrity.py` |
| **Dataset Merkle Integrity** | `DataIntegrityAuditor.build_dataset_merkle_tree` | SHA-256 leaves built from canonicalized image bytes concatenated with normalized annotation strings. Detects byte-level tampering in training sets. | `tests/test_data_integrity.py` |
| **Out-of-Distribution (OOD)** | [`services/assurance/ood_detection.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/ood_detection.py) | **Mahalanobis Distance** across feature representations ($z \sim \mathcal{N}(\mu, \Sigma)$). Flags abnormal surveillance scenes (e.g., lens occlusion, severe fog out of baseline). | `tests/test_ood_detection.py` |
| **Label Integrity Screening** | [`services/assurance/label_integrity.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/label_integrity.py) | **Confident Learning Principle**: Flags annotation discrepancy when model confidence $p > 0.70$, spatial overlap $\text{IoU} > 0.50$, but annotated class label $\hat{y} \neq y$. | `tests/test_label_integrity.py` |

### 1.3 Honesty Boundary
- aHash and dHash are used for deterministic perceptual duplicate screening.
- Confident learning does not claim automated dataset healing; it generates a triage queue for human annotators to review suspected label noise.

---

## 2. Model Trust

### 2.1 Objective
Verify the provenance, contributor identity, architecture composition, and behavioral consistency of checkpoints before operational admission.

### 2.2 Implemented Capabilities & Algorithms

| Capability | Module & Implementation | Algorithmic Mechanism | Verification Test |
| :--- | :--- | :--- | :--- |
| **Contributor Signing** | [`services/assurance/contributor_manifest.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/contributor_manifest.py) | **Ed25519 Public-Key Cryptography** (via PyCA `cryptography`). Signs SHA-256 weight hash, training config digest, and contributor metadata. | `tests/test_contributor_manifest.py` |
| **Software/AI Bill of Materials** | [`services/assurance/aibom_cyclonedx.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/aibom_cyclonedx.py) | **CycloneDX v1.5 JSON Specification**. Generates machine-readable dependency tree, base weights digest, dataset lineage, and license inventory. | `tests/test_aibom_cyclonedx.py` |
| **Behavioral Fingerprinting** | [`services/assurance/model_fingerprint.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/model_fingerprint.py) | **Output-Level Probe Battery**: Evaluates 5 deterministic synthetic CV probe patterns (daylight, low-light, fog, multi-scale grid, texture noise). Computes composite divergence: $S = 0.35 d_{\text{class}} + 0.30 \min(d_{\text{count}}, 1.0) + 0.20 \min(d_{\text{conf}}, 1.0) + 0.15 \min(d_{\text{geom}}, 1.0)$. Flags deviation when $S > 0.15$. | `tests/test_behavioral_fingerprint.py` |
| **One-Bit Mutation Sensitivity** | `ModelFingerprintEngine.compare_fingerprints` | Physical byte-level SHA-256 verification + behavioral probe scoring. Detects single-bit flip or parameter swap. | `tests/test_behavioral_fingerprint.py` |
| **Backdoor Heuristic Screening** | `screen_backdoors` / trigger battery | Trigger sensitivity profiling across synthetic patches (corner checkered, yellow block, watermark) to detect high-confidence anomaly spikes. | `tests/test_behavioral_fingerprint.py` |

### 2.3 Critical Defense Assertion: Signed $\neq$ Safe
As formally verified in `test_signed_but_behaviorally_suspicious_model` ([`tests/test_contributor_manifest.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/tests/test_contributor_manifest.py)):
- **Cryptographic Signature Verification** proves only *identity* and *unaltered transmission* from a contributor.
- A legitimate contributor's private key could sign a poisoned model, or credentials could be compromised.
- IBVAP enforces **Dual-Gated Admission**: A model must pass Ed25519 signature verification **AND** the behavioral fingerprint check. If the signature is valid but behavioral drift exceeds tolerance ($S \ge 0.15$), the model is placed in `QUARANTINE`.

---

## 3. Inference Trust

### 3.1 Objective
Bind every frame inference result cryptographically to its input pixels, model checkpoint, and execution parameters, rendering post-hoc evidence tampering detectable.

### 3.2 Implemented Capabilities & Algorithms

| Capability | Module & Implementation | Algorithmic Mechanism | Verification Test |
| :--- | :--- | :--- | :--- |
| **Recursive Hash Chain** | [`services/assurance/inference_provenance.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/inference_provenance.py) | Sequential cryptographic chaining: $H_i = \text{SHA256}(H_{\text{input}} \parallel H_{\text{model}} \parallel H_{\text{config}} \parallel H_{\text{output}} \parallel H_{i-1} \parallel T \parallel N)$. | `tests/test_inference_provenance.py` |
| **Canonical Output Digest** | `InferenceProvenanceEngine.hash_output` | Float coordinates clipped to $[0.0, 1.0]$ and rounded to 4 decimals, classes sorted alphabetically, serialized to deterministic JSON before hashing. | `tests/test_inference_provenance.py` |
| **Replay Protection** | `InferenceProvenanceEngine.validate_provenance_chain` | Monotonically strictly increasing sequence counter ($S_i = S_{i-1} + 1$) + 128-bit cryptographically random nonces (`os.urandom(16)`). | `tests/test_inference_provenance.py` |
| **Core Cryptography** | [`crypto_ledger.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/crypto_ledger.py) | **Production**: Standard SHA-256 + 512-bit SHAKE-256 for collision-resistant chaining. (Experimental WOTS+ is isolated in testing and not claimed for production). | `tests/test_defense_pipeline_and_ledger.py` |

### 3.3 Hardware Latency Profile (Tested RTX 5050 Configuration)
- **Baseline YOLO11n Inference**: 14.94 ms (66.92 FPS)
- **Assurance-Secured Inference**: 18.13 ms (53.69 FPS)
- **Assurance Overhead**: 3.19 ms (21.36%)
  - Canonicalization & Hashing: 0.562 ms
  - DuckDB Ledger Commit: 5.554 ms (amortized in asynchronous background queue)
- **Throughput Verdict**: 53.69 FPS on tested RTX 5050 configuration provides sufficient processing headroom for representative 25–30 FPS surveillance workloads.

---

## 4. Governance Trust

### 4.1 Objective
Provide an operational decision policy and verifiable electronic audit trail for human security analysts.

### 4.2 Implemented Capabilities & Algorithms

| Capability | Module & Implementation | Algorithmic Mechanism | Verification Test |
| :--- | :--- | :--- | :--- |
| **Tri-State Verdict Policy** | `InferenceProvenanceEngine.evaluate_governance` | Deterministic state machine outputting `ACCEPT`, `REVIEW`, or `QUARANTINE` based on hash integrity, drift scores, and anomaly tags. | `tests/test_governance.py` |
| **Append-Only Evidence Ledger** | [`crypto_ledger.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/crypto_ledger.py) | High-speed DuckDB relational engine (`evidence_ledger.duckdb`) with SQLite fallback (`evidence_ledger.sqlite3`). | `tests/test_defense_pipeline_and_ledger.py` |
| **Chain Integrity Verifier** | `CryptoEvidenceLedger.verify_chain_integrity` | Full sequential re-computation of Merkle hash chain from genesis block to current tip. | `tests/test_defense_pipeline_and_ledger.py` |
| **Electronic Evidence Certificate** | `CryptoEvidenceLedger.generate_section_65b_certificate` | Generates a cryptographically verifiable electronic-evidence certificate designed to support evidence/audit workflows under applicable provisions of the Bharatiya Sakshya Adhiniyam, 2023. | `tests/test_defense_pipeline_and_ledger.py` |

---

## 5. Summary Verification Status

```
+------------------------------------------------------------------------------------+
| Pillar        | Primary Code File                    | Verification Status         |
+---------------+--------------------------------------+-----------------------------+
| Data Trust    | services/assurance/data_integrity.py  | Verified by unit tests      |
| Model Trust   | services/assurance/model_manifest.py | Verified by unit tests      |
| Inference     | services/assurance/inference_prov... | Verified by unit tests      |
| Governance    | crypto_ledger.py & routers/assuran.. | Verified by unit tests      |
+------------------------------------------------------------------------------------+
Overall Suite: 446 passed / 0 failed / 1 environment-dependent integration test skipped
```
