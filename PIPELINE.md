# IBVAP Pipeline Architecture & Frame Lifecycle

**System**: Intelligent Border Video Analytics Platform (IBVAP)  
**SIH Problem Statement**: 26187  
**Architecture Version**: Next-Gen Hybrid Fast-Path / Heavy-Path

---

## 1. Per-Frame Processing Lifecycle

Every incoming frame follows a deterministic 10-stage processing pipeline designed to eliminate lag and prevent thread starvation:

```
[Ingestion Tier]
  RTSP Stream / CCTV Camera / Video File
      │
      ▼
  Bounded Thread-Safe Queue (Max Size = 30) ──[Queue Full]──> Drop Oldest Frame (LIFO Telemetry)
      │
      ▼
[Stage 1: Preprocessing & Condition Analysis]
  ConditionAnalyzer (Light meter, Fog/Haze estimate, Blur Laplacian, Rain/Snow motion)
      │
      ├── CLEAR / NORMAL ─────────► Raw Frame Passed Forward
      ├── LOW_LIGHT / NIGHT ──────► CLAHE Contrast Enhancement
      ├── FOG / HAZE ─────────────► Dark Channel Prior Dehaze (Guided Filter)
      ├── RAIN / SNOW ────────────► Fast Bilateral Filter
      └── SEVERE BLUR / SHAKE ────► Marked DEGRADED (No Hallucination)
      │
      ▼
[Stage 2: Primary Object Detection (Fast Path)]
  DetectorBackend:
  - RF-DETR (Apache-2.0 RT-DETR) OR YOLOv8 Nano fallback
  - Optional: AdaptiveTiledDetector (SAHI Tiling) if Small Object Flag active & Budget < 120ms
  - Outputs: Raw Bounding Boxes, Canonical Classes, Confidence Scores, Per-Stage Latencies
      │
      ▼
[Stage 3: Multi-Object Tracking]
  ByteTrack 7-State Lifecycle Tracker:
  DETECTED ──► TENTATIVE ──► STABLE ──► VERIFIED ──► ALERT_ELIGIBLE ──► EXPIRED / CLEARED
  - Continuous Velocity Vector Computation: (vx, vy)
  - Track Quality & Trajectory History
      │
      ▼
[Stage 4: Spatial & Geometrical Reasoning]
  SpatialReasoningEngine & RelativeDepthEstimator:
  - Point-in-Polygon (PIP) Zone Classification (Exclusion Zone, Buffer Zone, Patrol Path)
  - Perimeter Fence Proximity (Warning Margin = 35px)
  - 8-Compass Direction Vectors (N, NE, E, SE, S, SW, W, NW)
  - Relative Depth / Looming Factor without uncalibrated centimeter claims
      │
      ▼
[Stage 5: Temporal Pattern & Trajectory Analysis]
  - Loitering Duration Tracking (configurable dwell threshold > 10.0s)
  - Approach Velocity Vectors & Direction of Travel towards Sensitive Zones
      │
      ▼
[Stage 6: Event Gating & Specialist Activation (Heavy Path)]
  SpecialistPipelineManager (Async Bounded ThreadPool, Max Concurrency = 4):
  - Infiltration / Breach Signal ────► Depth Estimation Specialist
  - Abnormal Human Movement ─────────► Pose / Movement Specialist (YOLOv8-Pose)
  - Vehicle Detected ────────────────► ANPR OCR Specialist (PaddleOCR / EasyOCR)
  - Threat Item Detected ────────────► Secondary Weapon / Object Verifier
  - Zero-Crash Contract: Failure isolated, does not halt frame processing
      │
      ▼
[Stage 7: Multi-Modal Confidence Fusion Engine]
  ConfidenceFusionEngine:
  - Combines: Base Detection + Track Consistency + Zone Context + Specialist Verification
  - Penalizes: Severe Blur / Weather Degradation
  - Fused Score: S = w_det*C_det + w_track*C_track + w_zone*C_zone + w_spec*C_spec - penalty
  - States: NORMAL (< 0.40) | OBSERVE (0.40-0.59) | REVIEW (0.60-0.79) | CONFIRMED_EVENT (>= 0.80)
      │
      ▼
[Stage 8: Alert & Evidence Generation]
  - Section 65B Indian Evidence Act Hash Chain:
    SHA-256(Raw Frame Image) + HMAC-SHA256(Audit Event Metadata)
  - Stored in Tamper-Evident Evidence Vault
      │
      ▼
[Stage 9: Telemetry & WebSocket Dispatch]
  - Ingestion Latency, Preprocessing Latency, Inference Latency, Tracking Latency
  - Active Tracks, Zone States, Bounding Boxes, Alert Records
      │
      ▼
[Stage 10: VMS Client Dashboard Display]
  - 3-Column Operator Layout with Real-time Canvas Rendering
```

---

## 2. Queue Architecture & Overflow Strategies

To prevent memory leaks and out-of-order frame delivery during network hiccups:

| Queue | Component | Max Capacity | Overflow Strategy | Purpose |
|---|---|---|---|---|
| `frame_queue` | `CameraSource` / `RTSPSource` | 30 frames | Drop oldest frame (DropHead) | Ensures real-time latency (<100ms) under heavy load |
| `specialist_queue` | `SpecialistPipelineManager` | 16 tasks | Reject with fallback status `DROPPED` | Prevents Heavy Path from starving Fast Path |
| `ws_broadcast_queue` | `FastAPI WebSocket Manager` | 100 messages | Non-blocking put; drop oldest | Prevents slow frontends from stalling video loops |

---

## 3. Specialist Activation Decision Matrix

Specialist models are **never** executed unconditionally on every frame. They trigger exclusively upon event thresholds:

| Trigger Condition | Target Entity | Activated Specialist | Latency Budget | Fallback if Timeout |
|---|---|---|---|---|
| Person in Exclusion Zone | `person` | `PoseMovementSpecialist` | 45 ms | Keep fast-path classification |
| Fast Vector towards Perimeter | `person` / `vehicle` | `DepthEstimatorSpecialist` | 40 ms | Bounding box height heuristic |
| Vehicle entering AOI | `car` / `truck` / `bus` | `PaddleOCR ANPR` | 60 ms | Mark as `PLATE_UNREADABLE` |
| Potential Threat Class | `firearm` / `knife` | `SecondaryWeaponVerifier` | 35 ms | Escalate to `REVIEW` with warning |
