import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime

class Severity(Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class CorrelatedEvent:
    event_id: str
    camera_id: str
    timestamp: datetime
    severity: Severity
    event_type: str
    track_id: Optional[int]
    zone_id: Optional[str]
    activity: Optional[str]
    confidence: float
    explanation: str
    contributing_signals: List[str] = field(default_factory=list)
    model_name: str = "unknown"
    model_version: str = "unknown"

@dataclass
class IncidentRecord:
    incident_id: str
    camera_id: str
    timestamp: datetime
    event_type: str
    severity: Severity
    model_version: str
    confidence: float
    evidence_reference: Optional[str]
    sha256: Optional[str]
    created_at: datetime
    acknowledged: bool
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
