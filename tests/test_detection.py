"""
IBVAP — Detection Engine & Schema Tests
=======================================
Verifies BBox normalization and property calculation,
Detection validation, and MockDetector batch outputs.
"""

import pytest
from datetime import datetime, timezone
from services.detection.schemas import BBox, Detection, DetectionBatch
from services.detection.mock_detector import MockDetector


def test_bbox_valid_geometry():
    bbox = BBox(x1=0.1, y1=0.2, x2=0.5, y2=0.8)
    assert pytest.approx(bbox.width) == 0.4
    assert pytest.approx(bbox.height) == 0.6
    assert pytest.approx(bbox.center_x) == 0.3
    assert pytest.approx(bbox.center_y) == 0.5
    assert pytest.approx(bbox.area) == 0.24


def test_bbox_invalid_coordinates_raises():
    with pytest.raises(ValueError):
        BBox(x1=0.5, y1=0.2, x2=0.1, y2=0.8) # x1 >= x2

    with pytest.raises(ValueError):
        BBox(x1=-0.1, y1=0.2, x2=0.5, y2=0.8) # negative


def test_detection_confidence_bounds():
    bbox = BBox(x1=0.1, y1=0.2, x2=0.5, y2=0.8)
    det = Detection(bbox=bbox, class_name="vehicle", confidence=0.85, subclass="car")
    assert det.class_name == "vehicle"
    assert det.subclass == "car"

    with pytest.raises(ValueError):
        Detection(bbox=bbox, confidence=1.5)


def test_mock_detector_generates_valid_batches():
    mock = MockDetector()
    mock.load_model()
    assert mock.is_loaded() is True

    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    now = datetime.now(timezone.utc)

    batch = mock.detect(frame=frame, camera_id="CAM-TEST", frame_id=42, timestamp=now)
    assert isinstance(batch, DetectionBatch)
    assert batch.camera_id == "CAM-TEST"
    assert batch.frame_id == 42
    assert len(batch.detections) >= 0


def test_pen_and_watch_taxonomy_calibration():
    from services.detection.model_orchestrator import COCO_BROAD_TAXONOMY, BroadCategory
    from services.detection.yolo_adapter import YOLO_CLASS_MAP

    # Verify pen calibration
    assert YOLO_CLASS_MAP["toothbrush"] == "equipment"
    assert YOLO_CLASS_MAP["pen"] == "equipment"
    assert COCO_BROAD_TAXONOMY["pen"]["category"] == BroadCategory.EQUIPMENT.value
    assert COCO_BROAD_TAXONOMY["pen"]["subclass"] == "pen"
    assert COCO_BROAD_TAXONOMY["toothbrush"]["subclass"] == "pen"

    # Verify watch calibration
    assert YOLO_CLASS_MAP["clock"] == "equipment"
    assert YOLO_CLASS_MAP["watch"] == "equipment"
    assert COCO_BROAD_TAXONOMY["watch"]["category"] == BroadCategory.EQUIPMENT.value
    assert COCO_BROAD_TAXONOMY["watch"]["subclass"] == "watch"
    assert COCO_BROAD_TAXONOMY["clock"]["subclass"] == "watch"


def test_threat_and_weapon_taxonomy():
    from services.detection.model_orchestrator import COCO_BROAD_TAXONOMY, BroadCategory
    from services.detection.yolo_adapter import YOLO_CLASS_MAP
    import os

    # Verify weapon broad category
    assert hasattr(BroadCategory, "WEAPON")
    assert BroadCategory.WEAPON.value == "weapon"

    # Verify weapon taxonomy entries
    for weapon in ["gun", "pistol", "rifle", "knife", "grenade", "explosive"]:
        assert weapon in COCO_BROAD_TAXONOMY
        assert COCO_BROAD_TAXONOMY[weapon]["category"] == BroadCategory.WEAPON.value
        assert YOLO_CLASS_MAP[weapon] == "weapon"

    # Verify threat model file presence and loading
    from ultralytics import YOLO
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    threat_path = os.path.join(project_root, "models", "threat_yolov8n.pt")
    assert os.path.exists(threat_path)

    m = YOLO(threat_path)
    assert 0 in m.names
    assert "gun" in str(m.names[0]).lower()
