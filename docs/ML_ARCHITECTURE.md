# ML Architecture

---

## Detection Engine Interface

All detection models implement the `DetectionEngine` ABC:

```python
# services/detection/detection_engine.py
class DetectionEngine(ABC):
    def detect(self, frame: np.ndarray) -> DetectionBatch: ...
    def detect_batch(self, frames: List[np.ndarray]) -> List[DetectionBatch]: ...
    def get_info(self) -> Dict[str, Any]: ...
```

### Current Adapters

| Adapter | File | Status | Backend |
|---------|------|--------|---------|
| `YOLOAdapter` | `yolo_adapter.py` | ✅ ACTIVE | Ultralytics YOLOv8n (AGPL-3.0) |
| `ONNXRuntimeAdapter` | `runtime_adapters.py` | 🔵 STUB | ONNX Runtime |
| `OpenVINOAdapter` | `runtime_adapters.py` | 🔵 STUB | Intel OpenVINO |
| `TensorRTAdapter` | `runtime_adapters.py` | 🔵 STUB | NVIDIA TensorRT |

Switching backends requires only changing the adapter — all downstream code is unchanged.

---

## ANPR Pipeline

```
Vehicle Detection (YOLOv8n)
    → vehicle bbox crop
    → PlateDetector (ContourPlateDetector baseline)
    → plate crop
    → OCREngine (PaddleOCR or TesseractOCR)
    → ANPRConsensusEngine (multi-frame voting)
    → PlateStatus: UNREADABLE / CANDIDATE / STABLE_VERIFIED
```

**Status: PARTIAL**
- Pipeline architecture: PASS (unit tested)
- Real plate recognition: NOT_VERIFIED (test video has no readable plates)
- Minimum for STABLE_VERIFIED: 3 consistent OCR readings, confidence ≥ threshold

**Never report a plate unless multi-frame consensus is met.**

---

## Tracking Architecture

```
DetectionBatch
    → FallbackIoUTracker.update()
    → Track objects (persistent IDs, trajectory, bbox history)
    → track_analytics.analyze_track()
    → TrackAnalytics (speed, direction, dwell_seconds, ground_trajectory)
```

| Feature | Status |
|---------|--------|
| Persistent track IDs | ✅ PASS |
| Trajectory (last 50 points) | ✅ PASS |
| Dwell time | ✅ PASS |
| Velocity (px/s) | ✅ PASS |
| 8-way direction | ✅ PASS |
| Track confidence | ✅ PASS |
| Cross-camera identity | ❌ NOT_DONE |

---

## Spatio-Temporal AI

```
Track + Zone data
    → RuleEngine (geometric: point-in-polygon, boundary crossing)
    → TemporalEventEngine:
        - ZONE_INTRUSION (cooldown: 30s, dedup: 5s)
        - LOITERING (dwell > 20s threshold)
        - REPEATED_ENTRY (entry count ≥ 3)
        - NIGHT_MOVEMENT (timestamp hour heuristic)
        - DIRECTION_VIOLATION (future: toward protected boundary)
    → Event: {camera_id, track_id, timestamp, event_type, confidence, reason, rule_version, severity}
```

---

## Model Registry

| Model | Version | Source | License | mAP50 (COCO) | Domain | Status |
|-------|---------|--------|---------|-------------|--------|--------|
| YOLOv8n | pretrained | Ultralytics | AGPL-3.0 | 0.522 | COCO-80 | ACTIVE_BASELINE |
| RTMDet | — | OpenMMLab | Apache-2.0 | — | COCO | EVALUATION_CANDIDATE |
| NVIDIA TAO DetectNet | — | NVIDIA | NVIDIA EULA | — | Custom | PLANNED |

**Custom border-domain model: NOT_DONE** — requires:
1. Dataset collection (`scripts/collect_dataset_frames.py`)
2. Labeling (CVAT / Label Studio)
3. Training (`ml/training/training_config.yaml`)
4. Evaluation on held-out test set
5. Registry entry in `ml/registry/model_registry.yaml`

---

## Training Pipeline (Architecture — NOT_DONE)

```
ml/datasets/
    raw/          ← frames from RTSP capture
    processed/    ← quality-filtered frames
    train/        ← labeled training split
    val/          ← labeled validation split
    test/         ← held-out test set (NEVER trained on)

ml/training/
    training_config.yaml   ← YOLOv8 training parameters

ml/evaluation/
    evaluation_report_template.md  ← metrics template

ml/registry/
    model_registry.yaml    ← model versioning
```

**Status: NOT_DONE** — no labeled data collected yet.
Use `scripts/collect_dataset_frames.py` to begin.

---

## ML Experiment Tracking (PLANNED)

| Tool | Adapter | Status |
|------|---------|--------|
| MLflow | `ml/adapters/mlflow_adapter.py` | PLANNED stub |
| DVC | `ml/adapters/dvc_adapter.py` | PLANNED stub |

Both adapters are stub implementations — install the tool and implement the adapter when a training run is ready.

---

## Night Analytics

**Status: PARTIAL**

| Feature | Status |
|---------|--------|
| CLAHE preprocessing | PARTIAL (code exists, not benchmarked) |
| Night classification by hour | PASS (TemporalEventEngine) |
| Dedicated low-light model | NOT_DONE |
| Night benchmark dataset | NOT_DONE |

See `docs/NIGHT_ANALYTICS.md`.

---

## Model Evaluation Matrix

See `docs/MODEL_EVALUATION.md` for full evaluation criteria.

Current evaluation summary:

| Model | CPU FPS | Accuracy | License | Notes |
|-------|---------|----------|---------|-------|
| YOLOv8n (baseline) | ~3-5 fps (i3) | mAP50=0.522 (COCO) | AGPL-3.0 | Active; not domain-fine-tuned |
| RTMDet | NOT_BENCHMARKED | — | Apache-2.0 | Evaluation candidate |
| ONNX Runtime | NOT_BENCHMARKED | — | MIT | Path for portability |
| OpenVINO | NOT_BENCHMARKED | — | Apache-2.0 | Intel CPU optimization |
| TensorRT | NOT_BENCHMARKED | — | NVIDIA EULA | Requires NVIDIA GPU |
