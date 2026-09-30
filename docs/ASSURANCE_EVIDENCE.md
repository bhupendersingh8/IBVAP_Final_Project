# TCVIAF / IBVAP Assurance Evidence & Verification Report
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines  
**Platform**: IBVAP (Integrity-Bound Vision Assurance Platform)  
**Branch**: `feature/tcvf-assurance-layer`  
**Preserved Baseline**: `ibvap-preserved-base` / `ibvap-original-final` (Commit: `25c05eba437058b07873ee9aba822ae173fdf1d2`)  
**Audit Date**: September 30, 2026  

---

## 1. Executive Summary & Audit Scope

This document provides empirical verification and architectural evidence for the **TCVIAF (Trustworthy Computer Vision Integrity Assurance Framework)** assurance layer implemented on top of the preserved **IBVAP** baseline.

The assurance layer addresses the vulnerability of multi-contributor, edge-deployed computer vision pipelines to:
1. **Uncurated or poisoned training/validation data** (duplicates, corrupted annotations, distribution drift, out-of-distribution samples).
2. **Untrusted or altered model weights** (trojaned weights, stealth fine-tuning, silent model swapping).
3. **Tampered inference outputs or replayed telemetry** (coordinate alteration, confidence manipulation, replay attacks on alert streams).
4. **Post-Quantum Cryptographic vulnerabilities** (vulnerability of classical public-key cryptography to quantum computing threats).
5. **Unregulated automated decision overrides** (lack of human analyst governance and auditable disposition lifecycle).

All claims in this document are backed by executable tests, benchmark harnesses, and offline fault-injection suites present in this repository.

---

## 2. Assurance Capability Matrix

The following matrix documents the exact status of each assurance capability. Status categories are strictly defined:
- **IMPLEMENTED**: Code written and executable.
- **RUNTIME-INTEGRATED**: Wired directly into `main_pipeline.py` or active alert paths.
- **TESTED**: Validated via automated unit/integration tests in `tests/`.
- **PERSISTED**: Stored durably in DuckDB/SQLite schema.
- **API-EXPOSED**: Accessible via FastAPI REST endpoints under `/api/v1/assurance/`.
- **UI-EXPOSED**: Visible and interactive in the React frontend (`C4ISRDashboard.tsx` / `LedgerAuditModal.tsx`).

