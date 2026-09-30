# Night Analytics

> **Status: PARTIAL** — Preprocessing exists; dedicated night model and benchmark NOT_DONE.

---

## Current Capability

### 1. CLAHE Preprocessing (`services/preprocessing/clahe_enhancer.py`)
- Contrast Limited Adaptive Histogram Equalization applied to low-light frames
- Improves local contrast in dark regions
- Applied in the preprocessing pipeline before inference
- **Benchmark status: NOT_DONE** — no controlled night test footage measured

### 2. Night Classification (`services/rules/temporal_event_engine.py`)
- `_is_night(timestamp)` function classifies frames by IST hour
- Night window: 22:00–05:00 IST (approximate UTC conversion)
- Used by `TemporalEventEngine.process_night_movement()` to emit `NIGHT_MOVEMENT` events
- **Status: PASS** — heuristic implemented and unit-testable

### 3. Night Movement Events
- Any detection during night hours emits a `NIGHT_MOVEMENT` event with `severity=LOW`
- If combined with `ZONE_INTRUSION`, severity escalates to `HIGH`
- **Status: PARTIAL** — logic present; not yet wired to live inference path

---

## Limitations (Honest)

| Limitation | Impact |
|-----------|--------|
| No dedicated night-trained model | Detection accuracy degrades significantly below ~5 lux |
| No night benchmark dataset | Cannot report night mAP or FNR |
| Time-based heuristic only | No frame brightness analysis for night detection |
| CLAHE not benchmarked | Unknown actual improvement in detection rate |
| No IR / thermal support | Cannot detect through complete darkness |

---

## What is Needed for Production Night Analytics

1. **Night test dataset**: 500+ labeled frames from the actual deployment camera at night
2. **Low-light model fine-tuning**: YOLOv8 trained on night + day mixed dataset
3. **Brightness metric**: Compute mean pixel brightness per frame to trigger CLAHE adaptively
4. **Night benchmark**: mAP50, FPR, FNR measured on held-out night test set
5. **IR/thermal camera**: For complete darkness; requires different model architecture

---

## Planned Improvement Path

```
Step 1: Capture night frames from deployment cameras using:
        scripts/collect_dataset_frames.py --source rtsp://... --night-only

Step 2: Label with CVAT (person, vehicle classes)

Step 3: Add to ml/datasets/train/ and ml/datasets/val/

Step 4: Fine-tune YOLOv8n on night+day combined dataset:
        ml/training/training_config.yaml

Step 5: Evaluate on held-out ml/datasets/test/ night split

Step 6: Report metrics in docs/PERFORMANCE_BENCHMARK.md
```

---

## Demonstrated on Monday

- CLAHE preprocessing: architecture shown (PARTIAL)
- Night movement event: fires correctly during night hours (PASS — by timestamp)
- Night-specific model accuracy: NOT_VERIFIED — no night footage available

*Do NOT claim field-grade night accuracy without completing Steps 1–6 above.*
