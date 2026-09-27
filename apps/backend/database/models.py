import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Float, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .connection import Base

def utcnow():
    return datetime.now(timezone.utc)

class Role(Base):
    __tablename__ = "roles"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, index=True)
    description = Column(String)
    created_at = Column(DateTime, default=utcnow)
    
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role_id = Column(String, ForeignKey("roles.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    last_login_at = Column(DateTime, nullable=True)

class Camera(Base):
    __tablename__ = "cameras"
    id = Column(String, primary_key=True) # e.g. CAM-01
    name = Column(String)
    rtsp_url_hash = Column(String) # Hashed to avoid plaintext exposure in DB
    scenario = Column(String)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class Zone(Base):
    __tablename__ = "zones"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id = Column(String, ForeignKey("cameras.id"), index=True)
    name = Column(String)
    zone_type = Column(String) # LINE, POLYGON, etc
    points_json = Column(JSON)
    enabled = Column(Boolean, default=True)
    color = Column(String, default="#FF0000")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class Event(Base):
    __tablename__ = "events"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id = Column(String, ForeignKey("cameras.id"), index=True)
    track_id = Column(Integer, nullable=True)
    zone_id = Column(String, ForeignKey("zones.id"), nullable=True)
    event_type = Column(String)
    severity = Column(String, index=True)
    confidence = Column(Float)
    explanation = Column(Text)
    contributing_signals_json = Column(JSON)
    model_name = Column(String)
    model_version = Column(String)
    timestamp = Column(DateTime, index=True)
    created_at = Column(DateTime, default=utcnow)

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id = Column(String, ForeignKey("cameras.id"), index=True)
    event_id = Column(String, ForeignKey("events.id"))
    timestamp = Column(DateTime, index=True)
    event_type = Column(String)
    severity = Column(String, index=True)
    model_version = Column(String)
    confidence = Column(Float)
    evidence_reference = Column(String, nullable=True)
    sha256 = Column(String, nullable=True)
    status = Column(String, default="NEW", index=True) # NEW, ACKNOWLEDGED, INVESTIGATING, RESOLVED
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey("incidents.id"), index=True)
    file_path = Column(String)
    file_type = Column(String) # image, video
    sha256 = Column(String)
    file_size_bytes = Column(Integer)
    created_at = Column(DateTime, default=utcnow)

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey("incidents.id"), index=True)
    operator_id = Column(String, ForeignKey("users.id"))
    label = Column(String) # TRUE_INTRUSION, FALSE_ALARM, UNSURE
    timestamp = Column(DateTime, default=utcnow)
    model_version = Column(String)
    prediction_confidence = Column(Float)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

class ModelRegistry(Base):
    __tablename__ = "models"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    version = Column(String, unique=True)
    state = Column(String) # CANDIDATE, VALIDATED, CANARY, PRODUCTION, REJECTED
    file_path_hash = Column(String)
    model_hash = Column(String)
    trained_at = Column(DateTime, nullable=True)
    deployed_at = Column(DateTime, nullable=True)
    dataset_version = Column(String)
    training_config_json = Column(JSON)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, index=True)
    resource_type = Column(String)
    resource_id = Column(String)
    result = Column(String) # success, failure
    details_json = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    reference_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=utcnow, index=True)

class SystemHealth(Base):
    __tablename__ = "system_health"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    service_name = Column(String, index=True)
    status = Column(String)
    details_json = Column(JSON)
    checked_at = Column(DateTime, default=utcnow)

class ANPRObservation(Base):
    __tablename__ = "anpr_observations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id = Column(String, ForeignKey("cameras.id"), index=True)
    track_id = Column(Integer, index=True)
    vehicle_class = Column(String)
    plate_text = Column(String, index=True, nullable=True)
    plate_confidence = Column(Float, default=0.0)
    plate_bbox_json = Column(JSON, nullable=True)
    status = Column(String, default="CANDIDATE")
    consistent_readings = Column(Integer, default=1)
    timestamp = Column(DateTime, default=utcnow, index=True)
    evidence_path = Column(String, nullable=True)
    evidence_sha256 = Column(String, nullable=True)
    model_version = Column(String, default="1.0.0")
    ocr_engine = Column(String, default="easyocr")
    created_at = Column(DateTime, default=utcnow)

class HashChainBlock(Base):
    __tablename__ = "evidence_hash_chain"
    sequence_id = Column(Integer, primary_key=True, autoincrement=True)
    record_hash = Column(String, unique=True, index=True)
    previous_hash = Column(String)
    event_id = Column(String, index=True)
    incident_id = Column(String, ForeignKey("incidents.id"), index=True)
    evidence_sha256 = Column(String)
    camera_id = Column(String)
    timestamp = Column(DateTime, default=utcnow)
    payload_json = Column(Text)

