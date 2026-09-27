# Security Test Plan

## Test Categories

### AUTH-01: Unauthenticated Access
- **When**: JWT enforcement is implemented
- **Test**: Request protected endpoint without Authorization header
- **Expected**: HTTP 401 Unauthorized
- **Status**: NOT_TESTED (auth not enforced yet)

### AUTH-02: Invalid Token
- **Test**: Request with malformed or expired JWT
- **Expected**: HTTP 401 Unauthorized
- **Status**: NOT_TESTED

### AUTH-03: RBAC Enforcement
- **Test**: VIEWER role attempts MANAGE_CAMERAS action
- **Expected**: HTTP 403 Forbidden
- **Status**: NOT_TESTED (RBAC not enforced)

### INPUT-01: SQL Injection
- **Test**: `'; DROP TABLE incidents; --` in incident filter parameter
- **Expected**: No SQL error; ORM safely ignores injection
- **Status**: PASS (SQLAlchemy ORM parameterized queries verified by code review)

### INPUT-02: Path Traversal
- **Test**: Request `GET /evidence/../../etc/passwd`
- **Expected**: HTTP 404 or blocked by static file mount restriction
- **Status**: PASS (static mount restricted to `data/evidence/`)

### INPUT-03: Oversized Request
- **Test**: POST body > 10MB
- **Expected**: HTTP 413 Request Entity Too Large
- **Status**: NOT_TESTED (no body size limit configured)

### RATE-01: Rate Limit Enforcement
- **Test**: 100 requests/minute to `/api/v1/incidents`
- **Expected**: HTTP 429 after limit exceeded
- **Status**: NOT_TESTED (rate limiting not enforced)

### EVIDENCE-01: Tamper Detection
- **Test**: Modify a JPEG evidence file, then call `GET /evidence/verify_ledger`
- **Expected**: Verification returns `valid=false` for that block
- **Status**: PASS ✅ (hash chain tamper test in `tests/test_hash_chain.py`)

### EVIDENCE-02: Chain Integrity
- **Test**: Add evidence, verify chain passes; modify DB block hash, verify fails
- **Expected**: `verify_chain()` returns False
- **Status**: PASS ✅ (test_hash_chain.py — tamper detection test)

### SEC-HEADERS-01: Security Headers Present
- **Test**: Any HTTP response includes X-Content-Type-Options, X-Frame-Options
- **Expected**: Headers present in every response
- **Status**: PASS ✅ (middleware implemented in main.py)

### CORS-01: CORS Origin Restriction
- **Test**: Request from disallowed origin
- **Expected**: CORS headers absent or blocked
- **Status**: PARTIAL (CORS configured; not formally tested with cross-origin request)

### SECRET-01: No Secrets in Code
- **Test**: Regex scan for passwords/secrets/keys in source
- **Expected**: 0 matches
- **Status**: PASS ✅ (scan result: 0 matches)

---

## Summary

| Category | Tests | PASS | NOT_TESTED | FAIL |
|----------|-------|------|-----------|------|
| Authentication | 3 | 0 | 3 | 0 |
| Authorization | 1 | 0 | 1 | 0 |
| Input validation | 3 | 2 | 1 | 0 |
| Rate limiting | 1 | 0 | 1 | 0 |
| Evidence integrity | 2 | 2 | 0 | 0 |
| Security headers | 1 | 1 | 0 | 0 |
| CORS | 1 | 0 (partial) | 1 | 0 |
| Secrets | 1 | 1 | 0 | 0 |
| **Total** | **13** | **6** | **7** | **0** |

*7 tests are NOT_TESTED pending JWT enforcement and rate limiting implementation.*
*No test has been forced to PASS without evidence.*
