"""
Direct test execution script for IBVAP Grand Finale Orchestration.
Can be executed with standard python without any test runner flags:
python run_tests_standalone.py
"""
import sys
import os
import math
import numpy as np
from datetime import datetime, timezone

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ml.registry.model_registry import ModelRegistry, ModelStatus, ModelMetadata
from services.orchestrator.cascade_levels import CascadeLevel, CascadeStatus, CascadedInferenceResult
from services.orchestrator.route_scorer import DynamicRouteScorer, RouteWeights
from services.orchestrator.confidence_fusion import ConfidenceFusionEngine, FusedTargetRecord
from services.orchestrator.multi_camera_bus import MultiCameraEventBus
from services.orchestrator.orchestrator import AutonomousAIOrchestrator
from services.detection.mock_detector import MockDetector


def run_all_tests():
    print("=" * 60)
    print("RUNNING GRAND FINALE ORCHESTRATOR VERIFICATION")
    print("=" * 60)

    # 1. 13 Pools Coverage
    registry = ModelRegistry()
    summary = registry.get_registry_summary()
    assert summary["total_models"] >= 50, f"Expected >= 50 models, got {summary['total_models']}"
    assert summary["expert_pool_count"] >= 13, f"Expected >= 13 pools, got {summary['expert_pool_count']}"
    print(f"[PASS] test_model_registry_13_expert_pools_coverage (Total models: {summary['total_models']}, Pools: {summary['expert_pool_count']})")

    # 2. Zero-Crash Fallback Hierarchy
    orchestrator = AutonomousAIOrchestrator(registry=registry)
    vlm_model, is_fb, st_desc = orchestrator.query_or_fallback("qwen2_5_vl_7b")
    assert is_fb is True
    assert "REGISTERED / NOT INSTALLED / FALLBACK ACTIVE" in st_desc
    assert vlm_model.model_id == "rule_based_copilot_baseline"
    print("[PASS] test_zero_crash_fallback_hierarchy")

    # 3. Dynamic Route Scorer Boundary and Robustness
    scorer = DynamicRouteScorer()
    score_high, directive_high, _ = scorer.calculate_score(0.92, 0.90, 1.0, 0.95, 1.0, 0.80, 0.75, 1.0)
    assert score_high >= 0.85
    assert directive_high == "CRITICAL_INTERCEPT_DISPATCH"

    score_nan, directive_nan, _ = scorer.calculate_score(None, float("nan"), float("inf"), 0.5, None)
    assert not math.isnan(score_nan)
    assert 0.0 <= score_nan <= 1.0
    print("[PASS] test_dynamic_route_scoring_formula and NaN/None robustness")

    # 4. Multi-Camera Event Bus Spatial Handover and Rejection
    bus = MultiCameraEventBus()
    received = []
    bus.subscribe("track.handover", lambda m: received.append(m))
    gid1 = bus.register_camera_track("CAM-01", 101, 0.92, 0.50, "UNAUTHORIZED")
    gid2 = bus.register_camera_track("CAM-02", 202, 0.08, 0.50, "UNAUTHORIZED")
    assert gid1 == gid2
    assert len(received) == 1

    # Incompatible positions reject handover
    bus.clear()
    gid_rej1 = bus.register_camera_track("CAM-01", 1, 0.10, 0.50)
    gid_rej2 = bus.register_camera_track("CAM-02", 2, 0.90, 0.50)
    assert gid_rej1 != gid_rej2
    print("[PASS] test_multi_camera_event_bus_handover and spatial rejection")

    # 5. Confidence Fusion Engine & Authorized Perimeter Inversion Fix
    fusion = ConfidenceFusionEngine()
    auth_breach = fusion.fuse_target("T_AUTH", "CAM-01", "person", 0.92, identity_state="AUTHORIZED",
                                      temporal_state="VERIFIED", temporal_frame_count=50,
                                      zone_hazard_score=0.95)
    assert auth_breach.alert_eligible is True
    print("[PASS] test_confidence_fusion_engine and critical perimeter authorized actor")

    # 6. Full Level 0 to 6 Cascade Execution
    mock = MockDetector()
    mock.load_model()
    cascade_orch = AutonomousAIOrchestrator(primary_detector=mock)
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    res = cascade_orch.process_frame(
        frame=frame,
        camera_id="CAM-01",
        frame_id=1,
        timestamp=datetime.now(timezone.utc),
        zone_name="PERIMETER_FENCE_NORTH",
        zone_hazard_score=0.90,
        simulate_established_tracks=True
    )
    assert res.overall_status == CascadeStatus.ALERT_TRIGGERED
    assert res.raw_detections_count > 0
    assert res.active_tracks_count > 0
    assert len(res.incidents_generated) > 0
    assert res.indic_dispatch is not None
    assert len(res.sha256_evidence_hash) == 64
    print("[PASS] test_autonomous_orchestrator_level_0_to_6_cascade")

    print("=" * 60)
    print("ALL ORCHESTRATION TESTS PASSED 100% WITHOUT REGRESSIONS")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
