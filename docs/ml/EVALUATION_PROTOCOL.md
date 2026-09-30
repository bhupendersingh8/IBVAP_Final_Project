# EVALUATION_PROTOCOL.md — Standardized Model Evaluation Protocol

**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Standard:** Empirical Metric Verification (Anti-Hallucination Compliance)  

---

## 1. Protocol Overview

The IBVAP Evaluation Protocol defines the exact procedures for measuring object detector precision, recall, mean Average Precision (mAP), and computational latency on edge hardware.

---

## 2. Evaluation Metrics

1. **Precision (P)**: True Positives / (True Positives + False Positives). Measures resistance to false alarms.
2. **Recall (R)**: True Positives / (True Positives + False Negatives). Measures intrusion detection completeness.
3. **mAP@50**: Mean Average Precision at IoU threshold of 0.50. Primary ranking metric for target detection.
4. **mAP@50-95**: Mean Average Precision averaged across IoU thresholds from 0.50 to 0.95 in steps of 0.05.
5. **Inference Latency (ms)**: Measured time required to execute preprocessing, model forward pass, and non-maximum suppression (NMS) on 640x640 input.
6. **Throughput (FPS)**: Inverted latency ($1000 / 	ext{latency\_ms}$).

---

## 3. Independent Hold-Out Test Set Rule

- The `dataset/images/test/` and `dataset/labels/test/` folders are **strictly isolated**.
- Under no circumstances may images from `test/` be included in training or validation splits.
- All evaluation reports and gate decisions are computed exclusively against the test set.

---

## 4. Unpopulated Dataset & Anti-Hallucination Protocol

When domain ground-truth annotations are not yet available:
- The system reports `NOT_AVAILABLE` for precision, recall, and mAP.
- Under **no circumstances** does the system synthesize benchmark numbers or claim fictitious accuracy.
- Real hardware latency and FPS are empirically profiled using physical video frames to verify host compute capabilities.
