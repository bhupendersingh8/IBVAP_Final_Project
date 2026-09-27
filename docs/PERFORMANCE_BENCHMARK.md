# Performance Benchmark

> ⚠️ **IMPORTANT: No fabricated numbers.**
> All figures below are either measured on actual hardware or marked NOT_BENCHMARKED.
> GPU performance figures will remain NOT_BENCHMARKED until NVIDIA hardware is available.

---

## Hardware Under Test

| Component | Value |
|-----------|-------|
| CPU | Intel Core i3 (exact model varies) |
| RAM | 12 GB |
| GPU | None (CPU-only) |
| OS | Windows 11 AMD64 |
| Python | 3.14.4 |
| Model | YOLOv8n pretrained |

---

## Inference Performance (CPU)

| Metric | Value | Method | Condition |
|--------|-------|--------|-----------|
| Inference FPS (CAM-01) | ~3–5 fps | Observed from dashboard | YOLOv8n, 640px input, i3 CPU |
| Inference FPS (PHONE-CAM-01) | ~3–5 fps | Observed from dashboard | YOLOv8n, 960px input, i3 CPU |
| Last inference latency | reported live | `/api/v1/metrics` endpoint | Per-frame measurement |
| Avg inference latency | NOT_BENCHMARKED | Requires sustained run + logging | — |
| End-to-end alert latency | NOT_BENCHMARKED formally | Observed ~1–2s | Detection → WebSocket → Dashboard |

> FPS numbers are approximate observations, not controlled benchmarks.
> A controlled benchmark requires: fixed test video, isolated hardware, 1000+ frame measurement.

---

## Tracking Performance

| Metric | Value | Notes |
|--------|-------|-------|
| IoU tracker update time | < 5ms (estimated) | Python, pure CPU, N < 20 tracks |
| Max tracked objects | NOT_BENCHMARKED | No load test performed |

---

## API Performance

| Endpoint | Measured Latency | Method |
|----------|-----------------|--------|
| GET /health/live | < 5ms (typical) | Observed in dev |
| GET /api/v1/incidents | NOT_BENCHMARKED | — |
| GET /api/v1/evidence | NOT_BENCHMARKED | — |
| WebSocket alert push | NOT_BENCHMARKED formally | Observed ~1–2s total |

---

## Test Suite Performance

| Metric | Value |
|--------|-------|
| Test count | 54 |
| Test runtime | 3.6–40s (varies by YOLO model load) |
| All pass | ✅ YES |

---

## GPU Performance (NOT_BENCHMARKED)

The following metrics will be measured when NVIDIA GPU hardware is available:

| Metric | Target (unvalidated estimate) | Hardware |
|--------|------------------------------|---------|
| TensorRT inference FPS | 60–120+ fps | NVIDIA T4 |
| DeepStream multi-camera capacity | 16–32 × 1080p | NVIDIA T4 |
| GPU memory at 8 cameras | — | T4 (16 GB) |
| Jetson AGX Orin FPS | — | Jetson AGX Orin |
| End-to-end latency | < 200ms target | GPU path |

> These are unvalidated target estimates from NVIDIA documentation.
> **Report actual numbers only after running the benchmark methodology in `docs/NVIDIA_DEPLOYMENT.md`.**

---

## What a Proper Benchmark Requires

1. Fixed, reproducible test video (minimum 5 minutes, known content)
2. Isolated hardware (no background processes)
3. Warm-up period (first 100 frames discarded)
4. Minimum 1000 frames measured
5. Report: mean, median, p95, p99 latency; min/max/avg FPS
6. Hardware description in full
7. Software version (Python, YOLO, CUDA, TensorRT)
8. Conditions (resolution, batch size, precision FP32/FP16/INT8)
