# IBVAP System Architecture

## Overview

IBVAP (Intelligent Border Video Analytics Platform) is a real-time video analytics system for border surveillance. It ingests RTSP camera streams, runs AI-based detection and tracking, enforces virtual fence rules, generates tamper-evident evidence, and delivers real-time alerts to an operator dashboard.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CAMERA LAYER                             │
│  IP CCTV / Phone IP-Cam / Local Video / RTSP                   │
│  CAM-01 (RTSP:8554/CAM-01)  │  PHONE-CAM-01 (HTTP:8080/video) │
└────────────────────┬────────────────────────────────────────────┘
                     │
                 MediaMTX (RTSP gateway :8554)
                 FFmpeg (video → RTSP relay)
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                     INGESTION LAYER                             │
│  services/ingestion/rtsp_source.py  ← RTSPSource               │
│  services/ingestion/camera_health.py ← CameraHealthMonitor     │
│  Frame buffer (bounded, latest-frame strategy)                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                   PERCEPTION LAYER                              │
│  services/detection/yolo_adapter.py ← YOLOAdapter (YOLOv8n)   │
│  services/detection/detection_engine.py ← DetectionEngine ABC  │
│  services/anpr/anpr_pipeline.py ← ANPRPipeline                │
│  services/preprocessing/clahe_enhancer.py ← Night enhancement │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                    TRACKING LAYER                               │
│  services/tracking/bytetrack_adapter.py ← FallbackIoUTracker  │
│  services/tracking/track_analytics.py  ← Velocity/Direction   │
│  Persistent track IDs, trajectory, dwell time                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                 SPATIO-TEMPORAL AI LAYER                        │
│  services/rules/rule_engine.py ← RuleEngine                   │
│  services/rules/temporal_event_engine.py ← TemporalEventEngine │
│  services/rules/activity_engine.py ← ActivityEngine           │
│  Virtual fence, zone intrusion, loitering, night movement     │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                   EVENT & EVIDENCE LAYER                        │
│  services/incidents/event_correlator.py ← EventCorrelator     │
│  services/evidence/hash_chain.py ← HashChainLedger            │
│  Evidence JPEGs + SHA-256 + hash chain + audit trail          │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│                    API LAYER (FastAPI)                          │
│  apps/backend/main.py ← FastAPI app                           │
│  apps/backend/routers/cameras.py    ← Camera CRUD             │
│  apps/backend/routers/events.py     ← Incidents/Evidence      │
│  apps/backend/routers/anpr.py       ← ANPR observations       │
│  apps/backend/routers/health.py     ← /health/live|ready      │
│  WebSocket /ws/alerts ← Real-time alert push                  │
│  SQLite (data/ibvap_dev.db) via SQLAlchemy async              │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────┐
│               OPERATIONS CENTER (React)                         │
│  apps/frontend/src/pages/Dashboard.tsx ← Live video + SVG     │
│  apps/frontend/src/pages/Incidents.tsx ← Incident lifecycle   │
│  apps/frontend/src/pages/Cameras.tsx   ← Camera management    │
│  apps/frontend/src/pages/Zones.tsx     ← Zone management      │
│  Vite dev server :5173 / dist build for production            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Inventory

| Component | File | Status |
|-----------|------|--------|
| RTSP Ingestion | `services/ingestion/rtsp_source.py` | PASS |
| Camera Health Monitor | `services/ingestion/camera_health.py` | PASS |
| Detection Engine (ABC) | `services/detection/detection_engine.py` | PASS |
| YOLOv8 Adapter | `services/detection/yolo_adapter.py` | PASS |
| ONNX Adapter | `services/detection/runtime_adapters.py` | PLANNED stub |
| OpenVINO Adapter | `services/detection/runtime_adapters.py` | PLANNED stub |
| TensorRT Adapter | `services/detection/runtime_adapters.py` | PLANNED stub |
| IoU Tracker | `services/tracking/bytetrack_adapter.py` | PASS |
| Track Analytics | `services/tracking/track_analytics.py` | PASS |
| Rule Engine | `services/rules/rule_engine.py` | PASS |
| Temporal Event Engine | `services/rules/temporal_event_engine.py` | PASS |
| ANPR Pipeline | `services/anpr/anpr_pipeline.py` | PARTIAL |
| CLAHE Enhancer | `services/preprocessing/clahe_enhancer.py` | PARTIAL |
| Event Correlator | `services/incidents/event_correlator.py` | PASS |
| Hash Chain Ledger | `services/evidence/hash_chain.py` | PASS |
| FastAPI Backend | `apps/backend/main.py` | PASS |
| Incident Router | `apps/backend/routers/events.py` | PASS |
| Health Router | `apps/backend/routers/health.py` | PASS |
| JWT Auth (stub) | `apps/backend/auth/jwt_auth.py` | PLANNED |
| RBAC | `apps/backend/auth/rbac.py` | PARTIAL |
| React Dashboard | `apps/frontend/src/` | PASS |
| MediaMTX | `infrastructure/mediamtx/` | PASS |
| SQLite Database | `data/ibvap_dev.db` | PASS |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.14.4 |
| ML Framework | Ultralytics YOLOv8n (AGPL-3.0) |
| API Framework | FastAPI + Uvicorn |
| Database | SQLite + SQLAlchemy (async) |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Stream Gateway | MediaMTX (RTSP/WebRTC) |
| Video I/O | FFmpeg + OpenCV |
| Logging | structlog |
| Testing | pytest + anyio |
| OS | Windows 11 (dev); Linux recommended for production |

---

## Data Flow

```
Camera Frame
  → RTSPSource.read_frame()
  → YOLOAdapter.detect(frame)
  → FallbackIoUTracker.update(detections)
  → RuleEngine.evaluate(tracks, zones)
  → TemporalEventEngine.process_intrusion(...)
  → EventCorrelator.correlate(event)
  → HashChainLedger.add_block(evidence)
  → SQLite commit (Incident + Evidence + HashChainBlock)
  → POST /api/v1/internal/broadcast_alert → WebSocket → Dashboard
```

---

## Deployment Topology (Current)

Single-node Windows development setup:
- All services run on `localhost`
- MediaMTX: `:8554` (RTSP), `:8889` (WebRTC)
- FastAPI Backend: `:8000`
- React Dev Server: `:5173`
- Inference Worker: subprocess or direct Python
- Database: file-based SQLite at `data/ibvap_dev.db`

See `docs/DEPLOYMENT_GUIDE.md` for production deployment path.
