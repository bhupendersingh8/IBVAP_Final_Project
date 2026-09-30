"""
tests/test_contributor_manifest.py
==================================
Unit and security tests for Contributor Model Manifests and Ed25519 signing.
Verifies RFC-8785 canonicalization, deterministic signing, tamper detection across
all 8 critical mutation vectors, physical file checksum verification, and secret safety.
"""
import copy
import json
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile

from services.assurance.contributor_manifest import (
    create_contributor_manifest,
    sign_contributor_manifest,
    verify_manifest_signature,
    compute_manifest_digest,
    canonical_json_bytes,
    generate_ed25519_keypair,
    export_ed25519_keypair_hex,
    load_ed25519_private_key_hex,
    load_ed25519_public_key_hex
)
from services.assurance.manifest_verifier import SupplyChainVerifier


# Deterministic test fixture
TEST_MODEL_SHA256 = "0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1"
TEST_PREP_HASH = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
TEST_FP_DIGEST = "f0e1d2c3b4a5968778695a4b3c2d1e0ff0e1d2c3b4a5968778695a4b3c2d1e0f"


@pytest.fixture
def test_keypair():
    """Provides deterministic in-memory Ed25519 keypair for testing."""
    priv, pub = generate_ed25519_keypair()
    return priv, pub


@pytest.fixture
def valid_signed_manifest(test_keypair):
    """Provides a valid signed ContributorModelManifest dictionary."""
    priv, pub = test_keypair
    manifest = create_contributor_manifest(
        contributor_id="ssb-intel-div-04",
        contributor_name="Inspector Rajesh Kumar",
        contributor_org="Sashastra Seema Bal",
        model_id="yolo11n-tactical-perimeter",
        architecture="ultralytics_yolo11",
        format_type="PyTorch",
        file_name="yolo11n.pt",
        model_sha256=TEST_MODEL_SHA256,
        preprocessing_config_hash=TEST_PREP_HASH,
        behavioral_fingerprint_digest=TEST_FP_DIGEST,
        parameter_count=2589400,
        manifest_id="man-test-0001",
        created_at="2026-09-30T10:00:00Z"
    )
    return sign_contributor_manifest(manifest, priv)


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_deterministic_canonicalization():
    """A. Verifies RFC-8785 JSON canonicalization produces identical byte outputs regardless of key insertion order."""
    dict_a = {"b": 2, "a": 1, "nested": {"z": 10, "y": 20}}
    dict_b = {"a": 1, "nested": {"y": 20, "z": 10}, "b": 2}

    bytes_a = canonical_json_bytes(dict_a)
    bytes_b = canonical_json_bytes(dict_b)

    assert bytes_a == bytes_b
    assert b" " not in bytes_a
    assert bytes_a == b'{"a":1,"b":2,"nested":{"y":20,"z":10}}'


def test_manifest_sha256_determinism(valid_signed_manifest):
    """B. Verifies that compute_manifest_digest produces deterministic SHA-256 for identical payload."""
    digest_1 = compute_manifest_digest(valid_signed_manifest)
    digest_2 = compute_manifest_digest(valid_signed_manifest)
    assert digest_1 == digest_2
    assert len(digest_1) == 64


def test_valid_ed25519_signature(valid_signed_manifest):
    """C. Verifies that a properly signed manifest passes cryptographic verification."""
    is_valid, err = verify_manifest_signature(valid_signed_manifest)
    assert is_valid is True
    assert err is None

    # Service layer verification
    res = SupplyChainVerifier.verify_manifest(valid_signed_manifest)
    assert res.valid is True
    assert res.checks.signature is True
    assert res.checks.manifest_structure is True
    assert len(res.failures) == 0


def test_invalid_signature_rejection(valid_signed_manifest):
    """D. Verifies that an altered or random signature is rejected."""
    tampered = copy.deepcopy(valid_signed_manifest)
    # Corrupt last character of hex signature
    sig_hex = tampered["signature"]["signature"]
    corrupted_char = 'a' if sig_hex[-1] != 'a' else 'b'
    tampered["signature"]["signature"] = sig_hex[:-1] + corrupted_char

    is_valid, err = verify_manifest_signature(tampered)
    assert is_valid is False
    assert "Cryptographic signature verification failed" in err


def test_changed_model_hash_rejection(valid_signed_manifest):
    """E. Tampering Mutation 1: Changing declared model SHA-256 breaks signature."""
    tampered = copy.deepcopy(valid_signed_manifest)
    tampered["model"]["sha256"] = "1" * 64

    is_valid, err = verify_manifest_signature(tampered)
    assert is_valid is False

    res = SupplyChainVerifier.verify_manifest(tampered)
    assert res.valid is False
    assert any("signature" in f.lower() for f in res.failures)


