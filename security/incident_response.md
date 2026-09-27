# Incident Response Plan

## Security Incident Types

| Type | Example | Severity |
|------|---------|---------|
| Evidence tampering | JPEG file modified | CRITICAL |
| Unauthorized API access | Unknown IP accessing incidents | HIGH |
| Camera stream compromise | Feed replaced with static | HIGH |
| Credential theft | JWT secret exposed | HIGH |
| Denial of Service | API flooded | MEDIUM |
| Insider misuse | Operator deletes evidence | HIGH |

---

## Response Procedures

### Evidence Tampering Detected

1. Immediately run `GET /api/v1/evidence/verify_ledger`
2. Note which `sequence_id` fails
3. Preserve the corrupt evidence file (do not delete)
4. Document timestamp and affected incident_id
5. Escalate to supervisor and legal team
6. Do not restart services until investigation complete

### Unauthorized Access Detected

1. Check API access logs for unauthorized IP
2. Rotate `IBVAP_JWT_SECRET` immediately (invalidates all sessions)
3. Restart backend: `.\scripts\ibvap.ps1 restart-backend`
4. Audit all incident acknowledgments in the past 24h
5. Preserve log files for forensics

### Camera Stream Compromise

1. Check MediaMTX logs for unexpected connections
2. Disconnect suspect camera from network
3. Inspect camera for physical tampering
4. Restore camera from known-good configuration
5. Review evidence frames from the period of suspected compromise

---

## Post-Incident

1. Document timeline of events
2. Identify root cause
3. Update threat model
4. Implement additional controls
5. Test recovery procedures
