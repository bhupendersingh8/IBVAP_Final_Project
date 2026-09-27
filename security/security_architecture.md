# SECURITY_ARCHITECTURE.md — Security Controls & Threat Defense Architecture

> **Status: HARDENING PHASE**
> Incorporates Zero-Trust, Principle of Least Privilege, and Cryptographic Traceability.

---

## 1. Security Architecture Overview

The IBVAP security perimeter is partitioned into four defense rings:

```
┌────────────────────────────────────────────────────────┐
│ Ring 0: Cryptographic Ledger (SHA-256 Hash Chain)       │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Ring 1: Application Security (FastAPI, RBAC, DB) │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │ Ring 2: Network & Ingestion Boundary       │  │  │
│  │  │  ┌──────────────────────────────────────┐  │  │  │
│  │  │  │ Ring 3: Physical & Sensor Layer      │  │  │  │
│  │  │  └──────────────────────────────────────┘  │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## 2. Layered Controls

### Ring 3: Physical & Sensor Layer
- **Tamper Alerting**: Continuous tracking of camera stream integrity. If frame entropy drops abruptly (camera covered, disconnected, or spray-painted), health monitors transition to `DEGRADED` or `OFFLINE`.
- **RTSP URL Masking**: Camera connection strings in logs have authentication credentials sanitized prior to logging.

### Ring 2: Network & Ingestion Boundary
- **Isolated Surveillance Subnet**: CCTV cameras communicate over an isolated VLAN or local bridge.
- **Security Response Headers**: All HTTP responses emit strict headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`).
- **CORS Allow-listing**: Restricted explicitly to the trusted frontend origins.

### Ring 1: Application Security
- **Parameterization**: Direct database queries use SQLAlchemy async ORM, preventing SQL Injection.
- **Path Traversal Shield**: The `/evidence` static endpoint explicitly maps to `./data/evidence`, preventing access to root or parent file systems.
- **Role-Based Access Control (RBAC)**: Formalized roles (`VIEWER`, `OPERATOR`, `ADMIN`, `SYSTEM`) and discrete permissions (`VIEW_INCIDENTS`, `ACKNOWLEDGE_INCIDENTS`, `MANAGE_CAMERAS`, etc.).
- **Forward-Compatible Authentication**: JWT authentication module stubbed in `apps/backend/auth/jwt_auth.py`.

### Ring 0: Cryptographic Ledger
- **Evidence Immutability**: Every saved frame creates a cryptographically linked `HashChainBlock`.
- **Tamper Detection**: An external auditor can invoke `/api/v1/evidence/verify_ledger` to immediately confirm whether any incident JPEG or database sequence record has been manipulated.

---

## 3. Defense Against OWASP Top 10

| OWASP Vulnerability | IBVAP Defense | Verification |
|---|---|---|
| **A01: Broken Access Control** | Enforced roles via RBAC schema & permissions table | Unit verified |
| **A02: Cryptographic Failures** | SHA-256 for all evidence hashes & chained blocks | PASS (test_hash_chain) |
| **A03: Injection** | Strict SQLAlchemy ORM parameterized queries; Pydantic request models | PASS (test_detection/test_rules) |
| **A04: Insecure Design** | Separation of ingestion, inference, database, and telemetry | PASS (architecture audit) |
| **A05: Security Misconfiguration** | Defensive HTTP headers injected on every request | PASS (main.py middleware) |
| **A07: Identification & Auth Failures** | Centralized JWT auth handler stub ready for token validation | Structured in backend/auth |
| **A08: Software & Data Integrity Failures** | Immutable block hashes and continuous chain validation | PASS (test_hash_chain) |
