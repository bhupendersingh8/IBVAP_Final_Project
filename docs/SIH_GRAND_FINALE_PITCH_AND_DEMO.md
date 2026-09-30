# IBVAP: SIH 2026 Grand Finale Master Pitch Deck & Demonstration Playbook

**Project**: IBVAP (Trustworthy Computer Vision Integrity Assurance Platform)  
**Team**: Team Trinetra DBUU (Team ID: 138109)  
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines  
**Category**: Blockchain & Cybersecurity  
**Active Branch**: `feature/tcvf-assurance-layer`  
**Preserved Baseline**: Commit `25c05eba437058b07873ee9aba822ae173fdf1d2`  
**Live Demo Runner**: `python scripts/demo_tamper_assurance_cycle.py`

---

## 1. Executive Summary & Core Thesis

> **“We don't blindly trust a dataset, model, inference result, or contributor.  
> IBVAP continuously establishes cryptographic evidence of integrity across the entire computer-vision lifecycle.”**

In modern security and critical infrastructure surveillance, over 95% of deployments blindly accept third-party weights, unverified datasets, and raw model predictions. IBVAP bridges this critical security gap by deploying an **air-gapped, model-agnostic assurance layer** that binds inputs, weights, configurations, and outputs into a **tamper-evident cryptographic ledger** while running at **53.69 FPS** on local edge hardware.

---

## 2. The 4 Pillars of Trust

| Pillar | Technical Mechanism | Attacks / Risks Mitigated |
| :--- | :--- | :--- |
| **1. Data Trust** | • 64-bit Average Hash (`aHash`) and Difference Hash (`dHash`) with Hamming distance ($\le 10$)<br>• Bitwise SHA-256 for exact duplicate images<br>• Confident Learning prediction discrepancy filtering<br>• Normalized coordinate and aspect ratio syntax checks | • Dataset poisoning<br>• Duplicate / redundant data inflation<br>• Label flipping & noisy annotations<br>• Out-of-bounds bounding box corruptions |
| **2. Model Trust** | • Physical checkpoint SHA-256 computation directly from disk<br>• PureEdDSA Ed25519 (RFC 8032) contributor signed manifests<br>• CycloneDX 1.5 AIBOM generation with cross-binding<br>• Probe-set behavioral fingerprinting (`ibvap-behavior-v1`, $N=5$) | • Checkpoint swapping & trojans<br>• Unattributed third-party weights<br>• Quantization degradation<br>• Silent model replacement |
| **3. Inference Trust** | • Deterministic JSON canonicalization (clipped coords, sorted classes)<br>• Classical SHA-256 + 512-bit SHAKE-256 commitment<br>• Monotonic sequence counters and cryptographic nonces<br>• Multi-metric distribution shift (KS test & Mahalanobis OOD) | • Bounding box output manipulation<br>• Replay & injection attacks<br>• Out-of-distribution hallucinations<br>• Uncurated environmental drift |
| **4. Governance Trust** | • Tri-state disposition policy (`ACCEPT`, `REVIEW`, `QUARANTINE`)<br>• Multi-contributor supply-chain provenance verification<br>• Immutable human override governance audit logging<br>• Technical electronic evidence certificate generation under Section 63 BSA 2023 | • Insider tampering<br>• Rogue contributor deployments<br>• Unverifiable electronic evidence<br>• Automated decision unreliability |

---

## 3. Dual-Mode Assurance Architecture

IBVAP adapts to operational security constraints:

