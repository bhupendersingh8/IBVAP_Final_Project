# Custom Domain-Trained Model Evaluation Report

**Model Name:** `ibvap-yolov8n-border-v1` (Candidate)  
**Base Architecture:** YOLOv8n  
**Target Domain Classes:** `person`, `car`, `truck`, `bus`, `motorcycle`  
**Extensible Schema:** `border_guard`, `civilian`, `animal`, `special_vehicle`  
**Dataset:** Border Perimeter Domain Dataset (Train / Val / Untouched Held-Out Test Split)  
**Evaluation Status:** `CUSTOM_MODEL_TRAINING = PENDING_REAL_DATA`

---

## 1. Strict Anti-Fabrication & Integrity Disclosure

In accordance with strict engineering ethics and SIH/MHA demonstration integrity:

> [!IMPORTANT]
> **NO FAKE TRAINING METRICS OR HARDCODED ACCURACY CLAIMS**:
> The training pipeline, data curation tooling (`scripts/collect_dataset_frames.py`), augmentations, and evaluation gates are fully engineered and executable. However, because a legally authorized and annotated multi-weather border dataset has not yet been annotated on this workstation, numerical metrics are marked **PENDING_REAL_DATA** rather than publishing fabricated figures.

---

## 2. Evaluation Gate Criteria (Target Thresholds)

When real annotated domain data is loaded, the model must meet the following mandatory acceptance gates before promotion to `CANARY` or `PRODUCTION`:

| Evaluation Gate Metric | Required Threshold | Rationale |
|---|:---:|---|
| **mAP@0.50** | $\ge 0.70$ | High detection reliability in border perimeter context |
| **mAP@0.50:0.95** | $\ge 0.50$ | High bounding box localization accuracy |
| **False Positive Rate (FPR)** | $\le 0.10$ | Minimizes operator alarm fatigue |
| **False Negative Rate (FNR)** | $\le 0.15$ | Strict security boundary enforcement |
| **CPU Inference Latency** | $\le 100	ext{ ms}$ | Maintains real-time edge processing on Core i3 CPU |
| **Held-Out Test Overfitting Gap** | $\le 0.08$ | Validates generalization on completely unseen test split |

---

## 3. Retraining Workflow

```
Authorized Border Video / Images
             ↓
Frame Extraction & Laplacian Sharpness Filter (Var > 100)
             ↓
Deduplication & Human Annotation
             ↓
Dataset Versioning (Train: 70%, Val: 15%, Test: 15%)
             ↓
YOLOv8 Fine-Tuning (yolo train cfg=ml/training/training_config.yaml)
             ↓
Untouched Test Split Evaluation
             ↓
Evaluation Gates Pass? ──No──> Reject / Annotate Failure Modes
             ↓ Yes
Model Registry (State: VALIDATED -> CANARY -> PRODUCTION)
```
