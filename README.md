# IBVAP — Intelligent Border Video Analytics Platform

> **SIH Problem Statement PS-26187** | MHA — Ministry of Home Affairs
> AI-powered analytics layer for existing IP-CCTV border surveillance infrastructure.

---

## What is IBVAP?

IBVAP adds intelligence to **existing** CCTV cameras without replacing hardware.

```
Existing CCTV → RTSP → Video Ingestion → AI Detection → Tracking
  → Spatial Rules → Event Correlation → Alert → Evidence → Dashboard
  → Operator Feedback → Dataset → Retraining → Canary → Production
```

Core philosophy: **Camera replace nahi karni. Existing CCTV ko intelligent banana hai.**

---

## Key Capabilities

| Capability | Status |
|---|---|
| Multi-camera RTSP ingestion | ✅ |
| Human & vehicle detection | ✅ |
| Multi-object tracking | ✅ |
| Virtual fence / zone rules | ✅ |
| ANPR (license plate OCR) | ✅ |
| Night / low-light processing | ✅ (CLAHE) |
| Suspicious activity detection | ✅ |
| Real-time alert dashboard | ✅ |
| Evidence with SHA-256 integrity | ✅ |
| Operator feedback loop | ✅ |
| Human-supervised model retraining | ✅ |
| Offline-first (no cloud dependency) | ✅ |
| Audit logging | ✅ |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        IBVAP System                             │
├─────────────────────────────────────────────────────────────────┤
│  CCTV / MediaMTX RTSP Simulator                                 │
│  CAM-01 (day) │ CAM-02 (night) │ CAM-03 (zone) │ CAM-04 (ANPR) │
├─────────────────────────────────────────────────────────────────┤
│  services/ingestion     → Bounded frame buffer, reconnect       │
│  services/preprocessing → Quality assessment, CLAHE             │
│  services/detection     → YOLOv8n (CPU) / GPU adapter          │
│  services/tracking      → ByteTrack multi-object tracker        │
│  services/rules         → Virtual fence, spatial rule engine    │
│  services/anpr          → Vehicle → Plate → EasyOCR             │
│  services/incidents     → Event correlation, evidence store     │
│  services/feedback      → Operator labeling loop                │
├─────────────────────────────────────────────────────────────────┤
│  apps/backend           → FastAPI + WebSocket + RBAC            │
│  apps/frontend          → React + TypeScript operations UI      │
├─────────────────────────────────────────────────────────────────┤
│  ml/                    → DVC datasets, MLflow, model registry  │
│  infrastructure/        → MediaMTX, Docker, optional NVIDIA     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
IBVAP/
├── apps/
│   ├── backend/          # FastAPI backend
│   └── frontend/         # React + TypeScript dashboard
├── services/
│   ├── ingestion/        # RTSP camera source + frame buffer
│   ├── preprocessing/    # Video quality + CLAHE
│   ├── detection/        # DetectionEngine interface + adapters
│   ├── tracking/         # Multi-object tracker
│   ├── rules/            # Spatial + temporal rule engine
│   ├── anpr/             # Vehicle → Plate → OCR pipeline
│   ├── incidents/        # Event correlation + evidence
│   └── feedback/         # Operator feedback service
├── ml/
│   ├── datasets/         # Dataset registry (no raw data in Git)
│   ├── labeling/         # CVAT/Label Studio export tools
│   ├── training/         # Retrain pipeline + active learning
│   ├── evaluation/       # MLflow tracking
│   └── models/           # Model registry (metadata only)
├── infrastructure/
│   ├── mediamtx/         # Local RTSP camera simulator
│   ├── docker/           # Docker Compose configs
│   └── nvidia/           # Optional TensorRT adapter
├── configs/              # Camera, zone, system configs
├── data/                 # LOCAL ONLY — never committed to Git
│   ├── raw/              # Source video clips
│   ├── processed/        # Preprocessed frames
│   ├── labeled/          # Annotated datasets
│   ├── validation/       # Fixed validation set (never modified)
│   └── incidents/        # Evidence files
├── tests/                # Unit + integration tests
├── docs/                 # All documentation
└── scripts/              # Dev utilities
```

---

## 🚀 Operational Command Reference

### Master Commands
| Operation | Command / Script | Description |
|-----------|------------------|-------------|
| **START CCTV DEMO** | `.\START_CCTV_DEMO.bat` *(or `.\scripts\ibvap.ps1 demo`)* | Starts MediaMTX, FFmpeg CAM-01 stream, FastAPI backend, YOLOv8 CPU inference, and Dashboard |
| **START WEBCAM DEMO** | `.\START_WEBCAM_DEMO.bat` *(or `.\scripts\ibvap.ps1 webcam`)* | Starts dedicated laptop webcam (`webcam:0`), FastAPI backend, YOLOv8 CPU inference, and Dashboard |
| **STOP ALL SERVICES** | `.\STOP_ALL_SERVICES.bat` *(or `.\scripts\ibvap.ps1 stop`)* | Cleanly terminates all MediaMTX, FFmpeg, Python worker, FastAPI, and Node processes |
| **SYSTEM STATUS** | `powershell -File .\scripts\ibvap.ps1 status` | Shows real-time process & port status for all 5 subsystems |
| **RUN VERIFIED TESTS** | `& C:\Users\dell\Desktop\p2\venv\Scripts\pytest.exe tests/` | Runs automated test suite on CPU |
| **VERIFY ENDPOINTS** | `& C:\Users\dell\Desktop\p2\venv\Scripts\python.exe scripts/test_backend_endpoints.py` | Validates FastAPI endpoints, DB connection, and SHA-256 ledger |

### Runtime Device Selection
```powershell
# CPU-First Mode (Default on this Dell Laptop)
$env:IBVAP_DEVICE = "cpu"

