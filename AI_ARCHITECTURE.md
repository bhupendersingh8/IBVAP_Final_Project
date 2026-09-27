# IBVAP AUTONOMOUS MULTI-MODEL AI ARCHITECTURE
**System:** Intelligent Border Video Analytics Platform (IBVAP)  
**Document:** End-to-End Autonomous AI Orchestration Architecture (Levels 0–6)  
**Host Target:** Dell Core i3-1115G4 (CPU-First Execution) + RTX 3050 & Sovereign Cloud Expansion  

---

## 1. System Overview & The 7-Tier Cascading Hierarchy

The IBVAP Autonomous Multi-Model AI Orchestrator replaces single-model pipelines with an intelligent **7-Tier Hierarchical Cascade (Level 0 through Level 6)**. This guarantees that:
- Heavy transformer and vision-language models are **never executed blindly** on every raw video frame.
- High-throughput edge models filter out environmental noise in real-time on CPU.
- When an object of interest, perimeter violation, or behavioral anomaly is detected, specialist models and multimodal reasoners are activated on-demand.
- If an advanced specialist model is not installed locally, the **Zero-Crash Fallback Contract** automatically routes the query to an active baseline model without halting the surveillance stream.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     LEVEL 0: SIGNAL & RESTORATION                               │
│   RTSP (MediaMTX: CAM-01) / DirectShow Webcam:0 -> Drop-Oldest Bounded Buffer  │
│   Low-Light Assessment -> Adaptive CLAHE/Gamma (Fallback: Retinexformer/ZeroDCE)│
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │ Clean Restored Video Frame (640x480)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     LEVEL 1: SPATIAL DETECTION                                  │
│   YOLOv8n (CPU Baseline, 2 Threads) / Fallback Router for D-FINE & RT-DETR      │
│   Broad Taxonomy Categorization (Person, Vehicle, Animal, Equipment, Weapon)    │
│   Low-Confidence Noise Rejection (< 0.25 threshold)                             │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │ 2D Bounding Boxes + Confidence Scores
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     LEVEL 2: TEMPORAL TRACKING                                  │
│   ByteTrack Adapter (C++ lapx Hungarian Matching & High/Low Confidence IoU)     │
│   Track ID Continuity Across Partial Occlusions + Velocity & Trajectory Vectors │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │ Persistent Tracklets (Track ID, Velocity)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     LEVEL 3: SPECIALIST EXTRACTION                              │
│   - Person  -> Face Detector + 4-State Identity Machine (AdaFace Fallback: Haar)│
│                + Skeleton Pose Estimator (RTMPose Fallback: YOLOv8n-pose)       │
│   - Vehicle -> Indian HSRP ANPR OCR (VehicleAttr Fallback: Fast-Plate Heuristic)│
│   - Animal  -> Livestock vs Wildlife Classifier                                 │
│   - Re-ID   -> Cross-Camera Affinity (TransReID Fallback: Spatio-Temporal)      │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │ Specialist Attributes & Verifications
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     LEVEL 4: TEMPORAL VALIDATION & RULES                        │
│   Temporal Event Engine State Machine:                                          │
│     DETECTED (1) -> TENTATIVE (5) -> STABLE (15) -> VERIFIED (30)               │
│     -> ALERT_ELIGIBLE (45 frames ≈ 1.5s at 30 FPS)                             │
│   Tactical Rules: Zone Intrusion, Line Transgression, Loitering, Speed Anomaly  │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │ Validated Events + Hazard Scores
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     LEVEL 5: MULTIMODAL FUSION & BUS                            │
│   Dynamic Route Scoring Formula (S_route) & Tactical Action Directives          │
│   Multi-Model Agreement / Disagreement Calibration Engine                       │
│   Multi-Camera Event Bus (Cross-Camera Handover between CAM-01, WEBCAM, CAM-02)│
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │ Fused Incident Context + Route Directives
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     LEVEL 6: TACTICAL COPILOT & AUDIT                           │
│   Vision-Language Intelligence Synthesis (Qwen2.5-VL Fallback: Tactical Rules)  │
│   Indic Language Alert Broadcast (English, Hindi, Punjabi)                      │
│   Cryptographic SHA-256 Tamper-Evident Ledger Packaging                         │
│   WebSocket Real-Time Broadcast -> React Single-Overlay Dashboard Viewport      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Dynamic Route Scoring Formula

To prevent false alarms and determine the exact operational response required, the orchestrator evaluates every tracked object against the **Dynamic Route Scoring Formula**:

$$S_{route} = w_d \cdot C_{det} + w_t \cdot C_{track} + w_{temp} \cdot C_{temporal} + w_z \cdot C_{zone} + w_{id} \cdot C_{identity} + w_a \cdot C_{anomaly} + w_v \cdot C_{vlm} + w_q \cdot C_{cam\_quality}$$

