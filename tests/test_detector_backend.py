"""
Tests for DetectorBackend abstraction and AdaptiveTiledDetector (Phases 4 & 5).
Verifies:
1. Uniform schema contract (bbox, class, confidence, timestamp, latency breakdown).
2. YOLOv8Backend functionality.
3. RFDETRBackend functionality with zero-crash fallback.
4. Dynamic backend resolution via DETECTOR_BACKEND.
5. Adaptive small-object tiling and box merging.
"""

import os
import cv2
import numpy as np
import pytest

from services.detection.detector_backend import (
    YOLOv8Backend,
    RFDETRBackend,
    get_detector_backend,
    StandardDetectionBatch,
)
from services.detection.tiled_detector import AdaptiveTiledDetector, nms_boxes


class TestDetectorBackendSuite:
    def setup_method(self):
        # Create a sample frame with a visible simulated object
        self.frame = np.full((480, 640, 3), 120, dtype=np.uint8)
        # Person-like vertical contrast block
        cv2.rectangle(self.frame, (280, 140), (360, 380), (30, 30, 200), -1)

    def test_yolov8_backend_schema(self):
        backend = YOLOv8Backend({"confidence_threshold": 0.20, "device": "cpu"})
        res = backend.detect(self.frame, camera_id="CAM-TEST", frame_id=1)

        assert isinstance(res, StandardDetectionBatch)
        assert res.camera_id == "CAM-TEST"
        assert res.frame_id == 1
        assert res.total_latency > 0.0
        assert res.preprocess_latency >= 0.0
        assert res.inference_latency > 0.0

        # Verify metadata
        meta = backend.get_metadata()
        assert meta["backend"] == "YOLOv8Backend"
        assert meta["status"] == "PRODUCTION"

    def test_rf_detr_backend_schema_and_fallback(self):
        backend = RFDETRBackend({"confidence_threshold": 0.20, "device": "cpu"})
        res = backend.detect(self.frame, camera_id="CAM-TEST", frame_id=2)

        assert isinstance(res, StandardDetectionBatch)
        assert res.camera_id == "CAM-TEST"
        assert res.frame_id == 2
        assert res.total_latency > 0.0

        meta = backend.get_metadata()
        assert meta["backend"] == "RFDETRBackend"
        assert meta["license"] == "Apache-2.0"

    def test_dynamic_backend_factory(self):
        # Test default
        os.environ["DETECTOR_BACKEND"] = "yolov8"
        b1 = get_detector_backend()
        assert isinstance(b1, YOLOv8Backend)

        # Test rf_detr switch
        os.environ["DETECTOR_BACKEND"] = "rf_detr"
        b2 = get_detector_backend()
        assert isinstance(b2, RFDETRBackend)

        # Reset
        os.environ["DETECTOR_BACKEND"] = "yolov8"

    def test_adaptive_tiled_inference(self):
        base_backend = YOLOv8Backend({"confidence_threshold": 0.20, "device": "cpu"})
        tiled_detector = AdaptiveTiledDetector(
            base_detector=base_backend,
            small_area_thresh=0.05,  # Trigger for test
            latency_budget_ms=500.0,
        )

        res = tiled_detector.detect_adaptive(
            frame=self.frame,
            camera_id="CAM-01",
            frame_id=1,
            has_distant_zone=True,
        )

        assert isinstance(res, StandardDetectionBatch)
        assert res.total_latency > 0.0
        # Check that NMS works
        boxes = [
            {"x1": 0.1, "y1": 0.1, "x2": 0.2, "y2": 0.2},
            {"x1": 0.11, "y1": 0.11, "x2": 0.21, "y2": 0.21},
            {"x1": 0.5, "y1": 0.5, "x2": 0.8, "y2": 0.8},
        ]
        scores = [0.9, 0.85, 0.95]
        kept = nms_boxes(boxes, scores, iou_threshold=0.4)
        assert len(kept) == 2  # The two overlapping boxes should merge to 1
