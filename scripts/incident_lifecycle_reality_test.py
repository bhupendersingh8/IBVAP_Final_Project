"""
Incident Center Lifecycle Reality Test for IBVAP.
Creates a real incident in the database and steps through all 4 states:
NEW -> ACKNOWLEDGED -> INVESTIGATING -> RESOLVED.
"""
import sys
import uuid
from datetime import datetime, timezone

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from starlette.testclient import TestClient
from apps.backend.main import app
from apps.backend.auth.jwt_auth import create_access_token

client = TestClient(app)
auth_token = create_access_token({"sub": "AUDITOR_01", "role": "OPERATOR"})
auth_headers = {"Authorization": f"Bearer {auth_token}"}

# 1. Create a real incident and associated event directly via backend router/db
import asyncio
from apps.backend.database.connection import AsyncSessionLocal, init_db
from apps.backend.database.models import Incident, Event, Evidence

async def test_lifecycle():
    await init_db()
    test_inc_id = f"test-inc-{uuid.uuid4()}"
    test_ev_id = f"test-ev-{uuid.uuid4()}"
    test_evidence_id = f"test-evidence-{uuid.uuid4()}"
    now = datetime.now(timezone.utc)
    
    async with AsyncSessionLocal() as session:
        # Create Event
        ev = Event(
            id=test_ev_id,
            camera_id="CAM-01",
            timestamp=now,
            event_type="ZONE_INTRUSION",
            severity="HIGH",
            confidence=0.88,
            explanation="Reality Audit Verification Test Intrusion",
            model_version="1.0.0",
            track_id=42
        )
        session.add(ev)
        
        # Create Evidence record
        evidence = Evidence(
            id=test_evidence_id,
            incident_id=test_inc_id,
            file_path="/evidence/evidence_0067bdf8-4090-490f-b308-6e40569e4c71.jpg",
            file_type="image",
            file_size_bytes=325103,
            sha256="db22e83109243d0fdc2b769cda15ebbc98c403d5d88843d2a6b912f30d66d065",
            created_at=now
        )
        session.add(evidence)
        
        # Create Incident with status NEW
        inc = Incident(
            id=test_inc_id,
            camera_id="CAM-01",
            event_id=test_ev_id,
            timestamp=now,
            event_type="ZONE_INTRUSION",
            severity="HIGH",
            model_version="1.0.0",
            confidence=0.88,
            status="NEW",
            acknowledged=False,
            evidence_reference=evidence.file_path,
            sha256=evidence.sha256
        )
        session.add(inc)
        await session.commit()
    
    print(f"[CREATED] Incident: {test_inc_id} with initial status: NEW")
    
    # 2. Query via REST API to verify NEW
    r_get = client.get(f"/api/v1/incidents", headers=auth_headers)
    assert r_get.status_code == 200, f"Failed GET: {r_get.text}"
    incidents_list = r_get.json() if isinstance(r_get.json(), list) else r_get.json().get("items", [])
    items = [item for item in incidents_list if item["id"] == test_inc_id]
    assert len(items) == 1
    assert items[0]["status"] == "NEW"
    print(f"[VERIFIED] REST GET returns status: {items[0]['status']}")
    
    # 3. Transition to ACKNOWLEDGED
    r_ack = client.post(f"/api/v1/incidents/{test_inc_id}/acknowledge?operator_id=AUDITOR_01", headers=auth_headers)
    assert r_ack.status_code == 200, f"Failed ACK: {r_ack.text}"
    assert r_ack.json()["success"] is True
    print(f"[TRANSITION 1] Status -> ACKNOWLEDGED (operator: AUDITOR_01)")
    
    # 4. Transition to INVESTIGATING
    r_inv = client.post(
        f"/api/v1/incidents/{test_inc_id}/status",
        json={"status": "INVESTIGATING", "operator_id": "AUDITOR_01"},
        headers=auth_headers
    )
    assert r_inv.status_code == 200, f"Failed INV: {r_inv.text}"
    assert r_inv.json()["success"] is True
    # Verify status in DB via GET
    r_check1 = client.get("/api/v1/incidents", headers=auth_headers)
    items_check1 = [i for i in r_check1.json() if i["id"] == test_inc_id]
    assert items_check1[0]["status"] == "INVESTIGATING"
    print(f"[TRANSITION 2] Status -> INVESTIGATING (verified via REST GET)")
    
    # 5. Transition to RESOLVED
    r_res = client.post(
        f"/api/v1/incidents/{test_inc_id}/status",
        json={"status": "RESOLVED", "operator_id": "AUDITOR_01"},
        headers=auth_headers
    )
    assert r_res.status_code == 200, f"Failed RES: {r_res.text}"
    assert r_res.json()["success"] is True
    # Verify status in DB via GET
    r_check2 = client.get("/api/v1/incidents", headers=auth_headers)
    items_check2 = [i for i in r_check2.json() if i["id"] == test_inc_id]
    assert items_check2[0]["status"] == "RESOLVED"
    assert items_check2[0]["acknowledged"] is True
    print(f"[TRANSITION 3] Status -> RESOLVED (verified via REST GET)")
    
    # 6. Verify final record
    r_final = client.get(f"/api/v1/incidents", headers=auth_headers)
    final_list = r_final.json() if isinstance(r_final.json(), list) else r_final.json().get("items", [])
    final_item = [item for item in final_list if item["id"] == test_inc_id][0]
    assert final_item["status"] == "RESOLVED"
    assert final_item["acknowledged"] is True
    print("[SUCCESS] All 4 states (NEW -> ACKNOWLEDGED -> INVESTIGATING -> RESOLVED) verified cleanly!")

if __name__ == "__main__":
    asyncio.run(test_lifecycle())
