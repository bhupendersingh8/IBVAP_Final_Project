"""
Unit & Integration Tests for IBVAP Grand Finale Autonomous AI Multi-Model Orchestration
========================================================================================
Validates:
1. Model Registry coverage across all 13 Expert Pools + Edge runtime stack
2. Zero-crash fallback hierarchy: missing models report REGISTERED / NOT INSTALLED / FALLBACK ACTIVE
3. Dynamic route scoring formula and priority directives
4. Multimodal confidence fusion without blind score averaging
5. Multi-camera event bus and cross-camera track handover
6. Level 0 to Level 6 end-to-end cascading inference
7. Indic language alert dispatch and SHA-256 evidence hashing
"""
import pytest
import numpy as np
from datetime import datetime, timezone

from ml.registry.model_registry import ModelRegistry, ModelStatus, ModelMetadata
from services.orchestrator.cascade_levels import CascadeLevel, CascadeStatus, CascadedInferenceResult
from services.orchestrator.route_scorer import DynamicRouteScorer, RouteWeights
from services.orchestrator.confidence_fusion import ConfidenceFusionEngine, FusedTargetRecord
from services.orchestrator.multi_camera_bus import MultiCameraEventBus
from services.orchestrator.orchestrator import AutonomousAIOrchestrator
from services.detection.mock_detector import MockDetector


def test_model_registry_17_expert_pools_coverage():
    """Verify that all 17 expert pools and edge stack are loaded and cataloged."""
    registry = ModelRegistry()
    summary = registry.get_registry_summary()

    # Total registered models should be over 100 (actually 121)
    assert summary["total_models"] >= 100
    assert summary["installed_models"] >= 10  # Active baselines installed on Dell
    assert summary["expert_pool_count"] == 17

    # Check all 17 expert pools exist
    expected_pools = [
        "detection", "segmentation", "tracking", "face_identity", "reid",
        "vlm", "video_understanding", "restoration", "pose_behavior",
        "anomaly", "foundation", "edge_stack", "anpr", "indian_ai",
        "temporal_event", "camera_health", "evidence_security"
    ]
    for pool in expected_pools:
        models = registry.get_models_by_pool(pool)
        assert len(models) > 0, f"Expected models in pool '{pool}', found none"

    # Verify DINOv3 defense/military licensing restriction safeguard
    dinov3 = registry.get_model("dinov3_nextgen_foundation")
    assert dinov3 is not None
    assert "RESTRICTED" in dinov3.license or "Military" in dinov3.license



def test_zero_crash_fallback_hierarchy():
    """Ensure missing advanced models resolve to safe CPU baselines without crashing."""
    registry = ModelRegistry()
    orchestrator = AutonomousAIOrchestrator(registry=registry)

    # 1. Query an uninstalled advanced VLM (e.g. Qwen2.5-VL 7B)
    vlm_model, is_fb, st_desc = orchestrator.query_or_fallback("qwen2_5_vl_7b")
    assert is_fb is True
    assert "REGISTERED / NOT INSTALLED / FALLBACK ACTIVE" in st_desc
    assert vlm_model.model_id == "rule_based_copilot_baseline"
    assert vlm_model.installed is True

    # 2. Query an uninstalled advanced Face model (AdaFace IR100)
    face_model, is_fb2, st_desc2 = orchestrator.query_or_fallback("adaface_ir100")
    assert is_fb2 is True
    assert "FALLBACK ACTIVE" in st_desc2
    assert face_model.model_id == "haar_face_baseline"
    assert face_model.installed is True

    # 3. Query an uninstalled advanced Segmentation model (SAM 2.1)
    sam_model, is_fb3, _ = orchestrator.query_or_fallback("sam_2_1_foundation")
    assert is_fb3 is True
    assert sam_model.model_id == "yolov8n_pretrained_baseline"

    # 4. Query an uninstalled advanced Temporal Event model (CEP Engine)
    cep_model, is_fb4, _ = orchestrator.query_or_fallback("cep_complex_event_processor")
    assert is_fb4 is True
    assert cep_model.model_id == "temporal_state_machine_baseline"
    assert cep_model.installed is True

    # 5. Query an uninstalled advanced Camera Health model (Deep Tamper CNN)
    tamper_model, is_fb5, _ = orchestrator.query_or_fallback("deep_tamper_occlusion_cnn")
    assert is_fb5 is True
    assert tamper_model.model_id == "camera_health_diagnostic_baseline"
    assert tamper_model.installed is True

    # 6. Query an uninstalled advanced Evidence model (RBAC Token Gate)
    rbac_model, is_fb6, _ = orchestrator.query_or_fallback("rbac_token_gate")
    assert is_fb6 is True
    assert rbac_model.model_id == "sha256_evidence_chain_baseline"
    assert rbac_model.installed is True