### Normalized Factor Definitions
1. **$C_{det}$ (Detector Confidence):** Primary detector score ($0.0 \le C_{det} \le 1.0$).
2. **$C_{track}$ (Tracking Continuity):** Association stability across consecutive frames ($0.0 \le C_{track} \le 1.0$).
3. **$C_{temporal}$ (Temporal Maturity):** Maturity ratio relative to 45 consecutive frames baseline ($\min(1.0, \text{frames} / 45)$).
4. **$C_{zone}$ (Zone Hazard Rating):** Buffer Zone = 0.3, Restricted Area = 0.7, Critical Border Fence = 1.0.
5. **$C_{identity}$ (Identity Threat Factor):**
   - `AUTHORIZED`: $C_{identity} = 0.0$
   - `UNKNOWN`: $C_{identity} = 0.5$
   - `UNVERIFIED`: $C_{identity} = 0.7$
   - `UNAUTHORIZED`: $C_{identity} = 1.0$
6. **$C_{anomaly}$ (Anomaly Score):** Departure from normal baseline motion or trajectory ($0.0 \le C_{anomaly} \le 1.0$).
7. **$C_{vlm}$ (Vision-Language Threat Rating):** Tactical semantic threat rating ($0.0 \le C_{vlm} \le 1.0$).
8. **$C_{cam\_quality}$ (Signal Quality Multiplier):** Video luminance, sharpness, and resolution ($0.2 \le C_{cam\_quality} \le 1.0$).

### Configurable Weights & Normalization
$$\sum w_i = w_d + w_t + w_{temp} + w_z + w_{id} + w_a + w_v + w_q = 1.0$$
- $w_d = 0.20$
- $w_t = 0.15$
- $w_{temp} = 0.15$
- $w_z = 0.15$
- $w_{id} = 0.15$
- $w_a = 0.10$
- $w_v = 0.05$
- $w_q = 0.05$

### Action Directive Decision Thresholds
| Range | Action Directive | Operational Response |
|:---|:---|:---|
| $S_{route} \ge 0.85$ | `CRITICAL_INTERCEPT_DISPATCH` | Immediate audible alarm, PTZ lock-on, Indic alert broadcast, SHA-256 evidence logged. |
| $0.65 \le S_{route} < 0.85$ | `ELEVATED_TACTICAL_ALERT` | Yellow border flash on dashboard, specialist face/ANPR verification forced. |
| $0.45 \le S_{route} < 0.65$ | `ACTIVE_MONITORING_TRACK` | Retain tracklet in memory, update velocity and trajectory, no operator alert. |
| $0.25 \le S_{route} < 0.45$ | `LOW_CONFIDENCE_OBSERVATION`| Log telemetry quietly; candidate under temporal maturation. |
| $S_{route} < 0.25$ | `DISREGARD_FILTERED_NOISE` | Environmental noise / foliage flutter; discard immediately without storing. |

---

## 3. Multi-Camera Event Bus & Cross-Camera Handover

The `MultiCameraEventBus` acts as a distributed pub/sub broker across all camera nodes:
- `CAM-01`: Canonical local RTSP CCTV simulation (`rtsp://127.0.0.1:8554/CAM-01`).
- `WEBCAM-01`: Laptop built-in DirectShow webcam (single-process owner).
- `CAM-02`: Secondary sector checkpoint simulation.

### Cross-Camera Handover Mechanism
When a target exits `CAM-01` on the right boundary ($\text{norm\_x} > 0.90$), the event bus records its departure vector and timestamp. If a target appears within 12 seconds on the left boundary of `CAM-02` ($\text{norm\_x} < 0.15$), the bus evaluates:
1. **Spatial Proximity:** Physical adjacency of camera installation zones.
2. **Temporal Window:** $\Delta t < 12.0\text{s}$.
3. **Appearance Affinity:** Color histogram and aspect ratio match.

When verified, the bus assigns the **same `GLOBAL-ID`**, preserving track history across multiple camera feeds.

---

## 4. Zero-Crash Fallback Hierarchy

The system enforces guaranteed reliability:

```
[Requested Model] ─────────► [ModelRegistry.resolve_model(id)]
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
         [Is Installed?]                         [Not Installed?]
                 │                                       │
                YES                                      NO
                 ▼                                       ▼
        [Execute Model]                 [Query metadata.fallback_target]
                                                         │
                                                         ▼
                                            [Status: REGISTERED / NOT INSTALLED
                                                     FALLBACK ACTIVE]
                                                         │
                                                         ▼
                                                [Execute Safe CPU Baseline]
                                                (yolov8n / haar / bytetrack)
```

No missing weight file, missing CUDA driver, or uninstalled Python package can cause a fatal process crash.
