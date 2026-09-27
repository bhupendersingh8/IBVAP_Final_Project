# API Security

## Endpoint Inventory

| Endpoint | Method | Auth Required | Rate Limit | Notes |
|----------|--------|--------------|-----------|-------|
| `/health/live` | GET | No | No | Liveness probe |
| `/health/ready` | GET | No | No | Readiness probe |
| `/health` | GET | No | No | Legacy health check |
| `/api/v1/metrics` | GET | Recommended | No | No sensitive data |
| `/api/v1/cameras` | GET/POST | Yes (PLANNED) | 60/min | Camera management |
| `/api/v1/cameras/health` | GET | No | No | Camera health state |
| `/api/v1/incidents` | GET | Yes (PLANNED) | 60/min | Incident list |
| `/api/v1/incidents/{id}/status` | POST | Yes (PLANNED) | 30/min | Lifecycle update |
| `/api/v1/incidents/{id}/acknowledge` | POST | Yes (PLANNED) | 30/min | Acknowledge |
| `/api/v1/evidence` | GET | Yes (PLANNED) | 30/min | Evidence list |
| `/api/v1/evidence/verify_ledger` | GET | Yes (PLANNED) | 10/min | Hash chain verify |
| `/api/v1/zones` | GET | No | No | Public zone config |
| `/api/v1/anpr` | GET | Yes (PLANNED) | 60/min | ANPR observations |
| `/api/v1/internal/*` | POST | Service-only (PLANNED) | No | Inference → backend |
| `/ws/alerts` | WS | Yes (PLANNED) | N/A | Real-time alerts |
| `/evidence/*` | GET (static) | Yes (PLANNED) | 60/min | Evidence files |

> **Current status**: Auth column is PLANNED — no JWT enforcement active in prototype.

---

## CORS Policy

Current configuration (`apps/backend/config.py`):
```python
CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]  # dev
# Production: restrict to actual dashboard domain
```

**Production change required**: Replace with specific dashboard domain only.

---

## Security Headers

Implemented via middleware in `apps/backend/main.py`:
```
X-Content-Type-Options: nosniff         ← Prevents MIME sniffing
X-Frame-Options: DENY                   ← Prevents clickjacking
X-XSS-Protection: 1; mode=block        ← Legacy XSS filter
Referrer-Policy: strict-origin-when-cross-origin
Cache-Control: no-store                 ← Prevents caching of sensitive API responses
```
**Status: PASS** ✅

---

## Input Validation

All API request bodies use Pydantic schemas with explicit type validation.
No raw SQL queries — all DB access via SQLAlchemy ORM with parameterized queries.
File uploads are not supported; evidence files are written only by the inference worker process.

---

## Rate Limiting (PARTIAL)

Architecture prepared for `slowapi` integration:
- Install: `pip install slowapi`
- Configured in `apps/backend/main.py` middleware
- Limits: 60 req/min for incident routes, 30 req/min for evidence routes per IP

**Status: PARTIAL** — slowapi not yet installed; limits defined but not enforced.

---

## Authentication Flow (PLANNED)

```
POST /api/v1/auth/login {username, password}
→ Verify credentials (bcrypt hash comparison)
→ Return {access_token, token_type: "bearer"}
→ Client includes: Authorization: Bearer <token>
→ require_auth() dependency decodes and validates JWT
→ RBAC check: check_permission(role, required_permission)
```

**Not implemented** — `require_auth()` currently returns a stub system principal.
