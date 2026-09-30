"""
FastAPI Router for Local Edge Autonomous Agents.
Exposes endpoints for the OBSERVE -> ANALYZE -> RECOMMEND -> HUMAN APPROVAL -> EXECUTE loop.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import structlog

from services.agents.local_agents import LocalAgentManager, UrgencyLevel, RecommendationStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/agents", tags=["Local Autonomous Agents"])


class CycleRequest(BaseModel):
    telemetry: Optional[Dict[str, Any]] = None
    camera_health: Optional[Dict[str, Any]] = None
    incidents: Optional[List[Dict[str, Any]]] = None


class ApprovalRequest(BaseModel):
    operator_id: str = Field(..., description="Human operator badge/username")
    notes: Optional[str] = Field("", description="Operational sign-off notes")


class RejectionRequest(BaseModel):
    operator_id: str = Field(..., description="Human operator badge/username")
    reason: Optional[str] = Field("", description="Reason for rejecting proposed action")


@router.get("/recommendations")
def list_recommendations(pending_only: bool = True):
    """List agent recommendations requiring human review or complete history."""
    mgr = LocalAgentManager.get_instance()
    if pending_only:
        return mgr.get_pending_recommendations()
    return mgr.get_all_recommendations()


@router.post("/cycle")
def trigger_agent_cycle(req: CycleRequest):
    """Trigger an OBSERVE -> ANALYZE -> RECOMMEND cycle across all local agents."""
    mgr = LocalAgentManager.get_instance()
    new_recs = mgr.run_cycle(
        telemetry=req.telemetry,
        camera_health=req.camera_health,
        incidents=req.incidents,
    )
    return {"generated_recommendations": [r.to_dict() for r in new_recs]}


@router.post("/recommendations/{recommendation_id}/approve")
def approve_recommendation(recommendation_id: str, req: ApprovalRequest):
    """Human approval gate: Operator signs off on a proposed action."""
    mgr = LocalAgentManager.get_instance()
    try:
        updated = mgr.approve_recommendation(recommendation_id, req.operator_id, req.notes)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/recommendations/{recommendation_id}/reject")
def reject_recommendation(recommendation_id: str, req: RejectionRequest):
    """Human operator rejects a proposed recommendation."""
    mgr = LocalAgentManager.get_instance()
    try:
        updated = mgr.reject_recommendation(recommendation_id, req.operator_id, req.reason)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/recommendations/{recommendation_id}/execute")
def execute_recommendation(recommendation_id: str):
    """Execute an approved recommendation. Strictly rejects unapproved or forbidden actions."""
    mgr = LocalAgentManager.get_instance()
    try:
        result = mgr.execute_recommendation(recommendation_id)
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/audit")
def get_agent_audit_log():
    """Retrieve tamper-evident audit log of all agent recommendations and executions."""
    mgr = LocalAgentManager.get_instance()
    return {"audit_log": mgr.audit_log}
