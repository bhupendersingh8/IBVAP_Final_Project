# IBVAP Data & Curation Pipeline

**Version**: 1.0.0  
**Data Governance**: Defense / SIH Prototype Strict Compliance  

---

## 1. Directory Layout & Dataset Partitioning

The standardized dataset format follows standard YOLO object detection requirements:
```
dataset/
├── dataset.yaml
├── images/
│   ├── train/     # 70% of curated samples
│   ├── val/       # 20% validation split
│   └── test/      # 10% held-out test split
└── labels/
    ├── train/     # Normalized YOLO TXT: <class_id> <cx> <cy> <w> <h>
    ├── val/
    └── test/
```

### Classes
- `0`: `person` (border perimeter intruders, walkers, loiterers)
- `1`: `vehicle` (border patrol, civilian, logistics vehicles)

---

## 2. Live Frame Sampling & Quality Filtering

Frames can be extracted from phone cameras (`http://10.63.26.249:8080/video`) or standard CCTV RTSP streams:
```powershell
python scripts/collect_dataset_frames.py --source http://10.63.26.249:8080/video --split train --sample-interval 2.0 --max-frames 100
```

### Quality Assurance Criteria
- **Blur Filter**: Rejects frames where Laplacian variance is below 30.0.
- **Illumination Filter**: Excludes underexposed (<20 mean intensity) or overexposed (>240 mean intensity) frames.
- **Deduplication**: Enforces temporal sampling separation (minimum 2.0 seconds) to prevent visual redundancy.
