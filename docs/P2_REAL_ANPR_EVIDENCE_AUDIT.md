# IBVAP P2 Real ANPR Evidence Audit Report

**Audit Date**: September 5, 2026  
**Auditor**: Antigravity AI Engineering Agent  
**Environment**: Windows 11 (AMD64), Intel i3 CPU, 12GB RAM, CPU-only Execution  
**Video Asset Under Audit**: `data/raw/test_video.mp4` (authorized local test video)  
**Evidence Artifacts Inspected**:
- `docs/evidence/p2/` (Screenshots `01_dashboard_loaded.png` through `10_websocket_recovered.png`)
- `docs/P2_AUTOMATED_ACCEPTANCE_REPORT.md`
- `data/ibvap_dev.db` (SQLite database)
- `scripts/browser_acceptance.py`

---

## 1. Executive Summary & Verdict

This is an **evidence-only validation audit** evaluating whether real license plate recognition occurred on genuine vehicles present in `data/raw/test_video.mp4`.

### Core Audit Finding:
1. **Vehicle Detection & Subclass Analytics**: **VERIFIED**  
   YOLOv8n reliably detects real vehicles in `data/raw/test_video.mp4` (`class_name="vehicle"`, `subclass="car"`). Real vehicle bounding boxes and persistent tracking IDs (e.g., `CAR #8`, `CAR #5`) are actively displayed on the live dashboard canvas overlay.
2. **Plate Localization & Text OCR on `test_video.mp4`**: **NOT VERIFIED**  
   The authorized video is a wide-angle CCTV surveillance clip recorded at `592x360` resolution. All vehicles in the scene are distant background objects occupying between `19x14` and `75x41` pixels total. At this distance and resolution, license plates are optically sub-pixel (~$8 \times 3$ pixels or less) and completely illegible. Consequently, the heuristic `ContourPlateDetector` correctly finds no valid plate candidates, and the pipeline correctly marks plates as `PLATE: UNREADABLE`.
3. **Database Records Inspection**:  
   The 5 records currently present in the SQLite `anpr_observations` table were generated exclusively by the automated integration test fixture `test_anpr_db_persistence_and_sha256` (`CAM-TEST`, track 999, synthetic test payload). **Zero** plate readings were persisted from the live video stream.
4. **Browser Acceptance Test Flaw Identified**:  
   In `scripts/browser_acceptance.py`, Step 4 unconditionally reported `PASS` for `ANPR Pipeline & Consensus` without asserting that a real plate was recognized or verified from the live video stream.

```
REAL_PLATE_RECOGNITION: NOT_VERIFIED
```

---

## 2. Granular Evidence Breakdown

| Item | Requirement | Evidence Found | Status |
| :--- | :--- | :--- | :---: |
| **1. Vehicle Detection** | Real vehicle detected in `test_video.mp4` | YOLOv8n detected 129 vehicle instances across sample frames. Visible in `06_vehicle_anpr_section.png` (`CAR #8`, `CAR #5`). | **VERIFIED** |
| **2. Persistent Vehicle Track ID** | Vehicle assigned persistent ID with trajectory | `FallbackIoUTracker` assigned IDs (`#5`, `#8`, `#11`). Visible in SVG live overlay pill. | **VERIFIED** |
| **3. Real Plate Localization** | Bounding box of plate localized on vehicle crop | All detected vehicles are distant ($19 \times 14$ to $75 \times 41$ px). Minimum readable plate width is 35px. No plate localized. | **NOT VERIFIED** |
| **4. Actual OCR Text** | Legitimate plate characters read from real vehicle | Sub-pixel resolution renders text optically absent. OCR returns `UNREADABLE`. | **NOT VERIFIED** |
| **5. OCR Confidence** | Confidence score $\ge 0.50$ from real plate crop | No OCR read performed due to absence of localized plate candidate. | **NOT VERIFIED** |
| **6. Multi-Frame Consensus** | $\ge 2$ consistent matching readings on same track | Since no text was read, no consensus could form. | **NOT VERIFIED** |
| **7. STABLE_VERIFIED State** | Track transitioned to `STABLE_VERIFIED` | Live stream tracks remained in `UNREADABLE` status. | **NOT VERIFIED** |
| **8. Dashboard Rendering** | ANPR pill rendered on live video canvas | `06_vehicle_anpr_section.png` visually confirms the pill rendered directly beneath vehicle bounding boxes: `PLATE: UNREADABLE`. | **VERIFIED (as UNREADABLE)** |
| **9. Database Persistence** | Authoritative record in `anpr_observations` from live stream | SQLite table contains 5 rows, all originating from unit tests (`CAM-TEST`, track 999). Live stream produced 0 rows. | **NOT VERIFIED** |
| **10. Evidence Image + SHA-256** | Real plate crop JPEG and SHA-256 hash saved | No live ANPR evidence files exist in `data/evidence/`. | **NOT VERIFIED** |

