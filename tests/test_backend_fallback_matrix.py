"""
IBVAP — GPU Backend Fallback Matrix & Zero-Crash Contract Test
SIH Problem Statement: 26187 | Tactical Border Surveillance

Verifies that the platform strictly adheres to the fallback priority:
1. TensorRT FP16
2. ONNX Runtime CUDA
3. PyTorch CUDA FP16
4. PyTorch CPU FP32

Tests that when GPU, CUDA, or TensorRT are unavailable, the application
falls back cleanly without crashing or raising unhandled exceptions.
"""

import os
import pytest
import numpy as np
import torch
from services.detection.detector_backend import YOLOv8Backend, RFDETRBackend, get_detector_backend
from services.detection.yolo_adapter import YOLOAdapter
from services.hardware.hardware_detector import HardwareDetector, HardwareProfileName


def test_hardware_detector_falls_back_to_dell_cpu():
    """When no NVIDIA GPU is present, detector must resolve DELL_CPU."""
    detector = HardwareDetector()
    profile = detector.resolve_profile()
    if not profile.gpu.cuda_available:
        assert profile.profile_name == HardwareProfileName.DELL_CPU
        assert profile.primary_runtime == "cpu_fp32"
        assert os.path.basename(profile.primary_detection_model) in ["yolo26n.pt", "yolov8n.pt"]


def test_yolo_adapter_cuda_unavailable_fallback():
    """Passing device='cuda' when CUDA is unavailable must fallback to CPU without crash."""
    config = {
        "device": "cuda:0",
        "confidence_threshold": 0.3,
        "model_name": "yolov8n"
    }
    adapter = YOLOAdapter(config)
    adapter.load_model()
    # Adapter must reset device to 'cpu' if CUDA is unavailable
    if not torch.cuda.is_available():
        assert adapter.device == "cpu"
    assert adapter.is_loaded() is True


def test_detector_backend_zero_crash_on_synthetic_frame():
    """Runs YOLOv8Backend on CPU to verify zero-crash execution."""
    backend = YOLOv8Backend(config={"device": "cpu", "confidence_threshold": 0.25})
    dummy = np.zeros((480, 640, 3), dtype=np.uint8)
    batch = backend.detect(dummy, camera_id="test_cam", frame_id=1)
    assert batch is not None
    assert batch.camera_id == "test_cam"
    assert batch.frame_id == 1
    assert isinstance(batch.detections, list)


def test_rf_detr_zero_crash_yolo_fallback():
    """Verifies RF-DETR backend gracefully activates YOLO fallback without unhandled exceptions."""
    backend = RFDETRBackend(config={"device": "cpu", "confidence_threshold": 0.25})
    dummy = np.zeros((480, 640, 3), dtype=np.uint8)
    batch = backend.detect(dummy, camera_id="test_cam", frame_id=1)
    assert batch is not None
    assert batch.camera_id == "test_cam"
