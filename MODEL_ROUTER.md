# IBVAP MODEL ROUTER & DYNAMIC DISPATCH POLICY
**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Module:** `services/orchestrator/route_scorer.py` & `services/detection/model_orchestrator.py`  
**Host Target:** Dell Core i3-1115G4 (CPU Mode) + Target RTX 3050  

---

## 1. Routing Engine Architecture

The IBVAP Model Router governs the dynamic execution flow of detection, specialist invocation, confidence calibration, and alert generation. Rather than executing all models on all frames (which causes latency spikes and system lockups on CPU), the router employs an **event-driven, condition-gated execution model**.

---

## 2. Dynamic Route Scoring Policy

The router continuously evaluates every object track against the 8-factor dynamic scoring formula:

$$S_{route} = \sum_{i} w_i \cdot C_i$$

### Factor Breakdown & Weight Configuration
| Factor | Weight ($w$) | Metric Input | Normalized Range | Description |
|:---|:---:|:---|:---:|:---|
| Primary Detection ($C_{det}$) | 0.20 | Raw detector confidence | $[0.0, 1.0]$ | Bounding box spatial accuracy |
| Tracking Continuity ($C_{track}$) | 0.15 | Association IoU & Kalman stability | $[0.0, 1.0]$ | Track smoothness across frames |
| Temporal Maturity ($C_{temporal}$) | 0.15 | Frame streak / 45 frames baseline | $[0.0, 1.0]$ | Persistence duration ($\approx 1.5\text{s}$) |
| Zone Criticality ($C_{zone}$) | 0.15 | Tactical geofence hazard rating | $[0.0, 1.0]$ | Buffer (0.3), Alert (0.7), Fence (1.0) |
| Identity Risk ($C_{identity}$) | 0.15 | 4-State Identity Machine | $[0.0, 1.0]$ | Auth (0.0), Unk (0.5), Unauth (1.0) |
| Anomaly Severity ($C_{anomaly}$) | 0.10 | Outlier trajectory score | $[0.0, 1.0]$ | Wrong-way, speed or border tampering |
| VLM Threat Score ($C_{vlm}$) | 0.05 | Vision-Language semantic rating | $[0.0, 1.0]$ | Camouflage, concealed weapon |
| Stream Quality ($C_{cam\_quality}$) | 0.05 | Luminance, blur & contrast index | $[0.2, 1.0]$ | Degraded sensor attenuation |

---

## 3. Specialist Routing Trigger Conditions

Specialist models are activated conditionally to conserve CPU cycles:

```
[Object Detection Box]
         │
         ├── Class == "person"
         │       │
         │       ├── Every 4th frame AND Box Area >= 60x120px ──► Route to Face Specialist
         │       └── In Critical Fence Zone OR Loitering ──────► Route to Pose Specialist
         │
         ├── Class in ("car", "truck", "bus", "van")
         │       │
         │       └── Box Width >= 40px AND Box Height >= 30px ─► Route to ANPR Specialist
         │
         ├── Class == "animal"
         │       │
         │       └── Always ────────────────────────────────────► Route to Wildlife Classifier
         │
         └── Confidence < 0.45 AND Disagreement ────────────────► Mark UNKNOWN / UNSURE
```

### Trigger Rules
1. **ANPR Vehicle Specialist:**
   - **Condition:** $\text{Class} \in \{\text{vehicle, car, truck, bus, motorcycle}\}$ AND $\text{width} \ge 40\text{px}$ AND $\text{height} \ge 30\text{px}$.
   - **Action:** Crop bounding box with 10% padding; run license plate localization and character recognition.
2. **Face & Identity Specialist:**
   - **Condition:** $\text{Class} == \text{"person"}$ AND $(\text{frame\_id} \pmod 4 == 0)$ AND $\text{height} \ge 80\text{px}$.
   - **Action:** Extract upper 40% torso crop; detect facial landmarks; verify against authorized personnel database; assign 4-state identity.
3. **Pose & Behavior Specialist:**
   - **Condition:** Target in high-hazard zone ($\ge 0.80$) OR target loitering ($> 15$ frames).
   - **Action:** Run 17-keypoint skeleton estimator; flag fence climbing, crawling, crouching, or weapon-aiming postures.

---

## 4. Model Agreement & Disagreement Fusion Rules

The fusion engine prevents naive score averaging and protects against hallucinated alerts:

### Rule 1: Consensus Agreement
$$\text{If } \text{Class}_{primary} == \text{Class}_{specialist}:$$
$$C_{fused} = \min(0.99, \max(C_{primary}, C_{specialist}) + 0.02)$$
The confirmed subclass (e.g. `truck` over `vehicle`) is adopted, and confidence receives a calibrated boost.

### Rule 2: Overwhelming Specialist Disagreement
$$\text{If } \text{Class}_{primary} \neq \text{Class}_{specialist} \text{ and } C_{specialist} > (C_{primary} + 0.25):$$
The specialist model prediction supersedes the primary detector. A `MODEL_DISAGREEMENT` audit log is recorded.

### Rule 3: Low-Confidence Ambiguity
$$\text{If } \text{Class}_{primary} \neq \text{Class}_{specialist} \text{ and } |C_{primary} - C_{specialist}| < 0.15 \text{ and } C_{primary} < 0.50:$$
The target is classified as:
$$\text{Class} = \text{"UNKNOWN / UNSURE"}$$
No alarm is triggered. The track remains under observation until further frames resolve ambiguity.
