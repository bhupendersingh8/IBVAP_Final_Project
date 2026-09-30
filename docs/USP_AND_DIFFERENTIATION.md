# IBVAP — Core Differentiating Architecture & System USPs
## Technical Differentiation in Computer Vision Integrity Assurance

**Project**: IBVAP (Integrity-Bound Vision Assurance Platform)  
**SIH Problem Statement**: SIH26228 (Blockchain & Cybersecurity)  
**Team**: Team Trinetra DBUU (Team ID: 138109)  

---

## 1. Executive Summary

Most computer vision platforms treat neural network models as unverified black boxes, storing raw frames or bounding boxes in conventional databases with no tamper-evident binding. Meanwhile, naive blockchain implementations for video streams suffer from gas costs, 10–15s network latencies, and internet dependencies that fail in air-gapped environments.

IBVAP establishes a grounded, high-throughput, offline-capable computer vision integrity assurance platform centered on five core architectural differentiators.

---

## 2. The Five Core Architectural Differentiators

```
+---------------------------------------------------------------------------------------------------+
|                                 THE 5 DEFENSIBLE PILLARS OF IBVAP                                 |
+-------------------+--------------------+--------------------+--------------------+----------------+
| 1. Full Lifecycle | 2. Cryptographic   | 3. Output-Level    | 4. White-Box +     | 5. Offline     |
| Integrity Chain   | + Behavioral       | Atomic Provenance  | Black-Box Dual     | Tamper-Evident |
| (Data->Model->    | Dual-Gated Trust   | (7-Tuple Binding   | Assurance Paths    | Hash Chains    |
| Infer->Evidence)  | (Signed != Safe)   | in 0.562 ms)       | (Probe Battery)    | (Zero Gas/Net) |
+-------------------+--------------------+--------------------+--------------------+----------------+
```

### Differentiator 1: Full-Lifecycle Integrity Chain
Unlike solutions that only catalog models (model registries) or only hash video files, IBVAP provides an unbroken chain of custody spanning:
- **Data**: Average/Difference hash perceptual screening + Mahalanobis OOD feature checks.
- **Model**: Ed25519 contributor manifests + CycloneDX v1.5 AIBOMs.
- **Inference**: Microsecond 7-tuple cryptographic binding.
- **Evidence**: Append-only DuckDB ledger with automated verification.

### Differentiator 2: The "Signed $\neq$ Safe" Dual-Gating Paradigm
In supply chain security, code signing verifies author identity, not benign behavior. An authorized contributor's key could be stolen, or a model could be trained on subtle poisoned data.
IBVAP enforces **Dual-Gated Model Admission**:
- **Gate 1 (Cryptographic)**: Ed25519 signature verification over weight digest and CycloneDX v1.5 AIBOM.
- **Gate 2 (Behavioral)**: Fixed probe battery evaluating composite divergence $S$ across classes, counts, confidences, and geometry. If $S > 0.15$, the model is quarantined despite a valid signature.

### Differentiator 3: Atomic 7-Tuple Output Provenance
Rather than simply logging bounding boxes to an unencrypted database, IBVAP binds the entire execution context into an atomic digest:
$$\text{ProvenanceHash} = \text{SHA256}(H_{\text{input}} \parallel H_{\text{model}} \parallel H_{\text{config}} \parallel H_{\text{output}} \parallel H_{\text{prev}} \parallel \text{Timestamp} \parallel \text{Nonce})$$
Altering any pixel, swapping the model weights, modifying the confidence threshold, or tampering with detection coordinates in the database breaks the cryptographic chain.

### Differentiator 4: Full-Weight + Black-Box Assurance Compatibility
IBVAP supports both white-box and black-box verification regimes:
- **White-Box**: When model internals and weights are accessible, the system verifies byte-level SHA-256 digests and CycloneDX AIBOM component trees.
- **Black-Box**: When third-party models are provided as opaque compiled runtimes or remote inference endpoints, the deterministic 5-probe synthetic battery evaluates behavior externally through input-output mapping without requiring access to internal layer weights.

### Differentiator 5: Tamper-Evident Offline Evidence Without Public Blockchain
Public blockchains cannot support real-time video feeds (120 FPS across 4 cameras would incur massive gas fees and latency). IBVAP implements an in-process, high-throughput **Recursive Merkle Hash Chain** backed by **DuckDB**:
- Hashing & Canonicalization Latency: **0.562 ms**
- Secured Throughput: **53.69 FPS** on tested RTX 5050 configuration
- Total Assurance Overhead: **3.19 ms (21.36%)**
- 100% offline, zero gas fees, zero external network dependency.

---

## 3. Grounded Statutory Alignment

IBVAP generates cryptographically verifiable electronic-evidence certificates designed to support evidence/audit workflows under applicable provisions of the **Bharatiya Sakshya Adhiniyam, 2023 (Section 63)**.
