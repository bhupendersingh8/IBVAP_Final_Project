from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from datetime import datetime, timezone

from ..database.connection import get_db
from ..database.models import Incident, Event, Feedback
from ..schemas.event import IncidentResponse, EventResponse, FeedbackCreate, IncidentStatusUpdate
from ..schemas.common import SuccessResponse
from ..auth.jwt_auth import require_auth, require_permission
from ..auth.rbac import Role, Permission

router = APIRouter(prefix="/api/v1", tags=["Incidents & Events"])

@router.get("/incidents", response_model=List[IncidentResponse])
@router.get("/incidents/", response_model=List[IncidentResponse], include_in_schema=False)
async def list_incidents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    unacknowledged_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.VIEW_INCIDENTS))
):
    """Retrieve a list of correlated incidents with explanation from associated event."""
    query = select(Incident, Event.explanation, Event.track_id).outerjoin(Event, Incident.event_id == Event.id).order_by(Incident.timestamp.desc())
    
    if unacknowledged_only:
        query = query.where(Incident.acknowledged == False)
        
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    
    rows = result.all()
    incidents = []
    for inc, explanation, track_id in rows:
        ts = inc.timestamp
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        inc_dict = {
            "id": inc.id,
            "camera_id": inc.camera_id,
            "timestamp": ts,
            "event_type": inc.event_type,
            "severity": inc.severity,
            "confidence": inc.confidence,
            "track_id": track_id,
            "explanation": explanation or f"{inc.event_type} on {inc.camera_id}",
            "evidence_reference": inc.evidence_reference,
            "sha256": inc.sha256,
            "status": inc.status or ("ACKNOWLEDGED" if inc.acknowledged else "NEW"),
            "acknowledged": inc.acknowledged,
            "acknowledged_by": inc.acknowledged_by,
            "acknowledged_at": inc.acknowledged_at
        }
        incidents.append(IncidentResponse(**inc_dict))

    return incidents
 
@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.VIEW_INCIDENTS))
):
    """Retrieve details for a specific incident by ID."""
    query = select(Incident, Event.explanation, Event.track_id).outerjoin(
        Event, Incident.event_id == Event.id
    ).where(Incident.id == incident_id)
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")

    inc, explanation, track_id = row
    ts = inc.timestamp
    if ts and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return IncidentResponse(
        id=inc.id,
        camera_id=inc.camera_id,
        timestamp=ts,
        event_type=inc.event_type,
        severity=inc.severity,
        confidence=inc.confidence,
        track_id=track_id,
        explanation=explanation or f"{inc.event_type} on {inc.camera_id}",
        evidence_reference=inc.evidence_reference,
        sha256=inc.sha256,
        status=inc.status or ("ACKNOWLEDGED" if inc.acknowledged else "NEW"),
        acknowledged=inc.acknowledged,
        acknowledged_by=inc.acknowledged_by,
        acknowledged_at=inc.acknowledged_at
    )

