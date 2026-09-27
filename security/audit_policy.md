# AUDIT_POLICY.md — System Audit & Log Management Policy

> **Status: ACTIVE POLICY**
> Establishes traceability for all security-relevant operational actions.

---

## 1. Audit Scope

The following events must generate non-repudiable audit records:
1. **Operator Actions**:
   - Incident acknowledgment (`POST /api/v1/incidents/{id}/acknowledge`)
   - Incident lifecycle updates (`POST /api/v1/incidents/{id}/status`)
   - Camera addition, removal, or parameter changes
   - Zone geometry modifications
2. **System Health Transitions**:
   - Camera transition from `ONLINE` to `DEGRADED` / `OFFLINE` / `RECONNECTING`
   - Inference pipeline restart or crash recovery
3. **Cryptographic Events**:
   - Execution of ledger verification (`GET /api/v1/evidence/verify_ledger`)
   - Detection of any ledger discontinuity or hash mismatch

---

## 2. Audit Log Format

Audit events are emitted as structured JSON objects via `structlog`:

```json
{
  "timestamp": "2026-09-06T00:15:30.123456Z",
  "event_type": "AUDIT_INCIDENT_STATUS_CHANGE",
  "operator_id": "OPERATOR_ALPHA_42",
  "incident_id": "01d6c851-afec-41eb-97e7-4beb1a03c6b5",
  "previous_status": "NEW",
  "new_status": "INVESTIGATING",
  "client_ip": "10.63.26.100",
  "user_agent": "IBVAP-React-Console/1.0"
}
```

---

## 3. Log Protection & Retention

- **Write-Only Storage**: In production, audit logs are forwarded to an append-only remote syslog or immutable storage bucket.
- **Log Rotation**: Local audit logs rotate daily with a 90-day retention window.
- **Audit Verification**: Periodic automated routines verify that no sequence IDs in the evidence ledger are missing or have altered timestamps.
