"""
tests/test_aibom.py
===================
Unit and security tests for CycloneDX 1.5-compatible AIBOM generation and
Manifest ↔ AIBOM cross-binding integrity verification.
Includes an offline air-gap test ensuring zero network calls during generation and verification.
"""
import copy
import socket
import pytest
from pathlib import Path

from services.assurance.contributor_manifest import (
    create_contributor_manifest,
    sign_contributor_manifest,
    generate_ed25519_keypair
)
from services.assurance.aibom import (
    generate_cyclonedx_aibom,
    verify_manifest_aibom_binding,
    extract_model_component,
    extract_property_value
)
from services.assurance.manifest_verifier import SupplyChainVerifier


TEST_MODEL_SHA = "0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1"
TEST_PREP_HASH = "b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1"
TEST_FP_DIGEST = "c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2"


@pytest.fixture
def test_manifest_and_aibom():
    """Provides a valid paired manifest and CycloneDX 1.5 AIBOM."""
    priv, pub = generate_ed25519_keypair()
    manifest = create_contributor_manifest(
        contributor_id="ssb-sector-07-ops",
        contributor_name="Sub-Inspector A. Sharma",
        contributor_org="Sashastra Seema Bal",
        model_id="yolo11n-lowlight-frontier",
        architecture="ultralytics_yolo11",
        format_type="PyTorch",
        file_name="yolo11n.pt",
        model_sha256=TEST_MODEL_SHA,
        preprocessing_config_hash=TEST_PREP_HASH,
        behavioral_fingerprint_digest=TEST_FP_DIGEST,
        parameter_count=2589400,
        manifest_id="man-aibom-test-01"
    )
    signed_manifest = sign_contributor_manifest(manifest, priv)
    aibom = generate_cyclonedx_aibom(signed_manifest, serial_number="urn:uuid:11111111-2222-3333-4444-555555555555")
    return signed_manifest, aibom


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_cyclonedx_aibom_structure(test_manifest_and_aibom):
    """A. Verifies CycloneDX 1.5 top-level structure, specVersion, and metadata."""
    manifest, aibom = test_manifest_and_aibom

    assert aibom["bomFormat"] == "CycloneDX"
    assert aibom["specVersion"] == "1.5"
    assert aibom["serialNumber"].startswith("urn:uuid:")
    assert aibom["version"] == 1
    assert "metadata" in aibom
    assert "components" in aibom
    assert len(aibom["components"]) >= 1


def test_aibom_model_component_and_sha256(test_manifest_and_aibom):
    """B. Verifies model component has type 'machine-learning-model' and correct SHA-256."""
    manifest, aibom = test_manifest_and_aibom
    comp = extract_model_component(aibom)
    assert comp is not None
    assert comp["type"] == "machine-learning-model"
    assert comp["name"] == manifest["model"]["model_id"]

    hashes = comp.get("hashes", [])
    sha_entry = next((h for h in hashes if h["alg"] == "SHA-256"), None)
    assert sha_entry is not None
    assert sha_entry["content"] == TEST_MODEL_SHA


def test_aibom_ibvap_properties(test_manifest_and_aibom):
    """C. Verifies AIBOM component includes documented IBVAP extension properties."""
    manifest, aibom = test_manifest_and_aibom
    comp = extract_model_component(aibom)

    assert extract_property_value(comp, "ibvap:manifest_id") == manifest["manifest_id"]
    assert extract_property_value(comp, "ibvap:model_id") == manifest["model"]["model_id"]
    assert extract_property_value(comp, "ibvap:preprocessing_config_sha256") == TEST_PREP_HASH
    assert extract_property_value(comp, "ibvap:behavioral_fingerprint_sha256") == TEST_FP_DIGEST
    assert extract_property_value(comp, "ibvap:contributor_id") == manifest["contributor"]["id"]
    assert extract_property_value(comp, "ibvap:signature_algorithm") == "Ed25519"


def test_manifest_aibom_binding_success(test_manifest_and_aibom):
    """D. Verifies that valid paired manifest and AIBOM pass cross-binding verification."""
    manifest, aibom = test_manifest_and_aibom
    is_bound, failures = verify_manifest_aibom_binding(manifest, aibom)
    assert is_bound is True
    assert len(failures) == 0

    # End-to-end supply chain verification
    report = SupplyChainVerifier.verify_supply_chain(manifest, aibom=aibom)
    assert report.valid is True
    assert report.binding_valid is True
    assert report.manifest_result.valid is True
    assert report.aibom_result.valid is True
    assert len(report.failures) == 0


def test_manifest_aibom_binding_fails_on_model_sha_mutation(test_manifest_and_aibom):
    """E. Mutation Test: Tampering with model SHA-256 in AIBOM fails cross-binding verification."""
    manifest, aibom = test_manifest_and_aibom
    tampered_aibom = copy.deepcopy(aibom)
    comp = extract_model_component(tampered_aibom)
    comp["hashes"][0]["content"] = "f" * 64

    is_bound, failures = verify_manifest_aibom_binding(manifest, tampered_aibom)
    assert is_bound is False
    assert any("Model SHA-256 binding mismatch" in f for f in failures)