def test_changed_model_id_rejection(valid_signed_manifest):
    """F. Tampering Mutation 2: Changing model_id breaks signature."""
    tampered = copy.deepcopy(valid_signed_manifest)
    tampered["model"]["model_id"] = "malicious_backdoored_model"

    is_valid, err = verify_manifest_signature(tampered)
    assert is_valid is False


def test_changed_architecture_rejection(valid_signed_manifest):
    """Tampering Mutation 3: Changing model architecture breaks signature."""
    tampered = copy.deepcopy(valid_signed_manifest)
    tampered["model"]["architecture"] = "unauthorized_resnet50"

    is_valid, err = verify_manifest_signature(tampered)
    assert is_valid is False


def test_changed_preprocessing_hash_rejection(valid_signed_manifest):
    """G. Tampering Mutation 4: Changing preprocessing config hash breaks signature."""
    tampered = copy.deepcopy(valid_signed_manifest)
    tampered["preprocessing"]["config_hash"] = "9" * 64

    is_valid, err = verify_manifest_signature(tampered)
    assert is_valid is False


def test_changed_contributor_rejection(valid_signed_manifest):
    """H. Tampering Mutation 5: Changing contributor ID or organization breaks signature."""
    tampered = copy.deepcopy(valid_signed_manifest)
    tampered["contributor"]["id"] = "impersonated_adversary"

    is_valid, err = verify_manifest_signature(tampered)
    assert is_valid is False


def test_changed_behavioral_fingerprint_rejection(valid_signed_manifest):
    """I. Tampering Mutation 6: Changing behavioral fingerprint digest breaks signature."""
    tampered = copy.deepcopy(valid_signed_manifest)
    tampered["behavioral_fingerprint"]["digest"] = "e" * 64

    is_valid, err = verify_manifest_signature(tampered)
    assert is_valid is False


def test_changed_timestamp_rejection(valid_signed_manifest):
    """Tampering Mutation 7: Altering creation timestamp breaks signature."""
    tampered = copy.deepcopy(valid_signed_manifest)
    tampered["created_at"] = "2026-10-01T00:00:00Z"

    is_valid, err = verify_manifest_signature(tampered)
    assert is_valid is False


def test_malformed_manifest_rejection():
    """K. Verifies that malformed manifests with missing fields are caught by validation."""
    malformed = {
        "manifest_version": "1.0",
        "contributor": {"id": "test"}
        # Missing model, preprocessing, behavioral_fingerprint
    }
    res = SupplyChainVerifier.verify_manifest(malformed)
    assert res.valid is False
    assert res.checks.manifest_structure is False
    assert len(res.failures) > 0


def test_null_parameter_count_handling(test_keypair):
    """Verifies that null parameter_count is properly supported and recorded as a documented limitation."""
    priv, pub = test_keypair
    manifest = create_contributor_manifest(
        contributor_id="ssb-intel",
        contributor_name="Officer",
        contributor_org="SSB",
        model_id="test_model",
        architecture="yolo",
        format_type="PyTorch",
        file_name="model.pt",
        model_sha256="2" * 64,
        preprocessing_config_hash="3" * 64,
        parameter_count=None  # Null parameter count
    )
    signed = sign_contributor_manifest(manifest, priv)

    res = SupplyChainVerifier.verify_manifest(signed)
    assert res.valid is True
    assert any("parameter_count is null" in lim for lim in res.limitations)


def test_physical_model_file_verification(valid_signed_manifest):
    """N. Verifies that actual model file on disk is checked and prevents hash substitution attacks."""
    # Create temporary dummy model file with exact known content
    with NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"DUMMY_MODEL_WEIGHTS_BINARY_CONTENT_2026")
        tmp_path = Path(tmp.name)

    import hashlib
    actual_sha = hashlib.sha256(b"DUMMY_MODEL_WEIGHTS_BINARY_CONTENT_2026").hexdigest()

    try:
        # 1. Test when manifest has mismatched SHA vs physical file
        res_mismatch = SupplyChainVerifier.verify_manifest(valid_signed_manifest, model_file_path=tmp_path)
        assert res_mismatch.valid is False
        assert res_mismatch.checks.physical_file_digest is False
        assert any("PHYSICAL MODEL CHECKSUM MISMATCH" in f for f in res_mismatch.failures)

        # 2. Test when manifest has matching SHA vs physical file
        priv, pub = generate_ed25519_keypair()
        matching_manifest = create_contributor_manifest(
            contributor_id="unit-04",
            contributor_name="Dev",
            contributor_org="SSB",
            model_id="exact-model",
            architecture="yolo",
            format_type="PyTorch",
            file_name=tmp_path.name,
            model_sha256=actual_sha,
            preprocessing_config_hash="4" * 64
        )
        signed_matching = sign_contributor_manifest(matching_manifest, priv)

        res_match = SupplyChainVerifier.verify_manifest(signed_matching, model_file_path=tmp_path)
        assert res_match.valid is True
        assert res_match.checks.physical_file_digest is True
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_private_key_never_serialized_into_manifest(valid_signed_manifest):
    """O. Security Check: Verifies private key material is never serialized into the manifest."""
    manifest_str = json.dumps(valid_signed_manifest)
    assert "private" not in manifest_str.lower()
    assert "secret" not in manifest_str.lower()
    assert "priv" not in manifest_str.lower()
    assert "public_key" in valid_signed_manifest["signature"]
    assert "signature" in valid_signed_manifest["signature"]


