# Model Evaluation Report Template

**Model Identifier:** `[e.g., ibvap_yolov8n_border_v1]`  
**Base Architecture:** `[e.g., YOLOv8n / RTMDet-tiny / TAO DetectNet]`  
**Evaluation Date:** `YYYY-MM-DD`  
**Evaluator:** `[Engineer / Automated Pipeline]`  
**Test Dataset Split:** `ml/datasets/test/ (Manifest SHA-256: [hash])`  

---

## 1. Quantitative Performance Metrics

| Metric | Measured Value | Acceptance Threshold | Result |
|---|---|---|---|
| **mAP@50** | `0.XX` | $\ge 0.70$ | `PASS / FAIL` |
| **mAP@50-95** | `0.XX` | $\ge 0.50$ | `PASS / FAIL` |
| **Precision (Overall)** | `0.XX` | $\ge 0.75$ | `PASS / FAIL` |
| **Recall (Overall)** | `0.XX` | $\ge 0.75$ | `PASS / FAIL` |
| **False Positive Rate** | `0.XX` | $\le 0.10$ | `PASS / FAIL` |
| **False Negative Rate** | `0.XX` | $\le 0.15$ | `PASS / FAIL` |

---

## 2. Per-Class Performance Breakdown

| Class Name | Ground Truth Count | True Positives | False Positives | False Negatives | mAP@50 |
|---|---|---|---|---|---|
| **Person** | `0` | `0` | `0` | `0` | `0.XX` |
| **Car** | `0` | `0` | `0` | `0` | `0.XX` |
| **Truck** | `0` | `0` | `0` | `0` | `0.XX` |
| **Bus** | `0` | `0` | `0` | `0` | `0.XX` |
| **Motorcycle** | `0` | `0` | `0` | `0` | `0.XX` |

---

## 3. Hardware & Runtime Profiling

- **Target Device:** `[e.g., Intel Core i3-1115G4 / NVIDIA T4 / Jetson AGX Orin]`
- **Inference Precision:** `[FP32 / FP16 / INT8]`
- **Batch Size:** `1`
- **Mean Preprocessing Latency:** `X.X ms`
- **Mean Inference Latency:** `X.X ms`
- **Mean Postprocessing Latency:** `X.X ms`
- **Effective FPS:** `X.X frames/sec`
- **Peak RAM / VRAM Utilization:** `X.X MB`

---

## 4. Environmental & Stress Conditions

- [ ] Low-Light / Night (CLAHE enabled)
- [ ] Atmospheric Fog / Mist
- [ ] Boundary Occlusion (Mesh / Barbed Wire)
- [ ] Extreme Aspect Ratio / Ground Distance

---

## 5. Certification & Promotion Gate

- **Verdict:** `[REJECTED | CANDIDATE | PROMOTED_TO_PRODUCTION]`
- **Sign-off Note:**
