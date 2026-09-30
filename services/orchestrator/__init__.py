"""
IBVAP Autonomous AI Multi-Model Orchestration Package
=====================================================
Exports Level 0-6 Cascade definitions, Route Scorer,
Confidence Fusion Engine, Multi-Camera Bus, and the
Autonomous AI Orchestrator.
"""

from .cascade_levels import (
    CascadeLevel,
    CascadeStatus,
    LevelTelemetry,
    CascadedInferenceResult,
)
from .route_scorer import (
    DynamicRouteScorer,
    RouteWeights,
)
from .confidence_fusion import (
    ConfidenceFusionEngine,
    FusedTargetRecord,
)
from .multi_camera_bus import (
    MultiCameraEventBus,
    BusMessage,
    GlobalTracklet,
)
from .orchestrator import (
    AutonomousAIOrchestrator,
)
from .model_runtime_manager import (
    ModelRuntimeManager,
    ModelTier,
    ModelResidency,
)

from .cooperative_registry import (
    CooperativeModelRegistry,
    CooperativeModelEntry,
    ModelRole,
    ModelOperationalStatus,
)
from .cooperative_orchestrator import (
    CooperativeAIOrchestrator,
    CooperativeCandidate,
    QualityAssessment,
)

__all__ = [
    "CascadeLevel",
    "CascadeStatus",
    "LevelTelemetry",
    "CascadedInferenceResult",
    "DynamicRouteScorer",
    "RouteWeights",
    "ConfidenceFusionEngine",
    "FusedTargetRecord",
    "MultiCameraEventBus",
    "BusMessage",
    "GlobalTracklet",
    "AutonomousAIOrchestrator",
    "ModelRuntimeManager",
    "ModelTier",
    "ModelResidency",
    "CooperativeModelRegistry",
    "CooperativeModelEntry",
    "ModelRole",
    "ModelOperationalStatus",
    "CooperativeAIOrchestrator",
    "CooperativeCandidate",
    "QualityAssessment",
]

