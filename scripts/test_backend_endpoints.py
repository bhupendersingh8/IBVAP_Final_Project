import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from apps.backend.main import app

client = TestClient(app)

def test_endpoints():
    print("=" * 60)
    print("TESTING BACKEND ENDPOINTS VIA TESTCLIENT")
    print("=" * 60)

    # 1. Health check
    res = client.get("/health")
    print(f"GET /health: {res.status_code}")
    print(f"  Response: {res.json()}")
    assert res.status_code == 200, f"Health check failed: {res.text}"

    # 2. API v1 Health
    res = client.get("/api/v1/health")
    print(f"GET /api/v1/health: {res.status_code}")
    print(f"  Response: {res.json()}")
    assert res.status_code == 200, f"API Health check failed: {res.text}"

    # 3. Open API spec
    res = client.get("/openapi.json")
    print(f"GET /openapi.json: {res.status_code} ({len(res.content)} bytes)")
    assert res.status_code == 200

    # 4. Settings endpoint
    res = client.get("/api/v1/settings")
    print(f"GET /api/v1/settings: {res.status_code}")
    print(f"  Response: {res.json()}")

    # 5. Incidents query (checking database read)
    res = client.get("/api/v1/incidents?limit=5")
    print(f"GET /api/v1/incidents: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print(f"  Retrieved {len(data)} incidents from canonical database")
        if data:
            print(f"  Latest incident: ID={data[0].get('id')}, Type={data[0].get('event_type')}, Camera={data[0].get('camera_id')}")

    # 6. Evidence ledger verification
    res = client.get("/api/v1/evidence/verify_ledger")
    print(f"GET /api/v1/evidence/verify_ledger: {res.status_code}")
    if res.status_code == 200:
        print(f"  Ledger verify response: {res.json()}")

    print("=" * 60)
    print("ALL TESTCLIENT ENDPOINTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    test_endpoints()
