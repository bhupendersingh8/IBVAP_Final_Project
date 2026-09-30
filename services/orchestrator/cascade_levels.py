"""
IBVAP Level 0 to Level 6 Model Cascading Architecture Definitions
=================================================================
Defines the canonical 7-tier model cascading hierarchy for the
Intelligent Border Video Analytics Platform (IBVAP).
"""
from enum import IntEnum, Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class CascadeLevel(IntEnum):
    LEVEL_0_SIGNAL = 0          # Hardware, RTSP/Webcam Ingestion, Bounded Buffering & Restoration
    LEVEL_1_DETECTION = 1       # Primary Spatial Object Detection & Edge Filtering
    LEVEL_2_TRACKING = 2        # Temporal Multi-Object Tracking & Motion Association
    LEVEL_3_SPECIALIST = 3      # Specialist Feature Extraction (Face/ID, ANPR, Pose, Animal, Re-ID)
    LEVEL_4_TEMPORAL_RULES = 4  # Spatial-Temporal Validation State Machine & Tactical Rules
    LEVEL_5_FUSION_MULTICAM = 5 # Dynamic Route Scoring, Multimodal Fusion & Multi-Camera Event Bus
    LEVEL_6_TACTICAL_VLM = 6    # Tactical AI Copilot, Indic Language Alerting, SHA-256 Packaging


class CascadeStatus(str, Enum):
    PASS = "PASS"
    FALLBACK_ACTIVE = "FALLBACK_ACTIVE"
    SKIPPED = "SKIPPED"
    FILTERED = "FILTERED"
    ALERT_TRIGGERED = "ALERT_TRIGGERED"
    MODEL_NOT_AVAILABLE = "MODEL_NOT_AVAILABLE"


@dataclass
class LevelTelemetry:
    level: CascadeLevel
    level_name: str
    status: CascadeStatus
    latency_ms: float
    model_used: str
    is_fallback: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CascadedInferenceResult:
    camera_id: str
    frame_id: int
    timestamp: datetime
    overall_status: CascadeStatus
    total_latency_ms: float
    levels_executed: List[LevelTelemetry] = field(default_factory=list)
    raw_detections_count: int = 0
    active_tracks_count: int = 0
    fused_events_count: int = 0
    incidents_generated: List[Dict[str, Any]] = field(default_factory=list)
    fallback_records: List[Dict[str, Any]] = field(default_factory=list)
    route_score: float = 0.0
    action_directive: str = "ACTIVE_MONITORING_TRACK"
    indic_dispatch: Optional[Dict[str, str]] = None
    sha256_evidence_hash: Optional[str] = None
