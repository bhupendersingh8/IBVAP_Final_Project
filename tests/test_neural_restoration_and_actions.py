"""
Unit Tests for Zero-DCE++, Skeleton Actions, and Tactical VLM
=============================================================
"""

import pytest
import numpy as np
import torch

from ml.models.zero_dce import ZeroDCEPlusPlusRestorer
from services.preprocessing.night_enhancer import NightVisionEnhancer
from ml.models.skeleton_action import TemporalSkeletonActionRecognizer
from services.vision_language.local_tactical_vlm import LocalTacticalVLM


def test_zero_dce_enhancement():
    restorer = ZeroDCEPlusPlusRestorer()
    dark_frame = np.random.randint(0, 30, (240, 320, 3), dtype=np.uint8)
    enhanced, lat = restorer.enhance_frame(dark_frame)
    assert enhanced.shape == dark_frame.shape
    assert lat > 0.0
    assert enhanced.mean() >= dark_frame.mean()


def test_night_enhancer_with_zero_dce():
    enhancer = NightVisionEnhancer(use_neural=True)
    assert enhancer.use_neural is True
    dark_frame = np.random.randint(0, 25, (240, 320, 3), dtype=np.uint8)
    res = enhancer.enhance(dark_frame)
    assert res.is_night is True
    assert res.mode == "PITCH_NIGHT"
    assert res.frame.shape == dark_frame.shape


def test_skeleton_action_recognition_climbing():
    recognizer = TemporalSkeletonActionRecognizer()
    climb_kpts = np.zeros((17, 3), dtype=np.float32)
    climb_kpts[5] = [100, 100, 0.9] # L_SHOULDER
    climb_kpts[6] = [140, 100, 0.9] # R_SHOULDER
    climb_kpts[9] = [100, 40, 0.9]  # L_WRIST (raised above head)
    climb_kpts[10] = [140, 40, 0.9] # R_WRIST
    climb_kpts[11] = [110, 200, 0.9] # L_HIP
    climb_kpts[12] = [130, 200, 0.9] # R_HIP

    for _ in range(5):
        res = recognizer.update_track_pose(1, climb_kpts)
    assert res["action"] == "SCALING_FENCE"
    assert res["is_threat"] is True


def test_local_tactical_vlm():
    vlm = LocalTacticalVLM()
    crop = np.random.randint(50, 150, (224, 224, 3), dtype=np.uint8)
    rep = vlm.analyze_event(
        frame_crop=crop,
        event_type="RESTRICTED_FENCE_APPROACH",
        camera_id="CAM-01",
        pose_action="SCALING_FENCE"
    )
    assert "threat_level" in rep
    assert "sitrep" in rep
    assert "recommended_protocol" in rep
    assert rep["latency_ms"] > 0.0
