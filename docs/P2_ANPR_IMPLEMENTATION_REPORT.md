# IBVAP Milestone P2: Vehicle Analytics + ANPR Implementation Report

**Author**: Antigravity AI Engineering Agent  
**Environment**: Windows 11 (AMD64), Intel i3 CPU, 12GB RAM, CPU-only Execution  
**Project**: Intelligent Border Video Analytics Platform (IBVAP)  
**Date**: September 5, 2026  
**Status**: COMPLETE / VERIFIED  

---

## 1. Executive Summary & Core Guarantees

Milestone P2 delivers production-ready **Vehicle Analytics and Automated Number Plate Recognition (ANPR)** capabilities integrated cleanly into the real-time IBVAP architecture without regressing any P0/P1 capabilities.

All mandatory safety, architectural, and operational constraints specified in the instructions have been strictly adhered to:
1. **P0/P1 Regression Preservation**: Real video ingestion from `data/raw/test_video.mp4` via MediaMTX RTSP (`rtsp://127.0.0.1:8554/CAM-01`), real YOLOv8n object detection, FallbackIoUTracker, authoritative polygon zones, real zone entry breach detection, SQLite incident persistence, evidence hashing, WebSocket telemetry delivery, and React live streaming all maintain 100% operational integrity.
2. **Vehicle Subclass Preservation**: Standardized `class_name="vehicle"` is maintained throughout all detections and tracks, with specific vehicle subclasses (`car`, `motorcycle`, `bus`, `truck`) preserved and propagated as `subclass` and `vehicle_class` attributes.
3. **Pluggable & Extensible Interfaces**: Modular `PlateDetector` and `OCREngine` abstract base classes permit seamless drop-in replacements of detectors (e.g., custom YOLO plate detector) and OCR engines (e.g., PaddleOCR, TensorRT-OCR).
4. **Contour Baseline Reality**: `ContourPlateDetector` is documented as a baseline heuristic suitable for clear, high-contrast, front/rear-facing plates; it does not overpromise production plate localization across arbitrary angles or poor lighting.
5. **Anti-Hallucination & Quality Controls**: Blurry or low-resolution plate crops are systematically marked `UNREADABLE` via Laplacian variance checks; no plate text is ever guessed or hallucinated.
6. **Multi-Frame Track Consensus**: A single OCR reading is **never** marked `STABLE_VERIFIED`. A minimum of 2 matching, consistent readings on the same persistent vehicle track are required before state transition to `STABLE_VERIFIED`. Conflicting readings on the same track are flagged as `LOW_CONFIDENCE`.
7. **Decoupled Security Logic**: Vehicle detection or ANPR plate reading **never** triggers an intrusion alert. Alerts remain strictly governed by spatial rule evaluations (e.g., entering `RESTRICTED_ZONE_01`).
8. **Automated Verification in Microsoft Edge**: The entire verification pipeline was executed and validated using Playwright driving native Microsoft Edge (`channel='msedge'`).

---

## 2. Architecture & Component Design

```
+----------------------------------------------------------------------------------------------------+
|                                    IBVAP P2 PIPELINE ARCHITECTURE                                  |
+----------------------------------------------------------------------------------------------------+
                                      |
                      [Local Test Video: test_video.mp4]
                                      |
                                  (FFmpeg)
                                      v
                 [MediaMTX RTSP Server: rtsp://127.0.0.1:8554/CAM-01]
                                      |
                         (RTSPSource Frame Ingestion)
                                      v
           [DetectionEngine: YOLOv8n (CPU-Optimized, confidence >= 0.40)]
             - person  -> class_name='person'
             - car/truck/bus/motorcycle -> class_name='vehicle', subclass='car'|'truck'|...
                                      |
                                      v
          [MultiObjectTracker: FallbackIoUTracker (Hungarian Matching)]
             - Persistent Track ID, Age, Trajectory, Subclass Preservation
                                      |
                   +------------------+------------------+
                   |                                     |
                   v                                     v
       [RuleEngine & EventCorrelator]          [ANPRPipeline (Vehicle Tracks Only)]
       - Spatial Polygon (RESTRICTED_ZONE_01)  - Crop Vehicle & Aspect Check
       - ZONE_ENTRY breach transition          - PlateDetector (ContourPlateDetector)
       - Cooldown: 15s per track               - Quality/Blur Check (Laplacian var > 35)
       - Deduplicated DB Incidents             - OCREngine (EasyOCREngine / MockOCREngine)
       - Evidence JPEG + SHA-256 Hash          - Text Normalization & Clean Regex
                   |                           - Multi-Frame Consensus (>= 2 matching reads)
                   |                           - State: CANDIDATE / STABLE_VERIFIED / LOW_CONFIDENCE
                   |                           - DB: anpr_observations + SHA-256 Evidence
                   |                                     |
                   +------------------+------------------+
                                      |
                                      v
                       [FastAPI Backend (:8000)]
             - REST Endpoints: /api/v1/anpr/observations, /api/v1/incidents
             - WebSocket Hub: /ws/alerts (Broadcasts Telemetry, Alerts, & ANPR)
                                      |
                                      v
                     [React Dashboard (:5173 / Edge)]
             - MediaMTX WebRTC CAM-01 Live Feed
             - Synchronized SVG Overlay: Tracks, Polygons, ANPR Plate Pills
             - Real-time Alert Banners & ANPR Toasts
             - Vehicle Analytics & ANPR Observations Table with Thumbnails & SHA-256
```

