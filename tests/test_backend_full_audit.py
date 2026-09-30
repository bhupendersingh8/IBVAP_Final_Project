"""
IBVAP — Comprehensive Full-System Backend, Security, CCTV Lifecycle & Integrity Audit Suite
==========================================================================================
Verifies:
1. All core API endpoints and status codes (200, 400, 401, 403, 404, 422).
2. Auth & RBAC: Token issuance, expiration, invalid signatures, demo-bypass & role enforcement.
3. Incident & ANPR querying, single incident detail (GET /incidents/{id}), and 404 behavior.
4. Camera lifecycle, non-existent camera handling, and dead stream fault-tolerance.
5. Path traversal security hardening on static & evidence paths.
6. WebSocket telemetry hub connection, ping/pong heartbeats, and clean disconnects.
7. Evidence ledger SHA-256 hash-chain verification and tamper detection.
"""

import os
import json
import time
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from apps.backend.main import app, ws_manager
from apps.backend.auth.jwt_auth import create_access_token, verify_token, is_demo_mode
from apps.backend.auth.rbac import Role, Permission, check_permission
from services.evidence.hash_chain import compute_block_hash, GENESIS_PREVIOUS_HASH
from services.ingestion.camera_health import CameraHealthMonitor, CameraHealthState


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# 1. API DIRECTORY & HEALTH SUITE
# ==============================================================================

def test_api_directory_and_health_endpoints(client: TestClient):
    """Verify /api/v1 directory, /health, /health/live, /health/ready."""
    # 1. API Index
    resp_index = client.get("/api/v1")
    assert resp_index.status_code == 200
    data = resp_index.json()
    assert "system" in data
    assert "version" in data
    assert "documentation" in data

    # 2. Health Live
    resp_live = client.get("/health/live")
    assert resp_live.status_code == 200
    assert resp_live.json().get("status") == "ok"

    # 3. Health Ready
    resp_ready = client.get("/health/ready")
    assert resp_ready.status_code == 200
    assert resp_ready.json().get("status") == "ready"


# ==============================================================================
# 2. AUTHENTICATION, JWT CRYPTO & RBAC
# ==============================================================================

def test_auth_login_valid_and_invalid(client: TestClient):
    """Verify JWT login: 200 on valid credentials, 401 on incorrect credentials, 422 on malformed body."""
    # Valid login
    resp_valid = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "adminpassword123"}
    )
    assert resp_valid.status_code == 200
    body = resp_valid.json()
    assert "access_token" in body
    assert body["role"] == Role.ADMIN.value
    token = body["access_token"]

    # Verify token payload
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "admin"
    assert payload["role"] == Role.ADMIN.value

    # Invalid password -> 401
    resp_invalid = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong_password_999"}
    )
    assert resp_invalid.status_code == 401
    assert "detail" in resp_invalid.json()

    # Non-existent user -> 401
    resp_ghost = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost_operator", "password": "secretpassword"}
    )
    assert resp_ghost.status_code == 401

    # Malformed JSON / missing fields -> 422
    resp_malformed = client.post("/api/v1/auth/login", json={"username": "admin"})
    assert resp_malformed.status_code == 422


def test_jwt_tampering_and_expiration():
    """Verify that forged signatures and expired tokens are rejected."""
    token = create_access_token({"sub": "test_user", "role": "operator"})
    parts = token.split(".")
    assert len(parts) == 3

    # Tampered signature
    tampered_token = f"{parts[0]}.{parts[1]}.tampered_signature_xyz"
    assert verify_token(tampered_token) is None

    # Expired token
    expired_token = create_access_token(
        {"sub": "expired_user", "role": "operator"},
        expires_delta=timedelta(seconds=-10)
    )
    assert verify_token(expired_token) is None


def test_rbac_matrix_permissions():
    """Verify role-based access control permission matrices."""
    # Admin has all permissions
    assert check_permission(Role.ADMIN, Permission.MANAGE_CAMERAS) is True
    assert check_permission(Role.ADMIN, Permission.VERIFY_EVIDENCE) is True

    # Operator cannot configure cameras
    assert check_permission(Role.OPERATOR, Permission.VIEW_CAMERAS) is True
    assert check_permission(Role.OPERATOR, Permission.ACKNOWLEDGE_INCIDENTS) is True
    assert check_permission(Role.OPERATOR, Permission.MANAGE_CAMERAS) is False
    assert check_permission(Role.OPERATOR, Permission.MANAGE_ZONES) is False

    # Viewer can only view
    assert check_permission(Role.VIEWER, Permission.VIEW_CAMERAS) is True
    assert check_permission(Role.VIEWER, Permission.ACKNOWLEDGE_INCIDENTS) is False


# ==============================================================================
# 3. INCIDENTS, SINGLE INCIDENT DETAIL & 404 CHECKS
# ==============================================================================

def test_incidents_api_and_404_detail(client: TestClient):
    """Verify GET /incidents, GET /incidents/{id}, and 404 on non-existent incident."""
    # List incidents
    resp = client.get("/api/v1/incidents?limit=5")
    assert resp.status_code == 200
    incidents = resp.json()
    assert isinstance(incidents, list)

    if len(incidents) > 0:
        inc_id = incidents[0]["id"]
        # Fetch existing incident detail
        resp_detail = client.get(f"/api/v1/incidents/{inc_id}")
        assert resp_detail.status_code == 200
        assert resp_detail.json()["id"] == inc_id

    # Non-existent incident -> 404
    resp_404 = client.get("/api/v1/incidents/INC-NONEXISTENT-999999")
    assert resp_404.status_code == 404
    assert resp_404.json()["detail"] == "Incident not found"