def test_dynamic_route_scoring_formula():
    """Validate mathematical correctness and boundary behavior of route scoring."""
    scorer = DynamicRouteScorer()

    # High threat scenario: high confidence, high temporal maturity, perimeter zone, unauthorized identity
    score_high, directive_high, breakdown_high = scorer.calculate_score(
        c_det=0.92,
        c_track=0.90,
        c_temporal=1.0,     # mature > 45 frames
        c_zone=0.95,         # fence perimeter
        c_identity=1.0,      # UNAUTHORIZED
        c_anomaly=0.80,
        c_vlm=0.75,
        c_cam_quality=1.0
    )
    assert score_high >= 0.85
    assert directive_high == "CRITICAL_INTERCEPT_DISPATCH"
    assert breakdown_high["s_route"] == score_high

    # Low noise scenario: low confidence, fleeting, buffer zone, authorized person
    score_low, directive_low, breakdown_low = scorer.calculate_score(
        c_det=0.20,
        c_track=0.10,
        c_temporal=0.05,
        c_zone=0.20,
        c_identity=0.0,      # AUTHORIZED
        c_anomaly=0.0,
        c_vlm=0.0,
        c_cam_quality=0.5
    )
    assert score_low < 0.25
    assert directive_low == "DISREGARD_FILTERED_NOISE"


def test_confidence_fusion_no_blind_averaging():
    """Validate that fusion engine boosts agreements and flags disagreements without naive averaging."""
    fusion = ConfidenceFusionEngine()

    # 1. Agreement case: Primary = vehicle (0.80), Specialist = vehicle:truck (0.85)
    fused_agree = fusion.fuse_target(
        target_id="T1",
        camera_id="CAM-01",
        primary_class="vehicle",
        primary_conf=0.80,
        specialist_results=[{
            "name": "ANPR_Vehicle_Specialist",
            "class": "vehicle",
            "subclass": "truck",
            "confidence": 0.85
        }]
    )
    assert fused_agree.primary_class == "vehicle"
    assert fused_agree.subclass == "truck"
    assert fused_agree.fused_confidence >= 0.85  # Calibrated boost
    assert len(fused_agree.disagreements) == 0

    # 2. Disagreement case: Primary = vehicle (0.45), Specialist = person (0.85)
    fused_disagree = fusion.fuse_target(
        target_id="T2",
        camera_id="CAM-01",
        primary_class="vehicle",
        primary_conf=0.45,
        specialist_results=[{
            "name": "Face_Specialist",
            "class": "person",
            "subclass": "person",
            "confidence": 0.85
        }]
    )
    assert len(fused_disagree.disagreements) > 0
    # Confident specialist overturns weak primary
    assert fused_disagree.primary_class == "person"


def test_multi_camera_event_bus_handover():
    """Verify track handover across cameras and pub/sub message dispatch."""
    bus = MultiCameraEventBus()
    received_handover = []

    def on_handover(msg):
        received_handover.append(msg)

    bus.subscribe("track.handover", on_handover)

    # 1. Register track on CAM-01 near right boundary (x=0.92, y=0.50)
    gid1 = bus.register_camera_track(
        camera_id="CAM-01",
        local_track_id=101,
        norm_x=0.92,
        norm_y=0.50,
        identity_state="UNAUTHORIZED"
    )
    assert "GLOBAL-CAM-01-101" in gid1

    # 2. Within 2 seconds, target appears on adjacent CAM-02 near left boundary (x=0.08, y=0.50)
    gid2 = bus.register_camera_track(
        camera_id="CAM-02",
        local_track_id=202,
        norm_x=0.08,
        norm_y=0.50,
        identity_state="UNAUTHORIZED"
    )

    # Target should be associated to same global ID
    assert gid1 == gid2
    assert len(received_handover) == 1
    assert received_handover[0].payload["from_camera"] == "CAM-01"
    assert received_handover[0].payload["to_camera"] == "CAM-02"


