# DATA_GOVERNANCE.md — Surveillance Data Governance & Privacy Policy

> **Status: ACTIVE SPECIFICATION**
> Adheres to European-style Privacy-by-Design and MHA Surveillance Integrity Standards.

---

## 1. Principles of Data Governance

1. **Data Minimization**: Only video frames associated with verified rule violations (intrusions, line crossing, ANPR detections) are persisted as persistent evidence. Continuous raw video feeds are buffered transiently in memory and discarded.
2. **Cryptographic Accountability**: Every saved evidence artifact is fingerprinted with a SHA-256 digest and linked into a sequentially hashed ledger.
3. **Strict Storage Boundaries**: Sensitive evidence directories (`data/evidence/`, `data/ibvap_dev.db`) are excluded from version control via `.gitignore`.

---

## 2. Evidence Retention & Lifecycle Policy

| Category | Retention Window | Storage Medium | Destruction Protocol |
|---|---|---|---|
| **Raw Video Buffers** | Transient (5–10 seconds) | In-memory RAM buffer | Flushed on ring-buffer overwrite |
| **Telemetry & Metrics** | 7 days | SQLite / Redis | Rolling purge of records > 7 days |
| **Incident Snapshots** | 90 days (Configurable) | Encrypted Local / NAS Storage | Automated secure file zeroing |
| **Evidence Hash Ledger** | Permanent / Indefinite | Append-only DB Ledger | Immutable historical audit record |

---

## 3. Privacy-Preserving Architecture

### Face & Identity Protection
- Face detection models are architecturally isolated and default to **privacy redaction (blurring)** on operator consoles unless elevated by a warrant-level credential.
- Vehicle registration data is categorized as Restricted PII. ANPR logs must never be exported to external third-party services without end-to-end cryptographic transport.

### Operator Access & Auditability
- All access to evidence snapshots (`/evidence/*.jpg`) requires operator authentication and generates a permanent audit trail entry.
- Manual alteration of evidence files immediately triggers an anomaly event on subsequent ledger verification calls (`GET /api/v1/evidence/verify_ledger`).

---

## 4. Compliance Checklist

- [x] No raw CCTV streams stored indefinitely without cause.
- [x] Evidence files protected by SHA-256 hashing.
- [x] Chain-of-custody verifiable via tamper-evident ledger.
- [x] Separation of concerns between detection metadata and stored media.
- [ ] Face blurring pipeline activated on live web dashboard (Planned Phase).
- [ ] Automated disk quotas and rolling purging worker (Planned Phase).