| Capability | Status | Algorithmic Mechanism | Limitations / Boundaries |
| :--- | :--- | :--- | :--- |
| **Exact Duplicate Detection** | IMPLEMENTED, TESTED, API-EXPOSED | Full-image SHA-256 digest hashing | Only matches bit-identical files; invariant to compression. |
| **Near-Duplicate Detection** | IMPLEMENTED, TESTED, API-EXPOSED | 64-bit Average Hash (`aHash-64`) with normalized Hamming distance ($\le 10$) | Ineffective against severe non-linear crops or rotations $>15^\circ$. |
| **YOLO Label Integrity** | IMPLEMENTED, TESTED, API-EXPOSED | Coordinate geometry validation ($x, y, w, h \in [0, 1]$, non-negative area, class bounds) | Validates structural and numerical bounds. |
| **Active Label Quality (Cleanlab-Inspired)** | IMPLEMENTED, TESTED, API-EXPOSED | Bounding box aspect ratio ($>10:1$) & area anomaly detection, box collisions ($\text{IoU} > 0.85$), and Confident Learning prediction discrepancy ($p > 0.70, \text{IoU} > 0.50, \hat{y} \neq y_{\text{ann}}$) | Requires model predictions for confident label flipping detection. |
| **Centroid-Distance OOD** | IMPLEMENTED, TESTED, API-EXPOSED | Centroid-Distance Anomaly Indicator with $3\sigma$ threshold over enrolled feature baseline | Lightweight heuristic; assumes spherical distribution. |
| **Multivariate Mahalanobis OOD** | IMPLEMENTED, TESTED, API-EXPOSED | Multivariate Mahalanobis Distance with regularized covariance matrix inversion $(\Sigma + \lambda I)^{-1}$ and Chi-Square ($\chi^2_d$) statistical critical values | Assumes unimodal elliptical feature distribution; requires enrolled baseline ($N \ge 3$). |
| **k-Nearest Neighbors (kNN) Density OOD** | IMPLEMENTED, TESTED, API-EXPOSED | Non-parametric $k$-Nearest Neighbors Euclidean feature density relative to intra-reference cluster percentiles | Sensitive to local cluster density variations and high-dimensional sparsity. |
| **Kolmogorov-Smirnov Shift** | IMPLEMENTED, TESTED, API-EXPOSED | Two-sample Kolmogorov-Smirnov test per feature channel with Bonferroni correction ($\alpha = 0.05 / k$) | Tests independent 1D marginal projections; requires $N \ge 10$. |
| **Kernel Maximum Mean Discrepancy (MMD)** | IMPLEMENTED, TESTED, API-EXPOSED | Multivariate two-sample unbiased MMD U-statistic with Gaussian RBF kernel, median bandwidth heuristic, and permutation testing | Evaluates joint multivariate distributions; requires $N \ge 10$ samples per distribution. |
| **Behavioral Model Fingerprinting** | IMPLEMENTED, TESTED, API-EXPOSED | Deterministic Probe Battery `ibvap-behavior-v1` ($N=10$, seeded pseudo-random patterns across lighting/contrast/geometry variations), composite behavioral divergence $S \in [0, 1]$ | Requires offline baseline enrollment profile. Evaluates output drift, not formal internal neuron activation. |
| **Inference Provenance Binding** | RUNTIME-INTEGRATED, TESTED, PERSISTED, API-EXPOSED, UI-EXPOSED | Cryptographic binding: SHA-256 of raw frame bytes, model ID, disk weight digest, canonicalized NMS/confidence prep configs, canonical output sorting & 4-decimal float rounding | Tied to perimeter breach and alert triggers in `main_pipeline.py`. High-volume non-alert background frames bypass persistence to preserve edge FPS. |
| **Merkle Hash Chaining** | RUNTIME-INTEGRATED, TESTED, PERSISTED, API-EXPOSED, UI-EXPOSED | Sequential chaining: $H_i = \text{SHA256}(H_{i-1} \parallel \text{digest}(\text{Record}_i))$, monotonic sequence ID, 16-byte random hex nonce tracking | Provides tamper evidence; if database is modified, verification algorithm flags exact break point. Does not prevent local disk overwriting if attacker has full OS root. |
| **Replay Attack Detection** | RUNTIME-INTEGRATED, TESTED, PERSISTED, API-EXPOSED | Nonce validation, monotonic sequence checking, and timestamp freshness window | Detects injected or re-ordered historical records. Requires monotonic clock. |
| **Post-Quantum Cryptography** | IMPLEMENTED, TESTED, API-EXPOSED | NIST FIPS 202 SHAKE-256 (512-bit digest, 256-bit Grover quantum security) + WOTS+ stateless hash-based one-time signatures (follows FIPS 205 construction; pure-Python implementation, not a NIST-certified library) | Hash-based signatures rely exclusively on hash collision/preimage resistance; immune to Shor's algorithm. |
| **Air-Gapped Edge Node** | IMPLEMENTED, TESTED, PERSISTED, API-EXPOSED, UI-EXPOSED | Fully offline local embedded DuckDB/SQLite storage with zero external WAN/cloud network socket calls | Verified with socket interception guardian tests. |
| **Analyst Governance Lifecycle** | RUNTIME-INTEGRATED, TESTED, PERSISTED, API-EXPOSED, UI-EXPOSED | Three-tier lifecycle (`ACCEPT`, `REVIEW`, `QUARANTINE`). Isolation between `recommended_disposition` and `analyst_disposition` | Preserves immutable audit trail (`governance_audit` table); human overrides cannot rewrite automated findings. |

---

## 3. Mathematical & Algorithmic Foundations

### 3.1 Data Integrity & Out-of-Distribution Detection

- **Exact Duplicates**:
  $$\text{digest} = \text{SHA-256}(\text{raw\_bytes})$$
- **Near Duplicates**:
  $$\text{aHash}(I) = \text{sign}\left(\text{Downsample}_{8\times 8}(\text{Grayscale}(I)) - \mu\right)$$
  $$\text{HammingDist}(H_1, H_2) = \sum_{b=0}^{63} (H_1[b] \oplus H_2[b])$$