def test_autonomous_orchestrator_level_0_to_6_cascade():
    """Execute complete Level 0 through Level 6 cascading inference end-to-end."""
    mock = MockDetector()
    mock.load_model()
    orchestrator = AutonomousAIOrchestrator(primary_detector=mock)

    # 1. Create synthetic frame with normal daylight illumination
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    now = datetime.now(timezone.utc)

    # Process frame through full cascade with established simulation tracks
    result = orchestrator.process_frame(
        frame=frame,
        camera_id="CAM-01",
        frame_id=1,
        timestamp=now,
        zone_name="PERIMETER_FENCE_NORTH",
        zone_hazard_score=0.90,
        simulate_established_tracks=True
    )

    assert isinstance(result, CascadedInferenceResult)
    assert result.camera_id == "CAM-01"
    assert len(result.levels_executed) == 7
    assert result.raw_detections_count > 0
    assert result.active_tracks_count > 0

    # Verify each level 0 through 6 ran in sequence
    for lvl_idx in range(7):
        lvl_telemetry = result.levels_executed[lvl_idx]
        assert lvl_telemetry.level == lvl_idx
        assert lvl_telemetry.latency_ms >= 0.0

    # Verify fallback audit records were generated
    assert len(result.fallback_records) > 0
    for fb in result.fallback_records:
        assert "FALLBACK ACTIVE" in fb["status"]

    # Verify alert generation and Indic language dispatch unconditionally
    assert result.overall_status == CascadeStatus.ALERT_TRIGGERED
    assert len(result.incidents_generated) > 0
    assert result.indic_dispatch is not None
    assert "TACTICAL ALERT" in result.indic_dispatch["en"]
    assert "रणनीतिक चेतावनी" in result.indic_dispatch["hi"]
    assert "ਰਣਨੀਤਕ ਚੇਤਾਵਨੀ" in result.indic_dispatch["pa"]
    assert result.sha256_evidence_hash is not None
    assert len(result.sha256_evidence_hash) == 64  # Valid SHA-256 hex string


def test_dynamic_route_scorer_nan_none_robustness():
    """Verify route scorer handles None, NaN, and Inf without TypeError or NaN pollution."""
    scorer = DynamicRouteScorer()
    score, directive, breakdown = scorer.calculate_score(
        c_det=None,
        c_track=float("nan"),
        c_temporal=float("inf"),
        c_zone=0.5,
        c_identity=None,
        c_anomaly=float("-inf"),
        c_vlm=None,
        c_cam_quality=None
    )
    import math
    assert not math.isnan(score)
    assert 0.0 <= score <= 1.0
    assert directive in ("CRITICAL_INTERCEPT_DISPATCH", "ELEVATED_TACTICAL_ALERT",
                         "ACTIVE_MONITORING_TRACK", "LOW_CONFIDENCE_OBSERVATION",
                         "DISREGARD_FILTERED_NOISE")


def test_confidence_fusion_critical_perimeter_authorized():
    """Verify authorized person violating critical perimeter fence correctly triggers alert."""
    engine = ConfidenceFusionEngine()
    record = engine.fuse_target(
        target_id="AUTH_ACTOR_01",
        camera_id="CAM-01",
        primary_class="person",
        primary_conf=0.92,
        identity_state="AUTHORIZED",
        temporal_state="VERIFIED",
        temporal_frame_count=50,
        zone_name="PERIMETER_FENCE_EAST",
        zone_hazard_score=0.95
    )
    # Even though actor is AUTHORIZED, fence hazard score >= 0.85 triggers alert
    assert record.alert_eligible is True
    assert record.zone_hazard_score == 0.95


def test_multi_camera_event_bus_spatial_rejection():
    """Verify incompatible spatial coordinates reject cross-camera handover."""
    bus = MultiCameraEventBus()

    # CAM-01: target is at far left (x=0.10, y=0.50)
    gid1 = bus.register_camera_track(
        camera_id="CAM-01",
        local_track_id=1,
        norm_x=0.10,
        norm_y=0.50,
        identity_state="UNKNOWN"
    )

    # CAM-02: target appears at far right (x=0.90, y=0.50) within 1 sec
    gid2 = bus.register_camera_track(
        camera_id="CAM-02",
        local_track_id=2,
        norm_x=0.90,
        norm_y=0.50,
        identity_state="UNKNOWN"
    )

    # Incompatible spatial positions must NOT be merged
    assert gid1 != gid2

