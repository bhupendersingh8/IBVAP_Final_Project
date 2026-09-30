# ANPR Dataset Directory Specification

**Status:** ARCHITECTURALLY SEPARATED (Phase B Requirement 10)  
**Governance Rule:** Under NO circumstances may license plate annotations be mixed into the standard 5-class object detection dataset (`person`, `car`, `motorcycle`, `truck`, `bus`).

---

## 1. Directory Layout

```
dataset/anpr/
├── images/           # High-resolution vehicle crops containing readable plates
├── labels/           # Two-stage annotations (plate bounding box + OCR text ground truth)
└── metadata/
    └── plates.jsonl  # Ground-truth plate metadata schema
```

---

## 2. Annotation Schema

License plate datasets require a two-stage annotation schema:

1. **Plate Detection Bounding Box (`labels/<image_stem>.txt`)**:
   Standard normalized coordinates:
   ```
   0 <center_x> <center_y> <width> <height>
   ```
   Class `0` is strictly reserved for `license_plate`.

2. **OCR Ground Truth (`metadata/plates.jsonl`)**:
   ```json
   {
     "image_id": "VEHICLE_CAM04_0001",
     "plate_text": "DL01AB1234",
     "state_code": "DL",
     "optical_width_px": 84,
     "aspect_ratio": 3.42,
     "readability": "CLEAR",
     "lighting": "DAY"
   }
   ```

---

## 3. Anti-Hallucination & Resolution Threshold

- Optical plates must have an on-sensor width of $\ge 35$ pixels and aspect ratio between $2.0$ and $5.5$.
- Fake or hallucinated plate strings must **never** be committed.
