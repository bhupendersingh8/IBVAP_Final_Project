# IBVAP — Pipeline Gap Analysis & Target Architecture
**Project:** Intelligent Border Video Analytics Platform (IBVAP)  
**SIH Problem Statement:** PS-26187  
**Analysis Date:** September 2026  
**Reference Specification:** Master Prompt Next-Generation CV Upgrade  

---

## 1. Fast Path vs Heavy Path Architectural Gap

### Current State
* The live inference loop (`services/inference/main_inference_worker.py`) executes YOLOv8 detection on each ingested frame (with adaptive motion skipping), updates ByteTrack, checks polygon fences, and invokes specialist modules (threat detection, facial recognition) when certain criteria are met.
* Confidence scoring uses `services/orchestrator/confidence_fusion.py` to prevent naive score averaging.

### Target State
* Strict architectural decoupling between **FAST PATH** and **HEAVY PATH**:
  ```
  FAST PATH (Every Frame / Budget < 25ms):
  RTSP Capture → Quality & Health → Motion/Change Gate → Primary Detector → Multi-Object Tracker → Spatial/Temporal Rules
  
  HEAVY PATH (Event-Triggered On Demand / Asynchronous):
  Candidate Event → Specialist AI (Pose / ANPR / Depth / Re-ID / Seg) → Confidence Fusion → Integrity Chain → Alert & UI
  ```
* **Required Action**: Formalize the `SpecialistPipelineManager` to manage asynchronous handoffs to specialist workers without blocking the fast-path frame queue.

---

## 2. Ingestion & Bounded Queues Gap Analysis

| Requirement | Current Status | Planned Implementation | Priority |
| :--- | :--- | :--- | :---: |
| **RTSP & MediaMTX support** | Fully operational (`rtsp://127.0.0.1:8554/CAM-01`) | Preserve existing MediaMTX architecture | MAINTAIN |
| **Webcam fallback** | Supported via DirectShow (`cv2.VideoCapture(0)`) | Preserve local camera fallback | MAINTAIN |
| **Bounded Queues & Drop Stale Frames** | Internal OpenCV buffer dropping | Add explicit ring buffer drop counter with latency threshold (> 150ms drops oldest frame) | HIGH |
| **Expose Telemetry Metrics** | FPS, CPU, VRAM, and Latency exposed | Expose capture latency, inference latency, queue depth, dropped frames, and reconnect time | HIGH |

---

## 3. Condition-Aware Perception Gap Analysis

| Requirement | Current Status | Planned Implementation | Priority |
| :--- | :--- | :--- | :---: |
| **Condition Categorization** | CLAHE + Night booster active | Create `ConditionAnalyzer` to detect CLEAR, LOW_LIGHT, NIGHT, FOG_HAZE, RAIN/SNOW, BLUR, CAMERA_SHAKE, COMPRESSION_NOISE | HIGH |
| **Adaptive Enhancement** | Low-light gamma stretch | Create `EnhancementManager` to apply CLAHE/stabilization only when beneficial | HIGH |
| **Transformation Telemetry** | Logged via structlog | Return structured object per frame: `input_quality`, `output_quality`, `latency_ms`, and `decision_reason` | HIGH |
| **Anti-Hallucination on Blur** | Basic Laplacian threshold | Mark quality as DEGRADED instead of attempting speculative detection on low-clarity frames | CRITICAL |

---

## 4. Primary Detection & Backend Abstraction Gap Analysis

| Requirement | Current Status | Planned Implementation | Priority |
| :--- | :--- | :--- | :---: |
| **Detector Abstraction** | `DetectionEngine` ABC | Implement `DetectorBackend` with uniform output: `bbox`, `class`, `confidence`, `timestamp`, `preprocess_latency`, `inference_latency`, `postprocess_latency`, `total_latency` | CRITICAL |
| **YOLOv8/YOLO26 Backend** | `YOLOAdapter` (Ultra-optimized CPU baseline) | Encapsulate into `YOLOv8Backend` | HIGH |
| **RF-DETR-L Integration** | Registered in model registry | Implement `RFDETRBackend` wrapper with licensed PyTorch checkpoint and graceful fallback | HIGH |
| **Dynamic Configuration** | Environment & JSON config | Support `DETECTOR_BACKEND=yolov8` and `DETECTOR_BACKEND=rf_detr` via environment variables | HIGH |
| **Empirical Benchmarking** | Synthetic FPS benchmarks present | Run side-by-side benchmark on recorded border video measuring precision, recall, small-object recall, FPS, p50, p95, CPU, RAM | HIGH |

---

## 5. Small & Distant Object Detection (SAHI / Tiling) Gap Analysis

| Requirement | Current Status | Planned Implementation | Priority |
| :--- | :--- | :--- | :---: |
| **Adaptive Tiling** | Basic fixed crop ROI | Implement `AdaptiveTiledDetector` triggered when object bbox area < 0.005 of frame or border ROI requires high resolution | HIGH |
| **Box Merging** | Standard NMS | Implement NMS-based tiled box fusion with coordinate transformation | HIGH |
| **Resource Guard** | None | Automatically skip tiling if frame processing time exceeds 100ms budget | HIGH |

