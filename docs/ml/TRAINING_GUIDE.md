# TRAINING_GUIDE.md — IBVAP Model Training & Fine-Tuning Runbook

**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Target Architecture:** YOLOv8n / YOLOv8s Detection Network  
**Supported Compute:** CPU (Development Fallback) / NVIDIA Jetson / CUDA GPU (Production)  

---

## 1. Overview

The IBVAP training pipeline fine-tunes deep convolutional/vision transformer object detectors for border surveillance perimeters. It provides deterministic reproducibility, automated validation gating, and integration with the IBVAP Model Registry.

---

## 2. Prerequisites

1. Populated and validated dataset in `dataset/` (`train`, `val`, `test` splits).
2. Clean audit report from `python scripts/validate_dataset.py`.
3. Installed ML dependencies (`ultralytics`, `torch`, `torchvision`).

---

## 3. Execution Commands

### 3.1 Standard Development Training (CPU Mode)

```powershell
python -m ml.training.train `
    --model yolov8n.pt `
    --data dataset/dataset.yaml `
    --epochs 50 `
    --batch 16 `
    --imgsz 640 `
    --device cpu `
    --name ibvap_border_candidate
```

### 3.2 Production Training (NVIDIA GPU / CUDA)

```powershell
python -m ml.training.train `
    --model yolov8s.pt `
    --data dataset/dataset.yaml `
    --epochs 100 `
    --batch 32 `
    --imgsz 640 `
    --device 0 `
    --name ibvap_border_prod_v1
```

---

## 4. Hyperparameter Guidelines for Fixed CCTV Cameras

Fixed border cameras operate with specific visual constraints:
- **Degrees (Rotation):** `5.0` (Fixed mounts rarely rotate significantly).
- **Flipping:** `flipud: 0.0` (Never flip upside down); `fliplr: 0.5` (Horizontal flips are valid).
- **Scale:** `0.5` (Captures targets at close, medium, and distant fence boundaries).
- **Color Jitter (HSV):** `hsv_v: 0.4` (Simulates dawn, dusk, and illumination shifts).

---

## 5. Automated Gate Evaluation & Artifact Output

Upon completion of the training epochs:
1. Weights are saved to `ml/runs/<experiment_name>/weights/best.pt`.
2. Validation metrics (`mAP50`, `mAP50-95`, `precision`, `recall`, `latency`) are evaluated.
3. The `ValidationGate` evaluates the candidate against baseline requirements.
4. Model metadata is saved to `ml/registry/model_registry.yaml` with status `CANDIDATE` or `VALIDATED`.
5. Candidate models **DO NOT** replace production weights automatically until approved.
