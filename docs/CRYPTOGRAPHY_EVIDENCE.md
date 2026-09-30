# IBVAP Cryptography Evidence & Implementation Specification

**Document**: `docs/CRYPTOGRAPHY_EVIDENCE.md`  
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines  
**Timestamp**: 2026-09-30T16:11:00+05:30  
**Evaluator**: Senior Cryptography Auditor  

---

## 1. Cryptographic Primitives Specification

Every cryptographic algorithm implemented in IBVAP is grounded in verified, standard hardware and software primitives. The platform implements a **two-tier cryptographic architecture**:
1. **Asymmetric Public-Key Cryptography (Ed25519)**: Dedicated to offline contributor model manifest release provenance, developer identity verification, and multi-contributor supply-chain signing.
2. **Dual-Commitment Symmetric & Extendable Hashing (SHA-256 + SHAKE-256)**: Dedicated to high-frequency runtime inference provenance, sequential ledger hash chaining, and incremental binary Merkle tree root computation.

---

## 2. Cryptographic Primitives Truth Table

| Primitive | Purpose | Standard / RFC | Library / Implementation | Key / Digest Size | Verification Path | Automated Tests | Known Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SHA-256** | Frame hashing, file checksums, canonical digests | FIPS 180-4 | Python standard `hashlib.sha256` | 256 bits (32 bytes) | Bitwise hash comparison (`==`) | `test_data_integrity.py`, `test_inference_provenance.py` | Classical security only; theoretical 128-bit collision bound against Grover quantum search. |
| **SHAKE-256** | Dual-commitment hybrid digest for inference records | FIPS 202 (SHA-3 family XOF) | Python standard `hashlib.shake_256(..., 64)` | 512 bits (64 bytes) | Recomputation of 64-byte digest | `test_post_quantum_crypto.py` | Provides 256 bits of Grover collision resistance. Does NOT confer post-quantum security to the entire platform. |
| **Ed25519** | Contributor model manifest digital signing | RFC 8032 / FIPS 186-5 (PureEdDSA over Curve25519) | `cryptography.hazmat.primitives.asymmetric.ed25519` | 256-bit public key, 512-bit signature | `Ed25519PublicKey.verify(sig, data)` | `test_contributor_manifest.py` (17 tests) | Classical elliptic curve cryptography. Vulnerable to Shor's algorithm on a cryptographically relevant quantum computer (CRQC). |
| **RFC 8785 JCS** | Canonical JSON serialization before signing | RFC 8785 | Native Python recursive key-sorting & compact separators (`separators=(',', ':')`) | N/A (canonical byte stream) | Canonical byte reproducibility check | `test_contributor_manifest.py` | Requires strict UTF-8 normalization and integer rounding for floating point. |
| **Merkle Hash Chain** | Sequential incident block chaining in ledger | Merkle Damgård construction | Native Python `CryptoEvidenceLedger` | 256 bits per block | `verify_chain_integrity()` traversing genesis to tip | `test_defense_pipeline_and_ledger.py` | Provides tamper-evidence (not tamper-prevention against root OS physical drive overwrite). |
| **Binary Merkle Tree** | Incremental historical block aggregation | Binary tree reduction | Native Python pairwise SHA-256 | 256-bit Merkle root | Recomputation over all block hashes | `test_clip_ledger_integration.py` | Recalculated incrementally; order-sensitive. |
| **WOTS+** | Stateless hash-based one-time signatures | RFC 8391 / SLH-DSA construction | Pure Python `services/assurance/post_quantum.py` | $w=16$, SHAKE-256 hash chains | Hash chain iteration verification | `test_post_quantum_crypto.py` | One-time key pair usage restriction; signature size is ~2.1 KB. Experimental readiness tier. |

---

## 3. Disclaimed Overclaims & Explicit Guardrails

1. **NO "Platform-Wide Post-Quantum Security"**: While SHAKE-256 is an extendable-output function from FIPS 202 offering 256 bits of Grover collision resistance, the system's contributor signing uses classical Ed25519. The system must always be described as:  
   > *"Dual cryptographic digest using SHA-256 and SHAKE-256."*
2. **NO "Unhackable / Tamper-Proof"**: Cryptographic hash chaining provides mathematical **tamper-evidence**, not physical hardware protection. Modifying historical records is detected with mathematical certainty, but software cannot prevent an attacker with root OS access from physically modifying local disk blocks.
3. **NO "Decentralized Blockchain"**: IBVAP is an air-gapped, zero-WAN, high-speed local cryptographic ledger optimized for sub-millisecond edge video analytics. It does not use peer-to-peer consensus, proof-of-work, or mining.
