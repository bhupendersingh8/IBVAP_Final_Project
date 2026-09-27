"""
Unit & Integration Tests for Eye Blink Liveness & Anti-Spoofing (SIH PS-26187)
==============================================================================
Tests:
- Eye openness computation (open vs. closed discrimination)
- Temporal state machine for natural blink detection (Open -> Closed -> Open)
- Photo presentation attack detection (static variance thresholding)
- Integration with AuthorizedPersonnelManager.verify_track_person()
"""

import os
import tempfile
import json
import cv2
import numpy as np
import pytest

from services.auth_personnel.blink_detector import (
    EyeBlinkLivenessDetector,
    TrackBlinkState,
    LivenessResult
)
from services.auth_personnel.personnel_manager import (
    AuthorizedPersonnelManager,
    PersonnelVerificationResult
)


def make_synthetic_eye(state="open"):
    """Generates synthetic 32x24 eye patch in open or closed state."""
    patch = np.full((24, 32, 3), 180, dtype=np.uint8)  # skin tone
    if state == "open":
        # White sclera
        cv2.ellipse(patch, (16, 12), (10, 6), 0, 0, 360, (235, 235, 235), -1)
        # Dark pupil and iris
        cv2.circle(patch, (16, 12), 4, (30, 25, 25), -1)
        # Eyelid margins
        cv2.line(patch, (6, 7), (26, 7), (40, 35, 30), 2)
        cv2.line(patch, (7, 17), (25, 17), (90, 80, 75), 1)
    else:
        # Smooth skin with thin closed horizontal seam
        cv2.line(patch, (6, 13), (26, 13), (120, 110, 105), 1)
    return patch


def test_eye_openness_score_discrimination():
    detector = EyeBlinkLivenessDetector()
    open_eye = make_synthetic_eye(state="open")
    closed_eye = make_synthetic_eye(state="closed")

    score_open = detector.compute_eye_openness(open_eye)
    score_closed = detector.compute_eye_openness(closed_eye)

    assert score_open > score_closed
    # Closure must cause at least a 50% drop
    drop = (score_open - score_closed) / max(1.0, score_open)
    assert drop >= 0.50, f"Expected drop >= 50%, got {drop*100:.1f}%"


def test_temporal_blink_cycle_detection():
    detector = EyeBlinkLivenessDetector(min_blinks_required=1)
    track_id = 101

    # Simulate sequence: 8 open frames -> 2 closed frames -> 8 open frames
    open_eye = make_synthetic_eye(state="open")
    closed_eye = make_synthetic_eye(state="closed")

    # Empty frame with dummy person bbox
    dummy_frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    bbox = {"x1": 0.2, "y1": 0.1, "x2": 0.6, "y2": 0.8}

    # Helper to mock extract_eye_patches
    orig_extract = detector.extract_eye_patches

    # 1. First 8 frames: Eyes are open -> Awaiting blink
    detector.extract_eye_patches = lambda *args, **kwargs: [open_eye, open_eye]
    for _ in range(8):
        res = detector.update_track(track_id, dummy_frame, bbox)
    assert res.blink_count == 0
    assert res.is_live is False
    assert res.liveness_status == "AWAITING_BLINK"

    # 2. Next 2 frames: Eyes close (blink dip)
    detector.extract_eye_patches = lambda *args, **kwargs: [closed_eye, closed_eye]
    for _ in range(2):
        res = detector.update_track(track_id, dummy_frame, bbox)

    # 3. Next 3 frames: Eyes re-open -> Blink verified!
    detector.extract_eye_patches = lambda *args, **kwargs: [open_eye, open_eye]
    for _ in range(3):
        res = detector.update_track(track_id, dummy_frame, bbox)

    assert res.blink_count >= 1
    assert res.is_live is True
    assert res.liveness_status == "VERIFIED_LIVE"


def test_static_photo_spoof_detection():
    detector = EyeBlinkLivenessDetector(min_blinks_required=1, spoof_frame_threshold=25)
    track_id = 202

    static_eye = make_synthetic_eye(state="open")
    dummy_frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    bbox = {"x1": 0.2, "y1": 0.1, "x2": 0.6, "y2": 0.8}

    detector.extract_eye_patches = lambda *args, **kwargs: [static_eye, static_eye]

    # Present completely static photo for 35 frames (zero natural blink or variation)
    res = None
    for _ in range(35):
        res = detector.update_track(track_id, dummy_frame, bbox)

    assert res is not None
    assert res.blink_count == 0
    assert res.is_live is False
    assert res.liveness_status == "STATIC_SPOOF_SUSPECTED"


def test_authorized_personnel_gated_by_blink():
    tmp = tempfile.mkdtemp()
    img_dir = os.path.join(tmp, "images")
    os.makedirs(img_dir, exist_ok=True)

    # Registered authorized officer
    auth_img = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.circle(auth_img, (100, 90), 50, (200, 180, 160), -1)
    cv2.circle(auth_img, (80, 80), 8, (40, 30, 20), -1)
    cv2.circle(auth_img, (120, 80), 8, (40, 30, 20), -1)
    cv2.imwrite(os.path.join(img_dir, "officer_live.jpg"), auth_img)

    registry_data = [
        {
            "id": "AUTH-LIVE-001",
            "name": "Inspector Rajesh",
            "role": "Border Commander",
            "department": "BSF Sector Alpha",
            "image_file": "officer_live.jpg",
            "status": "authorized"
        }
    ]
    with open(os.path.join(tmp, "authorized_people.json"), "w", encoding="utf-8") as f:
        json.dump(registry_data, f)

    mgr = AuthorizedPersonnelManager(data_dir=tmp)

    full_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    full_frame[50:250, 50:250] = auth_img
    bbox = {"x1": 50 / 640, "y1": 50 / 480, "x2": 250 / 640, "y2": 250 / 480}
    track_id = 999

    open_eye = make_synthetic_eye("open")
    closed_eye = make_synthetic_eye("closed")

    # Step 1: Matching face observed without blink -> Clearance pending / awaiting blink
    mgr.blink_detector.extract_eye_patches = lambda *args, **kwargs: [open_eye, open_eye]
    for _ in range(5):
        res = mgr.verify_track_person(full_frame, bbox, track_id)

    assert res.person_id == "AUTH-LIVE-001"
    assert res.name == "Inspector Rajesh"
    assert res.is_authorized is False  # Clearance gated until blink!
    assert res.liveness_status == "AWAITING_BLINK"

    # Step 2: Officer blinks eyes (2 frames closed, then reopens)
    mgr.blink_detector.extract_eye_patches = lambda *args, **kwargs: [closed_eye, closed_eye]
    mgr.verify_track_person(full_frame, bbox, track_id)
    mgr.verify_track_person(full_frame, bbox, track_id)

    mgr.blink_detector.extract_eye_patches = lambda *args, **kwargs: [open_eye, open_eye]
    res_after = mgr.verify_track_person(full_frame, bbox, track_id)

    # Step 3: Verified live -> Full clearance granted!
    assert res_after.is_authorized is True
    assert res_after.is_live is True
    assert res_after.blink_count >= 1
    assert res_after.liveness_status == "VERIFIED_LIVE"


def test_track_cleanup():
    detector = EyeBlinkLivenessDetector()
    track_id = 303
    dummy_frame = np.full((100, 100, 3), 120, dtype=np.uint8)
    detector.update_track(track_id, dummy_frame)
    assert track_id in detector.track_states

    detector.cleanup_track(track_id)
    assert track_id not in detector.track_states