---

## 6. Multi-Object Tracking & Re-ID Memory Gap Analysis

| Requirement | Current Status | Planned Implementation | Priority |
| :--- | :--- | :--- | :---: |
| **ByteTrack Core** | Two-stage association operational | Preserve ByteTrack implementation | MAINTAIN |
| **7-State Lifecycle** | Partial state tracking | Enforce explicit track states: `DETECTED` → `TENTATIVE` → `STABLE` → `VERIFIED` → `ALERT_ELIGIBLE` → `EXPIRED` → `CLEARED` | HIGH |
| **OSNet Re-ID Continuity** | `OSNet-x0.25` gallery implemented | Re-ID used strictly for track continuity across occlusion; low similarity never triggers false identity matching | HIGH |
| **Benchmark Metrics** | Unit test validations | Track ID switches, fragmentation, persistence, and tracking latency | HIGH |

---

## 7. ANPR & License Plate Recognition Gap Analysis

| Requirement | Current Status | Planned Implementation | Priority |
| :--- | :--- | :--- | :---: |
| **Multi-frame Consensus** | `TrackANPRState` active | Preserve multi-frame voting | MAINTAIN |
| **PaddleOCR / License-Cleared OCR** | `EasyOCREngine` implemented | Add `PaddleOCREngine` and mock fallback with Apache-2.0 compliance | HIGH |
| **Output Structure** | Plate text & confidence | Expose `plate_text`, `ocr_confidence`, `observation_count`, `best_frame`, `temporal_consistency` | HIGH |
| **Anti-Hallucination Fallback** | Normalized text | Return `UNKNOWN` when confidence < 0.50; never invent characters | CRITICAL |

---

## 8. Depth & Spatial Geometry Gap Analysis

| Requirement | Current Status | Planned Implementation | Priority |
| :--- | :--- | :--- | :---: |
| **Monocular Depth** | Not active in default loop | Implement `DepthAnythingBackend` (Depth Anything v2/v3 candidate) as optional event module | HIGH |
| **Relative Depth Guarantee** | N/A | Strictly use relative depth; never claim centimeter accuracy without physical camera calibration | CRITICAL |
| **SpatialReasoningEngine** | Rules geometry in `services/rules/` | Formalize `SpatialReasoningEngine` supporting virtual fences, entry/exit vectors, and camera geometry | HIGH |

---

## 9. Temporal Intelligence & Confidence Fusion Gap Analysis

| Requirement | Current Status | Planned Implementation | Priority |
| :--- | :--- | :--- | :---: |
| **Temporal Engine** | `TemporalEventEngine` operational | Enforce: Detected → Tracked → Persistent → Zone Relation → Trajectory → Temporal Correlation → Candidate → Verification → Incident | MAINTAIN / POLISH |
| **Confidence Fusion** | `ConfidenceFusionEngine` active | Calibrated fusion: detection + tracking + pose + OCR + depth + zone hazard + quality. Decision states: `NORMAL`, `OBSERVE`, `REVIEW`, `CONFIRMED_EVENT` | HIGH |
| **Specialist Pipeline Manager** | Partially in `model_orchestrator.py` | Create dedicated `SpecialistPipelineManager` tracking `started`, `completed`, `failed`, `latency`, `confidence`, `reason` | HIGH |

---

## 10. Evidence & Section 65B Hash-Chain Integrity Gap Analysis

| Requirement | Current Status | Planned Implementation | Priority |
| :--- | :--- | :--- | :---: |
| **Local SHA-256 Ledger** | `HashChainLedger` operational | Preserve unbroken SHA-256 block chain linking | MAINTAIN |
| **POST /evidence/verify** | `GET /evidence/verify_ledger` active | Add `POST /api/v1/evidence/verify` validating individual incident evidence files against database hash | HIGH |
| **Tamper-Evident Terminology** | Verified in docstrings | Consistently enforce "TAMPER-EVIDENT" and "INTEGRITY-VERIFIABLE" terminology across all UI and docs | HIGH |

---

## 11. Frontend VMS Design Gap Analysis

| Requirement | Current Status | Planned Implementation | Priority |
| :--- | :--- | :--- | :---: |
| **Aesthetic** | Dark cyber-neon theme | Refine to professional VMS layout with clean neutral background (`#0f172a`), crisp typography, blue accents, red/orange alert states | HIGH |
| **Left Column** | Camera dropdown tabs | Left rail: Camera list, live camera health indicators, zone configurations | HIGH |
| **Center Column** | Live video + SVG reticles | Live video player, tracked bounding boxes, restricted polygon overlays, target inspector | HIGH |
| **Right Column** | Incident cards & ANPR ticker | Incident audit ledger, severity badges, Section 65B hash cards, ANPR details | HIGH |
| **Bottom Ribbon** | Minimal footer | Real-time multi-stage pipeline HUD: Camera → Ingestion → Quality → Detection → Tracking → Spatial → Temporal → Specialist AI → Evidence → Dashboard | HIGH |

---

## 12. Execution Roadmap & Summary

All required components build directly upon the existing, verified modular layers. No legacy test, database schema, or backend API will be broken. Each phase will be implemented incrementally with immediate regression verification.
