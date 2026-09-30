"""
tests/test_orchestrator_selective.py
====================================
Tests for Selective Specialist Dispatch & Missing Model Telemetry in AutonomousAIOrchestrator.
"""
from __future__ import annotations

import numpy as np
import pytest
from datetime import datetime, timezone

from services.orchestrator.orchestrator import AutonomousAIOrchestrator
from services.orchestrator.cascade_levels import CascadeLevel, CascadeStatus


def test_orchestrator_initialization():
    orch = AutonomousAIOrchestrator()
    assert orch.registry is not None
    assert orch.route_scorer is not None
    assert orch.event_bus is not None


def test_missing_model_fallback_reporting():
    """Verify that uninstalled model queries report MODEL_NOT_AVAILABLE / FALLBACK_ACTIVE."""
    orch = AutonomousAIOrchestrator()
    model, is_fallback, status_desc = orch.query_or_fallback("qwen2_5_vl_72b_instruct")
    assert is_fallback is True
    assert "MODEL_NOT_AVAILABLE" in status_desc


def test_selective_specialist_dispatch_person():
    """Verify that person detection triggers Face and Pose, but NOT ANPR."""
    orch = AutonomousAIOrchestrator()
    frame = np.full((360, 640, 3), 120, dtype=np.uint8)

    class MockPersonDetector:
        def detect(self, *args, **kwargs):
            return [{"class_name": "person", "confidence": 0.88, "bbox": {"x1": 0.3, "y1": 0.3, "x2": 0.5, "y2": 0.7}}]

    orch.primary_detector = MockPersonDetector()
    result = orch.process_frame(frame, camera_id="CAM-01", frame_id=1, simulate_established_tracks=True)

    # Check Level 3 specialist telemetry
    l3 = next(lvl for lvl in result.levels_executed if lvl.level == CascadeLevel.LEVEL_3_SPECIALIST)
    assert l3 is not None
    # Verify fallback records contain MODEL_NOT_AVAILABLE for missing heavy weights
    for fb in result.fallback_records:
        assert "MODEL_NOT_AVAILABLE" in fb["status"]


def test_selective_specialist_dispatch_vehicle():
    """Verify that vehicle detection triggers ANPR, but NOT Face/Pose."""
    orch = AutonomousAIOrchestrator()
    frame = np.full((360, 640, 3), 120, dtype=np.uint8)

    class MockVehicleDetector:
        def detect(self, *args, **kwargs):
            return [{"class_name": "car", "confidence": 0.85, "bbox": {"x1": 0.2, "y1": 0.2, "x2": 0.6, "y2": 0.6}}]

    orch.primary_detector = MockVehicleDetector()
    result = orch.process_frame(frame, camera_id="CAM-01", frame_id=2, simulate_established_tracks=True)

    l3 = next(lvl for lvl in result.levels_executed if lvl.level == CascadeLevel.LEVEL_3_SPECIALIST)
    assert l3 is not None
