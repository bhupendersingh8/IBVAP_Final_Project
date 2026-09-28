# IBVAP — Next-Generation Computer Vision Upgrade Migration Plan
**Project:** Intelligent Border Video Analytics Platform (IBVAP)  
**SIH Problem Statement:** PS-26187  
**Baseline Verification:** 188/188 pytest passing (100% green)  
**Target Delivery:** Research-Grade, Condition-Aware, Modular CV Platform  

---

## 1. Guiding Migration Principles

1. **Baseline Preservation**: The existing working system (188/188 tests passing, MediaMTX RTSP streaming, CPU fallback, FastAPI, React dashboard, Section 65B hash-chain ledger) is sacred. No working module will be deleted or broken.
2. **Incremental Test-Driven Implementation**: Every phase will be implemented modularly, accompanied by unit and regression tests, verified immediately via pytest before proceeding.
3. **No Unsubstantiated Claims**: No artificial or simulated accuracy (no "100% accuracy", "zero false positives", "tamper-proof"). All benchmarks will reflect empirical measurements labeled `SYNTHETIC`, `RECORDED_VIDEO`, or `LIVE_CAMERA`.
4. **Fast Path / Heavy Path Separation**: Keep primary per-frame detection lightweight (< 25ms on CPU) and invoke heavy models (Pose, ANPR, Depth, Seg) strictly on event triggers.

---

## 2. Phased Migration Schedule (Phases 1–30)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 0: REPOSITORY AUDIT & GOVERNANCE                                      │
│ Status: COMPLETED (Audit, Gap Analysis, Model Registry, License Manifest)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ STAGE 1: PERCEPTION & INGESTION HARDENING (Phases 1, 2, 3)                  │
│ • Bounded Ingestion Queues & Stale Frame Dropping                           │
│ • ConditionAnalyzer (CLEAR, LOW_LIGHT, NIGHT, FOG, RAIN, BLUR, SHAKE)       │
│ • Adaptive EnhancementManager with Transformation Latency & Telemetry       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ STAGE 2: DETECTION & SPATIAL EXPANSION (Phases 4, 5, 9, 10)                 │
│ • DetectorBackend Abstraction (YOLOv8Backend & RFDETRBackend)               │
│ • SAHI Adaptive Tiling for Tiny/Distant Border Infiltrators                 │
│ • Relative Monocular Depth Geometry (Depth Anything 3 integration)          │
│ • SpatialReasoningEngine (Virtual Fences, Entry/Exit Direction Vectors)     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ STAGE 3: TRACKING & SPECIALIST SUITE (Phases 6, 7, 8, 12, 14)               │
│ • ByteTrack 7-State Track Lifecycle (DETECTED -> TENTATIVE -> ALERT)        │
│ • Event-Triggered Pose Verification (RTMPose / Fallback Keypoints)          │
│ • Multi-Frame ANPR Consensus & PaddleOCR Engine                             │
│ • Event-Triggered Segmentation (RT-DETR-R18-Seg)                            │
│ • SpecialistPipelineManager Tracking                                        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ STAGE 4: FUSION, EVIDENCE & INTEGRITY (Phases 11, 13, 16, 20, 21)           │
│ • Temporal Intelligence Multi-Stage State Machine                           │
│ • ConfidenceFusionEngine (Decision States: NORMAL, OBSERVE, REVIEW, ALERT)  │
│ • Tamper-Evident SHA-256 Ledger & POST /api/v1/evidence/verify              │
│ • FastAPI Clean Endpoints & Real-Time WebSocket Telemetry                   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ STAGE 5: FRONTEND VMS & BENCHMARKING (Phases 18, 19, 22, 24, 28, 29, 30)    │
│ • Professional VMS UI: Left (Cameras), Center (Video+HUD), Right (Alerts),  │
│   Bottom (Live Pipeline Status: Ingestion -> Quality -> Detector -> ...)     │
│ • Adverse-Condition Benchmark Suite (16 Environmental Stress Scenarios)     │
│ • Full Regression & Offline-First Verification                              │
│ • Comprehensive Project Documentation Suite                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Verification Gates

| Phase | Milestone Deliverables | Verification Command | Gate Criteria |
| :--- | :--- | :--- | :--- |
| **Stage 1** | `ConditionAnalyzer`, `EnhancementManager`, Bounded queue dropping | `pytest tests/test_night_vision.py` | 100% pass; 0 unhandled drop exceptions |
| **Stage 2** | `DetectorBackend`, `RFDETRBackend`, SAHI tiling, `SpatialReasoningEngine` | `pytest tests/test_detection.py` | Seamless detector swap via config |
| **Stage 3** | ByteTrack 7-state machine, ANPR consensus, `SpecialistPipelineManager` | `pytest tests/test_tracking.py tests/test_anpr.py` | Zero ID switch regressions |
| **Stage 4** | `POST /api/v1/evidence/verify`, `ConfidenceFusionEngine` | `pytest tests/test_hash_chain.py` | Tampered file returns `400 / Invalid` |
| **Stage 5** | VMS React UI, Adverse Benchmark, Offline validation | `pytest tests/ && npm run build` | Full test pass; clean SPA bundle |
