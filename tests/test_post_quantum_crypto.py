"""
tests/test_post_quantum_crypto.py
=================================
Unit and integration tests for Post-Quantum Cryptographic Assurance:
1. NIST FIPS 202 SHAKE-256 512-bit extended digest generation.
2. Classical-Quantum Hybrid Hash Commitments (SHA-256 + SHAKE-256).
3. NIST FIPS 205 Stateless Hash-Based One-Time Signatures (WOTS+ over SHAKE-256).
4. Provenance Record post-quantum signature binding & verification.
5. Forensic Section 65B Audit Certificate Post-Quantum Readiness.
6. FastAPI endpoints for post-quantum status and mathematical signature verification.
"""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

import sys
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from services.assurance.post_quantum import (
    compute_shake256_digest,
    compute_hybrid_hash_commitment,
    WOTSPlusSHAKE256,
    PostQuantumAssuranceEngine
)
from services.assurance.inference_provenance import (
    InferenceProvenanceEngine,
    InferenceProvenanceRecord
)
from crypto_ledger import CryptoEvidenceLedger
from apps.backend.main import app


@pytest.fixture
def clean_ledger(tmp_path):
    db_path = tmp_path / "test_pq.sqlite3"
    return CryptoEvidenceLedger(db_path=db_path, use_sqlite_fallback=True)


def test_shake256_digest_properties():
    """Verifies that SHAKE-256 generates full 512-bit (64-byte) digests."""
    data = b"border_surveillance_feed_frame_001"
    digest = compute_shake256_digest(data, output_bytes=64)
    assert len(digest) == 128  # 64 bytes = 128 hex chars
    assert isinstance(digest, str)

    # Determinism
    digest2 = compute_shake256_digest(data, output_bytes=64)
    assert digest == digest2

    # Avalanche effect (1 bit change -> completely different digest)
    data_altered = b"border_surveillance_feed_frame_002"
    digest_alt = compute_shake256_digest(data_altered, output_bytes=64)
    assert digest != digest_alt


def test_hybrid_hash_commitment():
    """Verifies dual classical and post-quantum hybrid commitment."""
    data = b"perimeter_breach_detection_event"
    hc = compute_hybrid_hash_commitment(data)

    assert "classical_sha256" in hc
    assert len(hc["classical_sha256"]) == 64  # 256-bit SHA-256
    assert "pq_shake256" in hc
    assert len(hc["pq_shake256"]) == 128  # 512-bit SHAKE-256
    assert hc["quantum_security_bits"] == 256
    assert "hybrid_digest" in hc
    assert len(hc["hybrid_digest"]) == 64


def test_wots_plus_keypair_and_signing():
    """Verifies WOTS+ key generation, signing, and signature verification."""
    wots = WOTSPlusSHAKE256(w=16)
    keypair = wots.generate_keypair()

    assert "pub_key" in keypair
    assert "priv_keys" in keypair
    assert len(keypair["priv_keys"]) == 67  # 64 + 3 checksum chains

    message = b"canonical_provenance_record_hash_2026"
    sig_dict = wots.sign(message, keypair)

    assert sig_dict["algorithm"] == "WOTS+-SHAKE256"
    assert len(sig_dict["signature"]) == 67

    # Verify signature
    valid = wots.verify(message, sig_dict)
    assert valid is True

    # Tampered message must fail
    tampered_msg = b"canonical_provenance_record_hash_tampered"
    assert wots.verify(tampered_msg, sig_dict) is False

    # Tampered signature component must fail
    sig_tampered = dict(sig_dict)
    sig_tampered["signature"] = list(sig_dict["signature"])
    # Flip first character of chain 0
    sig_tampered["signature"][0] = ("0" if sig_tampered["signature"][0][0] != "0" else "1") + sig_tampered["signature"][0][1:]
    assert wots.verify(message, sig_tampered) is False


def test_inference_provenance_pq_integration(clean_ledger):
    """Verifies post-quantum signature binding onto live InferenceProvenanceRecord."""
    engine = InferenceProvenanceEngine(ledger=clean_ledger)
    record = engine.create_provenance_record(
        input_bytes=b"raw_yolo_camera_frame",
        model_id="yolo11n",
        model_sha256="0" * 64,
        architecture_id="ultralytics_yolo",
        raw_detections=[{"class_id": 0, "confidence": 0.95, "bbox": [0.1, 0.1, 0.2, 0.2]}],
        config={"conf": 0.25},
        preprocessing_config={"res": "640x640"},
        sequence_id=101
    )
    assert record.pq_hybrid_digest is not None
    assert len(record.pq_hybrid_digest) == 64

    # Sign with Post-Quantum WOTS+
    signed_rec = engine.sign_record_post_quantum(record)
    assert signed_rec.pq_signature is not None
    assert signed_rec.pq_signature["algorithm"] == "WOTS+-SHAKE256"

    # Mathematically verify
    is_valid = engine.verify_post_quantum_signature(signed_rec)
    assert is_valid is True


def test_section_65b_cert_includes_pq_readiness(clean_ledger):
    """Verifies that exported forensic certificate contains post-quantum readiness."""
    clean_ledger.commit_event(
        frame=b"evidence_frame",
        camera_id="CAM-01",
        event_type="INTRUSION_ALERT",
        severity="CRITICAL"
    )
    cert = clean_ledger.export_audit_certificate()
    assert "post_quantum_readiness" in cert
    pq = cert["post_quantum_readiness"]
    assert "SHAKE-256" in pq["hash_family"]
    assert "Category 5" in pq["quantum_security_level"]


def test_api_post_quantum_endpoints(clean_ledger, monkeypatch):
    """Verifies FastAPI endpoints for post-quantum status and verification."""
    from apps.backend.routers import assurance as assurance_module
    from apps.backend.auth.jwt_auth import require_permission
    from apps.backend.auth.rbac import Permission

    monkeypatch.setattr(assurance_module, "get_ledger", lambda: clean_ledger)
    app.dependency_overrides[require_permission(Permission.VIEW_EVIDENCE)] = lambda: {"sub": "analyst_1", "role": "ADMIN"}

    try:
        client = TestClient(app)

        # 1. Status endpoint
        resp_status = client.get("/api/v1/assurance/post_quantum/status")
        assert resp_status.status_code == 200
        status_data = resp_status.json()
        assert status_data.get("experimental_pqc_active") is True or status_data.get("post_quantum_ready") is True
        assert status_data["symmetric_quantum_security_bits"] == 256

        # 2. Verify endpoint
        pq_engine = PostQuantumAssuranceEngine()
        msg = b"alert_sequence_number_9999"
        signed = pq_engine.sign_record(msg)

        resp_verify = client.post(
            "/api/v1/assurance/post_quantum/verify",
            json={
                "message_text": "alert_sequence_number_9999",
                "pq_signature": signed["pq_signature"]
            }
        )
        assert resp_verify.status_code == 200
        verify_data = resp_verify.json()
        assert verify_data["is_valid"] is True
        assert verify_data["verification_status"] == "SIGNATURE_VERIFIED"
    finally:
        app.dependency_overrides.clear()

