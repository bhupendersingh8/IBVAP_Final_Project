# ANPR High-Resolution Validation Dataset & Fixture Specification

**Directory:** `data/anpr_validation/`  
**Purpose:** Dedicated staging directory for high-resolution (1080p / 4K) vehicle gate CCTV recordings and ground-truth annotations to validate the ANPR OCR consensus pipeline.  
**Authoritative Status:** `REAL_ANPR_VALIDATION = NOT_VERIFIED` (Pending high-res camera footage)

---

## 1. Optical Readability Requirements

To prevent OCR hallucination, the IBVAP ANPR pipeline enforces the following physical and optical constraints:

1. **Plate Width in Pixels**: Minimum 35 pixels (recommended $\ge 80$ pixels for $\ge 95\%$ OCR accuracy).
2. **Plate Height in Pixels**: Minimum 12 pixels.
3. **Aspect Ratio Constraint**: Between $2.0$ and $5.5$.
4. **Lighting Conditions**: Adequate direct or supplemental IR illumination; maximum motion blur angle $< 15^\circ$.
5. **Frame Rate**: Minimum 10 FPS to allow multi-frame consensus across at least 2 consecutive detections on the same vehicle track.

---

## 2. Test Fixture Structure

```
data/anpr_validation/
├── README.md                           # This specification
├── footage/                            # 1080p authorized MP4 clips of vehicle gates
│   └── sample_gate_1080p.mp4           # (To be populated with authorized footage)
├── crops/                              # Cropped plate evaluation benchmarks
│   ├── DL01AB1234_clear.jpg            # Ground truth: DL01AB1234
│   └── HR26DQ5555_angled.jpg           # Ground truth: HR26DQ5555
└── ground_truth.json                   # Ground-truth mapping
```

---

## 3. Anti-Hallucination Policy

If an ingested vehicle crop does not meet the minimum optical resolution or character recognition confidence ($< 0.50$), the system outputs:
```json
{
  "status": "UNREADABLE",
  "plate_text": null,
  "plate_confidence": 0.0
}
```
Under NO circumstances does the system fabricate or guess random plate strings.
