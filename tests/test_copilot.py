import pytest
from starlette.testclient import TestClient
from apps.backend.main import app

def test_copilot_sitrep():
    client = TestClient(app)
    resp = client.post("/api/v1/copilot/sitrep", json={"shift_notes": "Night patrol shift"})
    assert resp.status_code == 200
    data = resp.json()
    assert "briefing" in data
    assert data.get("status") == "success"
    assert "threat_level" in data or "TACTICAL" in data.get("briefing", "")

def test_copilot_query_vehicles_and_status():
    client = TestClient(app)
    # Query trucks
    resp = client.post("/api/v1/copilot/query", json={"query": "Are there any trucks detected?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Truck Intelligence" in data.get("answer", "")

    # Query plates
    resp2 = client.post("/api/v1/copilot/query", json={"query": "Show me verified license plates"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "ANPR Plate Records" in data2.get("answer", "")