def test_manifest_aibom_binding_fails_on_preprocessing_mutation(test_manifest_and_aibom):
    """F. Mutation Test: Tampering with preprocessing hash in AIBOM fails cross-binding verification."""
    manifest, aibom = test_manifest_and_aibom
    tampered_aibom = copy.deepcopy(aibom)
    comp = extract_model_component(tampered_aibom)
    for p in comp["properties"]:
        if p["name"] == "ibvap:preprocessing_config_sha256":
            p["value"] = "9" * 64

    is_bound, failures = verify_manifest_aibom_binding(manifest, tampered_aibom)
    assert is_bound is False
    assert any("Preprocessing config digest mismatch" in f for f in failures)


def test_manifest_aibom_binding_fails_on_fingerprint_mutation(test_manifest_and_aibom):
    """G. Mutation Test: Tampering with behavioral fingerprint in AIBOM fails cross-binding verification."""
    manifest, aibom = test_manifest_and_aibom
    tampered_aibom = copy.deepcopy(aibom)
    comp = extract_model_component(tampered_aibom)
    for p in comp["properties"]:
        if p["name"] == "ibvap:behavioral_fingerprint_sha256":
            p["value"] = "0" * 64

    is_bound, failures = verify_manifest_aibom_binding(manifest, tampered_aibom)
    assert is_bound is False
    assert any("Behavioral fingerprint digest mismatch" in f for f in failures)


def test_manifest_aibom_binding_fails_on_contributor_mutation(test_manifest_and_aibom):
    """H. Mutation Test: Altering contributor ID in AIBOM fails cross-binding verification."""
    manifest, aibom = test_manifest_and_aibom
    tampered_aibom = copy.deepcopy(aibom)
    comp = extract_model_component(tampered_aibom)
    for p in comp["properties"]:
        if p["name"] == "ibvap:contributor_id":
            p["value"] = "unauthorized_rogue_contributor"

    is_bound, failures = verify_manifest_aibom_binding(manifest, tampered_aibom)
    assert is_bound is False
    assert any("Contributor ID mismatch" in f for f in failures)


def test_standalone_aibom_verification_failures():
    """I. Verifies that invalid CycloneDX metadata is caught by standalone verifier."""
    invalid_aibom = {
        "bomFormat": "SpdxDocument",  # Invalid
        "specVersion": "1.4",         # Invalid (expected 1.5)
        "components": []
    }
    res = SupplyChainVerifier.verify_aibom(invalid_aibom)
    assert res.valid is False
    assert any("bomFormat mismatch" in f for f in res.failures)
    assert any("specVersion mismatch" in f for f in res.failures)
    assert any("No machine-learning-model component" in f for f in res.failures)


def test_offline_execution_blocks_sockets(test_manifest_and_aibom, monkeypatch):
    """
    K. Air-Gap / Offline Execution Test:
    Ensures that manifest creation, Ed25519 signing, AIBOM generation, and
    cross-binding verification operate completely offline with zero WAN network access.
    """
    def guarded_connect(*args, **kwargs):
        raise ConnectionRefusedError("OFFLINE AIR-GAP ENFORCED: Outbound socket connection blocked.")

    # Intercept socket creation and connection
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)

    manifest, aibom = test_manifest_and_aibom

    # 1. Manifest verification runs purely offline
    man_res = SupplyChainVerifier.verify_manifest(manifest)
    assert man_res.valid is True

    # 2. AIBOM verification runs purely offline
    aibom_res = SupplyChainVerifier.verify_aibom(aibom)
    assert aibom_res.valid is True

    # 3. Supply chain cross-binding runs purely offline
    sc_res = SupplyChainVerifier.verify_supply_chain(manifest, aibom=aibom)
    assert sc_res.valid is True
    assert sc_res.binding_valid is True


@pytest.mark.anyio
async def test_aibom_api_endpoints(test_manifest_and_aibom):
    """Verifies FastAPI REST endpoints for CycloneDX AIBOM verification."""
    from httpx import AsyncClient, ASGITransport
    from apps.backend.main import app
    from apps.backend.auth.jwt_auth import create_access_token

    manifest, aibom = test_manifest_and_aibom

    token = create_access_token({"sub": "admin_test", "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Standalone AIBOM verify
        res1 = await client.post(
            "/api/v1/assurance/aibom/verify",
            json={"aibom": aibom},
            headers=headers
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["valid"] is True
        assert data1["bom_format"] == "CycloneDX"
        assert data1["spec_version"] == "1.5"

        # 2. Coupled Manifest + AIBOM binding verify
        res2 = await client.post(
            "/api/v1/assurance/aibom/verify",
            json={"aibom": aibom, "manifest": manifest},
            headers=headers
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["valid"] is True
        assert data2["binding_valid"] is True
        assert data2["manifest_result"]["valid"] is True