```
                          ┌───────────────────────────────┐
                          │   DATASET INGESTION & AUDIT   │
                          │  • aHash/dHash Duplicates     │
                          │  • SHA-256 Exact Duplicates   │
                          │  • YOLO Bbox Geometry Checks  │
                          └───────────────┬───────────────┘
                                          │
                                          ▼
                          ┌───────────────────────────────┐
                          │     MODEL REGISTRY & TRUST    │
                          └───────────────┬───────────────┘
                                          │
               ┌──────────────────────────┴──────────────────────────┐
               ▼                                                     ▼
┌─────────────────────────────────────────┐       ┌─────────────────────────────────────────┐
│     FULL-WEIGHT ASSURANCE MODE          │       │       BLACK-BOX ASSURANCE MODE          │
│   (When model weights are accessible)   │       │   (Proprietary / restricted models)     │
├─────────────────────────────────────────┤       ├─────────────────────────────────────────┤
│ • Physical Checkpoint SHA-256           │       │ • Input Frame Byte SHA-256              │
│ • Ed25519-Signed Contributor Manifest   │       │ • Output Prediction SHA-256             │
│ • CycloneDX 1.5 AIBOM Binding           │       │ • Monotonic Sequence + Nonce            │
│ • Probe-Set Behavioral Fingerprinting   │       │ • Distribution Shift (KS & Mahalanobis) │
│   (`ibvap-behavior-v1` divergence score)│       │ • Transparent Limitation Disclosure     │
└────────────────────┬────────────────────┘       └────────────────────┬────────────────────┘
                     │                                                 │
                     └────────────────────┬────────────────────────────┘
                                          │
                                          ▼
                          ┌───────────────────────────────┐
                          │    RUNTIME INFERENCE ENGINE   │
                          │  • YOLO11n + ByteTrack (CUDA) │
                          │  • MobileSAM Camouflage ROIs  │
                          └───────────────┬───────────────┘
                                          │
                                          ▼
                          ┌───────────────────────────────┐
                          │  PROVENANCE BINDING ENGINE    │
                          │  • 7-Tuple Canonicalization   │
                          │  • SHA-256 Recursive Chaining │
                          └───────────────┬───────────────┘
                                          │
                                          ▼
                          ┌───────────────────────────────┐
                          │   TAMPER-EVIDENT LEDGER       │
                          │  • DuckDB / SQLite Hash Chain │
                          │  • Binary Merkle Tree Root    │
                          └───────────────┬───────────────┘
                                          │
                                          ▼
                          ┌───────────────────────────────┐
                          │   GOVERNANCE & DECISIONING    │
                          │  • ACCEPT / REVIEW / QUARANTINE│
                          │  • Human Override Audit Trail │
                          │  • Section 63 BSA Certificate │
                          └───────────────────────────────┘
```

---

## 4. SIH Grand Finale 6-Slide Presentation Narrative

### Slide 1: The Trust Crisis in Computer Vision Pipelines
* **The Vulnerability**: Off-the-shelf vision systems blindly trust inputs, models, and predictions. If an attacker tampers with an inference bounding box or swaps a model checkpoint, standard systems accept it without question.
* **The Solution**: **IBVAP** — an offline, model-agnostic assurance layer that establishes a verifiable chain of trust from training data to evidence.
* **Team**: Team Trinetra DBUU (Team ID: 138109) | SIH26228.

### Slide 2: The 4 Pillars of Trust
* **Data Trust**: Automated perceptual deduplication, coordinate validation, and label noise filtering.
* **Model Trust**: Physical on-disk SHA-256 hashing, Ed25519 contributor signing, CycloneDX 1.5 AIBOMs, and 5-probe synthetic behavioral fingerprinting.
* **Inference Trust**: 7-tuple cryptographic provenance records binding frames, models, configurations, and bounding boxes.
* **Governance Trust**: Multi-contributor supply-chain provenance, tri-state disposition, and human-override governance logs.

### Slide 3: Dual-Mode Architecture & Execution Flow
* **Full-Weight Mode**: Deep cryptographic and behavioral supply-chain assurance.
* **Black-Box Fallback**: Operates when weights are proprietary or unreleased, binding input-output hashes and monitoring distribution drift with transparent limitation disclosure.
* **End-to-End Operational Flow**: Ingest $\rightarrow$ Data Integrity $\rightarrow$ Model Integrity $\rightarrow$ Inference Execution $\rightarrow$ Provenance Binding $\rightarrow$ Assurance Engine $\rightarrow$ Governance Decisioning $\rightarrow$ Electronic Certificate Export.

### Slide 4: Real Edge Hardware Performance (Tested RTX 5050 Laptop GPU)
* **Empirical Benchmark Platform**: Intel Core i7 / NVIDIA GeForce RTX 5050 Laptop GPU (CUDA 12.8), 50 frames @ $640\times 640$.
* **Measured Benchmark Results**:
  * **Raw Baseline (YOLO11n)**: 14.94 ms (**66.92 FPS**)
  * **Secured Assurance Pipeline**: 18.13 ms (**53.69 FPS**)
  * **Overhead**: +3.19 ms (+21.4%) — *cryptographic canonicalization and hashing takes just 0.56 ms!*
* **Significance**: 53.69 FPS measured on the tested RTX 5050 configuration, above a 30 FPS reference workload.

### Slide 5: Controlled Fault-Injection Battery & Tamper Detection
* **17-Scenario Attack Matrix**: Tested against 17 simulated mutations including 1-byte pixel tampering, weight swaps, confidence alterations, and replay nonces.
* **Result**: **17 / 17 (100.0%) attacks detected and quarantined**.
* **Quarantine Enforcement**: Tampered records are routed to quarantine before acceptance into the verified evidence flow.
* **Live Proof**: Single-command demonstration runs in 3 seconds via `python scripts/demo_tamper_assurance_cycle.py`.

