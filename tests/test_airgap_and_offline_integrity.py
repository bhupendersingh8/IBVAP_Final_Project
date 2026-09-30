"""
tests/test_airgap_and_offline_integrity.py
==========================================
Verifies that all TCVIAF / IBVAP assurance, cryptographic, and pipeline modules
execute in 100% offline, air-gapped local mode with ZERO outbound WAN/cloud connections.
"""
import pytest
import socket
import numpy as np
from pathlib import Path

import sys
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from services.assurance.data_integrity import DataIntegrityAssurance
from services.assurance.post_quantum import PostQuantumAssuranceEngine
from services.assurance.inference_provenance import InferenceProvenanceEngine
from crypto_ledger import CryptoEvidenceLedger


@pytest.fixture
def socket_guardian(monkeypatch):
    """
    Blocks any attempt to connect to external/non-loopback IP addresses.
    If any module tries to call cloud/external APIs, socket.connect will raise an exception.
    """
    orig_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0]
        # Allow localhost / loopback only
        if host not in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
            raise ConnectionRefusedError(
                f"AIR-GAP VIOLATION: Attempted outbound WAN connection to {address} in air-gapped environment!"
            )
        return orig_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    return True


def test_airgap_assurance_pipeline_execution(tmp_path, socket_guardian):
    """
    Runs Data Integrity, Mahalanobis OOD, Kernel MMD, Post-Quantum Crypto,
    Inference Provenance, and Merkle Ledger under strict socket blocking.
    """
    db_path = tmp_path / "airgap_ledger.sqlite3"
    ledger = CryptoEvidenceLedger(db_path=db_path, use_sqlite_fallback=True)

    # 1. Data Integrity & Mahalanobis
    data_engine = DataIntegrityAssurance(ledger=ledger)
    ref = np.random.default_rng(42).normal(0, 1, size=(50, 4))
    sample = np.array([0.1, 0.1, -0.1, 0.2])

    f_ood = data_engine.check_ood_mahalanobis("sample_01", sample, ref)
    assert f_ood.status == "IN_DISTRIBUTION"

    # 2. Kernel MMD Shift
    f_mmd = data_engine.check_distribution_shift_mmd(ref[:25], ref[25:], n_permutations=20)
    assert f_mmd.status == "IN_DISTRIBUTION"

    # 3. Label Quality Check
    f_labels = data_engine.check_label_quality("img_01", [{"class_id": 0, "bbox": [0.5, 0.5, 0.2, 0.2]}])
    assert len(f_labels) == 0

    # 4. Post-Quantum Signing & Verification
    pq_engine = PostQuantumAssuranceEngine()
    record_bytes = b"autonomous_sentry_edge_event_payload"
    signed_block = pq_engine.sign_record(record_bytes)
    assert pq_engine.verify_record(record_bytes, signed_block["pq_signature"]) is True

    # 5. Inference Provenance Binding
    prov_engine = InferenceProvenanceEngine(ledger=ledger)
    rec = prov_engine.create_provenance_record(
        input_bytes=b"raw_frame_airgap",
        model_id="yolo11n",
        model_sha256="0" * 64,
        architecture_id="ultralytics_yolo",
        raw_detections=[{"class_id": 0, "confidence": 0.90, "bbox": [0.2, 0.2, 0.4, 0.4]}],
        config={"conf": 0.25},
        preprocessing_config={"res": "640x640"},
        sequence_id=1
    )
    assert rec.sequence_id == 1
    assert rec.pq_hybrid_digest is not None

    # 6. Cryptographic Chain & Forensic Certificate
    ledger.commit_event(
        frame=b"frame_bytes_alert",
        camera_id="CAM_AIRGAP_01",
        event_type="PERIMETER_BREACH",
        severity="CRITICAL"
    )
    cert = ledger.export_audit_certificate()
    assert cert["is_tamper_free"] is True
    assert "post_quantum_readiness" in cert
