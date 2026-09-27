from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from ..detection.schemas import BBox

class TrackState(Enum):
    ACTIVE = "ACTIVE"
    LOST = "LOST"
    REMOVED = "REMOVED"

@dataclass
class TrackPoint:
    timestamp: datetime
    bbox: BBox
    center_x: float
    center_y: float
    confidence: float

    def __post_init__(self):
        if self.timestamp.tzinfo is None:
            raise ValueError("TrackPoint timestamp must be timezone-aware (UTC).")

@dataclass
class Track:
    track_id: int
    camera_id: str
    class_name: str
    state: TrackState
    bbox: BBox
    center_x: float
    center_y: float
    first_seen: datetime
    last_seen: datetime
    subclass: Optional[str] = None
    confidence_history: List[float] = field(default_factory=list)
    trajectory: List[TrackPoint] = field(default_factory=list)
    age_frames: int = 0

    def __post_init__(self):
        if self.first_seen.tzinfo is None or self.last_seen.tzinfo is None:
            raise ValueError("Track timestamps must be timezone-aware (UTC).")
    
    @property
    def duration_seconds(self) -> float:
        return (self.last_seen - self.first_seen).total_seconds()
        
    @property
    def avg_confidence(self) -> float:
        if not self.confidence_history:
            return 0.0
        return sum(self.confidence_history) / len(self.confidence_history)

    @property
    def distance_traveled(self) -> float:
        if len(self.trajectory) < 2:
            return 0.0
        dist = 0.0
        for i in range(1, len(self.trajectory)):
            dx = self.trajectory[i].center_x - self.trajectory[i - 1].center_x
            dy = self.trajectory[i].center_y - self.trajectory[i - 1].center_y
            dist += (dx ** 2 + dy ** 2) ** 0.5
        return dist

@dataclass
class TrackingResult:
    camera_id: str
    frame_id: int
    timestamp: datetime
    active_tracks: List[Track] = field(default_factory=list)
    new_tracks: List[int] = field(default_factory=list)
    lost_tracks: List[int] = field(default_factory=list)

    def __post_init__(self):
        if self.timestamp.tzinfo is None:
            raise ValueError("TrackingResult timestamp must be timezone-aware (UTC).")

