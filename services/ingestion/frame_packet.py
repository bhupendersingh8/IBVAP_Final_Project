"""
IBVAP Canonical Source-Agnostic FramePacket Specification
=========================================================
Grand Finale Master Architecture - Section 3
Standardizes all video sources into an identical, immutable data contract.
No AI model or downstream pipeline stage directly depends on source hardware.
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import numpy as np


class SourceType(str, Enum):
    """Canonical video ingestion source types."""
    WEBCAM = "WEBCAM"
    VIDEO_FILE = "VIDEO_FILE"
    RTSP = "RTSP"
    MEDIAMTX = "MEDIAMTX"


@dataclass
class FramePacket:
    """
    Canonical source-agnostic frame packet passed across the entire IBVAP pipeline.
    
    Invariants:
    1. Every source enters the SAME canonical FramePacket pipeline.
    2. Models and algorithms process FramePacket, never raw camera handles.
    3. Retains full provenance, hardware timestamps, and metadata.
    """
    camera_id: str
    frame_id: int
    source_type: SourceType
    timestamp: float  # Unix epoch timestamp in seconds
    raw_bgr: np.ndarray  # Canonical OpenCV BGR frame (H, W, 3)
    width: int
    height: int
    fps: float = 30.0

    # Device tensors & cached intermediate representations
    gpu_tensor: Optional[Any] = None  # torch.Tensor [1, 3, H, W] on target CUDA/CPU device

    # Per-stage metadata bags
    preprocessing_metadata: Dict[str, Any] = field(default_factory=dict)
    camera_metadata: Dict[str, Any] = field(default_factory=dict)
    inference_metadata: Dict[str, Any] = field(default_factory=dict)
    tracking_metadata: Dict[str, Any] = field(default_factory=dict)
    evidence_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Validate shapes and dimensions
        if self.raw_bgr is not None and isinstance(self.raw_bgr, np.ndarray):
            h, w = self.raw_bgr.shape[:2]
            if self.width <= 0:
                self.width = w
            if self.height <= 0:
                self.height = h

        if not isinstance(self.source_type, SourceType):
            try:
                self.source_type = SourceType(str(self.source_type).upper())
            except ValueError:
                self.source_type = SourceType.RTSP

    @property
    def iso_timestamp(self) -> str:
        """Returns ISO 8601 UTC timestamp string."""
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat()

    @property
    def age_seconds(self) -> float:
        """Calculates current freshness of the frame."""
        import time
        return max(0.0, time.time() - self.timestamp)

    def is_stale(self, max_age_seconds: float = 1.0) -> bool:
        """Returns True if the frame is older than the allowed freshness limit."""
        return self.age_seconds > max_age_seconds

    def to_summary_dict(self) -> Dict[str, Any]:
        """Provides a serializable metadata summary without heavy pixel payloads."""
        return {
            "camera_id": self.camera_id,
            "frame_id": self.frame_id,
            "source_type": self.source_type.value,
            "timestamp": self.timestamp,
            "iso_timestamp": self.iso_timestamp,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "age_seconds": round(self.age_seconds, 4),
            "has_gpu_tensor": self.gpu_tensor is not None,
            "preprocessing": self.preprocessing_metadata,
            "camera": self.camera_metadata,
            "inference": self.inference_metadata,
            "tracking": self.tracking_metadata,
            "evidence": self.evidence_metadata,
        }
