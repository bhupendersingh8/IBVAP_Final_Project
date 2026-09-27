# DATA_QUALITY.md — Optical Data Quality Standards & Filtering Protocol

**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Module:** `ml/dataset/quality.py` (`QualityFilter`)  

---

## 1. Quality Assessment Dimensions

| Dimension | Metric | Good Threshold | Low Quality Threshold | Rejection Threshold |
|---|---|:---:|:---:|:---:|
| **Resolution** | Dimensions $(W 	imes H)$ | $\ge 640 	imes 360$ | N/A | $< 592 	imes 360$ |
| **Sharpness** | Laplacian Variance | $\ge 50.0$ | $30.0 - 50.0$ | $< 30.0$ (Severe blur) |
| **Exposure** | Mean Gray Value | $50.0 - 200.0$ | $25.0 - 50.0$ / $200.0 - 235.0$ | $< 25.0$ / $> 235.0$ |
| **Contrast** | Pixel Standard Deviation | $\ge 25.0$ | $18.0 - 25.0$ | $< 18.0$ (Flat frame) |
| **Deduplication**| Normalized Cross-Correlation| $< 0.95$ | N/A | $\ge 0.95$ (Duplicate) |

---

## 2. Non-Destructive Filtering Policy

- Frames marked `LOW_QUALITY` or `DUPLICATE` are flagged in `dataset/metadata/frames.jsonl` rather than being deleted immediately.
- This allows human data engineers to review edge cases or train dedicated low-light/fog enhancement models before pruning.