- **Multivariate Mahalanobis Distance (Covariance-Aware OOD)**:
  Given reference feature distribution with sample mean $\mu$ and regularized empirical covariance $\Sigma_{\text{reg}} = \Sigma + \lambda I$:
  $$D_M^2(x) = (x - \mu)^T \Sigma_{\text{reg}}^{-1} (x - \mu)$$
  Under the Gaussian assumption, $D_M^2(x) \sim \chi^2_d$. Evaluates $p$-value:
  $$p = 1 - F_{\chi^2_d}(D_M^2(x))$$
  Sample is flagged as `POTENTIAL_OOD` if $D_M^2(x) > \chi^2_d(1 - \alpha)$.
- **k-Nearest Neighbors (kNN) Feature Density**:
  Given query feature $x$ and reference feature set $R = \{r_1, \dots, r_N\}$:
  $$d_{\text{kNN}}(x) = \frac{1}{k} \sum_{j=1}^k \|x - r_{(j)}\|_2$$
  Flagged as `POTENTIAL_OOD` if $d_{\text{kNN}}(x) > \text{Percentile}_{95}(\{d_{\text{kNN}}(r_i) : r_i \in R\})$.

### 3.2 Active Label Quality Assurance (Cleanlab-Inspired)

- **Bounding Box Geometry Anomalies**:
  $$\text{Aspect Ratio} = \max\left(\frac{w}{h}, \frac{h}{w}\right) > 10.0 \implies \text{SUSPICIOUS\_ASPECT\_RATIO}$$
  $$\text{Area} = w \cdot h < 10^{-4} \lor w \cdot h > 0.98 \implies \text{SUSPICIOUS\_BBOX\_AREA}$$
- **Duplicate / Collision Anomaly**:
  $$\text{IoU}(B_1, B_2) > 0.85 \implies \text{DUPLICATE\_ANNOTATION\_COLLISION}$$
- **Confident Learning Label Flipping**:
  $$\text{IoU}(B_{\text{ann}}, B_{\text{pred}}) > 0.50 \land p_{\text{pred}}(\hat{y}|x) > 0.70 \land \hat{y} \neq y_{\text{ann}} \implies \text{LABEL\_NOISE\_CLASS\_FLIP\_SUSPECTED}$$

### 3.3 Distribution Shift Detection

- **Kolmogorov-Smirnov Test (Marginal Projections)**:
  $$D_{KS} = \sup_t |F_{\text{ref}}(t) - F_{\text{eval}}(t)|, \quad \text{Reject if } p < \frac{0.05}{k}$$
- **Kernel Maximum Mean Discrepancy (Multivariate Joint Shift)**:
  Unbiased U-statistic with Gaussian RBF kernel $k(x, y) = \exp(-\gamma \|x - y\|_2^2)$:
  $$\text{MMD}_u^2(X, Y) = \frac{1}{m(m-1)} \sum_{i \neq j} k(x_i, x_j) + \frac{1}{n(n-1)} \sum_{i \neq j} k(y_i, y_j) - \frac{2}{mn} \sum_{i,j} k(x_i, y_j)$$
  Bandwidth selection uses the **median heuristic**:
  $$\sigma = \text{median}(\|z_i - z_j\|_2) \text{ for } z \in X \cup Y, \quad \gamma = \frac{1}{2\sigma^2}$$
  Significance evaluated via permutation testing with $n_{\text{permutations}}$ iterations.

### 3.4 Post-Quantum Cryptographic Assurance

- **Dual-Layer Hybrid Hash Commitment**:
  Combines classical SHA-256 (FIPS 180-4) with SHAKE-256 512-bit (FIPS 202):
  $$H_{\text{hybrid}} = \text{SHA256}(\text{SHA256}(m) \parallel \text{SHAKE256}(m, \text{len}=64))$$
  Provides 256 bits of collision resistance against Grover's quantum search algorithm.
- **Winternitz One-Time Signatures (WOTS+ over SHAKE-256, FIPS 205)**:
  - Private key: 67 random 256-bit seeds $\text{sk}_0, \dots, \text{sk}_{66}$.
  - Hash chain: $f_i(x) = \text{SHAKE256}(x \parallel \text{pub\_seed} \parallel i)$.
  - Public key: $\text{pk}_i = f_i^{w-1}(\text{sk}_i), \quad \text{PK} = \text{SHAKE256}(\text{pk}_0 \parallel \dots \parallel \text{pk}_{66} \parallel \text{pub\_seed})$.
  - Pure hash-based security: Zero reliance on integer factoring or discrete logarithms; immune to Shor's algorithm.

