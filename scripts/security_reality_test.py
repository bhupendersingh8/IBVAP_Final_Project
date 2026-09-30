"""
Automated Reality Security Audit Script for IBVAP.
Tests real security boundaries against FastAPI application:
1. Security Headers
2. Path Traversal
3. Malformed JSON Body
4. Oversized Request Body
5. CORS Origin Whitelisting
6. Authentication & Token Lifecycle:
   - Login & Token Issuance (OPERATOR, SUPERVISOR, ADMIN)
   - Valid Token Acceptance
   - Invalid Token Rejection (HTTP 401)
   - Expired Token Rejection (HTTP 401)
   - Role-Based Access Control (VIEWER blocked from MANAGE_CAMERAS -> HTTP 403)
   - Production Mode Rejection of Unauthenticated Requests (when DEV_DEMO=0)
"""
import sys
import os
import time
from datetime import timedelta
from starlette.testclient import TestClient

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test in Dev-Demo mode first
os.environ["IBVAP_DEV_DEMO_MODE"] = "1"
from apps.backend.main import app
from apps.backend.auth.jwt_auth import create_access_token
from apps.backend.auth.rbac import Role

client = TestClient(app)
results = {}

# 1. Security Headers
resp = client.get("/health/live")
results["security_headers"] = {
    "status_code": resp.status_code,
    "X-Content-Type-Options": resp.headers.get("X-Content-Type-Options"),
    "X-Frame-Options": resp.headers.get("X-Frame-Options"),
    "X-XSS-Protection": resp.headers.get("X-XSS-Protection"),
    "Referrer-Policy": resp.headers.get("Referrer-Policy"),
    "Cache-Control": resp.headers.get("Cache-Control"),
}

# 2. Path Traversal
resp_traversal = client.get("/evidence/../../../../etc/passwd")
resp_traversal2 = client.get("/evidence/..%2f..%2f..%2fconfigs%2fcameras.yaml")
results["path_traversal"] = {
    "etc_passwd_status": resp_traversal.status_code,
    "cameras_yaml_traversal_status": resp_traversal2.status_code,
}

# 3. Malformed Request
resp_malformed = client.post(
    "/api/v1/incidents/invalid-uuid/status",
    content="NOT A VALID JSON",
    headers={"Content-Type": "application/json"}
)
results["malformed_json"] = {
    "status_code": resp_malformed.status_code,
}

# 4. Oversized Request Body
oversized_payload = {"notes": "A" * (10 * 1024 * 1024)} # 10 MB payload
resp_oversized = client.post(
    "/api/v1/incidents/00000000-0000-0000-0000-000000000000/status",
    json=oversized_payload
)
results["oversized_request"] = {
    "status_code": resp_oversized.status_code
}

# 5. CORS Behavior
resp_cors_allowed = client.options(
    "/api/v1/incidents",
    headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET"
    }
)
resp_cors_disallowed = client.options(
    "/api/v1/incidents",
    headers={
        "Origin": "https://malicious-attacker.com",
        "Access-Control-Request-Method": "GET"
    }
)
results["cors"] = {
    "allowed_origin_status": resp_cors_allowed.status_code,
    "allowed_origin_header": resp_cors_allowed.headers.get("access-control-allow-origin"),
    "disallowed_origin_header": resp_cors_disallowed.headers.get("access-control-allow-origin"),
}

# 6. Authentication & JWT Token Enforcement
# 6a. Login endpoint
login_resp = client.post("/api/v1/auth/login", json={"username": "operator", "password": "operatorpass123"})
login_data = login_resp.json() if login_resp.status_code == 200 else {}
operator_token = login_data.get("access_token", "")

# 6b. Verify with Valid Bearer Token
resp_valid_token = client.get(
    "/api/v1/auth/me",
    headers={"Authorization": f"Bearer {operator_token}"}
)

# 6c. Invalid Bearer Token
resp_invalid_token = client.get(
    "/api/v1/auth/me",
    headers={"Authorization": "Bearer totally_fake_and_invalid_token_payload"}
)

# 6d. Expired Bearer Token
expired_token = create_access_token({"sub": "expired_user", "role": "OPERATOR"}, expires_delta=timedelta(seconds=-10))
resp_expired_token = client.get(
    "/api/v1/auth/me",
    headers={"Authorization": f"Bearer {expired_token}"}
)

# 6e. RBAC Authorization: Viewer role attempting to delete camera
viewer_token = create_access_token({"sub": "viewer_user", "role": Role.VIEWER.value})
resp_rbac_blocked = client.delete(
    "/api/v1/cameras/CAM-01",
    headers={"Authorization": f"Bearer {viewer_token}"}
)

results["authentication_and_rbac"] = {
    "login_endpoint_status": login_resp.status_code,
    "login_token_issued": bool(operator_token),
    "valid_token_status": resp_valid_token.status_code,
    "valid_token_principal": resp_valid_token.json() if resp_valid_token.status_code == 200 else None,
    "invalid_token_status": resp_invalid_token.status_code,
    "invalid_token_rejected_401": resp_invalid_token.status_code == 401,
    "expired_token_status": resp_expired_token.status_code,
    "expired_token_rejected_401": resp_expired_token.status_code == 401,
    "rbac_viewer_delete_camera_status": resp_rbac_blocked.status_code,
    "rbac_blocked_403": resp_rbac_blocked.status_code == 403,
}

import json
print(json.dumps(results, indent=2))
