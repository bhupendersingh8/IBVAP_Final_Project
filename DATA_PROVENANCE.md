# Dataset Provenance, Open-Data Compliance & Reference Attack Benchmarks (SIH26228)

**System**: TRINETRA / IBVAP (TCVIAF — Trusted Computer Vision Integrity & Assurance Framework)  
**Problem Statement Reference**: SIH26228 (Defence CV Integrity Assurance)  
**Standard**: Zero-Trust Cryptographic Assurance & Reproducible Open Evaluation  
**Audited**: 2026-10-01  

---

## 1. Purpose

The purpose of this document and the accompanying assurance subsystems in TRINETRA (TCVIAF) is to provide verifiable dataset provenance, rigorous open-data licensing compliance, and reproducible attack benchmark evaluation for computer vision pipelines deployed in defense-adjacent and mission-critical contexts. Under SIH26228, integrity assurance is required across the entire lifecycle: training data ingestion, model enrollment and serialization, runtime inference, and temporal ledgering. This specification establishes cryptographic traceability for every asset evaluated or ingested by the system.

---

## 2. Open/Synthetic Data Policy

> **Mandatory Clause (SIH26228)**:  
> *"All development and evaluation data will be publicly available under applicable licences or synthetically generated. No classified, operational or service-generated data will be used."*

TRINETRA enforces strict programmatic and operational guardrails to guarantee compliance with this clause:
1. **Zero Classified or Operational Surveillance Ingestion**: No operational CCTV recordings, classified reconnaissance media, or service-generated military data assets have been collected, processed, or stored.
2. **Open-Access Licensing Exclusivity**: Third-party evaluation baselines are restricted exclusively to publicly documented open licenses (e.g., CC-BY-4.0, MIT, Apache-2.0, NIST Public Domain).
3. **Deterministic Synthetic Attack Generation**: Adversarial inputs, patch triggers, label corruptions, and distribution shifts are 100% synthetically generated offline via deterministic algorithms initialized with fixed random seeds.
4. **Zero Hash Fabrication**: External public benchmark datasets not present on local air-gapped storage are explicitly designated as `REGISTERED_BUT_NOT_EXECUTED`. Cryptographic SHA-256 digests are computed only for artifacts actually resident on disk.

---

## 3. Dataset Registry

The authoritative dataset registry is maintained in [`configs/dataset_manifest.json`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_SIH26228/configs/dataset_manifest.json) and mirrored in [`config/dataset_manifest.json`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_SIH26228/config/dataset_manifest.json).

| Dataset Identifier | Name & Scope | License | Intended Use | Storage / Location | Compliance Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `coco-2017-val` | MS COCO 2017 Validation Subset (5k images) | CC-BY-4.0 | Primary detector baseline evaluation | External Reference | `REGISTERED_BUT_NOT_EXECUTED` |
| `exdark-eval` | Exclusively Dark (ExDark) Low-Light Benchmark | Academic Open-Access | Low-light detection & Zero-DCE++ validation | External Reference | `REGISTERED_BUT_NOT_EXECUTED` |
| `darkface-benchmark` | DarkFace Nighttime CV Benchmark | Academic Open-Access | Extreme low-illumination evaluation | External Reference | `REGISTERED_BUT_NOT_EXECUTED` |
| `synthetic-border-eval-v1` | TRINETRA Synthetic Attack & Tampering Suite v1 | Apache-2.0 | Synthetic tampering & adversarial evaluation | `data/synthetic_eval/` | `FULLY_VERIFIED (SYNTHETIC)` |
| `nist-trojai-round1-reference` | NIST TrojAI Round 1 Reference Benchmark | NIST Public Domain | Trojan backdoor detection benchmark | External Reference | `REGISTERED_BUT_NOT_EXECUTED` |
| `nist-trojai-round2-reference` | NIST TrojAI Round 2 Reference Benchmark | NIST Public Domain | Filter-based backdoor detection benchmark | External Reference | `REGISTERED_BUT_NOT_EXECUTED` |
| `backdoorbench-reference` | BackdoorBench Comprehensive Benchmark Suite | MIT | Backdoor defense & trigger isolation | External Reference | `REGISTERED_BUT_NOT_EXECUTED` |

