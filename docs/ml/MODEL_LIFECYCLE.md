# MODEL_LIFECYCLE.md — IBVAP Model Governance & Promotion Protocol

**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Governance Standard:** Zero Silent Overwrite / Human-in-the-Loop Validation Gate  

---

## 1. Lifecycle States

Every model within the IBVAP platform transitions through explicit, immutable states recorded in `ml/registry/model_registry.yaml`:

```
   [ TRAIN ]
       │
       ▼
  [ CANDIDATE ] ────── (Fails Validation Gate) ──────> [ REJECTED ]
       │
 (Passes Gate)
       │
       ▼
  [ VALIDATED ]
       │
(Human Approval)
       │
       ▼
   [ CANARY ] ──────── (High False Positives) ────────> [ REJECTED ]
       │
(Operational Sign-off)
       │
       ▼
  [ PRODUCTION ] ──── (Regression Detected) ─────────> [ ROLLED_BACK ]
```

### 1.1 State Definitions
- **`CANDIDATE`**: Model freshly trained; awaiting automated validation against ground-truth evaluation set.
- **`VALIDATED`**: Model has achieved $\ge 0.70$ mAP50, $\le 0.10$ False Positive Rate, and $\le 100$ms CPU latency.
- **`CANARY`**: Model deployed to a single non-critical outpost camera for live operational observation.
- **`PRODUCTION`**: Active model deployed across all operational CCTV streams.
- **`REJECTED`**: Model failed accuracy, false positive, or latency thresholds. Retained for audit trail.
- **`ROLLED_BACK`**: Previously active production model demoted upon deployment of a superior model or emergency fallback.

---

## 2. Automated Validation Gates

A candidate model cannot be promoted without passing `ValidationGate`:

| Evaluation Gate | Acceptance Threshold | Failure Action |
|---|:---:|---|
| **mAP@50 (Domain Target)** | $\ge 0.70$ | Mark `REJECTED` |
| **mAP@50-95** | $\ge 0.50$ | Mark `REJECTED` |
| **False Positive Rate (FPR)** | $\le 0.10$ | Mark `REJECTED` |
| **CPU Inference Latency** | $\le 100.0$ ms | Mark `REJECTED` |
| **Baseline Parity** | $\ge 	ext{Baseline mAP}$ | Mark `REJECTED` |

---

## 3. Dynamic Inference Model Selection

The inference pipeline uses `services/detection/model_selector.py` to decouple detector weights from the engine:

```python
from services.detection.model_selector import ModelSelector

selector = ModelSelector()
model_path, version, metadata = selector.resolve()
```

- In production mode, the selector retrieves the model marked `PRODUCTION` in `model_registry.yaml`.
- If no custom production model exists or files are missing, it defaults safely to `"yolov8n.pt"` with zero system interruption.
- Rollbacks can be executed instantly without restarting services:
  ```python
  from ml.registry.model_registry import ModelRegistry
  registry = ModelRegistry()
  registry.rollback_production(reason="Elevated false alarms during rainstorm")
  ```
