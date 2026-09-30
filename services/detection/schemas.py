from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

@dataclass
class BBox:
    x1: float  # Normalized 0-1 or pixel coords
    y1: float  # Normalized 0-1 or pixel coords
    x2: float  # Normalized 0-1 or pixel coords
    y2: float  # Normalized 0-1 or pixel coords

    def __post_init__(self):
        if self.x1 < 0.0 or self.y1 < 0.0 or self.x2 < 0.0 or self.y2 < 0.0:
            raise ValueError("BBox coordinates must be non-negative")
        if self.x1 >= self.x2 or self.y1 >= self.y2:
            raise ValueError(f"Invalid BBox coordinates: x1 < x2 and y1 < y2 required. Got {self}")

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def center_x(self) -> float:
        return self.x1 + (self.width / 2)

    @property
    def center_y(self) -> float:
        return self.y1 + (self.height / 2)

    @property
    def area(self) -> float:
        return self.width * self.height
        
    def to_dict(self) -> Dict[str, float]:
        return {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2}

@dataclass
class Detection:
    bbox: BBox
    class_name: str = "person"
    confidence: float = 0.9
    camera_id: str = "cam_01"
    frame_id: int = 1
    timestamp: datetime = None
    model_name: str = "yolov8n"
    model_version: str = "1.0.0"
    inference_latency_ms: float = 0.0
    subclass: Optional[str] = None
    class_id: int = 0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "frame_id": self.frame_id,
            "timestamp": self.timestamp.isoformat(),
            "class_name": self.class_name,
            "subclass": self.subclass,
            "confidence": round(self.confidence, 4),
            "bbox": self.bbox.to_dict(),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "inference_latency_ms": round(self.inference_latency_ms, 2)
        }

@dataclass
class DetectionBatch:
    camera_id: str
    frame_id: int
    timestamp: datetime
    detections: List[Detection]
    total_inference_ms: float = 0.0
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None


    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "frame_id": self.frame_id,
            "timestamp": self.timestamp.isoformat(),
            "total_inference_ms": round(self.total_inference_ms, 2),
            "detections": [d.to_dict() for d in self.detections]
        }
