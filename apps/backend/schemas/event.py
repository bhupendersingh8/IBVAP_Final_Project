from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    camera_id: str
    event_type: str
    severity: str
    timestamp: datetime
    confidence: float
    explanation: Optional[str] = None

class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    camera_id: str
    timestamp: datetime
    event_type: str
    severity: str
    confidence: float
    track_id: Optional[int] = None
    explanation: Optional[str] = None
    evidence_reference: Optional[str] = None
    sha256: Optional[str] = None
    status: Optional[str] = "NEW" # NEW, ACKNOWLEDGED, INVESTIGATING, RESOLVED
    acknowledged: bool
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

class IncidentStatusUpdate(BaseModel):
    status: str # NEW, ACKNOWLEDGED, INVESTIGATING, RESOLVED
    operator_id: Optional[str] = None

class FeedbackCreate(BaseModel):
    incident_id: str
    label: str  # TRUE_INTRUSION, FALSE_ALARM, UNSURE
    notes: Optional[str] = None

class EvidenceVerifyRequest(BaseModel):
    incident_id: Optional[str] = None
    file_path: Optional[str] = None
    expected_sha256: Optional[str] = None

class EvidenceVerifyResponse(BaseModel):
    incident_id: Optional[str] = None
    file_path: Optional[str] = None
    recorded_sha256: str
    computed_sha256: str
    integrity_verified: bool
    status: str  # TAMPER_EVIDENT_VALID, TAMPER_DETECTED, FILE_NOT_FOUND, INCIDENT_NOT_FOUND
    message: str
