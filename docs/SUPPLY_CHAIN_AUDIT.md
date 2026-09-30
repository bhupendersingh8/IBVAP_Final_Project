# IBVAP — AI & Software Supply Chain Security Audit
## CycloneDX v1.5 AIBOM, Multi-Contributor Governance, and Dependency Lineage

**Document ID**: IBVAP-AUD-SUPPLY-2026  
**Target Repository**: `feature/tcvf-assurance-layer`  
**Problem Statement**: SIH26228 (Multi-Contributor Computer Vision Assurance)  

---

## 1. Multi-Contributor Threat Model in Computer Vision

In multi-agency or multi-vendor computer vision projects (e.g. smart cities, border security, defense surveillance), models and datasets originate from distributed third parties:
- Vendor A supplies low-light enhancement models.
- University B contributes fine-tuned object detection checkpoints.
- Third-party contractor C provides automated license plate recognition models.

**Vulnerabilities in Traditional Pipelines**:
1. Blindly importing `.pt` / `.onnx` files without contributor verification.
2. Silent weight poisoning or backdoor insertion by rogue contributors.
3. Lack of provenance regarding training data lineage and licenses.
4. Supply chain confusion attacks (dependency hijacking).

---

## 2. CycloneDX v1.5 AI Bill of Materials (AIBOM)

IBVAP implements automated machine-readable AIBOM generation adhering to the **CycloneDX v1.5 JSON Specification** via [`services/assurance/aibom_cyclonedx.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/aibom_cyclonedx.py).

### 2.1 AIBOM Component Structure

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.5",
  "serialNumber": "urn:uuid:6a839f22-4a57-4f10-91a1-37d45f8cb490",
  "version": 1,
  "metadata": {
    "timestamp": "2026-09-30T07:37:39Z",
    "tools": [
      { "vendor": "IBVAP", "name": "AIBOM Generator", "version": "1.0.0" }
    ],
    "component": {
      "type": "machine-learning-model",
      "name": "yolo11n-border-sentry",
      "version": "1.0.0",
      "hashes": [
        {
          "alg": "SHA-256",
          "content": "0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1"
        }
      ]
    }
  },
  "components": [
    {
      "type": "data",
      "name": "ExDark-LowLight",
      "version": "1.0",
      "licenses": [{ "license": { "id": "CC-BY-4.0" } }]
    },
    {
      "type": "library",
      "name": "torch",
      "version": "2.11.0+cu128",
      "licenses": [{ "license": { "id": "BSD-3-Clause" } }]
    },
    {
      "type": "library",
      "name": "cryptography",
      "version": "42.0.5",
      "licenses": [{ "license": { "id": "Apache-2.0" } }]
    }
  ]
}
```

---

## 3. Contributor Manifest & Ed25519 Signing Workflow

Every model checkpoint ingested into the IBVAP pipeline must be accompanied by an Ed25519-signed **Contributor Manifest** ([`services/assurance/contributor_manifest.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/contributor_manifest.py)):

```
[Contributor: Training & Export]
                |
                v
[Generate Checkpoint SHA-256 + CycloneDX AIBOM]
                |
                v
[Sign Digest using Contributor Private Key (Ed25519)]
                |
                v
[Package model_manifest.json with Public Key]
                |
                v
[IBVAP Ingestion Gateway: Verify Signature against Authorized Contributor Registry]
                |
        +-------+-------+
        | Valid         | Invalid Signature / Untrusted Public Key
        v               v
[Behavioral Gating]  [QUARANTINE: REJECT CHECKPOINT]
```

### Manifest Fields:
- `contributor_id`: Registered identity string (e.g. `team-trinetra-dev`).
- `model_name` & `model_version`: Architecture name and version tag.
- `weight_sha256`: Cryptographic digest of physical `.pt` or `.onnx` weight file.
- `aibom_sha256`: Cryptographic digest of associated CycloneDX AIBOM JSON.
- `public_key`: Base64-encoded 32-byte Ed25519 public key.
- `signature`: Base64-encoded 64-byte Ed25519 signature over canonical manifest payload.

---

## 4. The "Signed $\neq$ Safe" Architecture Safeguard

A critical supply chain insight implemented in IBVAP:
> **Cryptographic signing guarantees provenance and tamper-free transit, NOT benign runtime behavior.**

An authorized contributor with valid credentials may:
1. Suffer an internal credential compromise (stolen private key).
2. Train on poisoned data unknowingly containing trojan triggers.
3. Introduce silent behavioral regressions.

Therefore, IBVAP mandates **Dual-Gated Model Admission**:
- **Gate 1 (Cryptographic)**: Ed25519 signature must match authorized contributor public key.
- **Gate 2 (Behavioral)**: Checkpoint must execute against a deterministic synthetic probe battery ([`services/assurance/model_fingerprint.py`](file:///C:/Users/anmol/.gemini/antigravity/scratch/IBVAP_Final_Project/services/assurance/model_fingerprint.py)). If output activation drift $\Delta_{\text{drift}} \ge 0.15$ relative to baseline, the checkpoint is **QUARANTINED** despite possessing a valid signature.

---

## 5. Dependency License Audit

| Component | Library Version | Declared License | Operational Scope |
| :--- | :--- | :--- | :--- |
| **Deep Learning Framework** | PyTorch 2.11.0+cu128 | BSD-3-Clause | Edge Tensor Compute & Model Execution |
| **Computer Vision** | OpenCV 4.10.0 | Apache-2.0 | Frame Ingestion & Spatial Preprocessing |
| **Object Detection Engine** | Ultralytics (YOLO) | AGPL-3.0 | Local Edge Inference Worker |
| **Cryptographic Engine** | PyCA Cryptography 42.0+ | Apache-2.0 / BSD | Ed25519 Signatures & Key Management |
| **Relational Evidence Store**| DuckDB 1.1.0+ | MIT | Local In-Memory & File Append-Only Ledger |
| **Web API Framework** | FastAPI & Pydantic | MIT | Local REST Endpoints & WebSocket Server |
| **ExDark Dataset** | 12 Classes Low-Light | CC BY 4.0 | Benchmark Evaluation & Domain Pre-training |
| **LLVIP Dataset** | Vis-Thermal Paired | Academic Non-Commercial | Night-Vision Cross-Modal Evaluation |
| **RESIDE-RTTS Dataset** | Outdoor Hazy/Fog | Research License | Fog & Haze Preprocessing Benchmarking |
