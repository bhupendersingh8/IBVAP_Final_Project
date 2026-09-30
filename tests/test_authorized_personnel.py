"""
Unit and Integration Tests for Authorized Personnel Verification & Face Matching (SIH PS-26187)
"""
import os
import tempfile
import json
import cv2
import numpy as np
import pytest

from services.auth_personnel.personnel_manager import (
    AuthorizedPersonnelManager,
    AuthorizedPerson,
    PersonnelVerificationResult
)


@pytest.fixture
def temp_auth_dir():
    tmp = tempfile.mkdtemp()
    img_dir = os.path.join(tmp, "images")
    os.makedirs(img_dir, exist_ok=True)

    # Create sample authorized face
    auth_img = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.circle(auth_img, (100, 90), 50, (200, 180, 160), -1)
    cv2.circle(auth_img, (80, 80), 8, (40, 30, 20), -1)
    cv2.circle(auth_img, (120, 80), 8, (40, 30, 20), -1)
    cv2.imwrite(os.path.join(img_dir, "officer_test.jpg"), auth_img)

    # Create sample JSON
    registry_data = [
        {
            "id": "AUTH-TEST-001",
            "name": "Officer Test",
            "role": "Security Inspector",
            "department": "BSF Unit Alpha",
            "image_file": "officer_test.jpg",
            "status": "authorized"
        }
    ]
    with open(os.path.join(tmp, "authorized_people.json"), "w", encoding="utf-8") as f:
        json.dump(registry_data, f)

    yield tmp


def test_registry_loading(temp_auth_dir):
    mgr = AuthorizedPersonnelManager(data_dir=temp_auth_dir)
    people = mgr.get_all_personnel()
    assert len(people) >= 1
    p = people[0]
    assert p["id"] == "AUTH-TEST-001"
    assert p["name"] == "Officer Test"
    assert p["status"] == "authorized"


def test_authorized_person_matched(temp_auth_dir):
    mgr = AuthorizedPersonnelManager(data_dir=temp_auth_dir)
    # Query with the exact authorized photo
    auth_img = cv2.imread(os.path.join(temp_auth_dir, "images", "officer_test.jpg"))
    res = mgr.verify_crop(auth_img)
    assert res.is_authorized is True
    assert res.name == "Officer Test"
    assert res.person_id == "AUTH-TEST-001"
    assert res.confidence >= 0.80


def test_unauthorized_person_flagged(temp_auth_dir):
    mgr = AuthorizedPersonnelManager(data_dir=temp_auth_dir)
    # Dissimilar image (e.g. solid black or totally different colors)
    intruder_img = np.full((200, 200, 3), (10, 10, 150), dtype=np.uint8)
    res = mgr.verify_crop(intruder_img)
    assert res.is_authorized is False
    assert "Unauthorized" in res.name
    assert res.person_id is None


def test_dynamic_addition_and_hot_reload(temp_auth_dir):
    mgr = AuthorizedPersonnelManager(data_dir=temp_auth_dir)
    initial_count = len(mgr.get_all_personnel())

    # Add a new person programmatically
    new_face = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.circle(new_face, (100, 100), 60, (150, 200, 150), -1)
    _, enc = cv2.imencode(".jpg", new_face)

    res = mgr.add_authorized_person(
        name="Captain Vikram",
        role="Patrol Leader",
        department="Sector Bravo",
        image_bytes=enc.tobytes(),
        filename="capt_vikram.jpg"
    )
    assert res["status"] == "authorized"
    assert len(mgr.get_all_personnel()) == initial_count + 1

    # Verify that the new person is immediately matched
    verify_res = mgr.verify_crop(new_face)
    assert verify_res.is_authorized is True
    assert verify_res.name == "Captain Vikram"


def test_track_consensus_smoothing(temp_auth_dir):
    mgr = AuthorizedPersonnelManager(data_dir=temp_auth_dir, min_blinks=0)
    auth_img = cv2.imread(os.path.join(temp_auth_dir, "images", "officer_test.jpg"))

    # Frame with full coordinates
    full_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    full_frame[50:250, 50:250] = auth_img
    pbox = {"x1": 50/640, "y1": 50/480, "x2": 250/640, "y2": 250/480}

    # Verify across multiple frames for track #99
    r1 = mgr.verify_track_person(full_frame, pbox, track_id=99)
    r2 = mgr.verify_track_person(full_frame, pbox, track_id=99)
    assert r2.is_authorized is True
    assert r2.name == "Officer Test"
    assert r2.identity_state == "AUTHORIZED"


def test_phase10_four_identity_states(temp_auth_dir):
    """Verify Phase 10 explicit states: UNKNOWN, UNVERIFIED, AUTHORIZED, UNAUTHORIZED."""
    mgr = AuthorizedPersonnelManager(data_dir=temp_auth_dir, min_blinks=1)

    # 1. Unknown stranger
    unknown_img = np.zeros((100, 100, 3), dtype=np.uint8)
    res_unknown = mgr.verify_crop(unknown_img)
    assert res_unknown.is_authorized is False
    assert res_unknown.identity_state == "UNKNOWN"

    # 2. Officer image needing live blink -> UNVERIFIED (AWAITING_BLINK)
    auth_img = cv2.imread(os.path.join(temp_auth_dir, "images", "officer_test.jpg"))
    full_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    full_frame[50:250, 50:250] = auth_img
    pbox = {"x1": 50/640, "y1": 50/480, "x2": 250/640, "y2": 250/480}

    # First and second frame without blinks
    mgr.verify_track_person(full_frame, pbox, track_id=12)
    res_pending = mgr.verify_track_person(full_frame, pbox, track_id=12)
    assert res_pending.identity_state == "UNVERIFIED"
    assert res_pending.liveness_status == "AWAITING_BLINK"
    assert res_pending.is_authorized is False

    # 3. Same track with blinks satisfied -> AUTHORIZED
    mgr.blink_detector.track_blinks[12] = 2
    mgr.blink_detector.track_liveness[12] = True
    res_auth = mgr.verify_track_person(full_frame, pbox, track_id=12)
    assert res_auth.identity_state == "AUTHORIZED"
    assert res_auth.liveness_status == "VERIFIED_LIVE"
    assert res_auth.is_authorized is True

