# IBVAP — Comprehensive Architecture Audit
**Project:** Intelligent Border Video Analytics Platform (IBVAP)  
**SIH Problem Statement:** PS-26187  
**Baseline Commit:** `f524f44`  
**Test Suite Status:** 188/188 tests passing (100% green)  
**Date:** September 2026  

---

## 1. Executive Summary & Purpose

This audit provides an exhaustive inspection of the existing IBVAP repository prior to the Next-Generation Computer Vision Upgrade. IBVAP is an offline-capable, edge-optimized surveillance analytics platform designed for difficult border environments. The system ingests CCTV/RTSP streams, executes real-time AI perception, tracks cross-boundary movements, enforces spatial-temporal perimeter rules, and commits cryptographic tamper-evident Section 65B hash-chain records.

---

## 2. Subsystem-by-Subsystem Audit

### 2.1 Video Ingestion & Streaming Infrastructure (`services/ingestion/`, `infrastructure/mediamtx/`)
* **Core Modules**:
  * `services/ingestion/rtsp_source.py`: Threaded OpenCV/FFmpeg RTSP stream capture with automatic exponential-backoff reconnect and configurable frame timeouts.
  * `services/ingestion/frame_buffer.py`: Ring buffer storing `CameraFrame` with timestamps and frame sequence numbers.
  * `services/ingestion/camera_health.py`: Heartbeat and jitter monitor tracking FPS, frame drop rates, and connection states.
  * `infrastructure/mediamtx/`: Standalone MediaMTX RTSP/WebRTC server (`127.0.0.1:8554` RTSP, `127.0.0.1:8889` WebRTC).
* **Current Status**: Production-tested and highly stable. Zero-copy shared memory Seqlock buffer (`services/ingestion/shared_frame_buffer.py`) enables IPC without socket overhead.
* **Gaps vs Target**: Bounded queues need explicit drop-stale-frame heuristics when inference lags; metrics for capture latency vs inference latency need explicit external exposition.

### 2.2 Preprocessing & Condition-Aware Enhancement (`services/preprocessing/`)
* **Core Modules**:
  * `services/preprocessing/clahe_enhancer.py`: Contrast Limited Adaptive Histogram Equalization.
  * `services/preprocessing/night_enhancer.py`: Adaptive gamma stretch and low-light booster for nighttime feeds.
  * `services/preprocessing/quality_assessor.py`: Laplacian variance blur detection and luminance calculation.
  * `services/preprocessing/motion_detector.py`: Background subtraction change gate to skip static background frames.
* **Current Status**: Operational.
* **Gaps vs Target**: Missing a unified `ConditionAnalyzer` and `EnhancementManager` orchestrator to systematically categorize environmental states (CLEAR, LOW_LIGHT, NIGHT, FOG_HAZE, RAIN/SNOW, BLUR, CAMERA_SHAKE, COMPRESSION_NOISE) and report input quality, output quality, latency, and decision reason per transformation.

### 2.3 Detection Layer & Hardware Adapters (`services/detection/`, `ml/models/`)
* **Core Modules**:
  * `services/detection/detection_engine.py`: Abstract Base Class (`DetectionEngine`) with `load_model()`, `detect()`, `warmup()`.
  * `services/detection/yolo_adapter.py`: Production YOLOv8/YOLO26 baseline with CPU-friendly thread pooling.
  * `services/detection/model_orchestrator.py`: Multi-model coordinator with canonical taxonomy (`COCO_BROAD_TAXONOMY`) and agreement/disagreement scoring.
  * `services/detection/runtime_adapters.py`: TensorRT, ONNX Runtime, and OpenVINO runtime wrappers.
  * `ml/models/rtdetr_seg.py`: Native PyTorch implementation of RT-DETR-R18-Seg with hybrid encoder and ProtoNet mask head.
