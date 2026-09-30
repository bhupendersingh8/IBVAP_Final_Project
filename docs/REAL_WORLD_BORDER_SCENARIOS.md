# IBVAP Real-World Border Surveillance Scenarios (SIH PS 26187)

**Target Operating Organization**: Ministry of Home Affairs / Sashastra Seema Bal (SSB)  
**System**: Integrated Border & Perimeter Surveillance Vision Analytics Platform (IBVAP)  
**Configuration Reference**: `configs/border_scenarios.yaml`

---

## 1. Border Operational Topology & Zone Modeling

Border surveillance cannot be treated as a flat open playground. Real border posts consist of distinct tactical areas with strict rules of engagement, clearance levels, lighting variations, and physical obstacles.

IBVAP implements 10 standardized tactical zones:

### Zone A: BOP Entry / Sentry Gate (`ZONE_A_BOP_GATE`)
- **Camera**: `CAM-BOP-GATE-01` (Sentry gate ingress view)
- **Operational Purpose**: Access control for personnel and registered patrol vehicles.
- **Workflow**: Human Detection -> Face Localization -> YuNet/SFace Identity -> EAR/MAR Liveness -> Clearance Gate.
- **Allowed Personnel**: Registered BOP officers (`AUTH-001` through `AUTH-008`).
- **Alert Logic**: Unknown person entering without clearance triggers `STAFF_UNVERIFIED` investigation prompt.

### Zone B: Check Post Clearance Area (`ZONE_B_CHECK_POST`)
- **Camera**: `CAM-CHECKPOST-02` (Vehicle checkpoint barrier)
- **Operational Purpose**: Civilian and commercial vehicular traffic clearance.
- **Workflow**: Vehicle Detection -> Classification (`car`, `truck`, `bus`, `motorcycle`) -> ANPR Read.
- **Alert Logic**: Loitering exceeding 45 seconds or unauthorized vehicle bypass triggers warning.

### Zone C: Border Road & Patrol Route (`ZONE_C_BORDER_ROAD`)
- **Camera**: `CAM-ROAD-03` (Lateral highway road corridor)
- **Operational Purpose**: Speed monitoring and anti-stoppage interdiction.
- **Workflow**: Tracking -> Spatial Velocity Estimation (pixel/sec -> km/h projection).
- **Alert Logic**: Sudden stationary vehicle stoppage in transit lane (>15 sec) or excessive speed (>60 km/h).

### Zone D: Restricted Perimeter / Zero-Line Buffer (`ZONE_D_RESTRICTED_PERIMETER`)
- **Camera**: `CAM-PERIMETER-04` (150-meter international zero-line buffer strip)
- **Operational Purpose**: Complete denial zone for unauthorized civilian movement.
- **Workflow**: Human Detection -> ByteTrack -> Polygon Containment -> Temporal Persistence (2 frames).
- **Alert Logic**: Immediate `CRITICAL` perimeter intrusion alert with automatic video snapshot hashing.

### Zone E: Virtual Fence / Linear Tripwire (`ZONE_E_VIRTUAL_FENCE`)
- **Camera**: `CAM-PERIMETER-04` (Electronic tripwire aligned with international boundary marker)
- **Operational Purpose**: Unambiguous directional crossing detection.
- **Workflow**: Vector product between track trajectory $(x_{t} - x_{t-1}, y_{t} - y_{t-1})$ and normal vector $\vec{n}=(0.0, 1.0)$.
- **Alert Logic**: Crossing inward triggers instant directional breach alarm (`VIRTUAL_FENCE_BREACH`).

### Zone F: Forward Observation Post Area (`ZONE_F_OBSERVATION_AREA`)
- **Camera**: `CAM-PERIMETER-04` (Overwatch tower zone)
- **Operational Purpose**: Sentry vigil verification.
- **Workflow**: Pose Keypoint extraction (YOLO11n-Pose).
- **Alert Logic**: Sentry collapse / prolonged immobility / unattended post (>60 sec).

### Zone G: Vehicle Inspection & ANPR Bay (`ZONE_G_VEHICLE_CHECK`)
- **Camera**: `CAM-CHECKPOST-02` (Choke-point inspection bay)
- **Operational Purpose**: Mandatory plate extraction and registration check.
- **Workflow**: Crop plate region -> Dynamic contrast equalization -> EasyOCR -> Normalization -> Stolen/Watchlist query.

