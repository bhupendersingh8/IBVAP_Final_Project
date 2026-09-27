# Security Policy — IBVAP

## Scope

This document describes the security architecture, threat model, and security
assumptions for the IBVAP (Intelligent Border Video Analytics Platform)
prototype.

---

## Important Disclaimers

> **This is a SIH research prototype.**
> It has NOT undergone formal security assessment, penetration testing,
> or certification against any government or military security standard.
> Actual border-security deployment MUST include independent security review.

---

## Threat Model

### Assets We Protect

| Asset | Risk if Compromised |
|---|---|
| Camera credentials / RTSP URLs | Attacker gains direct camera access |
| Incident evidence files | Tampered evidence loses forensic value |
| Operator accounts | Unauthorized alert suppression or false alerts |
| Model weights | Model poisoning / adversarial manipulation |
| Audit logs | Covering tracks after unauthorized access |
| System configuration | Service disruption or mis-routing |

### Threats Considered

| Threat | Mitigation |
|---|---|
| Credential exposure via Git | .gitignore + .env pattern; secrets in environment only |
| Unauthorized dashboard access | JWT authentication + RBAC |
| Operator account compromise | Strong password hashing (bcrypt) + session expiry |
| SQL injection | SQLAlchemy ORM + parameterized queries only |
| Path traversal in evidence | File path validation + restricted storage root |
| Malicious file upload | Extension whitelist + size limits |
| Model poisoning via feedback | Feedback never directly modifies weights; human approval required |
| Data poisoning | Fixed validation set protected from retraining data |
| Camera tampering | Tamper detection alerts (blackout / static frame) |
| Network interception | TLS-ready configuration; enforce in production |
| Unauthorized evidence access | RBAC; evidence access is audit-logged |

### Out of Scope (Prototype Limitations)

- Hardware-level physical security
- Nation-state-level network attacks
- Supply-chain attacks on dependencies
- Formal cryptographic certification
- Legal admissibility certification

---

## Security Controls

### Authentication & Authorization

- JWT-based authentication with configurable expiry
- Role-Based Access Control (RBAC):
  - `admin` — full system access, user management, model promotion
  - `operator` — acknowledge alerts, submit feedback, view incidents
  - `read_only` — view-only access, no write operations
- Passwords hashed with bcrypt (via passlib)
- Refresh token rotation

### Secrets Management

- All secrets via environment variables (`.env` file)
- `.env` is `.gitignore`d — never committed
- No hardcoded credentials anywhere in source code
- Camera RTSP URLs stored in `configs/cameras.yaml` (excluded from Git)

### Data Protection

- Evidence files stored outside the SQL database (file references only)
- SHA-256 hash recorded for evidence integrity verification
  - Note: SHA-256 verifies file integrity only. It does not automatically
    establish legal admissibility.
- Evidence access is audit-logged per access event
- No complete video streams stored in the relational database

### Network Security

- CORS restricted to configured origins only
- Security headers: X-Content-Type-Options, X-Frame-Options, etc.
- Rate limiting on authentication endpoints
- TLS-ready (configure reverse proxy with TLS in production)
- WebSocket connections require authentication

### Audit Logging

All security-sensitive actions are logged with:
- actor (user ID)
- action
- timestamp (UTC)
- resource
- result (success/failure)
- request reference ID

Audit records are append-only. Operators cannot modify audit history.

### Model Security

- Operator feedback NEVER directly modifies production model weights
- All model promotions require explicit human approval
- Canary deployment on one camera before full rollout
- Previous model versions retained for instant rollback
- Model versions tracked in registry with metadata and hashes

### Dependency Security

- `pip-audit` for Python dependency vulnerability scanning
- Regular dependency updates recommended
- SBOM (Software Bill of Materials) generated via `cyclonedx-py`
- Container image scanning via Docker Scout (when Docker is used)

---

## Reporting Security Issues

This is a student research prototype. If you identify a security issue:

1. Do NOT publicly disclose it before it is addressed
2. Contact the development team directly
3. Provide: description, reproduction steps, potential impact

---

## What This System Does NOT Claim

- ❌ Certified against NIC, CERT-In, or MHA security frameworks
- ❌ Legally admissible evidence (requires formal chain-of-custody)
- ❌ Zero false positives or false negatives
- ❌ Production-ready without independent security review
- ❌ Compliance with any specific data protection regulation

---

*Last updated: 2026-09-04*
