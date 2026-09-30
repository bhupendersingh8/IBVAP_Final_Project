# IBVAP ML Datasets

This directory contains datasets used for training and evaluating domain-specific computer vision models for border surveillance.

## Directory Structure

```
ml/datasets/
├── README.md               - This guide
├── dataset_manifest.yaml   - Formal manifest detailing classes, splits, and sources
├── train/                  - Training image frames and YOLO-format labels (.txt)
├── val/                    - Validation set for hyperparameter tuning
└── test/                   - Held-out test set (STRICTLY ISOLATED: NEVER TRAINED ON)
```

## Dataset Collection Guidelines

1. **Approved Video Sources**:
   - Frames captured directly from IBVAP cameras (`scripts/collect_dataset_frames.py`).
   - Public benchmark research datasets (e.g. LLVIP, ExDark, VisDrone) under permissible open-science licenses.
2. **Quality Gates**:
   - Laplacian variance sharpness > 100.
   - Mean intensity between 30 and 240 (discarding pure black or blown-out frames).
3. **Label Format**:
   - Standard YOLO text format: `<class_id> <x_center> <y_center> <width> <height>` (normalized to $[0, 1]$).
4. **Held-Out Test Set Rule**:
   - `test/` partition must remain unseen during all training and validation runs.
   - Accuracy benchmarks published in reports must originate exclusively from this split.