# Optional GPU Acceleration Mode (For later NVIDIA RTX 3050 testing)
$env:IBVAP_DEVICE = "cuda"
```

### Accessing the Dashboard
- **Production Single-Port UI:** `http://localhost:8000/` (served natively by FastAPI from `apps/frontend/dist`)
- **Development Vite UI:** `http://localhost:5173/`
- **FastAPI OpenAPI Docs:** `http://localhost:8000/docs`
- **System Health:** `http://localhost:8000/health`
- **Live Stream (Raw):** `http://localhost:8000/api/v1/cameras/CAM-01/stream`

---

## 👥 Team Work Allocation & Status

For detailed role assignments and authoritative system disclosures:
- **[STATUS.md](STATUS.md)** — Empirical status matrix & anti-fabrication disclosure
- **[TEAM_TASKS.md](TEAM_TASKS.md)** — 5-member work allocation & roadmap
- **[SETUP.md](SETUP.md)** — Step-by-step teammate setup instructions
- **[TEST_REPORT.md](TEST_REPORT.md)** — Automated test verification results

---

## Important Disclaimers

> **⚠️ SIH Prototype Notice**
> This is a research and demonstration prototype built for Smart India Hackathon.
> It is **not** a certified operational deployment.
> Actual border deployment requires: security assessment, hardware validation, model validation,
> privacy/data governance, license clearance, network/security review, and operational acceptance testing.

> **🔒 No Cloud Dependency**
> Core inference, database, dashboard, and evidence storage operate fully offline.
> No data leaves the edge device during normal operation.

> **📜 License**
> See [LICENSE](LICENSE) and [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

---

## Documentation

### Grand Finale AI Orchestration Suite
| Document | Description |
|---|---|
| [MODEL_REGISTRY.md](MODEL_REGISTRY.md) | Authoritative registry across 13 Expert Pools & Edge Stacks |
| [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) | Level 0 to Level 6 Cascaded Autonomous Architecture & Event Bus |
| [MODEL_ROUTER.md](MODEL_ROUTER.md) | Dynamic Route Scoring formula & model agreement/disagreement fusion |
| [MODEL_BENCHMARK.md](MODEL_BENCHMARK.md) | Empirical benchmarks across Dell Core i3, RTX 3050, Orin, and A100 |
| [HARDWARE_MATRIX.md](HARDWARE_MATRIX.md) | 5-Tier hardware allocation matrix from Edge CPU to Sovereign Cloud |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Complete deployment guide for CPU, RTX 3050, and offline setups |
| [OFFLINE_MODE.md](OFFLINE_MODE.md) | Air-gapped offline operation protocol & local asset inventory |
| [EVIDENCE_INTEGRITY.md](EVIDENCE_INTEGRITY.md) | SHA-256 tamper-evident hash-chain ledger (7,694 blocks intact) |
| [GRAND_FINALE_DEMO.md](GRAND_FINALE_DEMO.md) | Step-by-step evaluator script for CCTV, webcam, hotkeys, and audit |
| [MODEL_REGISTRY_TEST.md](MODEL_REGISTRY_TEST.md) | Verification report for Model Registry & zero-crash fallbacks |
| [AI_ROUTING_TEST.md](AI_ROUTING_TEST.md) | Verification report for Dynamic Routing, Fusion, and Cascading |
| [GRAND_FINALE_DEMO_TEST.md](GRAND_FINALE_DEMO_TEST.md) | Full-stack verification matrix and database record audit |

### System & Engineering References
| Document | Description |
|---|---|
| [SETUP.md](SETUP.md) | Teammate setup & quick start guide |
| [STATUS.md](STATUS.md) | Honest status matrix & disclosures |
| [TEAM_TASKS.md](TEAM_TASKS.md) | 5-member roadmap & responsibilities |
| [TEST_REPORT.md](TEST_REPORT.md) | Empirical automated test report |
| [P2_CLEANUP_LOG.md](P2_CLEANUP_LOG.md) | Safe backup & file cleanup audit log |
| [FINAL_LOCAL_STATUS.md](FINAL_LOCAL_STATUS.md) | Phases 1–19 resolution summary & matrix |
| [SECURITY.md](SECURITY.md) | Security policy & threat model |
| [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) | All dependency licenses |

---

*Built for SIH 2026 | PS-26187 | Ministry of Home Affairs*

