from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
import numpy as np

from ..detection.schemas import BBox

class PlateStatus(str, Enum):
    UNREADABLE = "UNREADABLE"
    CANDIDATE = "CANDIDATE"              # Single reading or unconfirmed
    LOW_CONFIDENCE = "LOW_CONFIDENCE"    # Below confidence threshold or conflicting readings
    STABLE_VERIFIED = "STABLE_VERIFIED"  # Multi-frame consistent reading on same track

@dataclass
class VehicleObservation:
    vehicle_id: str
    camera_id: str
    track_id: int
    vehicle_class: str  # 'car', 'motorcycle', 'bus', 'truck'
    confidence: float
    bbox: BBox
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "camera_id": self.camera_id,
            "track_id": self.track_id,
            "vehicle_class": self.vehicle_class,
            "confidence": round(self.confidence, 4),
            "bbox": self.bbox.to_dict(),
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class PlateDetection:
    bbox: BBox
    confidence: float
    plate_crop: Optional[np.ndarray] = None
    aspect_ratio: float = 0.0

@dataclass
class OCRResult:
    raw_text: str
    normalized_text: str
    confidence: float
    processing_time_ms: float
    status: str  # 'SUCCESS', 'LOW_CONFIDENCE', 'UNREADABLE'

@dataclass
class ANPRObservation:
    observation_id: str
    camera_id: str
    track_id: int
    vehicle_class: str
    plate_text: Optional[str]
    plate_confidence: float
    status: PlateStatus
    plate_bbox: Optional[BBox] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_path: Optional[str] = None
    evidence_sha256: Optional[str] = None
    model_version: str = "1.0.0"
    ocr_engine: str = "easyocr"
    consistent_readings: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "camera_id": self.camera_id,
            "track_id": self.track_id,
            "vehicle_class": self.vehicle_class,
            "plate_text": self.plate_text,
            "plate_confidence": round(self.plate_confidence, 4),
            "status": self.status.value if isinstance(self.status, PlateStatus) else str(self.status),
            "plate_bbox": self.plate_bbox.to_dict() if self.plate_bbox else None,
            "timestamp": self.timestamp.isoformat(),
            "evidence_path": self.evidence_path,
            "evidence_sha256": self.evidence_sha256,
            "model_version": self.model_version,
            "ocr_engine": self.ocr_engine,
            "consistent_readings": self.consistent_readings
        }

@dataclass
class ANPRConfig:
    enabled: bool = True
    min_plate_confidence: float = 0.40
    min_ocr_confidence: float = 0.50
    min_plate_width: int = 35
    min_plate_height: int = 12
    ocr_interval_seconds: float = 1.0
    plate_detection_interval_seconds: float = 0.5
    anpr_cooldown_seconds: float = 20.0
    ocr_engine: str = "easyocr"
    min_consistent_frames: int = 2  # Multi-frame track consistency requirement
