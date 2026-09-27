# DATASET_GUIDE.md — IBVAP Dataset Engineering & Governance Guide

**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Standard Taxonomy:** 5 Classes (`person`, `car`, `motorcycle`, `truck`, `bus`)  
**Format:** Normalized YOLO Detection Format (`.txt`)  
**Storage Path:** `dataset/`  

---

## 1. Directory Structure

The IBVAP dataset is organized following standard YOLO detection layout:

```
dataset/
├── images/
│   ├── train/          # 70% Training images (.jpg, .png)
│   ├── val/            # 15% Validation images
│   └── test/           # 15% Independent hold-out test images
├── labels/
│   ├── train/          # Normalized bounding box coordinates (.txt)
│   ├── val/
│   └── test/
├── metadata/
│   ├── classes.yaml    # Class taxonomy and COCO mapping definitions
│   └── dataset_info.yaml # Dataset versioning, provenance, and license info
├── manifests/          # Audit manifests with SHA-256 digests per split
└── dataset.yaml        # Ultralytics/YOLO training configuration
```

---

## 2. Object Classes & Labeling Format

### 2.1 Defined Classes

| Class ID | Class Name | Description | Operational Significance |
|:---:|---|---|---|
| `0` | `person` | Human intruders, border guards, pedestrians | Primary intrusion threat |
| `1` | `car` | Sedans, SUVs, civilian light vehicles | Boundary approach detection |
| `2` | `motorcycle` | Two-wheelers, quad bikes | High-speed perimeter evasion |
| `3` | `truck` | Heavy goods vehicles, transport lorries | Logistics / supply breaches |
| `4` | `bus` | Passenger buses, utility transports | Mass movement tracking |

### 2.2 YOLO Annotation Syntax

Each text file corresponding to an image `image_name.jpg` must have the exact same base name `image_name.txt` and reside in `labels/<split>/`.

Each line represents a single bounding box:
```text
<class_id> <center_x> <center_y> <width> <height>
```
All coordinate values are normalized between `0.0` and `1.0` relative to image dimensions.

---

## 3. Anti-Fabrication & Data Governance Rules

1. **Zero Fake Detections or Synthetic Annotations**:
   - Never generate synthetic bounding boxes or fabricate label coordinates.
   - If an image contains no objects of interest, leave the corresponding `.txt` file empty (background frame).
2. **Authorized Data Sources Only**:
   - Authorized CCTV streams (e.g. `data/raw/test_video.mp4` / MediaMTX `CAM-01`).
   - Approved operational recordings from border surveillance stations.
   - Public open-access research benchmarks (e.g. VisDrone, LLVIP) when properly attributed.
   - **Prohibited**: Scraping copyrighted streams, unverified social media footage, or private civilian feeds.
3. **Data Protection**:
   - Raw video files and large datasets in `data/` and `dataset/` are gitignored to prevent accidental public leakage of sensitive operational footage.

---

## 4. DVC Dataset Versioning

IBVAP uses **Data Version Control (DVC)** principles to version large datasets alongside code:

1. **Dataset v1 (Initial Raw Outpost Baseline)**:
   - Extracted sharp frames from baseline outpost cameras.
   - Initial annotations for `person` and `vehicle`.
   - Tracked via `.dvc` pointer files.
2. **Dataset v2 (Adverse Weather & Night Augmentation)**:
   - Addition of rain, fog, and low-light / thermal infrared clips.
   - Hard negatives (wildlife, swaying trees) labeled as background.
   - Distinct DVC tag created: `git tag -a dataset-v2 -m "Added 500 low-light frames"`.
3. **Reproducibility Guarantee**:
   - Training runs record the exact `dataset_version` and DVC commit SHA in the model metadata.

---

## 5. Dataset Validation & Quality Control

Before any training run, run the automated validator:

```powershell
python scripts/validate_dataset.py --strict
```

The validator automatically inspects:
- Missing labels or orphan image files.
- Coordinate bounding box errors ($x, y, w, h 
otin [0, 1]$).
- Unknown or non-integer class IDs.
- Corrupted images unreadable by OpenCV.
- Duplicate images and cross-split leakage.

A complete audit report is automatically saved to `docs/ml/DATASET_AUDIT.md`.