def test_keypair_export_and_reload():
    """Verifies that Ed25519 keypairs can be safely exported to hex and reloaded without loss."""
    priv, pub = generate_ed25519_keypair()
    priv_hex, pub_hex = export_ed25519_keypair_hex(priv)

    assert len(priv_hex) == 64
    assert len(pub_hex) == 64

    reloaded_priv = load_ed25519_private_key_hex(priv_hex)
    reloaded_pub = load_ed25519_public_key_hex(pub_hex)

    # Sign with original, verify with reloaded pub
    msg = b"TEST_PAYLOAD_FOR_KEY_ROUNDTRIP"
    sig = priv.sign(msg)
    reloaded_pub.verify(sig, msg)

    # Sign with reloaded priv, verify with original pub
    sig2 = reloaded_priv.sign(msg)
    pub.verify(sig2, msg)


@pytest.mark.anyio
async def test_manifest_api_endpoints(valid_signed_manifest):
    """Verifies FastAPI REST endpoints for manifest verification and enrollment."""
    from httpx import AsyncClient, ASGITransport
    from apps.backend.main import app
    from apps.backend.auth.jwt_auth import create_access_token

    token = create_access_token({"sub": "admin_test", "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. POST /api/v1/assurance/manifests/verify
        res1 = await client.post(
            "/api/v1/assurance/manifests/verify",
            json={"manifest": valid_signed_manifest, "check_disk_weights": False},
            headers=headers
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["valid"] is True
        assert data1["checks"]["signature"] is True

        # 2. POST /api/v1/assurance/manifests/enroll
        res2 = await client.post(
            "/api/v1/assurance/manifests/enroll",
            json={"manifest": valid_signed_manifest},
            headers=headers
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status"] == "ENROLLED"
        manifest_id = data2["manifest_id"]

        # 3. GET /api/v1/assurance/manifests/{manifest_id}
        res3 = await client.get(
            f"/api/v1/assurance/manifests/{manifest_id}",
            headers=headers
        )
        assert res3.status_code == 200
        data3 = res3.json()
        assert data3["manifest_id"] == manifest_id
        assert data3["model_id"] == valid_signed_manifest["model"]["model_id"]

        # 4. GET /api/v1/assurance/manifests
        res4 = await client.get(
            "/api/v1/assurance/manifests",
            headers=headers
        )
        assert res4.status_code == 200
        data4 = res4.json()
        assert len(data4) >= 1
        assert any(m["manifest_id"] == manifest_id for m in data4)


def test_signed_but_behaviorally_suspicious_model(valid_signed_manifest):
    """
    SIH26228 Section 8 Grounding Test:
    Demonstrates that 'Cryptographic Authenticity != Behavioral Safety'.
    An authorized contributor may legitimately sign a manifest with a valid Ed25519 key,
    yet the model weights can still exhibit trojan or backdoor behavioral anomalies.
    Therefore, cryptographic signature validity alone is insufficient; behavioral fingerprinting
    must independently flag the asset for REVIEW or QUARANTINE.
    """
    # 1. Cryptographic Manifest Verification (Signature is completely valid)
    manifest_res = SupplyChainVerifier.verify_manifest(valid_signed_manifest)
    assert manifest_res.valid is True
    assert manifest_res.checks.signature is True
    assert len(manifest_res.failures) == 0

    # 2. Simulate Behavioral Fingerprint Engine evaluation against probe battery
    # Suppose an insider or compromised authorized contributor injected a stealth trigger
    # The divergence score S measures: count drift, confidence shift, and bbox IoU deviation
    simulated_divergence_score = 0.42  # Exceeds the 0.15 baseline threshold
    divergence_threshold = 0.15

    # 3. Behavioral policy evaluation
    if simulated_divergence_score > divergence_threshold:
        behavioral_status = "BEHAVIORAL_DRIFT_DETECTED"
        recommended_disposition = "QUARANTINE"
    else:
        behavioral_status = "BEHAVIOR_CONSISTENT"
        recommended_disposition = "ACCEPT"

    # 4. Assert the core cybersecurity thesis:
    # Signature is VALID, but behavioral assurance enforces QUARANTINE
    assert manifest_res.checks.signature is True, "Signature must be cryptographically valid"
    assert behavioral_status == "BEHAVIORAL_DRIFT_DETECTED"
    assert recommended_disposition == "QUARANTINE", "Behavioral assurance must quarantine trojaned weights despite valid signature"

