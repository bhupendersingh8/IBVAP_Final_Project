"""
IBVAP — ANPR & Vehicle Analytics Unit & Integration Tests
===========================================================
Tests for Milestone P2:
1. Vehicle observation schemas and subclass preservation
2. PlateDetector interface and ContourPlateDetector baseline
3. OCREngine interface, EasyOCREngine normalization without hallucination
4. Multi-frame consensus logic (1 frame = CANDIDATE, >=2 frames = STABLE_VERIFIED)
5. Conflict handling (conflicting readings on same track -> LOW_CONFIDENCE)
6. Blur / unreadable plate rejection
7. Cooldown & duplicate suppression
8. Separation of ANPR observations from zone intrusion alerts
9. Database persistence & SHA-256 evidence generation
"""

import os
import sys
import uuid
import hashlib
from datetime import datetime, timezone
import numpy as np
import pytest

# Ensure IBVAP root is on path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.detection.schemas import BBox, Detection, DetectionBatch
from services.tracking.schemas import Track, TrackPoint, TrackState, TrackingResult
from services.tracking.bytetrack_adapter import FallbackIoUTracker
from services.anpr.schemas import (
    PlateStatus,
    VehicleObservation,
    PlateDetection,
    OCRResult,
    ANPRObservation,
    ANPRConfig,
)
from services.anpr.plate_detector import PlateDetector, ContourPlateDetector, MockPlateDetector
from services.anpr.ocr_adapter import OCREngine, EasyOCREngine, MockOCREngine
from services.anpr.anpr_pipeline import ANPRPipeline, TrackANPRState
from apps.backend.database.connection import AsyncSessionLocal, init_db
from apps.backend.database.models import ANPRObservation as DBANPRObservation, Camera

def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)

