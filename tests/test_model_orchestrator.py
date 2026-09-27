"""
Tests for Model Orchestrator, Hierarchical Router, and Fusion Engine (Phases D, E, F, G)
"""

import pytest
import numpy as np
from datetime import datetime, timezone

from services.detection.schemas import BBox, Detection, DetectionBatch
from services.detection.mock_detector import MockDetector
from services.detection.model_orchestrator import (
    ModelOrchestrator,
    HierarchicalObjectRouter,
    ModelFusionEngine,
    SpecialistResult,
    BroadCategory,
    COCO_BROAD_TAXONOMY
)


def test_broad_taxonomy_mapping():
    assert COCO_BROAD_TAXONOMY["car"]["category"] == "vehicle"
    assert COCO_BROAD_TAXONOMY["truck"]["category"] == "vehicle"
    assert COCO_BROAD_TAXONOMY["person"]["category"] == "person"
    assert COCO_BROAD_TAXONOMY["dog"]["category"] == "animal"
    assert COCO_BROAD_TAXONOMY["cell phone"]["category"] == "equipment"
    assert COCO_BROAD_TAXONOMY["traffic light"]["category"] == "infrastructure"


def test_model_fusion_agreement():
    engine = ModelFusionEngine()
    spec = SpecialistResult(
        specialist_name="Vehicle_Classifier",
        verified_class="vehicle",
        subclass="truck",
        confidence=0.88,
        attributes={"wheels": 6}
    )
    final_class, final_sub, final_conf, is_disagree, meta = engine.fuse(
        primary_class="vehicle",
        primary_conf=0.85,
        primary_subclass="car",
        specialist_result=spec
    )
    assert final_class == "vehicle"
    assert final_sub == "truck"
    assert is_disagree is False
    assert final_conf >= 0.88  # Calibrated boost
    assert meta["specialist_name"] == "Vehicle_Classifier"


def test_model_fusion_disagreement():
    engine = ModelFusionEngine()
    # Primary says vehicle, specialist says animal
    spec = SpecialistResult(
        specialist_name="Animal_Classifier",
        verified_class="animal",
        subclass="wildlife",
        confidence=0.55
    )
    final_class, final_sub, final_conf, is_disagree, meta = engine.fuse(
        primary_class="vehicle",
        primary_conf=0.52,
        primary_subclass="car",
        specialist_result=spec
    )
    assert is_disagree is True
    assert "disagreement_reason" in meta


def test_hierarchical_router_vehicle_small_crop():
    router = HierarchicalObjectRouter()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Very small box: 5px wide, should be skipped
    tiny_box = BBox(x1=0.1, y1=0.1, x2=0.105, y2=0.105)
    det = Detection(bbox=tiny_box, class_name="vehicle", confidence=0.80)
    result = router.route_vehicle(frame, det, "CAM-01")
    assert result is None


def test_orchestrator_end_to_end_with_mock():
    mock = MockDetector()
    mock.load_model()
    orchestrator = ModelOrchestrator(primary_detector=mock)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    now = datetime.now(timezone.utc)
    batch = orchestrator.process_frame(frame, "CAM-TEST", 1, now)

    assert isinstance(batch, DetectionBatch)
    assert batch.camera_id == "CAM-TEST"
    assert batch.frame_id == 1
    assert batch.total_inference_ms >= 0.0
