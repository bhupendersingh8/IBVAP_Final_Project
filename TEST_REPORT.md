# IBVAP — Comprehensive Test & Verification Report
**Date:** 2026-09-27  
**Host:** Dell Laptop (Intel Core i3-1115G4 @ 3.00GHz, 12GB RAM, Windows 11)  
**Environment:** Python 3.11.9 (`C:\Users\dell\Desktop\p2\venv`) | PyTorch 2.4.1+cpu | OpenCV 4.10.0 | Ultralytics 8.2.100 | Node v25.9.0  

---

## 1. Executive Summary

| Subsystem / Suite | Target Verified | Method | Result | Status |
|---|---|---|---|---|
| **Python Environment** | Python 3.11.9 + CPU wheels | `scripts/verify_env.py` | Torch 2.4.1+cpu, OpenCV 4.10, Ultralytics 8.2, Lap 0.5.9 | **PASS** |
| **FastAPI Backend Core** | 76 registered API & WS routes | `scripts/test_backend_import.py` | Clean import, Pydantic-settings valid, CORS valid | **PASS** |
| **Database Preservation** | `data/ibvap_dev.db` (18.1 MB) | `scripts/db_count_check.py` | 30,867 historical records preserved (7,708 incidents) | **PASS** |
| **Tamper-Evident Ledger** | SHA-256 Block Integrity | `/api/v1/evidence/verify_ledger` | 7,694 blocks cryptographically validated | **PASS** |
| **Backend Endpoints** | Health, Settings, Incidents | `scripts/test_backend_endpoints.py` | HTTP 200 on `/health`, `/api/v1/health`, `/api/v1/settings` | **PASS** |
| **Ghost Box Bug Fix** | Single-overlay architecture | Code verification | Backend streams clean video; Frontend renders interactive SVG | **PASS** |
| **Identity Safety** | 4-state lifecycle | `tests/test_authorized_personnel.py` | Explicit `UNKNOWN`, `UNVERIFIED`, `AUTHORIZED`, `UNAUTHORIZED` (Detection != Identity) | **PASS** |
| **Temporal Event Validation** | State machine (45-frame baseline) | `tests/test_temporal_rules.py` | `DETECTED` → `TENTATIVE` → `STABLE` → `VERIFIED` → `ALERT_ELIGIBLE` | **PASS** |
| **Frontend Production Build** | React 18 + Vite + Tailwind | `apps/frontend/dist` | Built cleanly, statically mounted to root `/`, hotkeys & CAM-01 wired | **PASS** |

---

## 2. Deep Verification Details

### A. Environment Verification (`scripts/verify_env.py`)
```text
Python:       3.11.9 (C:\Users\dell\Desktop\p2\venv\Scripts\python.exe)
PyTorch:      2.4.1+cpu (CUDA Available: False)
OpenCV:       4.10.0
Ultralytics:  8.2.100
FastAPI:      0.115.0
Uvicorn:      0.30.6
Lap (lapx):   0.5.9
AioSQLite:    0.22.1
SQLAlchemy:   2.0.35
Pydantic:     2.9.0
ENVIRONMENT STATUS: ALL VERIFIED (CPU-FIRST)
```

### B. Database Preservation Record
- Canonical database: `data\ibvap_dev.db`
- File size: 18,157,568 bytes
- Baseline count before repair: 30,867 records
- Post-repair count: 30,867 records
- Breakdown:
  - `incidents`: 7,708 records
  - `events`: 7,708 records
  - `evidence`: 7,694 records
  - `evidence_hash_chain`: 7,694 records
  - `feedback`: 42 records
  - `anpr_observations`: 14 records
  - `cameras`: 5 records
  - `zones`: 2 records
- Historical preservation: **100% PRESERVED, 0 RECORDS LOST**.