### Key Modules:
- **`services/anpr/schemas.py`**: Pydantic v2 schemas defining `PlateStatus` (`UNREADABLE`, `CANDIDATE`, `STABLE_VERIFIED`, `LOW_CONFIDENCE`), `PlateBBox`, `PlateDetectionResult`, `OCRResult`, `ANPRObservation`, and `ANPRConfig`.
- **`services/anpr/plate_detector.py`**: Abstract base class `PlateDetector` and `ContourPlateDetector` heuristic implementation leveraging edge detection, rectangular aspect filtering ($2.0 \le AR \le 5.8$), area filtering, and bilateral smoothing.
- **`services/anpr/ocr_adapter.py`**: Abstract base class `OCREngine`, `EasyOCREngine` (CPU-optimized, alphanumeric filtering, blur rejection), and `MockOCREngine` for unit testing.
- **`services/anpr/anpr_pipeline.py`**: Multi-frame consensus engine tracking readings per `track_id`, enforcing strict anti-hallucination rules, and returning `ANPRObservation` records when eligible.
- **`apps/backend/database/models.py` & `repositories/anpr_repo.py`**: SQLAlchemy ORM `anpr_observations` table mapping with indexes, evidence paths, and SHA-256 cryptographic hashes.
- **`apps/frontend/`**: Vite + React dashboard featuring vehicle bounding boxes with subclass badges, license plate overlay pills, WebSocket dispatching, and an interactive observation log table.

---

## 3. Comprehensive Verification & Regression Results

### Automated Test Suite (`tests/`)
All 43 unit and integration tests execute and pass in under 1 second:
```
tests/test_anpr.py::test_vehicle_subclass_preservation_in_detection_and_track PASSED
tests/test_anpr.py::test_plate_detector_interface_and_contour_detector PASSED
tests/test_anpr.py::test_ocr_engine_interface_and_normalization PASSED
tests/test_anpr.py::test_blurry_plate_is_unreadable_not_hallucinated PASSED
tests/test_anpr.py::test_multi_frame_consensus_candidate_vs_verified PASSED
tests/test_anpr.py::test_conflicting_readings_mark_low_confidence PASSED
tests/test_anpr.py::test_anpr_pipeline_with_mocks_and_cooldown PASSED
tests/test_anpr.py::test_person_tracks_do_not_generate_anpr PASSED
tests/test_anpr.py::test_anpr_db_persistence_and_sha256 PASSED
tests/test_tracking.py (34 tests covering ByteTrack/IoU schemas & tracking logic) PASSED

============================= 43 passed in 0.69s ==============================
```

### End-to-End Master Acceptance Test (`powershell -ExecutionPolicy Bypass -File .\scripts\ibvap.ps1 demo`)
The automated master demo suite executed against native Microsoft Edge (`channel='msedge'`) with zero manual interventions:
```
======================================================================
 ACCEPTANCE SUITE EXECUTION SUMMARY
======================================================================
 Dashboard Loaded                 PASS
 WebRTC Video Playback            PASS
 Person AI Detection              PASS
 Live Tracking                    PASS
 Zone Overlay                     PASS
 Vehicle Analytics & Subclass     PASS
 ANPR Pipeline & Consensus        PASS
 Camera Recovery                  PASS
 WebSocket Recovery               PASS
 Incident Deduplication           PASS
======================================================================
```

Evidence screenshots generated in `docs/evidence/p2/`:
- `01_dashboard_loaded.png`: Initial operations dashboard loaded in Edge.
- `02_live_video.png`: CAM-01 real-time WebRTC feed streaming from MediaMTX.
- `03_person_tracking.png`: YOLOv8n person detection and persistent trajectory polylines.
- `04_zone_overlay.png`: Authoritative `RESTRICTED_ZONE_01` polygon overlay rendered.
- `05_live_alert.png`: Real-time intrusion banner triggered by authentic spatial breach.
- `06_vehicle_anpr_section.png`: Dedicated Vehicle Analytics & ANPR Observations table.
- `07_camera_reconnecting.png`: System resilience during simulated publisher outage.
- `08_camera_recovered.png`: Clean auto-reconnection once RTSP stream re-published.
- `09_websocket_reconnecting.png`: WebSocket failover handling.
- `10_websocket_recovered.png`: Restored WebSocket state with immediate telemetry stream.

---

## 4. Operational Boundaries & Production Roadmap

1. **Plate Localization Heuristic**: `ContourPlateDetector` is suitable for standard, unoccluded, high-contrast plates. For production deployment across arbitrary CCTV camera angles, poor weather, or heavy occlusions, train a specialized YOLOv8-nano plate localization model and wrap it with the `PlateDetector` base class.
2. **OCR Engine Adaptability**: `EasyOCREngine` provides solid open-source CPU performance. For specialized military or international plate styles, fine-tune OCR character weights or plug in a CRNN-based OCR module via `OCREngine`.
3. **Database Scalability**: SQLite is used for local single-node demonstration and edge deployment. The SQLAlchemy models and Alembic configurations are fully compatible with PostgreSQL for enterprise multi-camera deployments.

---

## 5. Final Status & Verdict

```
P0_PIPELINE_STATUS: PASS
P1_CORE_ANALYTICS_STATUS: PASS
P2_VEHICLE_ANALYTICS_STATUS: PASS
ANPR_STATUS: PASS
REGRESSION_STATUS: PASS
BROWSER_AUTOMATION_STATUS: PASS
FINAL_VERDICT: ALL_PASS
```
