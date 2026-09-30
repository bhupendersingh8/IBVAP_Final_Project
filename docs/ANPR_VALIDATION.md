# ANPR Validation Report

> **Status: PARTIAL** — Pipeline architecture PASS; real plate recognition NOT_VERIFIED.

---

## Pipeline Architecture (PASS)

```
Vehicle Detection (YOLOv8n)
    → vehicle bbox crop from frame
    → PlateDetector.detect_plate(crop) → plate_bbox, plate_crop
    → OCREngine.read_plate(plate_crop) → text, confidence
    → ANPRConsensusEngine.update(track_id, text, confidence)
    → PlateStatus: UNREADABLE / CANDIDATE / STABLE_VERIFIED
```

All components are modular and replaceable via the abstract interfaces.

### Component Status

| Component | Implementation | Status |
|-----------|---------------|--------|
| PlateDetector ABC | `services/anpr/plate_detector.py` | PASS |
| ContourPlateDetector | `services/anpr/plate_detector.py` | PARTIAL (baseline only) |
| OCREngine ABC | `services/anpr/ocr_adapter.py` | PASS |
| TesseractOCR | `services/anpr/ocr_adapter.py` | PARTIAL (requires tesseract binary) |
| PaddleOCR | `services/anpr/ocr_adapter.py` | PARTIAL (requires paddleocr install) |
| ANPRPipeline | `services/anpr/anpr_pipeline.py` | PASS |
| Multi-frame consensus | `services/anpr/anpr_pipeline.py` | PASS |
| Unit tests (9) | `tests/test_anpr.py` | PASS (with MockOCREngine) |

---

## Real Plate Recognition — NOT_VERIFIED

### Why NOT_VERIFIED

The current test video (`data/test_video.mp4`) is a 30-second clip that **does not contain a vehicle with a readable license plate**. Therefore:

- The ANPR pipeline runs and processes vehicle crops
- The plate detector finds candidate regions based on contour analysis
- The OCR engine returns low-confidence or empty results
- No plate reaches `STABLE_VERIFIED` status

This is **correct behavior** — the system honestly reports `UNREADABLE` rather than fabricating a plate number.

### Requirements for Real Validation

To produce a `STABLE_VERIFIED` plate reading, ALL of the following must be met:

| Requirement | Minimum Value |
|------------|--------------|
| Vehicle bbox area | > 10,000 pixels² |
| Plate crop size | > 60×15 pixels |
| OCR confidence | ≥ configured threshold (default 0.6) |
| Consistent readings | ≥ 3 frames with matching text |
| Text format match | Regex pattern (e.g., `[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}`) |

### What is Needed for Production ANPR Validation

1. **Authorized high-resolution test clip**: Vehicle with readable plate, camera at ≤ 15m distance, resolution ≥ 1080p
2. **Multiple frames**: Vehicle in frame for ≥ 3 seconds at capture FPS
3. **Known ground truth**: The actual plate number of the test vehicle
4. **Metrics to report**:
   - Correct reads / total attempts = Read Rate
   - Wrong reads / total reads = Error Rate
   - Time to `STABLE_VERIFIED` = Average consensus frames

---

## Multi-Frame Consensus (PASS — unit tested)

The consensus engine requires:
- Minimum 3 readings of the same text
- Confidence above threshold on each reading
- No conflicting high-confidence readings (marks `LOW_CONFIDENCE` if conflict)

This prevents false ANPR results from single-frame noise.

---

## Honest Demo Script (Monday)

**Show**:
- Vehicle detected in live stream (bounding box visible) ✅
- ANPR pipeline processing vehicle crop (log output) ✅
- `UNREADABLE` status when no readable plate present ✅ (correct behavior)
- Architecture diagram and multi-frame consensus logic ✅

**Do NOT claim**:
- Specific plate read unless demonstrated live with readable plate
- Production ANPR accuracy without proper test footage

---

## Production ANPR Upgrade Path

1. Replace `ContourPlateDetector` with specialized plate detection model (YOLOv8 trained on license plates)
2. Replace `TesseractOCR` with `PaddleOCR` (better accuracy on Indian plates)
3. Use NVIDIA TAO for domain-specific plate detector training
4. Test with Indian Regional Transport Office (RTO) plate format regex
5. Benchmark Read Rate, Error Rate on 100+ diverse plates