Every entry in the registry enforces `is_classified: false`, `is_operational: false`, and `is_service_generated: false`.

---

## 4. NIST TrojAI Resources

The NIST TrojAI (Trojan AI) benchmark series provides open-access reference architectures and datasets for evaluating trojan and backdoor detection algorithms:
- **Round 1 (Polygonal & Patch Triggers)**: Evaluates deep vision models trojaned with geometric patch triggers. Ground truth targets specific output classes when the trigger pattern is presented.
- **Round 2 (Filter & Instagram Triggers)**: Expands trojan mechanisms to whole-image filter transformations and subtle color-space perturbations.
- **Licensing**: Public domain as a work of the United States Government (NIST / IARPA).
- **Integration Status in TRINETRA**: Standardized via [`services/assurance/benchmarks/trojai_adapter.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_SIH26228/services/assurance/benchmarks/trojai_adapter.py). In air-gapped environments without multi-gigabyte external weight downloads, the adapter registers round specifications and executes localized trigger-inversion routines against synthetic trojan test patterns.

---

## 5. BackdoorBench Resources

BackdoorBench (NeurIPS 2022) is a standardized, open-source benchmark for backdoor learning and defenses:
- **Scope**: Implements 80+ combinations of backdoor attacks (BadNets, Blended, WaNet, Input-Aware) and defense mechanisms (Neural Cleanse, STRIP, Fine-Pruning, Spectral Signatures).
- **Licensing**: MIT License (open-access academic and commercial use).
- **Integration Status in TRINETRA**: Standardized via [`services/assurance/benchmarks/backdoorbench_adapter.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_SIH26228/services/assurance/benchmarks/backdoorbench_adapter.py). The adapter normalizes attack configurations, computes defense success rates against localized synthetic test samples, and exports audit evidence.

---

## 6. Additional Reference Attack Resources

In addition to TrojAI and BackdoorBench, TRINETRA integrates normalized interfaces for:
- **Cleanlab Confident Learning** (MIT License): Algorithmic identification of noisy labels, annotation errors, and label-flip poisoning.
- **PyTorch / Torchvision Models** (BSD-3-Clause / Apache-2.0): Baseline reference backbones for embedding extraction.
- **ExDark (Exclusively Dark)** (Academic Open-Access): Open dataset for evaluating low-illumination and night-vision enhancement.

---

## 7. License Verification

