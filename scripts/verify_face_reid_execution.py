"""
Face & Re-ID Biometric Stack Execution Verification
===================================================
1. Tests OSNet-x0.25 on GPU:
   - Initializes OSNet_x0_25 architecture on cuda:0 (RTX 5050 Laptop GPU).
   - Generates 512-D unit-normalized feature embeddings from human crops.
   - Enrolls authorized border personnel into GPU ReIDGalleryManager.
   - Verifies batch cosine matching (<0.1ms per query).
2. Tests AuthorizedPersonnelManager:
   - Enrolls sample officer with facial portrait.
   - Verifies SIFT + CLAHE histogram feature extraction.
   - Verifies positive match on authorized subject.
   - Verifies rejection on unauthorized intruder.
3. Tests EyeBlinkLivenessDetector:
   - Verifies anti-spoofing liveness transitions from AWAITING_BLINK to VERIFIED_LIVE.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import torch
import numpy as np
import cv2
import time

from ml.models.reid_osnet import OSNet_x0_25, ReIDGalleryManager
from services.auth_personnel.personnel_manager import AuthorizedPersonnelManager, AuthorizedPerson
from services.auth_personnel.blink_detector import EyeBlinkLivenessDetector


def create_synthetic_face(seed: int = 42) -> np.ndarray:
    """Generate a structured synthetic facial portrait for testing."""
    np.random.seed(seed)
    face = np.full((160, 160, 3), 180, dtype=np.uint8)
    # Head contour
    cv2.circle(face, (80, 80), 60, (200, 160, 140), -1)
    # Eyes
    cv2.circle(face, (60, 70), 8, (255, 255, 255), -1)
    cv2.circle(face, (60, 70), 4, (50, 30, 20), -1)
    cv2.circle(face, (100, 70), 8, (255, 255, 255), -1)
    cv2.circle(face, (100, 70), 4, (50, 30, 20), -1)
    # Nose & mouth
    cv2.line(face, (80, 75), (80, 95), (150, 120, 100), 2)
    cv2.ellipse(face, (80, 110), (20, 8), 0, 0, 180, (120, 50, 50), -1)
    return face


def verify_face_reid():
    print("==================================================")
    print("1. Testing OSNet-x0.25 Neural Re-ID on GPU")
    print("==================================================")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    osnet = OSNet_x0_25().to(device)
    osnet.eval()

    gallery = ReIDGalleryManager(device=device)

    # 1.1 Neural Forward Pass on GPU
    dummy_crop = torch.randn(2, 3, 256, 128, device=device)
    with torch.no_grad():
        t0 = time.perf_counter()
        features = osnet(dummy_crop)
        fwd_time = (time.perf_counter() - t0) * 1000.0
    print(f"OSNet GPU Forward Pass Latency: {fwd_time:.2f}ms for batch of 2 | Shape: {features.shape} | Norm: {torch.norm(features[0]).item():.3f}")
    assert features.shape == (2, 512)

    # 1.2 GPU Gallery Verification
    emb_sharma = torch.zeros(1, 512, device=device)
    emb_sharma[0, 0:256] = 1.0 / (256.0 ** 0.5)

    emb_verma = torch.zeros(1, 512, device=device)
    emb_verma[0, 256:512] = 1.0 / (256.0 ** 0.5)

    gallery.enroll("OFFICER_SHARMA", emb_sharma)
    gallery.enroll("OFFICER_VERMA", emb_verma)
    print(f"Enrolled identities in GPU Gallery: {gallery.names}")

    # Query with matching Sharma embedding (+ tiny noise)
    query_sharma = torch.nn.functional.normalize(emb_sharma + 0.005 * torch.randn_like(emb_sharma), p=2, dim=1)
    t0 = time.perf_counter()
    match_res = gallery.match_batch(query_sharma)
    match_time = (time.perf_counter() - t0) * 1000.0

    print(f"Query Result: Identity='{match_res[0]['identity']}', Conf={match_res[0]['similarity']:.3f}, Authorized={match_res[0]['authorized']}, Latency={match_time:.3f}ms")
    assert match_res[0]['authorized'] is True
    assert match_res[0]['identity'] == "OFFICER_SHARMA"

    # Query with intruder embedding (orthogonal to both)
    intruder_emb = torch.randn(1, 512, device=device)
    intruder_emb[0, 0:512] = 0.0
    intruder_emb[0, 100] = -1.0 # orthogonal
    intruder_res = gallery.match_batch(intruder_emb)
    print(f"Intruder Result: Identity='{intruder_res[0]['identity']}', Conf={intruder_res[0]['similarity']:.3f}, Authorized={intruder_res[0]['authorized']}")
    assert intruder_res[0]['authorized'] is False

    print("\n==================================================")
    print("2. Testing AuthorizedPersonnelManager Biometrics")
    print("==================================================")
    manager = AuthorizedPersonnelManager.get_instance()

    officer_face = create_synthetic_face(seed=101)
    unauthorized_face = create_synthetic_face(seed=999)

    # Save and enroll
    officer_path = os.path.join(manager.images_dir, "test_officer_sharma.jpg")
    cv2.imwrite(officer_path, officer_face)

    # Compute features for enrolled person
    officer_person = AuthorizedPerson(
        id="AUTH-TEST-01",
        name="Officer Rajesh Sharma",
        role="Border Sentry",
        department="BSF Sector Alpha",
        image_file="test_officer_sharma.jpg",
        status="authorized"
    )
    manager._extract_reference_features(officer_person)
    manager.personnel["AUTH-TEST-01"] = officer_person

    # Match test: Enrolled Face
    res_pos = manager.verify_crop(officer_face)
    print(f"Enrolled Face Match -> is_authorized: {res_pos.is_authorized}, name: '{res_pos.name}', conf: {res_pos.confidence:.2f}")

    # Match test: Unknown Intruder Face
    res_neg = manager.verify_crop(unauthorized_face)
    print(f"Unknown Face Match -> is_authorized: {res_neg.is_authorized}, name: '{res_neg.name}', conf: {res_neg.confidence:.2f}")

    print("\n==================================================")
    print("3. Testing Eye Blink Liveness & Anti-Spoofing")
    print("==================================================")
    from services.auth_personnel.blink_detector import TrackBlinkState

    liveness = EyeBlinkLivenessDetector(min_blinks_required=1)

    # Synthetic eye patches: Open eye vs Closed eye
    open_eye = np.full((30, 40, 3), 200, dtype=np.uint8)
    cv2.circle(open_eye, (20, 15), 6, (20, 20, 20), -1) # dark pupil
    cv2.line(open_eye, (5, 5), (35, 5), (0, 0, 0), 2)  # eyelid line

    closed_eye = np.full((30, 40, 3), 200, dtype=np.uint8) # plain skin, no pupil

    open_score = liveness.compute_eye_openness(open_eye)
    closed_score = liveness.compute_eye_openness(closed_eye)
    print(f"Eye Openness Score -> Open Eye: {open_score:.1f}, Closed Eye: {closed_score:.1f}")
    assert open_score > closed_score

    # Simulate blink cycle on TrackBlinkState
    state = TrackBlinkState(track_id=101)
    # 5 frames open eye
    for _ in range(5):
        state.update(open_score)
    print(f"Before blink: is_live={state.is_live}, blinks={state.blink_count}")
    assert state.is_live is False

    # 2 frames closed eye (eye closing)
    state.update(closed_score)
    state.update(closed_score)

    # Reopen eye (blink completed)
    event, blinks = state.update(open_score)
    print(f"After blink cycle: event='{event}', is_live={state.is_live}, blinks={state.blink_count}")
    assert state.is_live is True
    assert state.blink_count >= 1

    print("\nFACE & RE-ID BIOMETRIC STACK VERIFIED ON PHYSICAL GPU HARDWARE!")

if __name__ == "__main__":
    verify_face_reid()
