from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime

class ZoneType(Enum):
    LINE = "LINE"
    POLYGON = "POLYGON"
    RESTRICTED_ZONE = "RESTRICTED_ZONE"
    EXCLUSION_ZONE = "EXCLUSION_ZONE"

@dataclass
class Point:
    x: float  # Normalized 0-1
    y: float  # Normalized 0-1

@dataclass
class Zone:
    zone_id: str
    name: str
    camera_id: str
    zone_type: ZoneType
    points: List[Point]
    enabled: bool = True
    color: str = "#FF0000"

class EventType(Enum):
    LINE_CROSSING = "LINE_CROSSING"
    ZONE_ENTRY = "ZONE_ENTRY"
    ZONE_EXIT = "ZONE_EXIT"
    ZONE_PRESENCE = "ZONE_PRESENCE"
    LOITERING_CANDIDATE = "LOITERING_CANDIDATE"

@dataclass
class SpatialEvent:
    event_id: str
    camera_id: str
    track_id: int
    zone_id: str
    event_type: EventType
    timestamp: datetime
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""  # Human readable reason