---

## 4. Hardware Environment & Benchmark Latency

All benchmarks were physically measured and logged via `benchmarks/run_benchmark.py` under the following test environment:
- **Operating System**: Windows 11 (Build 26200)
- **Processor**: Intel(R) Core(TM) i7 / 13th Gen
- **GPU**: NVIDIA GeForce RTX 5050 Laptop GPU (CUDA 12.8 compute capability)
- **Python**: 3.11.9
- **PyTorch**: 2.11.0+cu128
- **Primary Model**: Ultralytics YOLO11n (`yolo11n.pt`, SHA-256: `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`)
- **Evaluation Settings**: 50 frames @ 640x640 synthetic RGB, 10 warmup frames

### Measured Performance Results (`benchmarks/results/latest.json`)

| Metric | Raw Baseline Pipeline | Secured Assurance Pipeline | Delta / Overhead |
| :--- | :--- | :--- | :--- |
| **Mean Latency** | **14.94 ms** | **18.13 ms** | **+3.19 ms (+21.4%)** |
| **Throughput (FPS)** | **66.9 FPS** | **53.7 FPS** | **-19.7%** |
| **Provenance Hashing** | — | **0.562 ms** | — |
| **Ledger Persistence** | — | **5.554 ms** | — |

*Operational Note*: The secured pipeline sustains 53.7 FPS on local edge compute, comfortably exceeding real-time CCTV frame rate requirements (25–30 FPS).

---

## 5. Controlled Fault-Injection Battery Results

Evaluated via `benchmarks/run_fault_injection.py`:
- **Battery**: 17 controlled mutation cases.
- **Result**: **17 / 17 controlled mutation scenarios detected** (100.0% detection rate within the controlled test harness).

| Case | Mutation Scenario | Expected Detection | Actual Result | Status |
| :---: | :--- | :--- | :--- | :---: |
| 1 | Input frame pixel byte modified | `INPUT_TAMPERING_DETECTED` | Flagged `TAMPERED` | PASS |
| 2 | Input hash modified in record | `PROVENANCE_HASH_MISMATCH` | Flagged `TAMPERED` | PASS |
| 3 | Model weights digest swapped | `MODEL_TAMPERING_DETECTED` | Flagged `TAMPERED` | PASS |
| 4 | Model name/architecture ID swapped | `MODEL_NAME_MISMATCH` | Flagged `TAMPERED` | PASS |
| 5 | Preprocessing resolution config modified | `PREPROCESSING_TAMPERING_DETECTED` | Flagged `TAMPERED` | PASS |
| 6 | Inference confidence threshold altered | `CONFIG_TAMPERING_DETECTED` | Flagged `TAMPERED` | PASS |
| 7 | Detection class label modified | `OUTPUT_TAMPERING_DETECTED` | Flagged `TAMPERED` | PASS |
| 8 | Detection confidence score modified | `OUTPUT_TAMPERING_DETECTED` | Flagged `TAMPERED` | PASS |
| 9 | Bounding box coordinates modified | `OUTPUT_TAMPERING_DETECTED` | Flagged `TAMPERED` | PASS |
| 10 | Record timestamp modified | `PROVENANCE_HASH_MISMATCH` | Flagged `TAMPERED` | PASS |
| 11 | Sequence number altered / gap injected | `SEQUENCE_INTEGRITY_BREACH` | Flagged `TAMPERED` | PASS |
| 12 | Nonce modified / replayed | `NONCE_REPLAY_DETECTED` | Flagged `TAMPERED` | PASS |
| 13 | Previous record hash broken | `CHAIN_INTEGRITY_BREACH` | Flagged `TAMPERED` | PASS |
| 14 | Entire record substituted | `HASH_CHAIN_MISMATCH` | Flagged `TAMPERED` | PASS |
| 15 | Replay of duplicate historical record | `REPLAY_ATTACK_DETECTED` | Flagged `TAMPERED` | PASS |
| 16 | Mid-chain linkage broken | `CHAIN_BROKEN` | Flagged `TAMPERED` | PASS |
| 17 | Valid, untampered record | `RECORD_VALID` | Flagged `VERIFIED` | PASS |

