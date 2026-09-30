# BASELINE_EVALUATION.md — Pretrained Detector Evaluation Report

**Model Artifact:** `yolov8n.pt`
**Execution Device:** `cpu`
**Evaluation Status:** LATENCY_BENCHMARKED_NO_GROUND_TRUTH

---

## 1. Measured Performance Metrics

| Metric | Measured Value | Standard / Target |
|---|:---:|:---:|
| **Precision** | NOT_AVAILABLE | >= 0.70 |
| **Recall** | NOT_AVAILABLE | >= 0.65 |
| **mAP@50** | NOT_AVAILABLE | >= 0.70 |
| **mAP@50-95** | NOT_AVAILABLE | >= 0.50 |
| **Inference Latency (CPU)** | **1344.54 ms** | <= 100 ms |
| **Throughput (CPU)** | **0.74 FPS** | >= 10 FPS |

---

## 2. Integrity & Data Availability Statement

> No labeled evaluation annotations found in dataset/labels/test. Metrics marked NOT_AVAILABLE per anti-hallucination protocol.

Per IBVAP anti-hallucination protocols, domain mAP metrics are **NOT** fabricated in the absence of labeled ground-truth field data.
Hardware inference latency and frame throughput are measured empirically on the Intel Core i3 host machine.
