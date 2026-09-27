import pytest
from starlette.testclient import TestClient
from apps.backend.main import app
from services.agents.tactical_ai_engine import TacticalAIEngine

def test_copilot_advanced_chat_endpoint():
    client = TestClient(app)
    payload = {
        "messages": [
            {"role": "user", "content": "What is the standard operating procedure for a night perimeter breach?"}
        ]
    }
    resp = client.post("/api/v1/copilot/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert "Standard Operating Procedure" in data["reply"]
    assert "Perimeter" in data["reply"]
    assert data["source"] in ("local_tactical_engine", "openai_chatgpt", "nvidia_nim")

def test_copilot_cv_ai_knowledge():
    client = TestClient(app)
    # Query YOLOv8
    resp = client.post("/api/v1/copilot/query", json={"query": "Explain how YOLOv8 works in this system"})
    assert resp.status_code == 200
    data = resp.json()
    assert "YOLOv8" in data.get("answer", "")
    assert "C2f" in data.get("answer", "")

    # Query ByteTrack
    resp2 = client.post("/api/v1/copilot/query", json={"query": "How does ByteTrack handle occlusion?"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "ByteTrack" in data2.get("answer", "")
    assert "Kalman" in data2.get("answer", "")

def test_copilot_action_intent_proposal():
    client = TestClient(app)
    resp = client.post("/api/v1/copilot/query", json={"query": "Please switch to webcam"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("action") is not None
    assert data["action"]["action_type"] == "switch_camera"
    assert data["action"]["camera_id"] == "WEBCAM-01"

def test_copilot_config_update():
    client = TestClient(app)
    # Get config
    get_resp = client.get("/api/v1/copilot/config")
    assert get_resp.status_code == 200
    cfg = get_resp.json()
    assert "provider" in cfg

    # Update config
    post_resp = client.post("/api/v1/copilot/config", json={
        "provider": "offline",
        "model": "ibvap_tactical_brain_v2"
    })
    assert post_resp.status_code == 200
    updated = post_resp.json()
    assert updated["status"] == "updated"
    assert updated["current_config"]["provider"] == "offline"