### C. Live Backend Endpoints (`scripts/test_backend_endpoints.py`)
- `GET /health` -> `200 OK` (`{'status': 'ok', 'uptime_seconds': 1.1}`)
- `GET /api/v1/health` -> `200 OK` (`{'status': 'ok'}`)
- `GET /openapi.json` -> `200 OK` (47,222 bytes OpenAPI 3.1 specification)
- `GET /api/v1/settings` -> `200 OK`
- `GET /api/v1/incidents?limit=5` -> `200 OK` (Returned historical incidents from `ibvap_dev.db`)
- `GET /api/v1/evidence/verify_ledger` -> `200 OK` (`{'ledger_verified': True, 'corrupted_sequence_id': None, 'audit_message': 'Chain integrity verified: 7694 blocks cryptographically validated.'}`)

---

## 3. Architecture Bug Fixes Verified

1. **Ghost / Double Bounding Box Elimination:**
   - Modified `services/inference/main_inference_worker.py`: Shared memory buffer receives clean raw video frames (`clean_jpeg_bytes`). Removed redundant disk write on line 728.
   - Modified `apps/backend/routers/cameras.py`: `/api/v1/cameras/{camera_id}/stream` strictly serves `raw_file` when `annotated=False` (never falls back to annotated image on delay).
   - Result: Frontend `Dashboard.tsx` renders the single interactive SVG bounding box layer over raw video with zero raster overlap.

2. **Phase 10 Identity Safety & Lifecycle:**
   - Enforced 4 explicit states: `UNKNOWN`, `UNVERIFIED`, `AUTHORIZED`, `UNAUTHORIZED`.
   - Detection is NOT identity: newly detected persons begin as `UNKNOWN` (slate gray overlay).
   - Candidate matching authorized personnel without confirmed blinks transitions to `UNVERIFIED` (amber overlay, `AWAITING_BLINK`).
   - Verified live personnel with eye blinks transition to `AUTHORIZED` (emerald green overlay).
   - In `main_inference_worker.py`, eliminated spurious intruder alarms: proactive critical alarms now only trigger if explicitly verified as `UNAUTHORIZED` or biometric `SPOOF`, completely avoiding alarms on `UNKNOWN` / `UNVERIFIED` tracks.
   - Verified in `tests/test_authorized_personnel.py` (`test_phase10_four_identity_states`).

3. **Phase 11 Temporal Event Validation Pipeline:**
   - Added `TemporalState` state machine in `services/rules/temporal_event_engine.py`:
     `DETECTED` → `TENTATIVE` → `STABLE` → `VERIFIED` → `ALERT_ELIGIBLE`.
   - Observation gaps exceeding `candidate_expiry_seconds` transition track to `EXPIRED`.
   - Configurable baseline threshold: ~45 consecutive frames (~1.5s at 30 FPS).
   - Verified in `tests/test_temporal_rules.py` (`test_temporal_state_progression`, `test_temporal_candidate_gap_expiry`, `test_temporal_candidate_clear`).

4. **Frontend Canonical Camera Selection & Hotkeys:**
   - Restored `CAM-01 (CCTV Feed)` as primary default in `apps/frontend/src/pages/Dashboard.tsx` and 2x2 grid.
   - Updated hotkeys in `Layout.tsx`, `KeyboardShortcutsModal.tsx`, and compiled bundle `index-CpAYsxY2.js`:
     - Key `1`: `CAM-01 (CCTV Canonical)`
     - Key `2`: `WEBCAM-01 (Laptop Webcam)`
     - Key `3`: `PHONE-CAM-01 (Mobile WiFi Camera)`
     - Key `4`: `CAM-02 (Perimeter East)`

5. **Runner Scripts Resolution:**
   - `scripts/start_full_demo.ps1` and `scripts/start_sih_demo.ps1` resolve Python virtual environment (`..\venv\Scripts\python.exe`) and bundled FFmpeg (`infrastructure\ffmpeg\bin\ffmpeg.exe`).
   - `scripts/camera_reality_test.py` dynamically resolves phone camera URL from `configs/system_settings.json`.
