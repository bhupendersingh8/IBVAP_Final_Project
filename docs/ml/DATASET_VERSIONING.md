# DATASET_VERSIONING.md — Dataset Lineage & Versioning Protocol

**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Governance Protocol:** Deterministic Manifest Tracking (DVC & Git Compatible)  

---

## 1. Versioning Architecture

Dataset versions are immutably cataloged in `dataset/metadata/dataset_info.yaml`:

```yaml
dataset_version: v1.0.0
status: POPULATED
created_at: '2026-09-06T12:00:00Z'
source_ids:
  - CAM-01-SECTOR-ALPHA
total_images: 450
annotated_images: 450
total_annotations: 1120
class_counts:
  0:person: 620
  1:car: 310
  2:motorcycle: 90
  3:truck: 80
  4:bus: 20
split_statistics:
  train: {images: 315, labels: 315, annotations: 784}
  val: {images: 67, labels: 67, annotations: 168}
  test: {images: 68, labels: 68, annotations: 168}
night_data_status: PASS
ir_data_status: NOT_AVAILABLE
manifest_sha256: 7f3a8b...
```

---

## 2. Sequence-Aware Split Guarantee

To eliminate temporal data leakage between training and validation:
- Video frames are partitioned using `sequence_aware` clustering in `DatasetSplitter`.
- Contiguous video sequences or entire camera source blocks are assigned as indivisible units to `train`, `val`, or `test`.
- The test set is held out permanently and is **never** exposed to hyperparameter selection or model training.