* **Current Status**: 100% verified on CPU fallback (Intel i3-1115G4), prepared for RTX 3050 (4GB/6GB).
* **Gaps vs Target**: Need formal `DetectorBackend` abstraction exposing uniform schema (`bbox`, `class`, `confidence`, `timestamp`, `preprocess_latency`, `inference_latency`, `postprocess_latency`, `total_latency`) with dynamic config (`DETECTOR_BACKEND=rf_detr` vs `DETECTOR_BACKEND=yolov8`). SAHI-style adaptive small-object tiled inference is currently experimental.

### 2.4 Multi-Object Tracking & Track Memory (`services/tracking/`)
* **Core Modules**:
  * `services/tracking/tracker.py`: Tracker interface.
  * `services/tracking/bytetrack_adapter.py`: ByteTrack two-stage association algorithm with low-confidence association and Kalman filtering.
  * `services/tracking/track_analytics.py`: Real-time velocity, directional vector calculation, and dwell-time accumulator.
  * `services/tracking/remembrance_store.py`: Re-identification embedding store and long-term track memory.
  * `ml/models/reid_osnet.py`: Lightweight OSNet-x0.25 (0.22M params) feature extractor.
* **Current Status**: Stable and verified across 188 unit/integration tests.
* **Gaps vs Target**: Explicit state machine transitions (`DETECTED`, `TENTATIVE`, `STABLE`, `VERIFIED`, `ALERT_ELIGIBLE`, `EXPIRED`, `CLEARED`) need to be exposed as first-class track metadata across all consumers.

### 2.5 Pose Estimation & Biometrics (`services/auth_personnel/`, `services/detection/face_detector.py`)
* **Core Modules**:
  * `services/auth_personnel/blink_detector.py`: EAR (Eye Aspect Ratio) liveness detection.
  * `services/auth_personnel/personnel_manager.py`: Authorized whitelist gallery and cosine distance matching.
  * `yolov8n-pose.pt`: Fallback keypoint detector for posture analysis.
* **Current Status**: Functional on demand.
* **Gaps vs Target**: License audit on RTMPose / OpenPose alternatives; ensure pose is never run on every person per frame, but strictly event-triggered.

### 2.6 Automatic Number Plate Recognition (ANPR) (`services/anpr/`)
* **Core Modules**:
  * `services/anpr/anpr_pipeline.py`: Vehicle track filtering, plate ROI cropping, and consensus voting.
  * `services/anpr/plate_detector.py`: Contour and edge-based candidate plate localization.
  * `services/anpr/ocr_adapter.py`: `OCREngine` interface with `EasyOCREngine` and regex-based plate normalization (`normalize_plate_text`).
* **Current Status**: Operational with multi-frame voting.
* **Gaps vs Target**: Need PaddleOCR backend integration with Apache-2.0 license clearance; strict temporal aggregation with observation counts and "UNKNOWN" fallback for sub-threshold confidence.

### 2.7 Spatial & Temporal Intelligence (`services/rules/`)
* **Core Modules**:
  * `services/rules/rule_engine.py`: Polygon intersection and Point-in-Polygon geometry calculations (via Shapely).
  * `services/rules/geometry.py`: Line crossing, directional heading, and coordinate normalization.
  * `services/rules/temporal_event_engine.py`: Temporal state machines for Zone Intrusion, Loitering, Direction Violation, Night Movement, and Repeated Entry.
* **Current Status**: Verified across 12 border surveillance operational scenarios.
* **Gaps vs Target**: Create dedicated `SpatialReasoningEngine` encapsulating relative depth cues and camera geometry without assuming uncalibrated absolute metrics.

### 2.8 Specialist Routing & Confidence Fusion (`services/orchestrator/`)
* **Core Modules**:
  * `services/orchestrator/orchestrator.py`: Multi-camera pipeline coordinator.
  * `services/orchestrator/confidence_fusion.py`: Calibrated multi-modal confidence fusion combining detection, tracking, zone hazard, and quality metrics without arithmetic score averaging.
  * `services/orchestrator/cascade_levels.py`: Computational tiers (L0 Motion -> L1 Detector -> L2 Tracker -> L3 Specialist).