### Zone H: Low-Light / Night Sector (`ZONE_H_NIGHT_SECTOR`)
- **Camera**: `CAM-NIGHT-05` (Forested flank / unlit perimeter)
- **Operational Purpose**: Infrared/Night-vision movement capture.
- **Workflow**: Quality Assessor (mean Luma < 75.0) -> Adaptive CLAHE equalization (Luma 27.2 -> 46.2) -> YOLO26n Detection -> ByteTrack.

### Zone I: Multi-Camera Overlapping Coverage (`ZONE_I_CAMERA_HANDOFF`)
- **Cameras**: `CAM-BOP-GATE-01` and `CAM-CHECKPOST-02`
- **Operational Purpose**: Handing off tracked subjects moving between adjacent camera fields of view without identity hallucination.
- **Workflow**: Exit polygon in Cam 1 links candidate entry in Cam 2 within 5.0s window via `LongTermRemembranceStore`.

### Zone J: Camera Blind-Spot & Occlusion Buffer (`ZONE_J_OCCLUSION_BUFFER`)
- **Camera**: `CAM-ROAD-03` (Culvert / Tree canopy shadow)
- **Operational Purpose**: Kalman filter trajectory extrapolation across momentary blind spots (up to 10 seconds).

---

## 2. Real-World Border Scenarios (Scenarios A through H)

| Scenario | Title | Tactical Description | Trigger Condition | Expected System Response | Integrity & Verification |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **A** | **Authorized Staff Entry** | Officer Inspector Rajesh returns through BOP primary gate | Person detected in Zone A; YuNet+SFace matches `AUTH-001`; Liveness passes | Identity state: `AUTHORIZED`. Clearance granted. **No security alarm triggered**. | SFace distance < 0.65; EAR/MAR blink verified. |
| **B** | **Perimeter Approach & Intrusion** | Unknown trespasser approaches 150m Zero-Line buffer strip | Unknown person detected in Zone D for >2.0s | State transition: `IDLE` -> `DETECTED` -> `PERSISTENT` -> `INCIDENT`. Trigger `CRITICAL` alert. | Explainable alert: "Human remained inside restricted perimeter for 3.2s". |
| **C** | **Vehicle Checkpost Clearance** | Vehicle arrives at sentry bay with readable plate | Vehicle classified as `car`; plate visible in Zone G | Plate read: `DL01AB1234` (conf=0.867). ANPR observation persisted to DB. | EasyOCR output normalized against MoRTH Indian plate regex. |
| **D** | **Unreadable / Obscured Plate** | Vehicle arrives with mud-covered or absent license plate | Vehicle detected, but plate crop lacks valid characters | State: `PLATE_UNREADABLE`. Low confidence recorded. **Zero manufactured text**. | Honest degradation without hallucination. |
| **E** | **Night Forest Intrusion** | Smuggler crawling through pitch-dark forest flank | Night camera feed with mean Luma = 27.2 | Night vision enhancer applies CLAHE; detection activates; candidate tracked. | Luma boosted to 46.2; movement flagged in dark. |
| **F** | **Virtual Fence Breach** | Intruder jumps boundary line moving inward | Trajectory vector crosses line segment in Zone E | Directional crossing confirmed. Event broadcast via WebSocket. | Vector dot-product confirms inward direction. |
| **G** | **Inter-Camera Subject Transit** | Subject exits Gate Camera and appears at Checkpost Camera | Trajectory leaves Zone I in Cam 01 and enters Cam 02 within 4.2s | Tracklet associated in `LongTermRemembranceStore` with `global_id=REID-P037`. | Cross-camera link verified by spatio-temporal window. |
| **H** | **RTSP Stream Disconnect & Recovery** | Power fluctuation or severed Ethernet cable cuts video feed | OpenCV VideoCapture `ret=False` for 4 consecutive frames | Camera state -> `DISCONNECTED`. Worker enters exponential backoff retry. Reconnects cleanly upon stream restore. | Zero backend crash; UI indicates `DEGRADED`. |
