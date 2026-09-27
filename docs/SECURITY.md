# IBVAP System Cybersecurity Architecture & Hardening Document

**Document Version**: 1.0.0  
**Classification**: Defense & Law Enforcement Operational Spec  
**Target Platform**: Edge & On-Premises Air-Gapped Surveillance Nodes  

---

## 1. Threat Model & Asset Classification

### Protected Assets
1. **Live Camera Streams (RTSP/WebRTC)**: Eavesdropping, stream hijacking, spoofing.
2. **Recorded Evidentiary Assets**: Video clips, high-resolution crops, bounding box JSON payloads.
3. **Audit Ledger**: Incident history, operator acknowledgment trails, classification logs.
4. **AI Models & Pipeline Configurations**: Model weights, detection thresholds, polygon coordinates.

### Threat Matrix & Mitigations
| Threat Actor | Vector | Potential Impact | IBVAP Safeguard |
| :--- | :--- | :--- | :--- |
| **Network Snooper** | Eavesdropping on LAN | Intercept live feeds or incident data | MediaMTX authentication, localhost-isolated RTSP bindings, internal token authentication |
| **Rogue Operator** | Evidence tampering | Altering snapshots or timestamps in court | **SHA-256 Cryptographic Hash Chain Ledger** linking each incident to prior block |
| **Web Attacker** | Path Traversal (`../../`) | Arbitrary file read on host | Strict file basename regex and explicit directory sandboxing in evidence downloads |
| **Denial of Service** | Flooding WebSocket / API | Exhausting server resources | Endpoint rate-limiting, bounded ring buffers (`FrameBuffer` maxsize drop) |
| **Malicious Model Injection** | Poisoned weights | Corrupting detections | Model hash verification on boot; AGPL-3.0 compliance checks |

---

## 2. Cryptographic Evidence Integrity (Hash Chain Ledger)

Rather than relying on heavy external third-party blockchain dependencies, IBVAP implements an immutable, zero-dependency, locally verifiable SHA-256 hash chain:

```
Genesis Block (Previous Hash: 0000...0000)
    │
    ▼
Block 1: Hash1 = SHA-256(PrevHash0 + IncidentID_1 + EvidenceSHA256_1 + Timestamp_1 + PayloadDigest_1)
    │
    ▼
Block 2: Hash2 = SHA-256(Hash1 + IncidentID_2 + EvidenceSHA256_2 + Timestamp_2 + PayloadDigest_2)
    │
    ▼
Block N: HashN = SHA-256(HashN-1 + IncidentID_N + EvidenceSHA256_N + Timestamp_N + PayloadDigest_N)
```

### Verification
Any operator or external auditor can run:
```bash
GET /api/v1/evidence/verify_ledger
```
or inspect offline using `python -m pytest tests/test_hash_chain.py`. If a single byte of evidence or database record is altered, the cryptographic chain is immediately invalidated, pointing to the exact corrupted sequence ID.

---

## 3. Network & Application Hardening Checklist

- [x] **CORS Configuration**: Restricted to trusted local development and operator workstation origins (`http://localhost:5173`).
- [x] **Path Traversal Protection**: Evidence serving strictly resolves against canonical `data/evidence/` path.
- [x] **Safe Credential Handling**: RTSP URLs with embedded basic authentication are masked and hashed (`rtsp_url_hash`).
- [x] **SQL Injection Prevention**: 100% parameterized queries via SQLAlchemy 2.0 ORM.
- [x] **Graceful Resource Clamping**: Ring buffers drop stale frames under CPU pressure to maintain bounded RAM (<1.2 GB).
- [x] **Secure Air-Gapped Deployment**: Zero cloud phone-home calls, telemetry, or external API reliance.
