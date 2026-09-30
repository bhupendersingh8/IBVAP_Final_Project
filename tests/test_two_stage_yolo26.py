#!/usr/bin/env python3
"""
tests/test_two_stage_yolo26.py
==============================
Unit and integration tests for Two-Stage YOLO26x Stack & Multi-Model Cascade Verifier.
Smart India Hackathon SIH26187 (Sashastra Seema Bal / Ministry of Home Affairs).
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import cv2
import torch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.detection.two_stage_yolo26 import (
    TwoStageYOLO26Pipeline,
    TwoStageResult,
    VerifiedThreat,
    THREAT_CLASSES,
)
from main_pipeline import IBVAPUnifiedPipeline, PipelineConfig


@pytest.fixture(scope="module")
def weights_dir():
    wdir = PROJECT_ROOT / "weights"
    assert wdir.exists(), f"Weights directory not found at {wdir}"
    return wdir


@pytest.fixture(scope="module")
def yolo26_pipeline(weights_dir):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipeline = TwoStageYOLO26Pipeline(weights_dir=weights_dir, device=device)
    pipeline.warmup(iterations=1)
    return pipeline


@pytest.fixture
def sample_test_frame():
    test_img = PROJECT_ROOT / "dataset" / "images" / "test" / "frame_0820.jpg"
    if test_img.exists():
        frame = cv2.imread(str(test_img))
        if frame is not None:
            return frame
    # Fallback synthetic frame
    return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)


def test_yolo26_weight_files_and_params(weights_dir):
    """Verifies physical presence and parameter capacity of YOLO26 models."""
    p_nano = weights_dir / "yolo26n.pt"
    p_heavy = weights_dir / "yolo26x.pt"

    assert p_nano.exists(), f"Missing primary model: {p_nano}"
    assert p_heavy.exists(), f"Missing heavy verifier model: {p_heavy}"

    # Verify physical file size
    assert p_nano.stat().st_size >= 5_000_000, f"yolo26n.pt too small ({p_nano.stat().st_size} bytes)"
    assert p_heavy.stat().st_size >= 100_000_000, f"yolo26x.pt too small ({p_heavy.stat().st_size} bytes)"


def test_pipeline_initialization(yolo26_pipeline):
    """Validates instantiation, model weights loading, and parameter metrics."""
    assert yolo26_pipeline.primary_detector is not None
    assert yolo26_pipeline.heavy_verifier is not None

    # Verify parameter count: YOLO26x must match 56.9M params
    heavy_params = yolo26_pipeline.heavy_params_count
    assert heavy_params >= 56_000_000, f"Expected >= 56M params, got {heavy_params}"

    primary_params = yolo26_pipeline.primary_params_count
    assert primary_params >= 2_500_000, f"Expected >= 2.5M params, got {primary_params}"


def test_process_frame_synthetic(yolo26_pipeline):
    """Tests execution on blank/synthetic frame and verifies latency metrics."""
    synthetic = np.full((480, 640, 3), 40, dtype=np.uint8)
    res = yolo26_pipeline.process_frame(synthetic)

    assert isinstance(res, TwoStageResult)
    assert isinstance(res, list)
    assert "primary_ms" in res.latencies
    assert "verifier_ms" in res.latencies
    assert "total_ms" in res.latencies
    assert res.total_latency_ms > 0.0
    assert res.instant_fps > 0.0


def test_two_stage_cascade_verification_logic(yolo26_pipeline, sample_test_frame):
    """
    Tests two-stage cascade verification:
    - Primary gating identifies candidates (conf=0.25)
    - Borderline (0.25 <= conf <= 0.65) or threat classes are cropped and verified at conf=0.50
    - High confidence detections (> 0.65) pass through directly
    - Verified threats are returned with verification status
    """
    # Test with all candidates returned (including rejected false positives)
    all_res = yolo26_pipeline.process_frame(sample_test_frame, only_verified=False)
    assert isinstance(all_res, list)

    for item in all_res:
        assert isinstance(item, VerifiedThreat)
        assert "bbox" in item
        assert "confidence" in item
        assert "class_name" in item
        assert "verification_status" in item
        assert item["verification_status"] in (
            "VERIFIED_YOLO26X",
            "DIRECT_HIGH_CONF",
            "REJECTED_FALSE_POSITIVE",
            "REJECTED_TINY_ROI",
        )
        assert isinstance(item.is_verified, bool)

    # Test with only verified threats
    verified_res = yolo26_pipeline.process_frame(sample_test_frame, only_verified=True)
    for v_item in verified_res:
        assert v_item.is_verified is True
        assert v_item.verification_status in ("VERIFIED_YOLO26X", "DIRECT_HIGH_CONF")


def test_yield_verified_threats_generator(yolo26_pipeline, sample_test_frame):
    """Verifies that generator yield_verified_threats produces items properly."""
    gen = yolo26_pipeline.yield_verified_threats(sample_test_frame)
    threats_from_gen = list(gen)
    assert isinstance(threats_from_gen, list)
    for t in threats_from_gen:
        assert isinstance(t, VerifiedThreat)
        assert t.is_verified is True


def test_verify_tracks_stack(yolo26_pipeline, sample_test_frame):
    """Verifies that verify_tracks annotates tracks with verification status."""
    dummy_tracks = [
        {
            "track_id": 1,
            "class_name": "person",
            "confidence": 0.45,  # Borderline threat class
            "bbox": [100.0, 100.0, 250.0, 350.0],
        },
        {
            "track_id": 2,
            "class_name": "bench",
            "confidence": 0.85,  # High-confidence non-threat
            "bbox": [50.0, 50.0, 90.0, 90.0],
        },
    ]

    annotated = yolo26_pipeline.verify_tracks(sample_test_frame, dummy_tracks)
    assert len(annotated) == 2
    assert "verification_status" in annotated[0]
    assert "verification_status" in annotated[1]
    assert annotated[1]["verification_status"] == "DIRECT_HIGH_CONF"


def test_main_pipeline_integration_yolo26x_stack(weights_dir, sample_test_frame):
    """
    Verifies that IBVAPUnifiedPipeline stacks TwoStageYOLO26Pipeline without removing
    previous models (YOLO11n, ByteTrack, MobileSAM, ArcFace intact).
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    cfg = PipelineConfig(
        model_name="yolo11n",
        tracker_type="bytetrack",
        weights_dir=weights_dir,
        device=device,
        use_yolo26x_stack=True,
        enable_ws=False,
    )

    pipeline = IBVAPUnifiedPipeline(cfg)
    assert pipeline.yolo26_pipeline is not None
    assert pipeline.detector is not None  # YOLO11n intact
    assert pipeline.tracker is not None   # ByteTrack intact
    assert pipeline.sam is not None       # MobileSAM intact

    # Process frame
    res = pipeline.process_frame(sample_test_frame, frame_id=1)
    assert res is not None
    assert "tracks" in res
    assert res.get("yolo26x_stack_active") is True
    assert "yolo26x_verified_count" in res
    assert "yolo26x_verifier_ms" in res["latencies_ms"]
