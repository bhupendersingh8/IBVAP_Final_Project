# IBVAP — Grand Finale Jury Q&A Playbook
## Critical Defense, Cybersecurity, and AI Questions & Grounded Answers

**Target Event**: Smart India Hackathon 2026 Grand Finale  
**Problem Statement**: SIH26228 (Blockchain & Cybersecurity)  
**Team**: Team Trinetra DBUU (Team ID: 138109)  

---

## Category 1: Blockchain & Cybersecurity Questions

### Q1: "The problem statement is under Blockchain & Cybersecurity. Where is your blockchain?"
**Answer**:
> *"We made an intentional, professional engineering choice: **public or consortium blockchains (like Ethereum or Hyperledger) are fundamentally unsuitable for real-time video surveillance**. Four cameras running at 30 FPS generate 120 frames per second. Committing these to a public blockchain incurs prohibitive gas costs, network latency (10–15 seconds per block), and requires constant internet connectivity—violating the air-gap mandate of secure installations.  
> Instead, IBVAP implements an in-process, high-throughput **Recursive Merkle Hash Chain** backed by DuckDB. It delivers the exact cryptographic immutability of a blockchain—where modifying any single pixel, weight, or detection breaks the hash chain—while executing in **0.56 milliseconds** at **53+ FPS** with **zero gas fees** and **zero internet dependency**."*

---

### Q2: "Where is the cybersecurity in your computer vision pipeline?"
**Answer**:
> *"Traditional computer vision pipelines treat raw model outputs as unverified truth. Cybersecurity in IBVAP is implemented across four integrity boundaries:
> 1. **Data Layer**: Average hash and difference hash near-duplicate screening + Mahalanobis OOD anomaly detection.
> 2. **Supply Chain Layer**: Ed25519 digital signatures on Contributor Manifests and CycloneDX v1.5 AIBOMs.
> 3. **Inference Layer**: Cryptographic binding of the 7-tuple:
>    $$\text{SHA256}(H_{\text{input}} \parallel H_{\text{model}} \parallel H_{\text{config}} \parallel H_{\text{output}} \parallel H_{\text{prev}} \parallel T \parallel N)$$
>    Any post-facto modification of video frames, detection boxes, classes, or weights triggers instant `QUARANTINE`.
> 4. **Temporal Layer**: Anti-replay defense using 128-bit cryptographically secure nonces and strictly monotonic sequence numbers."*

---

### Q3: "What happens if someone opens the DuckDB file and directly edits a row in the database?"
**Answer**:
> *"The tampering is immediately caught upon the very next verification cycle. Because each block incorporates the SHA-256 hash of the previous block ($H_{i-1}$), modifying or deleting an existing row changes its hash digest, which causes an immediate chain break ($H_{i-1} \neq H_{\text{prev}}$) for all downstream blocks. Our live verifier will display `PROVENANCE_CHAIN_MISMATCH` and identify the exact sequence ID where tampering occurred."*

---

### Q4: "How do you prevent replay attacks (e.g. an attacker replaying peaceful footage during an intrusion)?"
**Answer**:
> *"We enforce a two-factor temporal lock:
> 1. **Monotonically Increasing Sequence Counter**: Each record must strictly increment ($S_i = S_{i-1} + 1$). An old sequence number is rejected.
> 2. **128-bit Cryptographic Nonce**: Generated per frame via `os.urandom(16)`. The engine maintains a sliding-window cache; if a nonce is reused, the record is immediately flagged with `PROVENANCE_REPLAY_DETECTED` and routed to `QUARANTINE`."*

---

## Category 2: AI & Model Integrity Questions

### Q5: "If an authorized contributor signs a model with their valid Ed25519 private key, doesn't that guarantee the model is safe?"
**Answer**:
> *"**No, and that is a fundamental supply chain trap.** A valid signature proves only *who signed it* and that the file was not altered in transit. A valid contributor could have had their credentials stolen, or they could have trained the model on poisoned data containing a backdoor.  
> IBVAP enforces **Dual-Gated Model Admission**: Gate 1 verifies the cryptographic Ed25519 signature; Gate 2 independently executes the model against a deterministic synthetic probe battery to measure class, count, confidence, and geometry divergence. If a signed model exhibits anomalous divergence ($S > 0.15$), our system sends it to `QUARANTINE` regardless of its valid signature."*

---

### Q6: "Why are you using YOLO11n rather than massive vision-language models (VLMs)?"
**Answer**:
> *"We prioritized verified physical execution, edge feasibility, and licensing compliance:
> 1. **Physical Feasibility**: In edge deployments, hardware operates on limited power and VRAM (e.g. NVIDIA Jetson, 6GB–8GB GPUs). Massive VLMs draw high power and run at 1–3 FPS, missing fast-moving events.
> 2. **Verification Reality**: YOLO11n runs at **14.9 ms (66+ FPS)** on our hardware, providing sustained real-time tracking.
> 3. **Architectural Truth**: Surveillance requires reliable real-time bounding boxes and immediate cryptographic commitment, not conversational text generation."*

---

### Q7: "Do you claim 100% universal backdoor detection?"
**Answer**:
> *"No. Claiming 100% universal backdoor elimination across arbitrary neural networks is mathematically undecidable. What IBVAP implements is a rigorous **multi-tier defense**:
> - Contributor manifest verification and CycloneDX v1.5 AIBOM supply chain tracking.
> - Confident learning screening for label poisoning in training sets.
> - Behavioral probe fingerprinting for prediction and distribution divergence.
> - Outlier screening for prediction discrepancies.
> We provide strong heuristic screening while maintaining honest scientific boundaries."*

---

## Category 3: Legal, Operational & Hardware Questions

### Q8: "Does your system guarantee court admissibility under Indian Law?"
**Answer**:
> *"No software can guarantee court admissibility, because under Indian Law, admissibility is a judicial determination made exclusively by the presiding magistrate under Section 63(4) of the Bharatiya Sakshya Adhiniyam, 2023.  
> **We generate technically verifiable evidence. Whether that evidence is legally admissible is determined under the applicable law and judicial process.**  
> IBVAP generates a cryptographically verifiable electronic-evidence certificate designed to support evidence/audit workflows under applicable provisions of the Bharatiya Sakshya Adhiniyam, 2023."*

---

### Q9: "Can this system run completely air-gapped without internet?"
**Answer**:
> *"Yes, 100%. The entire pipeline—from camera ingestion (RTSP/CCTV) through YOLO11n inference, cryptographic hashing, DuckDB ledger storage, and the web dashboard—runs locally on the edge device. There are zero cloud API dependencies, zero external model downloads during runtime, and zero external network calls."*

---

### Q10: "What is the performance overhead of adding all this cryptography?"
**Answer**:
> *"On tested hardware (NVIDIA GeForce RTX 5050 Laptop GPU):
> - Baseline YOLO11n inference: **14.94 ms** (66.92 FPS)
> - Secured inference with full 7-tuple hashing and ledger commit: **18.13 ms** (53.69 FPS)
> - Hashing & Canonicalization latency: **0.562 ms**
> - Total Assurance Overhead: **3.19 ms (21.36%)**
> For a representative 25–30 FPS video workload, the measured secured throughput (53.69 FPS) provides sufficient processing headroom on the tested hardware."*
