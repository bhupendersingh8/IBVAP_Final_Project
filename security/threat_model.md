# IBVAP Threat Model

## Assets Under Protection

| Asset | Value | Location |
|-------|-------|----------|
| Camera streams | HIGH — real-time surveillance | MediaMTX, network |
| Evidence frames | CRITICAL — legal chain of custody | `data/evidence/` |
| Hash chain ledger | CRITICAL — tamper-evidence | `data/ibvap_dev.db` |
| Operator credentials | HIGH — dashboard access | `.env` / future auth system |
| Incident/event database | HIGH — operational records | `data/ibvap_dev.db` |
| Zone/camera configuration | MEDIUM — operational config | `configs/*.yaml` |
| Inference model weights | MEDIUM — IP | `yolov8n.pt` |

---

## Threat Actors

| Actor | Motivation | Capability |
|-------|-----------|-----------|
| External intruder | Evade surveillance / disable cameras | Low-Medium |
| Insider operator | Suppress evidence, cover tracks | Medium |
| Network attacker | DoS, data exfiltration | Medium-High |
| Physical attacker | Camera destruction, tampering | Low-High |

---

## Threat Scenarios

### T1 — Camera Stream Hijack
- **Threat**: Attacker replaces RTSP feed with pre-recorded footage
- **Impact**: Surveillance blind spot; missed intrusions
- **Mitigation**: RTSP authentication (NOT_DONE), network isolation (PLANNED), frame anomaly detection (PLANNED)
- **Residual risk**: HIGH until mitigated

### T2 — Evidence Tampering
- **Threat**: Insider modifies evidence JPEG files
- **Impact**: Legal evidence chain broken; accountability failure
- **Mitigation**: SHA-256 + HashChainLedger — tamper immediately detected ✅ PASS
- **Residual risk**: LOW (chain broken if file modified)

### T3 — API Abuse / Denial of Service
- **Threat**: Flood of API requests causes service degradation
- **Impact**: Dashboard unavailable; alerts delayed
- **Mitigation**: Rate limiting (PARTIAL — architecture ready), process isolation
- **Residual risk**: MEDIUM

### T4 — Credential Theft
- **Threat**: JWT secret or operator password stolen
- **Impact**: Unauthorized dashboard access; incident suppression
- **Mitigation**: JWT in env (NOT_DONE — not yet enforced), no hardcoded secrets (PASS)
- **Residual risk**: HIGH (no auth enforced in current prototype)

### T5 — Database Manipulation
- **Threat**: Direct SQLite file access by insider
- **Impact**: Incident records altered or deleted
- **Mitigation**: Hash chain provides independent tamper evidence (PASS); DB file permissions (NOT_DONE)
- **Residual risk**: MEDIUM

### T6 — Malicious API Input
- **Threat**: SQL injection, path traversal, malformed JSON
- **Impact**: Data exfiltration, code execution
- **Mitigation**: SQLAlchemy ORM (PASS), Pydantic validation (PASS), static mount restricted (PASS)
- **Residual risk**: LOW

### T7 — Network Interception
- **Threat**: MITM on dashboard ↔ API traffic
- **Impact**: Credential theft, alert suppression
- **Mitigation**: TLS (PLANNED — not configured in dev)
- **Residual risk**: HIGH in production without TLS

### T8 — Operator Misuse
- **Threat**: Authorized operator suppresses alerts or deletes evidence
- **Impact**: Surveillance failure; legal liability
- **Mitigation**: Audit trail (PARTIAL), hash chain (PASS), RBAC (PLANNED)
- **Residual risk**: MEDIUM

---

## Risk Summary

| Risk | Likelihood | Impact | Current Risk | After Mitigation |
|------|-----------|--------|-------------|-----------------|
| Evidence tampering | LOW | CRITICAL | LOW (mitigated) | LOW |
| API abuse | MEDIUM | MEDIUM | MEDIUM | LOW (after rate limiting) |
| Unauthorized access | MEDIUM | HIGH | HIGH (no auth) | LOW (after JWT) |
| Camera hijack | MEDIUM | HIGH | HIGH | MEDIUM |
| Network interception | MEDIUM | HIGH | HIGH (no TLS) | LOW (after TLS) |
| DB manipulation | LOW | HIGH | MEDIUM | LOW (after permissions) |

---

*Priority hardening: (1) JWT enforcement, (2) TLS, (3) Camera RTSP auth, (4) DB file permissions*