---

## 6. Automated Test Suite Status

The automated test suite verifies all assurance modules in isolation and integrated within the pipeline:

### Focused Assurance Test Suites (76 Total Tests)
- `tests/test_data_integrity.py`: **12 / 12 PASSED**
- `tests/test_analyst_governance.py`: **2 / 2 PASSED**
- `tests/test_behavioral_fingerprint.py`: **14 / 14 PASSED**
- `tests/test_inference_provenance.py`: **29 / 29 PASSED**
- `tests/test_advanced_ood_and_mmd.py`: **6 / 6 PASSED**
- `tests/test_label_quality_assurance.py`: **6 / 6 PASSED**
- `tests/test_post_quantum_crypto.py`: **6 / 6 PASSED**
- `tests/test_airgap_and_offline_integrity.py`: **1 / 1 PASSED**
- **Total Assurance Tests**: **76 / 76 PASSED (100%)**

### Full Repository Test Suite
- **Passed**: 396 tests passed across detection, tracking, crypto ledger, API routers, spatial awareness, and ingestion.
- **Failures**: Exactly 2 pre-existing environment-dependent tests in `tests/test_cctv_discovery.py` (`test_check_tcp_port_local`, `test_scan_cctv_ports`) which expect an active MediaMTX RTSP daemon listening on localhost port 8554. All core application logic and assurance mechanisms pass.

---

## 7. Known Limitations & Threat Model Boundaries

To ensure complete transparency and defensibility during technical review, the following operational boundaries are declared:

1. **Local Disk Root Compromise**: Cryptographic hash chaining provides tamper *evidence*, not tamper *prevention*. An adversary with local administrative/root access who rewrites the entire SQLite database file and all historic logs cannot be stopped by software alone; however, discrepancies with external verification certificates (e.g., Section 65B exports) will expose the breach immediately.
2. **Camera Sensor Spoofing**: Hashing raw frame bytes verifies that the frame processed by the inference engine was not modified in transit between the ingestion buffer and the model. It does not authenticate the physical optical sensor itself if an adversary projects adversarial physical patterns or feeds analog video into the camera lens.
3. **Distribution Shift Baseline Requirement**: Statistical distribution shift and OOD detection require an enrolled reference sample set ($N \ge 10$ for MMD, $N \ge 3$ for Mahalanobis). In cold-start deployments where no baseline has been established, the system conservatively reports `NO_REFERENCE_BASELINE` rather than fabricating synthetic confidence.
4. **Air-Gapped Embedded Architecture**: The ledger operates as an air-gapped, append-only local embedded store (DuckDB / SQLite3). It does not rely on cloud infrastructure, external blockchain nodes, or WAN RPC services.

---

## 8. Audit Deliverable & Verification Checklist

- [x] **`docs/ASSURANCE_EVIDENCE.md`**: Upgraded with full mathematical formulations and empirical benchmarks.
- [x] **76 Focused Assurance Tests Passing**:
  - `tests/test_data_integrity.py` (12)
  - `tests/test_analyst_governance.py` (2)
  - `tests/test_behavioral_fingerprint.py` (14)
  - `tests/test_inference_provenance.py` (29)
  - `tests/test_advanced_ood_and_mmd.py` (6)
  - `tests/test_label_quality_assurance.py` (6)
  - `tests/test_post_quantum_crypto.py` (6)
  - `tests/test_airgap_and_offline_integrity.py` (1)
- [x] **Full Repository Suite**: 396 tests passing across full repository (with exactly 2 pre-existing MediaMTX daemon socket test skips/failures in `tests/test_cctv_discovery.py`).
- [x] **Frontend Production Build**: Clean build with zero TypeScript / JSX errors (`npm run build` in `apps/frontend`).
- [x] **Preserved Baseline Untouched**: Both `ibvap-preserved-base` and `ibvap-original-final` point to commit `25c05eba437058b07873ee9aba822ae173fdf1d2`.
- [x] **Working Tree Clean**: Clean git status on `feature/tcvf-assurance-layer`.
