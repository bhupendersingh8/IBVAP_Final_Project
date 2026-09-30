"""
tests/test_cooperative_orchestrator.py
======================================
Comprehensive test suite for Multi-Model Cooperative AI Stack & Registry.
Smart India Hackathon SIH PS ID: 26187 (Sashastra Seema Bal / Ministry of Home Affairs).
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.orchestrator.cooperative_registry import (
    CooperativeModelRegistry,
    CooperativeModelEntry,
    ModelRole,
    ModelOperationalStatus,
)
from services.orchestrator.cooperative_orchestrator import (
    CooperativeAIOrchestrator,
    CameraQualityAnalyzer,
    CooperativeCandidate,
    QualityAssessment,
)


@pytest.fixture(scope="module")
def registry():
    return CooperativeModelRegistry()


@pytest.fixture(scope="module")
def orchestrator(registry):
    return CooperativeAIOrchestrator(registry=registry, enable_gpu_models=False)


def test_registry_initialization_and_model_counts(registry):
    """Validates that registry initializes with all cooperative models."""
    models = registry.list_models()
    assert len(models) >= 12

    # Check key primary, secondary, specialist, and async models exist
    names = {m.name for m in models}
    assert "YOLO11n" in names
    assert "TwoStageYOLO26x" in names
    assert "RT-DETR-L" in names
    assert "ByteTrack" in names
    assert "MobileSAM" in names
    assert "YOLOv8n-Pose" in names
    assert "EasyOCR" in names
    assert "ArcFace-512D" in names
    assert "MiDaS-v2.1-Small" in names
    assert "LocalTacticalVLM" in names


def test_model_schema_integrity(registry):
    """Verifies that every registered model satisfies the defined schema."""
    models = registry.list_models()
    for m in models:
        assert isinstance(m.name, str) and len(m.name) > 0
        assert isinstance(m.architecture, str)
        assert isinstance(m.task, str)
        assert isinstance(m.license, str)
        assert isinstance(m.role, ModelRole)
        assert isinstance(m.status, ModelOperationalStatus)
        assert isinstance(m.trigger_condition, str)
        assert m.latency_ms >= 0.0
        assert m.vram_mb >= 0


def test_honest_ecosystem_status(registry):
    """Verifies honest reporting of model statuses (no faking 'all active')."""
    summary = registry.get_ecosystem_summary()
    assert "total_registered_models" in summary
    assert "by_role" in summary
    assert "by_status" in summary

    by_status = summary["by_status"]
    # Verify that not all models are falsely claimed as 'ACTIVE'
    assert "ACTIVE" in by_status
    assert "EVENT_TRIGGERED" in by_status
    assert "ASYNC" in by_status
    assert "AVAILABLE" in by_status


def test_camera_quality_analyzer_daylight():
    """Tests quality analyzer on normal daylight frame (bypass enhancement)."""
    normal_frame = np.full((480, 640, 3), 128, dtype=np.uint8)
    assessment = CameraQualityAnalyzer.analyze(normal_frame)
    assert assessment.is_low_light is False
    assert assessment.is_hazy is False


def test_camera_quality_analyzer_low_light():
    """Tests quality analyzer on low-light frame (triggers low-light enhancement)."""
    dark_frame = np.full((480, 640, 3), 25, dtype=np.uint8)
    assessment = CameraQualityAnalyzer.analyze(dark_frame)
    assert assessment.is_low_light is True


def test_cooperative_image_quality_gate(orchestrator):
    """Tests that orchestrator enhances low-light frame and leaves daylight frame untouched."""
    normal_frame = np.full((480, 640, 3), 128, dtype=np.uint8)
    out_normal, assess_normal = orchestrator.cooperate_image_quality(normal_frame)
    assert assess_normal.enhancement_applied == "NONE"

    dark_frame = np.full((480, 640, 3), 20, dtype=np.uint8)
    out_dark, assess_dark = orchestrator.cooperate_image_quality(dark_frame)
    assert assess_dark.enhancement_applied == "ADAPTIVE_CLAHE_LOW_LIGHT"


def test_cooperative_detection_confident_passthrough(orchestrator):
    """Verifies that high-confidence non-threat passes through without secondary gating."""
    frame = np.full((480, 640, 3), 100, dtype=np.uint8)
    candidates = [
        {"bbox": [10.0, 10.0, 60.0, 60.0], "confidence": 0.88, "class_name": "backpack", "class_id": 24}
    ]
    results = orchestrator.cooperate_detection(frame, candidates)
    assert len(results) == 1
    assert results[0].verification_status == "DIRECT_CONFIDENT"
    assert results[0].verifier_model is None


def test_cooperative_detection_uncertain_threat_gating(orchestrator):
    """Verifies that uncertain candidate or threat class cooperates with verifier."""
    frame = np.full((480, 640, 3), 100, dtype=np.uint8)
    candidates = [
        {"bbox": [50.0, 50.0, 150.0, 200.0], "confidence": 0.45, "class_name": "person", "class_id": 0}
    ]
    results = orchestrator.cooperate_detection(frame, candidates, two_stage_verifier=None)
    assert len(results) == 1
    # When no secondary verifier passed, flagged as unverified threat
    assert results[0].verification_status == "UNVERIFIED_THREAT"


def test_cooperative_segmentation_crawling_trigger(orchestrator):
    """Tests that MobileSAM segmentation is triggered on crawling aspect ratio."""
    frame = np.full((480, 640, 3), 100, dtype=np.uint8)
    # Crawling person: width=120, height=40 -> aspect ratio = 0.33 (< 0.65)
    candidate = CooperativeCandidate(
        bbox=[50.0, 100.0, 170.0, 140.0],
        confidence=0.55,
        class_id=0,
        class_name="person"
    )
    res = orchestrator.cooperate_segmentation(frame, [candidate], sam_instance=None)
    assert res[0].is_crawling is True


def test_cooperative_depth_and_distance_estimation(orchestrator):
    """Tests optical ground distance estimation without crashing."""
    frame = np.full((480, 640, 3), 100, dtype=np.uint8)
    candidate = CooperativeCandidate(
        bbox=[100.0, 100.0, 200.0, 400.0],  # Foot at y=400 in 480p frame (near)
        confidence=0.85,
        class_id=0,
        class_name="person"
    )
    res = orchestrator.cooperate_depth(frame, [candidate])
    assert res[0].estimated_distance_m is not None
    assert 3.0 <= res[0].estimated_distance_m <= 120.0


def test_full_cooperative_pipeline_flow(orchestrator):
    """Tests end-to-end process_cooperative_frame execution."""
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    raw_candidates = [
        {"bbox": [50.0, 50.0, 180.0, 300.0], "confidence": 0.75, "class_name": "person", "class_id": 0},
        {"bbox": [200.0, 200.0, 450.0, 380.0], "confidence": 0.82, "class_name": "car", "class_id": 2},
    ]

    res = orchestrator.process_cooperative_frame(frame, raw_candidates)
    assert "quality_assessment" in res
    assert "candidates" in res
    assert len(res["candidates"]) == 2
    assert "orchestrator_latency_ms" in res
    assert res["orchestrator_latency_ms"] >= 0.0
