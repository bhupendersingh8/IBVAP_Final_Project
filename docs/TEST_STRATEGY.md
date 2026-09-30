# TEST_STRATEGY.md — Comprehensive Test & Verification Strategy

> **Status: ACTIVE & ENFORCED**
> Core Rule: Never convert an unverified test into a PASS. No synthetic claims.

---

## 1. Test Pyramid & Methodology

```
                   ▲
                  / \
                 /   \
                / E2E \       Live RTSP + WebSocket + UI Acceptance
               /-------\
              /  Integ  \     Pipeline, Hash Chain, Database, Events
             /-----------\
            /    Unit     \   Geometry, BBox, Schemas, Trackers, Adapters
           /---------------\
```

### Philosophy
1. **Deterministic Isolation**: Tests must run without network access, live camera hardware, or external dependencies.
2. **Failure Transparency**: Any feature that lacks hardware (e.g. NVIDIA GPU) or high-res input (ANPR live validation) reports `NOT_VERIFIED` or `PARTIAL`, never a fabricated `PASS`.
3. **No Mocks as Production Proof**: Mocks are strictly for verifying unit boundaries, never for declaring an entire system capability "verified in production".

---

## 2. Test Suite Structure

The IBVAP pytest suite contains 54 automated tests across 5 primary test modules:

```
tests/
├── test_anpr.py           (9 tests)   - Vehicle subclassing, OCR abstraction, consensus logic, DB persistence
├── test_detection.py      (4 tests)   - BBox geometry validation, bounds enforcement, mock detector
├── test_hash_chain.py     (4 tests)   - Cryptographic ledger integrity, block linking, tamper detection
├── test_rules.py          (3 tests)   - Bottom-center ground contact, polygon containment, intrusion trigger
└── test_tracking.py       (34 tests)  - ByteTrack/IoU fallback, persistent IDs, trajectories, UTC timestamps
```

---

## 3. Test Modules & Invariants

### A. ANPR Pipeline (`tests/test_anpr.py`)
- **Preservation of Vehicle Subclasses**: Ensures class `vehicle` retains specific attributes (`car`, `truck`, `motorcycle`).
- **Unreadable on Blur/Low Res**: Asserts that degraded crops return `UNREADABLE`, preventing hallucinated text.
- **Consensus Voting**: Validates candidate thresholding (minimum 3 consistent frames) before reaching `STABLE_VERIFIED`.
- **Conflict Handling**: Conflicting reads downgrade plate state to `LOW_CONFIDENCE`.

### B. Detection Validation (`tests/test_detection.py`)
- **BBox Geometry**: Coordinates must be normalized $[0, 1]$ where $x_1 \le x_2$ and $y_1 \le y_2$. Out-of-bound coordinates immediately raise `ValueError`.
- **Confidence Bounds**: Requires $0.0 \le \text{confidence} \le 1.0$.

### C. Evidence Integrity (`tests/test_hash_chain.py`)
- **Deterministic Hashing**: SHA-256 computed on sequence ID, evidence hash, timestamp, and previous block hash.
- **Tamper Evident**: Modifying a historical block breaks chain validation and raises an integrity failure.

### D. Geometry & Rules (`tests/test_rules.py`)
- **Ground Contact Point**: Bottom-center $(x_1 + x_2)/2, y_2$ is enforced as the contact anchor for fence intrusion, eliminating horizon perspective errors.
- **Ray-Casting Polygon Containment**: Evaluates complex concave and convex restricted boundary zones.

### E. Object Tracking (`tests/test_tracking.py`)
- **UTC Timezone Enforcement**: Every timestamp on track points and results must be explicitly timezone-aware (`timezone.utc`).
- **Trajectory Pruning**: Trajectories are bounded to prevent memory growth under long-running RTSP feeds.
- **Track Lifecycle**: State transitions `ACTIVE -> LOST -> REMOVED` based on `max_age` frame timeout.

---

## 4. Manual & System Acceptance Testing

| Level | Method | Tool | Frequency |
|---|---|---|---|
| **API Endpoints** | HTTP health & data assertions | FastAPI TestClient / cURL | Pre-commit |
| **Frontend UI** | TypeScript compilation & bundling | `npm run build` | Every release |
| **Live Stream** | Real-time RTSP + WebRTC relay | MediaMTX / VLC / Browser | Staging demo |
| **End-to-End** | Master orchestrator smoke test | `.\scripts\ibvap.ps1 demo` | Final freeze |

---

## 5. Running the Test Suite

```powershell
# Run full automated regression suite
C:\Python314\python.exe -m pytest tests/ -v --tb=short

# Run specific test module
C:\Python314\python.exe -m pytest tests/test_hash_chain.py -v

# Frontend build verification
cd apps\frontend
npm run build
```
