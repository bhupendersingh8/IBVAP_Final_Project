# MODEL_EVALUATION.md — Model Evaluation Strategy

> **Status: PARTIAL** — YOLOv8n baseline active. All other models NOT_BENCHMARKED.

---

## Evaluation Criteria

Every model candidate must be evaluated on **all** of the following axes before a production switch decision:

| Axis | Metric | Acceptable Threshold |
|------|--------|---------------------|
| Accuracy | mAP50 on held-out test set | ≥ 0.70 (domain-specific) |
| Accuracy | mAP50-95 | ≥ 0.50 |
| Accuracy | False Positive Rate | ≤ 0.10 |
| Accuracy | False Negative Rate | ≤ 0.15 |
| Speed | Inference latency (ms) | ≤ 100ms CPU / ≤ 30ms GPU |
| Speed | FPS | ≥ 10fps CPU / ≥ 30fps GPU |
| Memory | Peak RAM usage | ≤ 4 GB CPU inference |
| License | Deployment restriction | No AGPL in commercial deployment |
| Complexity | Deployment effort | Adapter writable in < 1 day |
| Maintenance | Community/support | Active project |

---

## Model Evaluation Matrix

| Model | mAP50 | CPU FPS | GPU FPS | RAM | License | CPU Compat | GPU Compat | Status |
|-------|-------|---------|---------|-----|---------|-----------|-----------|--------|
| **YOLOv8n** (COCO pretrained) | 0.522 (COCO) | ~3-5 fps (i3) | NOT_BENCHMARKED | ~500MB | AGPL-3.0 ⚠️ | ✅ | ✅ | ACTIVE_BASELINE |
| YOLOv8n (domain fine-tuned) | NOT_DONE | — | — | — | AGPL-3.0 ⚠️ | ✅ | ✅ | NOT_DONE |
| RTMDet-tiny | NOT_BENCHMARKED | — | — | — | Apache-2.0 ✅ | ✅ | ✅ | CANDIDATE |
| YOLOv8n via ONNX Runtime | NOT_BENCHMARKED | — | — | — | MIT ✅ | ✅ | ✅ | CANDIDATE |
| YOLOv8n via OpenVINO | NOT_BENCHMARKED | — | — | — | Apache-2.0 ✅ | Intel | Limited | CANDIDATE |
| YOLOv8n via TensorRT | NOT_BENCHMARKED | — | N/A w/o GPU | — | NVIDIA EULA | ❌ | ✅ | PLANNED |
| NVIDIA TAO DetectNet | NOT_DONE | — | — | — | NVIDIA EULA | ❌ | ✅ | PLANNED |

> ⚠️ **AGPL-3.0 License Note**: Ultralytics YOLOv8 is AGPL-3.0. For non-open-source or commercial deployment, a commercial license from Ultralytics is required. Check `docs/THIRD_PARTY_LICENSES.md`.

---

## How to Add a Model Candidate

1. Implement `DetectionEngine` ABC in `services/detection/`:
   ```python
   class MyModelAdapter(DetectionEngine):
       def detect(self, frame) -> DetectionBatch: ...
   ```

2. Create evaluation script:
   ```python
   # ml/evaluation/evaluate_model.py
   # Runs inference on ml/datasets/test/ and computes metrics
   ```

3. Run on held-out test set (NEVER train on test set):
   ```bash
   python ml/evaluation/evaluate_model.py --adapter MyModelAdapter --test-dir ml/datasets/test/
   ```

4. Fill in all columns of the matrix above with actual measured values.

5. Update `ml/registry/model_registry.yaml`.

---

## Optional Research Tools (NOT in Production Pipeline)

| Tool | Purpose | Status |
|------|---------|--------|
| SAM 2 (Meta) | Segmentation-based annotation assistance | Research only |
| Grounding DINO | Zero-shot detection for new class exploration | Research only |

These tools require significant VRAM and are not suitable for the current CPU-only deployment.
They are useful for dataset curation and annotation, not production inference.

---

## Domain Evaluation Gaps

The current baseline (YOLOv8n, COCO pretrained) has NOT been evaluated on:
- Border surveillance camera angles
- Night / low-light conditions
- Rain / fog / adverse weather
- Partial occlusion (vehicles behind fence)
- Small object detection at distance
- Vehicle types specific to border context (tractors, motorcycles, military vehicles)

These gaps must be addressed with domain-specific labeled data before claiming production accuracy.