---

## 3. Video Asset Resolution Analysis (`data/raw/test_video.mp4`)

- **Video Container**: MP4 (H.264 / AVC)
- **Native Dimensions**: `592 x 360` pixels
- **Frame Rate**: `30.0 FPS`
- **Total Frames / Duration**: `898 frames (29.93 seconds)`
- **Camera Perspective**: High-elevation wide-angle surveillance camera overlooking Times Square / pedestrian plaza.
- **Vehicle Scale**:
  - Distance: Vehicles are in the far background on cross-streets.
  - Typical Bounding Box: `[0.755, 0.465, 0.838, 0.522]` $\rightarrow$ Width: `49 px`, Height: `22 px`.
  - Max Vehicle Dimensions: `75 px` width $\times$ `41 px` height.
  - Theoretical Plate Region: Under 5% of vehicle area $\rightarrow$ $\approx 6 \times 3$ pixels.
- **Physical Feasibility**: Optical recognition of alphanumeric characters requires at least 20–30 vertical pixels across the plate lettering (Shannon-Nyquist sampling threshold for character legibility). In this video, individual letters are smaller than a single sensor pixel. No ANPR engine (open-source or proprietary) can decipher text that does not physically exist in the captured pixels.

---

## 4. Inspection of `scripts/browser_acceptance.py`

In `scripts/browser_acceptance.py`, Step 4 was evaluated:
```python
results["ANPR Pipeline & Consensus"] = "PASS"
details["ANPR Pipeline & Consensus"] = f"ContourPlateDetector + OCREngine with multi-frame consistency enforcement & anti-hallucination"
```
### Defect Analysis:
- The script verified that the ANPR pipeline code was configured and that vehicles were tracked.
- It also read `/api/v1/anpr/observations` and noted that records existed (which were left behind by unit test executions in the development DB).
- **It did not require a real plate to be read from `test_video.mp4`**.
- As required by the prompt instructions ("Any exception or missing evidence must result in NOT_VERIFIED or FAIL. Never convert exceptions into PASS"), claiming `PASS` for real ANPR recognition was inaccurate.

---

## 5. Non-Hallucination Compliance Confirmation

The pipeline correctly obeyed the mandatory safety rules:
1. **No Hallucination**: The system did **not** hallucinate or invent a fake plate string (e.g. `DL01AB1234`) on `test_video.mp4`.
2. **Correct Fallback**: Vehicles were detected, tracked with subclass badges, and their ANPR status was honestly rendered as `PLATE: UNREADABLE` on the live video stream (visible in `docs/evidence/p2/06_vehicle_anpr_section.png`).
3. **No False Alarms**: The pipeline never triggered a false security alarm merely because a vehicle was present or had an unreadable plate.

---

## 6. Audit Verdict

```
REAL_PLATE_RECOGNITION: NOT_VERIFIED
```