* **Current Status**: Implemented and active.
* **Gaps vs Target**: Standardize `SpecialistPipelineManager` to track `started`, `completed`, `failed`, `latency`, `confidence`, and `reason` across all triggered specialist sub-modules.

### 2.9 Evidence Management & Hash-Chain Ledger (`services/evidence/`, `apps/backend/routers/events.py`)
* **Core Modules**:
  * `services/evidence/hash_chain.py`: Append-only cryptographic Section 65B hash chain ledger linking `RecordHash(n) = SHA256(RecordHash(n-1) + incident_id + evidence_sha256 + timestamp + payload)`.
  * `apps/backend/routers/events.py`: Incident query, evidence retrieval, acknowledgement, and `GET /evidence/verify_ledger`.
* **Current Status**: Immutable verification active and fully tested.
* **Gaps vs Target**: Implement dedicated `POST /evidence/verify` endpoint with standalone tampering detection test suite; clarify documentation terminology as "TAMPER-EVIDENT" and "INTEGRITY-VERIFIABLE" (strictly avoiding "tamper-proof").

### 2.10 Backend API & WebSockets (`apps/backend/`)
* **Core Modules**:
  * `apps/backend/main.py`: FastAPI application root with CORS, static SPA mounting, and lifecycle events.
  * `apps/backend/routers/`: Modular route handlers (`cameras.py`, `events.py`, `anpr.py`, `health.py`, `auth_router.py`, `settings_router.py`, `copilot_router.py`).
  * `apps/backend/auth/`: JWT token signing, verification, and Role-Based Access Control (`ADMIN`, `OPERATOR`, `VIEWER`).
  * `apps/backend/database/`: SQLAlchemy async SQLite database connection (`data/ibvap_dev.db`).
* **Current Status**: Fast, clean, and reliable.
* **Gaps vs Target**: Explicit track update WebSocket stream without bulky base64 frame payloads.

### 2.11 Operations Dashboard Frontend (`apps/frontend/`)
* **Core Modules**:
  * `src/components/layout/Layout.tsx`: Tactical command header with live system clock, health status, and navigation.
  * `src/pages/Dashboard.tsx`: Primary surveillance command dashboard with live video, SVG HUD overlays, tactical alert feed, ANPR ribbon, and camera switcher.
  * `src/pages/Incidents.tsx`: Section 65B forensic ledger with search, filtering, and 1-click evidence inspection.
  * `src/pages/Cameras.tsx`: Camera node topology and stream management.
  * `src/pages/Settings.tsx`: Sensitivity tuning, loitering thresholds, and hardware diagnostics.
* **Current Status**: Clean, responsive, compiled production build (`dist/`) serving on `:5173` and `:8000`.
* **Gaps vs Target**: Refine layout into a clean VMS-style UI with neutral background, blue accent, clear typography, and a dedicated bottom pipeline HUD displaying real-time FPS, latency, and queue depth.

### 2.12 Testing & Quality Assurance (`tests/`)
* **Core Modules**: 188 automated pytest suites covering detection, tracking, rules, hash-chain, preprocessing, ANPR, auth, and real-world border scenarios.
* **Current Status**: 100% passing on CPU.
* **Gaps vs Target**: Add unit tests for `DetectorBackend` hot-swapping, depth failure resilience, OCR multi-frame aggregation, and explicit evidence tampering verification.

---

## 3. Architecture Audit Conclusion

The current IBVAP codebase contains strong, decoupled foundational primitives. It does not require any destructive rewrites. The upgrade path consists of:
1. Elevating existing components into formal modular interfaces (`DetectorBackend`, `ConditionAnalyzer`, `SpecialistPipelineManager`).
2. Integrating license-cleared optional models (RF-DETR, PaddleOCR, Depth Anything) behind graceful fallbacks.
3. Aligning the frontend HUD to the authoritative VMS design specifications.