### Slide 6: Governance & Legal Scope (Section 63 BSA 2023)
* **Human-in-the-Loop Governance**: Automated recommendations (`ACCEPT`, `REVIEW`, `QUARANTINE`) with immutable analyst override audit logs.
* **Electronic Evidence Framing**: Generates cryptographically verifiable electronic-evidence certificates designed to support evidence/audit workflows under applicable provisions of the **Bharatiya Sakshya Adhiniyam, 2023 (Section 63)**.
* **Jury Defense Boundary**: *"We generate technically verifiable evidence. Whether that evidence is legally admissible is determined under the applicable law and judicial process."*

---

## 5. Live Jury Demonstration Script (Step-by-Step)

Run this exact command in front of the evaluators:
```powershell
.\.venv_gpu\Scripts\python.exe scripts/demo_tamper_assurance_cycle.py
```

### Script Execution Progression:
1. **Model Checkpoint Enrollment**: Demonstrates genuine model discovery (`weights/yolo11n.pt`) and calculates real SHA-256 digest (`0ebbc80d...`).
2. **Contributor Signing**: Generates Ed25519 keypair for authorized contributor, signs manifest, and verifies CycloneDX 1.5 AIBOM.
3. **Supply-Chain Verification**: Supply chain verifier validates signature, physical file digest, and AIBOM schema $\rightarrow$ **`DISPOSITION = ACCEPT`**.
4. **Live Inference & Provenance**: Runs inference on frame, produces 7-tuple hash record, and commits Block #1 to DuckDB/SQLite ledger.
5. **Simulated Attacks & Instant Quarantine**:
   * **Attack 1 (Weight Swap)**: Checkpoint substituted $\rightarrow$ **`[BLOCKED] Physical SHA-256 Mismatch! -> DISPOSITION = QUARANTINE`**
   * **Attack 2 (Bounding Box Tampering)**: Coordinate altered $\rightarrow$ **`[BLOCKED] Output Tampering Detected! -> DISPOSITION = QUARANTINE`**
   * **Attack 3 (Replay Attack)**: Reused nonce submitted $\rightarrow$ **`[BLOCKED] Nonce Replay Detected! -> DISPOSITION = QUARANTINE`**
6. **Chain Integrity & Section 63 BSA Certificate**: Proves 100% chain integrity, generates Section 63 BSA technical certificate with Merkle root, and completes demonstration in under 3 seconds.

---

## 6. Adversarial Judge Q&A Playbook

### Q1: "Why not use Ethereum or Hyperledger blockchain?"
> **Answer**:  
> *"Public blockchains require consensus mechanisms (PoW/PoS) and introduce 2-to-15 second transaction latencies, which completely stalls a 30 FPS video pipeline and violates air-gapped security requirements. Instead, IBVAP implements an embedded tamper-evident hash-chain ledger with DuckDB storage. It executes cryptographic hashing in ~0.56 ms, operates fully offline, and delivers mathematical tamper-evidence: any modification to historical data invalidates the hash chain and Merkle root."*

### Q2: "What if an attacker with root OS access alters the local database?"
> **Answer**:  
> *"Software alone cannot prevent disk rewriting by an OS root compromise without hardware root-of-trust (such as TPM 2.0). However, our architecture provides **tamper-evidence**: because every incident block is chained and certificates are exported externally, any modification creates an immediate mathematical chain break ($H_{i-1} \neq \text{tip}$). The breach is immediately provable."*

### Q3: "What is your computational overhead on edge hardware?"
> **Answer**:  
> *"We benchmarked this on our RTX 5050 GPU: the raw baseline detector runs at 14.94 ms (66.92 FPS). Running active 7-tuple cryptographic provenance and assurance checks takes 18.13 ms (53.69 FPS). Canonicalization and hashing takes only 0.56 ms on CPU. 53.69 FPS was measured on the tested RTX 5050 configuration, comfortably above a 30 FPS reference workload."*

### Q4: "How does this differ from standard MLOps platforms like MLflow or W&B?"
> **Answer**:  
> *"MLflow and Weights & Biases are developer experiment trackers for training loss and hyperparameters. They do not cryptographically sign checkpoints, they do not bind raw frame bytes to bounding boxes at millisecond latency, they do not detect live adversarial output manipulation, and they do not generate verifiable electronic evidence certificates. IBVAP is an operational cybersecurity assurance platform."*

### Q5: "How do you detect adversarial attacks or model divergence?"
> **Answer**:  
> *"We employ a layered defense:
> 1. **At enrollment**: Our probe-set behavioral fingerprinting (`ibvap-behavior-v1`) evaluates candidate models against 5 standardized synthetic test patterns to detect divergence before deployment.
> 2. **At runtime**: Our distribution shift engine monitors input features and downstream predictions using two-sample Kolmogorov-Smirnov tests and Mahalanobis distance, catching feature drift even when an adversarial perturbation bypasses standard confidence thresholds."*
