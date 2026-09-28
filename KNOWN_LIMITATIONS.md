# IBVAP Known Limitations & Operational Boundaries

**System**: Intelligent Border Video Analytics Platform (IBVAP)  
**SIH Problem Statement**: 26187  
**Guiding Principle**: Absolute scientific honesty and anti-hallucination compliance.

---

## 1. Absolute Platform Boundaries

1. **No "100% Accuracy" or "Zero False Alarms" Claims**:
   - In computer vision operating in non-cooperative outdoor border environments, occlusion, physical clutter, and sensory noise inevitably cause transient false classifications.
   - IBVAP mitigates this via multi-frame temporal confirmation (7-state ByteTrack) and Multi-Modal Confidence Fusion, but edge-case misclassifications remain possible.

2. **Severe Environmental Degradation**:
   - **Zero-Visibility Fog / Blizzard**: If optical transmission drops below camera sensor threshold, optical cameras cannot resolve targets. Thermal/LWIR sensors are required for complete obscurant penetration.
   - **Total Lens Obscuration**: Mud, heavy snow caking, or physical tape on camera lenses triggers a `LENS_BLOCKED` system health alert rather than attempting hallucinated detections.

3. **Metric Depth Without Camera Calibration**:
   - Monocular depth estimation provides **relative depth ordering** (e.g., Target A is closer than Target B) and looming rates (growth rate of bounding box).
   - Metric distance (e.g., "14.2 meters") is mathematically ill-posed without calibrated camera intrinsics ($f_x, f_y, c_x, c_y$) and ground-plane homography. IBVAP clearly marks uncalibrated depth as `RELATIVE_PROXIMITY`.

4. **Hardware Capacity Limits**:

| Hardware Tier | Max Simultaneous 1080p Streams | Max Recommended Heavy-Path Specialists | Target Stream FPS |
|---|---|---|---|
| Intel Core i5 (Dell Laptop CPU) | 4 RTSP Streams | 2 Specialists (Event-Triggered) | 15-20 FPS |
| NVIDIA RTX 3050 Laptop (4GB VRAM) | 8 RTSP Streams | 4 Specialists Concurrently | 30 FPS |
| NVIDIA Jetson Orin Nano (8GB) | 6 RTSP Streams | 3 Specialists Concurrently | 25 FPS |
| Enterprise Edge Server (RTX 4090) | 24+ RTSP Streams | Full Specialist Pool Concurrently | 30 FPS |

5. **Camera Angle Requirements**:
   - Optimal detection occurs when surveillance cameras are mounted at 15° to 45° depression angle relative to the ground plane.
   - Steep overhead views (>70°) diminish human aspect ratios and pose detection accuracy.
