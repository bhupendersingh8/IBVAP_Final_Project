"""
IBVAP Canonical Model Interface & Standardized Prediction Data Contracts
========================================================================
Grand Finale Master Architecture - Section 3 & Execution Order
Standardizes all model interactions, lifecycle operations, and results across all 18 families:
- ModelInterface (ABC)
- DetectionResult
- TrackingResult
- IdentityResult
- OCRResult
- PoseResult
- SegmentationResult
- DepthResult
- VLMResult
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union
import time
import numpy as np


class ModelFamilyType(str, Enum):
    DETECTION = "DETECTION"
    TRACKING = "TRACKING"
    IDENTITY = "IDENTITY"
    ANPR = "ANPR"
    POSE = "POSE"
    SEGMENTATION = "SEGMENTATION"
    DEPTH = "DEPTH"
    RESTORATION = "RESTORATION"
    VLM = "VLM"
    INDIAN_AI = "INDIAN_AI"


# ==============================================================================
# Standardized Result Contracts
# ==============================================================================

@dataclass
class DetectionResult:
    """Standardized result for object detection models."""
    model_name: str
    boxes: List[List[float]]  # [[x1, y1, x2, y2], ...] normalized [0, 1]
    class_ids: List[int]
    class_names: List[str]
    confidences: List[float]
    latency_ms: float = 0.0
    count: int = 0
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.count == 0:
            self.count = len(self.boxes)


@dataclass
class TrackingResult:
    """Standardized result for multi-object tracking models."""
    model_name: str
    track_ids: List[int]
    global_ids: List[str]
    boxes: List[List[float]]
    class_names: List[str]
    confidences: List[float]
    velocities: List[float] = field(default_factory=list)
    ages: List[int] = field(default_factory=list)
    active_count: int = 0
    latency_ms: float = 0.0

    def __post_init__(self):
        if self.active_count == 0:
            self.active_count = len(self.track_ids)


@dataclass
class IdentityResult:
    """Standardized result for face/person Re-ID and identity verification."""
    is_authorized: bool
    identity_state: str  # "AUTHORIZED", "UNVERIFIED", "UNKNOWN", "UNAUTHORIZED"
    person_id: Optional[str]
    name: str
    confidence: float
    similarity: float = 0.0
    is_live: bool = False
    liveness_status: str = "AWAITING_BLINK"  # "VERIFIED_LIVE", "AWAITING_BLINK", "STATIC_SPOOF_SUSPECTED"
    blink_count: int = 0
    latency_ms: float = 0.0
    matched_features: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OCRResult:
    """Standardized result for ANPR license plate detection and OCR."""
    plate_text: Optional[str]
    normalized_text: str
    confidence: float
    status: str = "CANDIDATE"  # "STABLE_VERIFIED", "CANDIDATE", "LOW_CONFIDENCE", "UNREADABLE"
    plate_bbox: Optional[List[float]] = None
    consistent_readings: int = 1
    latency_ms: float = 0.0


@dataclass
class PoseResult:
    """Standardized result for human pose estimation and temporal skeleton action recognition."""
    model_name: str
    keypoints: List[List[List[float]]]  # [Person_idx, 17_kpts, [x, y, conf]]
    posture: str = "erect_walking"  # "erect_walking", "crawling", "climbing", "running", "prone"
    is_suspicious: bool = False
    confidence: float = 0.0
    latency_ms: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SegmentationResult:
    """Standardized result for instance and open-vocabulary segmentation models."""
    model_name: str
    masks: List[Any]  # Polygons [[x1, y1, ...]] or run-length encoded masks
    mask_count: int = 0
    class_names: List[str] = field(default_factory=list)
    confidences: List[float] = field(default_factory=list)
    latency_ms: float = 0.0


@dataclass
class DepthResult:
    """Standardized result for monocular spatial depth estimation."""
    model_name: str
    mean_depth: float = 0.5
    min_depth: float = 0.0
    max_depth: float = 1.0
    depth_map: Optional[np.ndarray] = None  # Normalized depth map [H, W] in [0, 1]
    spatial_regions: Dict[str, float] = field(default_factory=dict)  # {"near": pct, "mid": pct, "far": pct}
    latency_ms: float = 0.0


@dataclass
class VLMResult:
    """Standardized result for multimodal Vision-Language Models and video reasoning."""
    model_name: str
    narrative: str
    tactical_summary: str
    threat_assessment: str = "LOW"  # "NONE", "LOW", "ELEVATED", "CRITICAL"
    recommended_action: str = "CONTINUE_MONITORING"
    indic_dispatch: Dict[str, str] = field(default_factory=dict)  # {"en": ..., "hi": ..., "pa": ...}
    confidence: float = 0.0
    latency_ms: float = 0.0


# ==============================================================================
# Canonical ModelInterface Base Class
# ==============================================================================

class ModelInterface(ABC):
    """
    Authoritative Abstract Base Class for all models across the IBVAP architecture.
    Provides standard lifecycle management, execution contracts, latency tracking,
    and VRAM memory management.
    """
    def __init__(
        self,
        model_name: str,
        family: ModelFamilyType,
        device: str = "cpu",
        weights_path: Optional[str] = None
    ):
        self.model_name = model_name
        self.family = family
        self.device = device
        self.weights_path = weights_path
        self.is_loaded = False
        self.total_calls = 0
        self.total_latency_ms = 0.0
        self.last_latency_ms = 0.0

    @abstractmethod
    def load(self, weights_path: Optional[str] = None) -> bool:
        """Loads model weights and prepares runtime engine."""
        pass

    @abstractmethod
    def predict(self, input_data: Any) -> Any:
        """
        Executes model inference on input data.
        Returns one of the canonical Result dataclasses or a structured dict.
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Executes a diagnostic self-test with synthetic or sample data."""
        pass

    def unload(self) -> None:
        """Unloads weights from GPU VRAM and reclaims memory."""
        self.is_loaded = False
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def metadata(self) -> Dict[str, Any]:
        """Provides structured metadata and runtime telemetry."""
        avg_lat = round(self.total_latency_ms / self.total_calls, 2) if self.total_calls > 0 else 0.0
        return {
            "model_name": self.model_name,
            "family": self.family.value,
            "device": self.device,
            "is_loaded": self.is_loaded,
            "weights_path": self.weights_path,
            "total_calls": self.total_calls,
            "last_latency_ms": round(self.last_latency_ms, 2),
            "avg_latency_ms": avg_lat,
        }

    def _track_call(self, latency_ms: float):
        """Helper to maintain accurate runtime latency telemetry."""
        self.total_calls += 1
        self.last_latency_ms = latency_ms
        self.total_latency_ms += latency_ms