@router.post("/incidents/{incident_id}/status", response_model=SuccessResponse)
async def update_incident_status(
    incident_id: str,
    status_update: IncidentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.MANAGE_INCIDENTS))
):
    """Transition an incident lifecycle status (NEW, ACKNOWLEDGED, INVESTIGATING, RESOLVED)."""
    valid_statuses = {"NEW", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED"}
    target_status = status_update.status.upper()
    if target_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status_update.status}'. Allowed: {sorted(list(valid_statuses))}"
        )

    incident = await db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    current_status = (incident.status or "NEW").upper()

    # Enforce strict lifecycle transition rules:
    # NEW -> ACKNOWLEDGED, INVESTIGATING, RESOLVED
    # ACKNOWLEDGED -> INVESTIGATING, RESOLVED
    # INVESTIGATING -> RESOLVED, ACKNOWLEDGED
    # RESOLVED -> Only ADMIN or SUPERVISOR can reopen to INVESTIGATING
    ALLOWED_TRANSITIONS = {
        "NEW": {"ACKNOWLEDGED", "INVESTIGATING", "RESOLVED"},
        "ACKNOWLEDGED": {"INVESTIGATING", "RESOLVED"},
        "INVESTIGATING": {"RESOLVED", "ACKNOWLEDGED"},
        "RESOLVED": set() # Closed by default
    }

    if current_status == "RESOLVED":
        user_role = user.get("role", "")
        if user_role in (Role.ADMIN.value, Role.SUPERVISOR.value) and target_status in ("INVESTIGATING", "ACKNOWLEDGED"):
            pass # Authorized administrative reopen
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid transition: RESOLVED incidents cannot be modified or acknowledged without administrative reopen."
            )
    elif target_status not in ALLOWED_TRANSITIONS.get(current_status, set()) and target_status != current_status:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition from {current_status} to {target_status}."
        )

    incident.status = target_status
    if target_status in {"ACKNOWLEDGED", "INVESTIGATING", "RESOLVED"}:
        incident.acknowledged = True
        if not incident.acknowledged_at:
            incident.acknowledged_at = datetime.now(timezone.utc)
        if status_update.operator_id:
            incident.acknowledged_by = status_update.operator_id
        elif user.get("sub"):
            incident.acknowledged_by = user.get("sub")

    await db.commit()
    return SuccessResponse(success=True, message=f"Incident status updated to {target_status}")

@router.post("/incidents/{incident_id}/acknowledge", response_model=SuccessResponse)
async def acknowledge_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.ACKNOWLEDGE_INCIDENTS))
):
    """Mark an incident as acknowledged by an operator."""
    incident = await db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    incident.status = "ACKNOWLEDGED"
    incident.acknowledged = True
    incident.acknowledged_at = datetime.now(timezone.utc)
    if user.get("sub"):
        incident.acknowledged_by = user.get("sub")
    
    await db.commit()
    return SuccessResponse(success=True, message="Incident acknowledged successfully")

@router.get("/evidence/verify_ledger")
async def verify_evidence_hash_chain(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.VERIFY_EVIDENCE))
):
    """Cryptographically audits the tamper-evident SHA-256 evidence hash chain."""
    from services.evidence.hash_chain import HashChainLedger
    is_valid, corrupted_seq, message = await HashChainLedger.verify_chain(db)
    return {
        "ledger_verified": is_valid,
        "corrupted_sequence_id": corrupted_seq,
        "audit_message": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.post("/feedback", response_model=SuccessResponse)
@router.post("/events/feedback", response_model=SuccessResponse)
async def submit_feedback(
    feedback_in: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.MANAGE_INCIDENTS))
):
    """Submit human feedback for retraining (Active Learning loop)."""
    incident = await db.get(Incident, feedback_in.incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    operator_id = user.get("sub", "operator_demo")
    fb = Feedback(
        incident_id=feedback_in.incident_id,
        operator_id=operator_id,
        label=feedback_in.label,
        notes=feedback_in.notes,
        model_version=incident.model_version or "yolov8n-v1",
        prediction_confidence=incident.confidence or 0.85
    )
    db.add(fb)

    # Automatically synchronize incident status based on operator verdict
    if feedback_in.label == "FALSE_ALARM":
        incident.status = "RESOLVED"
        incident.acknowledged = True
        incident.acknowledged_by = operator_id
        incident.acknowledged_at = datetime.now(timezone.utc)
    elif feedback_in.label == "TRUE_INTRUSION":
        incident.status = "INVESTIGATING"
        incident.acknowledged = True
        incident.acknowledged_by = operator_id
        incident.acknowledged_at = datetime.now(timezone.utc)
    elif feedback_in.label == "UNSURE":
        incident.acknowledged = True

    await db.commit()
    return SuccessResponse(success=True, message=f"Feedback recorded as {feedback_in.label} for active learning")