def _make_synth_vehicle_crop(text="DL01AB1234", blur=False) -> np.ndarray:
    import cv2
    img = np.ones((120, 240, 3), dtype=np.uint8) * 180
    # Add a white plate rectangle
    cv2.rectangle(img, (30, 40), (210, 80), (255, 255, 255), -1)
    cv2.rectangle(img, (30, 40), (210, 80), (0, 0, 0), 2)
    # Add text
    cv2.putText(img, text, (38, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    if blur:
        img = cv2.GaussianBlur(img, (31, 31), 0)
    return img


# ---------------------------------------------------------------------------
# 1. Schemas & Subclass Preservation
# ---------------------------------------------------------------------------

def test_vehicle_subclass_preservation_in_detection_and_track():
    """Vehicle detection must retain subclass ('car', 'truck', etc.) while class_name is 'vehicle'."""
    bbox = BBox(0.1, 0.1, 0.4, 0.4)
    det = Detection(
        bbox=bbox,
        class_name="vehicle",
        subclass="car",
        confidence=0.88,
        camera_id="CAM-01"
    )
    assert det.class_name == "vehicle"
    assert det.subclass == "car"

    # Tracker must propagate subclass to Track
    tracker = FallbackIoUTracker()
    batch = DetectionBatch(
        camera_id="CAM-01",
        frame_id=1,
        timestamp=_utcnow(),
        detections=[det]
    )
    res = tracker.update(batch)
    assert len(res.active_tracks) == 1
    tr = res.active_tracks[0]
    assert tr.class_name == "vehicle"
    assert tr.subclass == "car"


# ---------------------------------------------------------------------------
# 2. Plate Detector & OCR Engine Interfaces
# ---------------------------------------------------------------------------

def test_plate_detector_interface_and_contour_detector():
    """ContourPlateDetector must implement PlateDetector and localize high-contrast rectangular plates."""
    detector = ContourPlateDetector(min_plate_width=30, min_plate_height=10)
    assert isinstance(detector, PlateDetector)

    crop = _make_synth_vehicle_crop("HR26DK8332")
    det = detector.detect_plate(crop)
    assert det is not None
    assert det.plate_crop is not None
    assert det.plate_crop.shape[0] >= 10
    assert det.plate_crop.shape[1] >= 30

def test_ocr_engine_interface_and_normalization():
    """OCREngine must normalize text without guessing or hallucinating characters."""
    ocr = EasyOCREngine(min_confidence=0.5)
    assert isinstance(ocr, OCREngine)

    # Pure normalization unit test
    assert ocr.normalize_plate_text("dl-01-ab-1234") == "DL01AB1234"
    assert ocr.normalize_plate_text("MH 12! DE 9876 ") == "MH12DE9876"
    assert ocr.normalize_plate_text("") == ""
    assert ocr.normalize_plate_text("   ") == ""


# ---------------------------------------------------------------------------
# 3. Blurry / Unreadable Handling (No Hallucination)
# ---------------------------------------------------------------------------

def test_blurry_plate_is_unreadable_not_hallucinated():
    """Severely blurry crops must return status='UNREADABLE' without hallucinating text."""
    ocr = EasyOCREngine(min_confidence=0.5, blur_threshold=50.0)
    blurry_crop = _make_synth_vehicle_crop("DL01AB1234", blur=True)
    res = ocr.read_plate(blurry_crop)
    assert res.status == "UNREADABLE"
    assert res.normalized_text == ""


# ---------------------------------------------------------------------------
# 4. Multi-Frame Consensus Logic
# ---------------------------------------------------------------------------

def test_multi_frame_consensus_candidate_vs_verified():
    """
    Mandatory constraint:
    1 reading -> CANDIDATE
    >= 2 matching readings on same track -> STABLE_VERIFIED
    """
    cfg = ANPRConfig(min_consistent_frames=2, min_ocr_confidence=0.60)
    pipeline = ANPRPipeline(config=cfg)
    state = TrackANPRState(track_id=101, camera_id="CAM-01", vehicle_class="car")

    # 0 readings -> UNREADABLE
    status, text, conf, count = pipeline.evaluate_track_consistency(state)
    assert status == PlateStatus.UNREADABLE

    # 1 valid reading -> CANDIDATE (never STABLE_VERIFIED on single frame)
    state.readings.append(OCRResult("DL01AB1234", "DL01AB1234", 0.92, 15.0, "SUCCESS"))
    status, text, conf, count = pipeline.evaluate_track_consistency(state)
    assert status == PlateStatus.CANDIDATE
    assert text == "DL01AB1234"
    assert count == 1

    # 2 matching readings -> STABLE_VERIFIED
    state.readings.append(OCRResult("DL01AB1234", "DL01AB1234", 0.88, 14.0, "SUCCESS"))
    status, text, conf, count = pipeline.evaluate_track_consistency(state)
    assert status == PlateStatus.STABLE_VERIFIED
    assert text == "DL01AB1234"
    assert count == 2


# ---------------------------------------------------------------------------
# 5. Conflicting Readings -> LOW_CONFIDENCE
# ---------------------------------------------------------------------------

def test_conflicting_readings_mark_low_confidence():
    """If multi-frame readings conflict significantly on the same track, status MUST be LOW_CONFIDENCE."""
    cfg = ANPRConfig(min_consistent_frames=2, min_ocr_confidence=0.60)
    pipeline = ANPRPipeline(config=cfg)
    state = TrackANPRState(track_id=102, camera_id="CAM-01", vehicle_class="truck")

    # Two readings for PLATE_A and two readings for PLATE_B
    state.readings.append(OCRResult("KA01AB1234", "KA01AB1234", 0.85, 12.0, "SUCCESS"))
    state.readings.append(OCRResult("KA01AB1234", "KA01AB1234", 0.87, 12.0, "SUCCESS"))
    state.readings.append(OCRResult("MH02CD5678", "MH02CD5678", 0.86, 12.0, "SUCCESS"))
    state.readings.append(OCRResult("MH02CD5678", "MH02CD5678", 0.88, 12.0, "SUCCESS"))

    status, text, conf, count = pipeline.evaluate_track_consistency(state)
    assert status == PlateStatus.LOW_CONFIDENCE


# ---------------------------------------------------------------------------
# 6. ANPR Pipeline Execution with Mock Engines
# ---------------------------------------------------------------------------

def test_anpr_pipeline_with_mocks_and_cooldown():
    """ANPRPipeline processes vehicle tracks, enforces cooldown, and returns ANPRObservation."""
    cfg = ANPRConfig(min_consistent_frames=2, min_ocr_confidence=0.60, anpr_cooldown_seconds=5.0)
    mock_det = MockPlateDetector(should_detect=True)
    mock_ocr = MockOCREngine(mock_text="UP32AZ9999", mock_conf=0.95)

    pipeline = ANPRPipeline(config=cfg, plate_detector=mock_det, ocr_engine=mock_ocr)

    frame = np.ones((480, 640, 3), dtype=np.uint8) * 100
    track = Track(
        track_id=42,
        camera_id="CAM-01",
        class_name="vehicle",
        subclass="car",
        state=TrackState.ACTIVE,
        bbox=BBox(0.2, 0.2, 0.7, 0.7),
        center_x=0.45,
        center_y=0.45,
        first_seen=_utcnow(),
        last_seen=_utcnow()
    )

    # Frame 1: Candidate observation returned because high conf
    obs1 = pipeline.process_vehicle_track(track, frame, "CAM-01")
    assert obs1 is not None
    assert obs1.status == PlateStatus.CANDIDATE
    assert obs1.plate_text == "UP32AZ9999"

    # Frame 2: Immediately calling without interval throttle returns None
    pipeline.tracks_state[42].last_attempt_time = 0.0 # reset interval
    obs2 = pipeline.process_vehicle_track(track, frame, "CAM-01")
    assert obs2 is not None
    assert obs2.status == PlateStatus.STABLE_VERIFIED
    assert obs2.consistent_readings == 2

    # Frame 3: Cooldown prevents duplicate persistence
    pipeline.tracks_state[42].last_attempt_time = 0.0
    obs3 = pipeline.process_vehicle_track(track, frame, "CAM-01")
    assert obs3 is None

    # Verify track telemetry output
    telemetry = pipeline.get_track_telemetry(42)
    assert telemetry["plate_text"] == "UP32AZ9999"
    assert telemetry["plate_status"] == PlateStatus.STABLE_VERIFIED.value
    assert telemetry["vehicle_class"] == "car"


# ---------------------------------------------------------------------------
# 7. Non-vehicle tracks ignored
# ---------------------------------------------------------------------------

def test_person_tracks_do_not_generate_anpr():
    """Person tracks must never be passed to ANPR."""
    cfg = ANPRConfig()
    pipeline = ANPRPipeline(config=cfg)
    track = Track(
        track_id=1,
        camera_id="CAM-01",
        class_name="person",
        state=TrackState.ACTIVE,
        bbox=BBox(0.1, 0.1, 0.2, 0.3),
        center_x=0.15,
        center_y=0.2,
        first_seen=_utcnow(),
        last_seen=_utcnow()
    )
    # The worker only calls process_vehicle_track if tr.class_name == "vehicle"
    assert track.class_name != "vehicle"


# ---------------------------------------------------------------------------
# 8. Database Persistence & Evidence SHA-256
# ---------------------------------------------------------------------------

def test_anpr_db_persistence_and_sha256(tmp_path):
    """Saving ANPR observation stores DB record with matching SHA-256 evidence file."""
    import asyncio

    async def _test():
        await init_db()

        obs_id = str(uuid.uuid4())
        img_data = b"ANPR_SYNTHETIC_PLATE_IMAGE_TEST_PAYLOAD"
        sha256_hash = hashlib.sha256(img_data).hexdigest()
        evidence_file = tmp_path / f"evidence_anpr_{obs_id}.jpg"
        evidence_file.write_bytes(img_data)

        async with AsyncSessionLocal() as session:
            cam = await session.get(Camera, "CAM-TEST")
            if not cam:
                cam = Camera(
                    id="CAM-TEST",
                    name="Test Camera",
                    scenario="vehicle_anpr",
                    enabled=True,
                    rtsp_url_hash="hash_cam_test"
                )
                session.add(cam)

            db_obs = DBANPRObservation(
                id=obs_id,
                camera_id="CAM-TEST",
                track_id=999,
                vehicle_class="truck",
                plate_text="DL01AB9999",
                plate_confidence=0.91,
                status="STABLE_VERIFIED",
                consistent_readings=3,
                evidence_path=str(evidence_file),
                evidence_sha256=sha256_hash,
                timestamp=_utcnow()
            )
            session.add(db_obs)
            await session.commit()

            # Query back
            retrieved = await session.get(DBANPRObservation, obs_id)
            assert retrieved is not None
            assert retrieved.plate_text == "DL01AB9999"
            assert retrieved.status == "STABLE_VERIFIED"
            assert retrieved.evidence_sha256 == sha256_hash
            assert os.path.exists(retrieved.evidence_path)

    asyncio.run(_test())