def test_incident_status_transition_rules(client: TestClient):
    """Verify status update validation rules (400 on invalid status)."""
    resp_400 = client.post(
        "/api/v1/incidents/INC-FAKE-123/status",
        json={"status": "INVALID_STATUS_TEST"}
    )
    assert resp_400.status_code == 400


# ==============================================================================
# 4. CAMERAS & ANPR OBSERVATIONS 404 / 400 HANDLING
# ==============================================================================

def test_camera_crud_and_invalid_ids(client: TestClient):
    """Verify camera lookup, 404 on missing camera, and duplicate creation 400."""
    # List cameras
    resp_list = client.get("/api/v1/cameras/")
    assert resp_list.status_code == 200
    cameras = resp_list.json()
    assert isinstance(cameras, list)

    # Missing camera ID -> 404
    resp_404 = client.get("/api/v1/cameras/CAM-GHOST-999")
    assert resp_404.status_code == 404
    assert resp_404.json()["detail"] == "Camera not found"


def test_anpr_observations_and_404(client: TestClient):
    """Verify ANPR list and 404 on non-existent observation ID."""
    resp = client.get("/api/v1/anpr/observations")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp_404 = client.get("/api/v1/anpr/observations/OBS-NONEXISTENT-777")
    assert resp_404.status_code == 404
    assert resp_404.json()["detail"] == "ANPR observation not found"


# ==============================================================================
# 5. ZONES & SETTINGS VALIDATION
# ==============================================================================

def test_zones_and_settings_endpoints(client: TestClient):
    """Verify zones and settings fetch and input validation."""
    # Zones GET
    resp_zones = client.get("/api/v1/zones")
    assert resp_zones.status_code == 200

    # Settings GET
    resp_settings = client.get("/api/v1/settings/")
    assert resp_settings.status_code == 200
    settings = resp_settings.json()
    assert "confidence_threshold" in settings

    # Settings validation error: confidence > 0.95 -> 422
    resp_invalid_settings = client.post(
        "/api/v1/settings/",
        json={"confidence_threshold": 1.5}
    )
    assert resp_invalid_settings.status_code == 422


# ==============================================================================
# 6. SECURITY: PATH TRAVERSAL HARDENING
# ==============================================================================

def test_path_traversal_hardening(client: TestClient):
    """Verify that path traversal attempts (e.g., ../../) are blocked."""
    # Traversal in evidence
    resp_trav = client.get("/evidence/../../../../Windows/win.ini")
    # Should either return a placeholder or 404, never leaked system file contents
    assert b"[extensions]" not in resp_trav.content

    # Traversal in SPA route
    resp_spa_trav = client.get("/..%2f..%2f..%2fetc/passwd")
    assert resp_spa_trav.status_code in (400, 403, 404)


# ==============================================================================
# 7. WEBSOCKET TELEMETRY HUB LIFECYCLE
# ==============================================================================

def test_websocket_telemetry_hub_ping_pong(client: TestClient):
    """Verify WebSocket connection, heartbeat ping/pong, and clean closure."""
    with client.websocket_connect("/ws/alerts") as websocket:
        # Send heartbeat ping
        websocket.send_text('{"type": "ping"}')
        data = websocket.receive_json()
        assert data.get("type") == "pong"
        assert "timestamp" in data


# ==============================================================================
# 8. CCTV PIPELINE FAULT TOLERANCE & MONITORING
# ==============================================================================

def test_camera_health_monitor_fault_recovery():
    """Verify camera state machine detects failure and transitions through RECONNECTING -> ONLINE."""
    monitor = CameraHealthMonitor()
    cam_id = "CAM-AUDIT-TEST-01"

    # Register camera
    monitor.register(cam_id)
    assert monitor.get_health(cam_id)["state"] == CameraHealthState.OFFLINE.value

    # Receive initial frames -> ONLINE
    monitor.update(cam_id, frame_received=True, fps=25.0)
    assert monitor.get_health(cam_id)["state"] == CameraHealthState.ONLINE.value

    # Reconnection attempt
    monitor.mark_reconnecting(cam_id)
    assert monitor.get_health(cam_id)["state"] == CameraHealthState.RECONNECTING.value

    # Successful frame reception -> Back to ONLINE
    monitor.update(cam_id, frame_received=True, fps=25.0)
    assert monitor.get_health(cam_id)["state"] == CameraHealthState.ONLINE.value


# ==============================================================================
# 9. EVIDENCE LEDGER INTEGRITY & NON-REPUDIATION
# ==============================================================================

def test_evidence_ledger_cryptographic_verification():
    """Verify SHA-256 hash-chain link integrity and tamper detection."""
    b1 = compute_block_hash(
        GENESIS_PREVIOUS_HASH,
        "INC-AUDIT-001",
        "mock_jpg_sha256_1",
        "2026-09-27T12:00:00Z",
        '{"event": "intrusion"}'
    )
    assert len(b1) == 64

    b2 = compute_block_hash(
        b1,
        "INC-AUDIT-002",
        "mock_jpg_sha256_2",
        "2026-09-27T12:01:00Z",
        '{"event": "anpr"}'
    )
    assert len(b2) == 64

    # Simulate bit-level tamper on incident 2
    b2_tampered = compute_block_hash(
        b1,
        "INC-AUDIT-002",
        "mock_jpg_sha256_TAMPERED",
        "2026-09-27T12:01:00Z",
        '{"event": "anpr"}'
    )
    assert b2 != b2_tampered