License terms for all registered datasets and reference benchmarks are verified before any asset is ingested:
1. Manifest entries must specify a valid open-source or public domain license identifier.
2. Proprietary, classified, or non-commercial restricted licenses that conflict with open evaluation are blocked by [`services/assurance/dataset_hashing.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_SIH26228/services/assurance/dataset_hashing.py).
3. The `DatasetComplianceAuditor` scans all registered datasets and outputs a compliance claim status (`FULLY_VERIFIED` or `PARTIAL / PENDING VERIFICATION`).

---

## 8. SHA-256 Verification

Cryptographic verification is performed using deterministic streaming SHA-256 hashing:
- **Chunk Size**: 64 KB (65,536 bytes) chunks to prevent memory spikes on large archives.
- **Directory Hashing**: Evaluates child files in sorted relative path order. Metadata files containing the final hash (e.g., `synthetic_provenance.json`) are excluded to avoid circular dependency.
- **Strict Authenticity Invariant**: No SHA-256 checksum is ever fabricated or mocked for un-downloaded external assets. If an external dataset is registered but not stored locally, `computed_sha256` remains `None` and status is reported as `REGISTERED_BUT_NOT_EXECUTED`.

---

## 9. Synthetic Data Generation

To ensure 100% reproducible evaluation under air-gapped conditions, TRINETRA implements an automated synthetic attack generator at [`scripts/generate_synthetic_cases.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_SIH26228/scripts/generate_synthetic_cases.py) backed by [`services/assurance/synthetic_eval.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_SIH26228/services/assurance/synthetic_eval.py).

- **Generation Seed**: `26228` (constant and deterministic).
- **Generator Version**: `2.0.0`.
- **Cases Generated**: 21 discrete test cases spanning four operational domains:
  - **DATA**: Label flips, systemic mislabeling, duplicate flooding, near-duplicate floods, malformed annotations, class substitutions.
  - **ENVIRONMENT**: Low-light illumination drops, atmospheric fog/haze, severe Gaussian blur, high-ratio compression artifacts.
  - **MODEL**: BadNets patch triggers, raw weight byte mutations, layer substitutions, signed-suspicious weights.
  - **INFERENCE**: Bounding box coordinate inversions, confidence spoofing, class tampering, replay nonce reuse, provenance record substitution.

---

## 10. Merkle Provenance

Every generated synthetic test case is cryptographically committed into a binary Merkle Tree:
- **Batch ID**: `SYNTH-EVAL-26228-V2`
- **Total Leaf Artifacts**: 25 (21 case descriptors + companion data buffers)
- **Merkle Tree Root**: `6ecccafecf627c52d40bba90b23c4971b07f7fda62ad05ca19ba83de29c1d486`
- **Provenance Commitment File**: [`data/synthetic_eval/synthetic_provenance.json`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_SIH26228/data/synthetic_eval/synthetic_provenance.json)
- **Mathematical Validation**: Verified via `verify_synthetic_merkle_provenance()` in [`services/assurance/synthetic_eval.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_SIH26228/services/assurance/synthetic_eval.py), confirming exact bit-for-bit reproducibility.

---

## 11. Attack Coverage

The TRINETRA attack taxonomy standardizes 14 attack classes with designated assurance mechanisms and automated governance transitions:

| Attack Class | Pipeline Stage | Primary Defense Mechanism | Automated Decision |
| :--- | :--- | :--- | :--- |
| `TRIGGER_INJECTION` | Data / Model | Neural Cleanse Trigger Inversion / Coordinate Probe | `QUARANTINE` |
| `BACKDOOR` | Model Weights | $L_1$ Norm Inversion & Anomaly Index ($A > 2.0$) | `QUARANTINE` |
| `TROJAN` | Model Weights | NIST TrojAI Behavioral Probing | `QUARANTINE` |
| `LABEL_FLIPPING` | Training Data | Confident Learning (Cleanlab) Joint Distribution | `QUARANTINE` |
| `DATA_POISONING` | Training Data | Merkle Leaf Divergence & SHA-256 Checksums | `QUARANTINE` |
| `DUPLICATE_FLOODING` | Training Data | Perceptual Hashing & Exact Byte Deduplication | `REVIEW` |
| `OOD_INSERTION` | Input Stream | ArcFace Cosine Distance & Maximum Mean Discrepancy | `REVIEW` |
| `MODEL_SUBSTITUTION` | Deployment | CycloneDX AIBOM SHA-256 Checksum Validation | `QUARANTINE` |
| `MODEL_WEIGHT_TAMPERING` | Runtime | Dynamic In-Memory Weight Checksums & Layer Probing | `QUARANTINE` |
| `OUTPUT_TAMPERING` | Inference | Recursive Merkle Hashing $H_n$ & Canonical Digest | `QUARANTINE` |
| `REPLAY` | Pipeline Stream | Monotonic Sequence Counter & Nonce Freshness Check | `QUARANTINE` |
| `PROVENANCE_TAMPERING` | Ledger Audit | Merkle Hash-Chain Discontinuity Verification | `QUARANTINE` |
| `DISTRIBUTION_SHIFT` | Environment | Zero-DCE++ Lux Curve & Two-Sample KS Test | `ACCEPT` / `REVIEW` |
| `ADVERSARIAL_INPUT` | Frame Ingestion | Boundary Guardrails & Wavelet Spatial Filters | `QUARANTINE` |

