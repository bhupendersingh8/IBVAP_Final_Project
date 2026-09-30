"""
Tests for POST /api/v1/evidence/verify endpoint (Phase 16).
Validates:
1. Valid untampered evidence passes verification.
2. Tampered evidence (even 1 altered byte) fails verification and flags TAMPER_DETECTED.
3. Missing file reporting.
"""

import hashlib
import os
import tempfile
import pytest
from httpx import AsyncClient, ASGITransport

from apps.backend.main import app
from apps.backend.database.connection import get_db, AsyncSessionLocal
from apps.backend.database.models import Incident
from apps.backend.auth.jwt_auth import create_access_token


@pytest.mark.anyio
async def test_evidence_verify_tamper_detection():
    # 1. Create a dummy evidence file
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"ORIGINAL_BORDER_EVIDENCE_FRAME_DATA_12345")
        temp_path = f.name

    try:
        # Compute original SHA-256
        hasher = hashlib.sha256()
        with open(temp_path, "rb") as f:
            hasher.update(f.read())
        orig_sha = hasher.hexdigest()

        # Generate auth token with VERIFY_EVIDENCE permission (Role.ADMIN has all)
        token = create_access_token({"sub": "test_officer", "role": "ADMIN"})
        headers = {"Authorization": f"Bearer {token}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Test 1: Verification with matching hash
            resp1 = await client.post(
                "/api/v1/evidence/verify",
                json={"file_path": temp_path, "expected_sha256": orig_sha},
                headers=headers,
            )
            assert resp1.status_code == 200
            data1 = resp1.json()
            assert data1["integrity_verified"] is True
            assert data1["status"] == "TAMPER_EVIDENT_VALID"
            assert data1["computed_sha256"] == orig_sha

            # Test 2: TAMPER TEST — modify 1 byte of the evidence file
            with open(temp_path, "ab") as f:
                f.write(b"_TAMPERED_BYTE")

            resp2 = await client.post(
                "/api/v1/evidence/verify",
                json={"file_path": temp_path, "expected_sha256": orig_sha},
                headers=headers,
            )
            assert resp2.status_code == 200
            data2 = resp2.json()
            assert data2["integrity_verified"] is False
            assert data2["status"] == "TAMPER_DETECTED"
            assert data2["computed_sha256"] != orig_sha

            # Test 3: Missing file test
            resp3 = await client.post(
                "/api/v1/evidence/verify",
                json={"file_path": "non_existent_file_xyz123.jpg", "expected_sha256": orig_sha},
                headers=headers,
            )
            assert resp3.status_code == 200
            data3 = resp3.json()
            assert data3["integrity_verified"] is False
            assert data3["status"] == "FILE_NOT_FOUND"

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
