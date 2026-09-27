import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from apps.backend.main import app
from services.agents.local_agents import (
    LocalAgentManager,
    SystemSupervisorAgent,
    CameraHealthAgent,
    IncidentCorrelationAgent,
    AgentRecommendation,
    UrgencyLevel,
    RecommendationStatus,
    FORBIDDEN_ACTIONS,
)

@pytest.fixture
def agent_manager():
    # Fresh instance for isolation
    mgr = LocalAgentManager()
    LocalAgentManager._instance = mgr
    return mgr

def test_system_supervisor_agent(agent_manager):
    supervisor = SystemSupervisorAgent()
    obs = supervisor.observe({"vram_used_mb": 3800.0, "vram_total_mb": 4096.0, "ram_percent": 95.0})
    assert obs["vram_used_mb"] == 3800.0

    recs = supervisor.analyze(obs)
    assert len(recs) == 2
    actions = [r.proposed_action for r in recs]
    assert "throttle_specialist_batch" in actions
    assert "flush_dormant_buffers" in actions

def test_camera_health_agent(agent_manager):
    cam_agent = CameraHealthAgent()
    obs = {
        "CAM_01": {"state": "OFFLINE", "fps": 0.0, "reconnect_count": 4},
        "CAM_02": {"state": "DEGRADED", "fps": 1.5, "reconnect_count": 0},
        "CAM_03": {"state": "ONLINE", "fps": 25.0, "reconnect_count": 0},
    }
    recs = cam_agent.analyze(obs)
    assert len(recs) == 2
    actions = [r.proposed_action for r in recs]
    assert "restart_camera_pipeline" in actions
    assert "switch_substream_resolution" in actions

def test_incident_correlation_agent(agent_manager):
    corr_agent = IncidentCorrelationAgent()
    incidents = [
        {"camera_id": "SECTOR_ALPHA", "event_type": "restricted_zone_intrusion", "timestamp": "2026-09-07T12:00:00"},
        {"camera_id": "SECTOR_BRAVO", "event_type": "virtual_fence_intrusion", "timestamp": "2026-09-07T12:00:30"},
    ]
    recs = corr_agent.analyze(incidents)
    assert len(recs) == 1
    assert recs[0].urgency == UrgencyLevel.CRITICAL
    assert recs[0].proposed_action == "escalate_sector_alarm"

def test_full_agent_manager_loop_and_safety_gate(agent_manager):
    # 1. Run cycle (OBSERVE -> ANALYZE -> RECOMMEND)
    new_recs = agent_manager.run_cycle(
        telemetry={"vram_used_mb": 3900.0, "vram_total_mb": 4096.0},
        camera_health={"CAM_OUTPOST": {"state": "OFFLINE", "fps": 0.0, "reconnect_count": 5}},
        incidents=[],
    )
    assert len(new_recs) >= 2
    rec = new_recs[0]
    rec_id = rec.recommendation_id

    # 2. Try to EXECUTE without approval -> MUST FAIL
    with pytest.raises(PermissionError):
        agent_manager.execute_recommendation(rec_id)

    # 3. Human Approval Gate
    approved = agent_manager.approve_recommendation(
        recommendation_id=rec_id,
        operator_id="COMMANDER_SHARMA",
        notes="Approved throttling for sector stability"
    )
    assert approved["status"] == RecommendationStatus.APPROVED.value
    assert approved["approved_by"] == "COMMANDER_SHARMA"

    # 4. Safe Execution
    executed = agent_manager.execute_recommendation(rec_id)
    assert executed["status"] == RecommendationStatus.EXECUTED.value
    assert "Successfully executed" in executed["execution_result"]

def test_safety_boundary_blocks_forbidden_actions(agent_manager):
    # Craft a malicious/forbidden recommendation proposing model deletion
    malicious_rec = AgentRecommendation(
        recommendation_id="rogue_001",
        agent_name="RogueAgent",
        created_at=datetime.now(timezone.utc),
        urgency=UrgencyLevel.CRITICAL,
        title="Unauthorized Model Wipe",
        description="Attempt to delete core detection model",
        proposed_action="delete_model",
        action_parameters={"target": "yolov8n.engine"},
    )
    agent_manager.recommendations[malicious_rec.recommendation_id] = malicious_rec

    # Operator approves without noticing
    res = agent_manager.approve_recommendation("rogue_001", operator_id="INATTENTIVE_USER")
    # Safety invariant must automatically reject and block
    assert res["status"] == RecommendationStatus.REJECTED.value
    assert "Blocked by Safety Invariant" in res["execution_result"]

    # Verify execution is blocked
    with pytest.raises(PermissionError):
        agent_manager.execute_recommendation("rogue_001")

def test_agents_api_endpoints():
    client = TestClient(app)

    # Trigger cycle via API
    resp = client.post("/api/v1/agents/cycle", json={
        "telemetry": {"vram_used_mb": 3800.0, "vram_total_mb": 4096.0},
        "camera_health": {},
        "incidents": []
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "generated_recommendations" in data

    # List pending recommendations
    list_resp = client.get("/api/v1/agents/recommendations?pending_only=true")
    assert list_resp.status_code == 200
    pending = list_resp.json()
    assert len(pending) > 0
    rec_id = pending[0]["recommendation_id"]

    # Approve recommendation
    app_resp = client.post(f"/api/v1/agents/recommendations/{rec_id}/approve", json={
        "operator_id": "OFFICER_01",
        "notes": "Verified safe operational action"
    })
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "APPROVED"

    # Execute recommendation
    exec_resp = client.post(f"/api/v1/agents/recommendations/{rec_id}/execute")
    assert exec_resp.status_code == 200
    assert exec_resp.json()["status"] == "EXECUTED"

    # Audit log
    audit_resp = client.get("/api/v1/agents/audit")
    assert audit_resp.status_code == 200
    assert len(audit_resp.json()["audit_log"]) > 0
