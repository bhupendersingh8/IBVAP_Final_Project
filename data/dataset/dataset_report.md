# IBVAP Dataset Recovery & Quality Gate Audit Report

**Date:** Grand Finale Execution
**Platform:** Intelligent Border Video Analytics Platform (IBVAP)
**Dataset Directory:** `C:\Users\anmol\.gemini\antigravity\scratch\IBVAP_Final_Project\data\dataset`

---

## 1. Dataset Partition Summary

| Split | Image Count | Percentage | Annotations |
| :--- | :--- | :--- | :--- |
| **Train** | 113 | 69.8% | - |
| **Validation** | 24 | 14.8% | - |
| **Test** | 25 | 15.4% | - |
| **Total** | **162** | **100.0%** | **1182** |

---

## 2. Class Distribution (Ground Truth)

| Class ID / Name | Instance Count |
| :--- | :--- |
| `car` | 763 |
| `person` | 277 |
| `class_9` | 86 |
| `bus` | 52 |
| `class_8` | 3 |
| `class_4` | 1 |

---

## 3. Data Leakage Prevention Verification

- **Strategy:** Temporal Disjoint Partitioning.
- **Verification:** Images are ordered by stream sequence ID. Train partition contains blocks `[0..112]`, Validation contains `[113..136]`, and Test contains `[137..161]`.
- **Cross-Split Duplicate Check:** 0 overlapping frame IDs or adjacent frames between train and test.
- **Format:** Darknet / Ultralytics YOLO normalized bounding boxes with `data.yaml`.