---

## 12. Reproducibility

Evaluation results can be reproduced independently using the following commands:

```bash
# 1. Regenerate synthetic evaluation cases with deterministic seed 26228
.\venv_rtx\Scripts\python.exe scripts/generate_synthetic_cases.py

# 2. Run open-data dataset compliance audit
.\venv_rtx\Scripts\python.exe -c "from services.assurance.dataset_hashing import DatasetComplianceAuditor; a = DatasetComplianceAuditor(); r = a.run_audit(); print(f'Compliant: {r.overall_compliant}, Datasets: {r.total_datasets}, Status: {r.compliance_claim_status}')"

# 3. Execute reference attack benchmark test suite
.\venv_rtx\Scripts\pytest.exe tests/test_dataset_provenance.py tests/test_trojai_backdoorbench.py tests/test_reference_attack_benchmarks.py -v
```

---

## 13. Offline/Air-Gap Operation

TRINETRA is designed for deployment in secure, air-gapped operational environments:
- **No Outbound Network Dependency**: Zero external network or cloud API calls are made during dataset hashing, synthetic case generation, trigger inversion, or inference assurance.
- **Local Artifact Verification**: All models, configs, and synthetic test suites are read from local filesystems.
- **Graceful Handling of External References**: Benchmarks requiring external downloads remain in `REGISTERED_BUT_NOT_EXECUTED` state without failing the pipeline.

---

## 14. White-Box Assumptions

When white-box access to model architecture and weights is available:
1. **$L_1$ Trigger Inversion (Neural Cleanse)**: Optimizes a perturbation mask and pattern across candidate classes to identify anomalous minimum perturbation norms.
2. **Layer Checksumming**: Individual layer tensors are checksummed at load time to detect targeted weight manipulation.
3. **Weight Mutation Detection**: Bitwise differences in model state dicts are detected against the enrolled CycloneDX AIBOM manifest.

---

## 15. Black-Box Limitations

When models are accessed strictly as black boxes (e.g., compiled binaries, proprietary runtimes):
1. **Trigger Inversion Infeasibility**: Without gradient access or parameter visibility, trigger inversion optimization cannot be executed.
2. **Behavioral Probing Fallback**: Black-box models are evaluated via behavioral probing, output distribution statistics, coordinate guardrails, and latency variance.
3. **Output Integrity Focus**: Integrity guarantees shift to inference provenance, SHA-256 frame-to-output binding, and hash-chain ledgering.

---

## 16. Known Limitations

1. **Storage Footprint of Full External Benchmarks**: Complete TrojAI rounds contain hundreds of gigabytes of models and images. These are registered but not bundled in the lightweight offline distribution.
2. **Computational Overhead of Trigger Inversion**: Exhaustive Neural Cleanse trigger inversion across large class taxonomies (e.g., 80 COCO classes) requires significant GPU compute. TRINETRA optimizes inversion on tactical classes (e.g., person, vehicle, weapon).
3. **GPU Kernel Compatibility**: On newer host GPUs (e.g., NVIDIA RTX 50-series / Blackwell `sm_120`), PyTorch CUDA wheels may lack native kernel images. TRINETRA implements an automatic zero-overhead CPU fallback to ensure continuous operation.

---

## 17. Coverage Statement

TRINETRA (TCVIAF) provides comprehensive, mathematically verifiable integrity assurance across data, models, and inference outputs. In full compliance with SIH26228 guidelines:
- **No classified, operational or service-generated data will be used.**
- **All development and evaluation assets are publicly licensed or synthetically generated.**
- **All cryptographic commitments are verifiable via SHA-256 and Merkle Trees.**
- **All benchmark statuses reflect honest, verified execution.**
