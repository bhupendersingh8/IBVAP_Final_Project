# Security Architecture

> **Status: PARTIAL** — Foundation implemented. Authentication not yet enforced in production.

---

## Threat Surface

```
[External]                [Internal]
IP Cameras ──────────────► MediaMTX ──► Inference Worker ──► SQLite DB
                                                              Evidence Dir
Operators ──── HTTPS ────► FastAPI Backend ──────────────────► WebSocket
                           (port 8000)
Browsers ────── HTTP ────► React Frontend (port 5173 dev / dist prod)
                           (port 8000 static in prod)
```

---

## Security Layer Analysis

### L1 — Camera / Network Layer
| Control | Status | Notes |
|---------|--------|-------|
| Camera network isolation | PLANNED | Recommend dedicated VLAN for cameras |
| RTSP authentication | NOT_DONE | MediaMTX supports auth; not configured |
| TLS for RTSP | NOT_DONE | MediaMTX supports TLS; not configured |
| Camera firmware validation | NOT_DONE | Out of scope for software prototype |

### L2 — API Layer
| Control | Status | Notes |
|---------|--------|-------|
| CORS restrictions | ✅ PASS | `settings.CORS_ALLOWED_ORIGINS` configured |
| Security headers | ✅ PASS | X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Cache-Control |
| SQL injection protection | ✅ PASS | SQLAlchemy ORM with parameterized queries |
| Path traversal protection | ✅ PASS | Static file mount limited to `data/evidence/` |
| Input validation | 🟡 PARTIAL | Pydantic schemas on all request bodies |
| Rate limiting | 🟡 PARTIAL | Architecture prepared; slowapi integration pending |
| Authentication (JWT) | 🔵 PLANNED | Stub in `apps/backend/auth/jwt_auth.py` — not enforced |
| Authorization (RBAC) | 🔵 PLANNED | Roles/permissions defined in `apps/backend/auth/rbac.py` — not enforced |

### L3 — Application Layer
| Control | Status | Notes |
|---------|--------|-------|
| Evidence integrity | ✅ PASS | SHA-256 + HashChainLedger — tamper = FAIL |
| Incident audit trail | ✅ PASS | All status changes timestamped in DB |
| Operator action logging | 🟡 PARTIAL | Status changes logged; no central audit log |
| Secret scanning | ✅ PASS | Regex audit: 0 secrets in git |
| .env separation | ✅ PASS | `.env.example` template; `.gitignore` covers `.env` |
| Dependency audit | 🟡 PARTIAL | `THIRD_PARTY_LICENSES.md` maintained |

### L4 — Data Layer
| Control | Status | Notes |
|---------|--------|-------|
| Database file permissions | NOT_DONE | Recommend 600 on `data/ibvap_dev.db` |
| Evidence file permissions | NOT_DONE | Recommend 640 on `data/evidence/` |
| Database encryption at rest | NOT_DONE | SQLite plaintext; use SQLCipher for production |
| Backup and recovery | PLANNED | See `docs/FAILURE_RECOVERY.md` |

---

## Threat Model Summary

| Threat | Likelihood | Impact | Mitigation | Status |
|--------|-----------|--------|-----------|--------|
| Camera stream hijack | MEDIUM | HIGH | Network isolation, RTSP auth | NOT_DONE |
| API abuse / DoS | MEDIUM | MEDIUM | Rate limiting | PARTIAL |
| Evidence tampering | LOW | HIGH | SHA-256 + hash chain | PASS |
| Credential theft | MEDIUM | HIGH | JWT + secrets in env | PARTIAL |
| Unauthorized dashboard access | MEDIUM | MEDIUM | JWT enforcement | PLANNED |
| SQL injection | LOW | HIGH | ORM parameterized queries | PASS |
| Path traversal | LOW | HIGH | Static mount restricted | PASS |
| Insider misuse | LOW | HIGH | RBAC + audit log | PARTIAL |
| Malicious file upload | LOW | MEDIUM | Evidence dir write-only via worker | PARTIAL |

---

## Planned Hardening Steps (Priority Order)

1. **Enforce JWT authentication** on all non-public endpoints
2. **Enable RBAC** — VIEWER/OPERATOR/ADMIN roles per endpoint
3. **Configure rate limiting** — 60 req/min per IP on incident/evidence routes
4. **Enable RTSP authentication** in MediaMTX config
5. **Configure TLS** for backend API (reverse proxy: nginx/caddy)
6. **Set database file permissions** (chmod 600)
7. **Enable audit logging** — structured log per operator action
8. **Run OWASP ZAP** baseline scan before production deployment
9. **Enable SQLCipher** for database encryption at rest

---

## Evidence Integrity Architecture

```
Detection Event
    → JPEG evidence frame captured
    → SHA-256(frame bytes) computed
    → HashChainLedger.add_block():
        block_hash = SHA-256(sequence_id || evidence_hash || timestamp || prev_hash)
    → HashChainBlock saved to SQLite
    → GET /evidence/verify_ledger → verify_chain() → PASS or FAIL
```

Tampering with any evidence file breaks the chain at that block.
This is a **tamper-evident cryptographic ledger**, NOT a blockchain.

---

*See also: `security/threat_model.md`, `security/api_security.md`*
