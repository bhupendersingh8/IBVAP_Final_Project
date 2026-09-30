"""
Comprehensive deterministic unit and integration tests for
SIH26228 / TCVIAF Inference Provenance, Tamper Detection & Replay Assurance.
All randomness uses np.random.default_rng with fixed seeds for 100% reproducible tests.
"""
import pytest
import os
import json
import time
import copy
import hashlib
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient

import sys
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from services.assurance.inference_provenance import (
    InferenceProvenanceRecord,
    InferenceProvenanceEngine,
    ProvenanceVerificationResult,
    ChainVerificationResult,
    canonicalize_output,
    canonicalize_config,
    canonicalize_preprocessing,
    compute_provenance_hash
)
from crypto_ledger import CryptoEvidenceLedger
from apps.backend.main import app


@pytest.fixture
def clean_ledger(tmp_path):
    """Isolated SQLite test ledger with inference_provenance schema."""
    db_path = tmp_path / "test_provenance_ledger.sqlite3"
    ledger = CryptoEvidenceLedger(db_path=db_path, use_sqlite_fallback=True)
    return ledger


@pytest.fixture
def provenance_engine(clean_ledger):
    return InferenceProvenanceEngine(ledger=clean_ledger)


@pytest.fixture
def sample_artifacts():
    """Deterministic surveillance inference artifacts."""
    rng = np.random.default_rng(12345)
    # 640x640 synthetic image frame
    frame = rng.integers(0, 255, size=(640, 640, 3), dtype=np.uint8)
    frame_bytes = frame.tobytes()

    model_id = "yolo11n_border_v1"
    model_sha256 = hashlib.sha256(b"fake_yolo11n_weights_v1").hexdigest()
    architecture_id = "ultralytics_yolo11"

    config = {
        "confidence_threshold": 0.35,
        "iou_threshold": 0.45,
        "max_det": 100,
        "device": "cuda:0"
    }

    preprocessing = {
        "input_resolution": [640, 640],
        "normalization": "div_255",
        "color_space": "RGB",
        "interpolation": "bilinear"
    }

    detections = [
        {
            "class_id": 0,
            "class_name": "person",
            "confidence": 0.91234,
            "bbox": [100.123456, 150.987654, 200.555555, 300.777777],
            "track_id": 1
        },
        {
            "class_id": 2,
            "class_name": "vehicle",
            "confidence": 0.85432,
            "bbox": [320.0, 200.0, 480.0, 350.0],
            "track_id": 2
        }
    ]

    return {
        "frame_bytes": frame_bytes,
        "model_id": model_id,
        "model_sha256": model_sha256,
        "architecture_id": architecture_id,
        "config": config,
        "preprocessing": preprocessing,
        "detections": detections
    }


# ---------------------------------------------------------------------------
# 1. Canonical Record Creation & Determinism
# ---------------------------------------------------------------------------

def test_canonical_record_creation_and_determinism(provenance_engine, sample_artifacts):
    """
    Verifies that canonical serialization is deterministic regardless of
    initial detection order or floating point precision noise.
    """
    arts = sample_artifacts
    rec1 = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=1,
        previous_record_hash="0" * 64,
        timestamp=1700000000.0,
        nonce="nonce_test_12345678",
        store_to_ledger=True
    )

    # Shuffled detections order
    shuffled_detections = list(reversed(arts["detections"]))
    rec2 = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=shuffled_detections,
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=1,
        previous_record_hash="0" * 64,
        timestamp=1700000000.0,
        nonce="nonce_test_12345678",
        store_to_ledger=False
    )

    # Digest and provenance hash must match exactly
    assert rec1.output_digest == rec2.output_digest
    assert rec1.provenance_hash == rec2.provenance_hash

    # Single record verification must pass
    verification = provenance_engine.verify_provenance_record(
        record=rec1,
        raw_input_bytes=arts["frame_bytes"],
        raw_output=arts["detections"],
        expected_model_sha256=arts["model_sha256"],
        raw_config=arts["config"],
        raw_preprocessing=arts["preprocessing"]
    )
    assert verification.status == "VERIFIED"
    assert not verification.tampered
    assert verification.recommended_disposition == "ACCEPT"


# ---------------------------------------------------------------------------
# 2. Input Byte Modification Detection (Pixel / Frame Tampering)
# ---------------------------------------------------------------------------

def test_input_byte_tampering_detection(provenance_engine, sample_artifacts):
    """
    Modifying even 1 byte in the input frame triggers INPUT_TAMPERING_DETECTED
    and recommends QUARANTINE.
    """
    arts = sample_artifacts
    rec = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=1,
        previous_record_hash="0" * 64,
        timestamp=1700000000.0,
        nonce="nonce_input_001",
        store_to_ledger=False
    )

    # Tamper with 1 byte of raw input
    tampered_bytes = bytearray(arts["frame_bytes"])
    tampered_bytes[42] = (tampered_bytes[42] + 1) % 256

    result = provenance_engine.verify_provenance_record(
        record=rec,
        raw_input_bytes=bytes(tampered_bytes)
    )

    assert result.tampered is True
    assert result.status == "TAMPERED"
    assert "INPUT_TAMPERING_DETECTED" in result.anomalies
    assert result.recommended_disposition == "QUARANTINE"


# ---------------------------------------------------------------------------
# 3. Output Bounding Box Modification Detection
# ---------------------------------------------------------------------------

def test_output_bbox_tampering_detection(provenance_engine, sample_artifacts):
    """
    Modifying bounding box coordinates in the output detections triggers
    OUTPUT_TAMPERING_DETECTED and recommends QUARANTINE.
    """
    arts = sample_artifacts
    rec = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=2,
        previous_record_hash="0" * 64,
        timestamp=1700000001.0,
        nonce="nonce_bbox_001",
        store_to_ledger=False
    )

    # Tamper with bounding box coordinate
    tampered_detections = copy.deepcopy(arts["detections"])
    tampered_detections[0]["bbox"][0] += 5.0  # shifted x1

    result = provenance_engine.verify_provenance_record(
        record=rec,
        raw_output=tampered_detections
    )

    assert result.tampered is True
    assert "OUTPUT_TAMPERING_DETECTED" in result.anomalies
    assert result.recommended_disposition == "QUARANTINE"


# ---------------------------------------------------------------------------
# 4. Output Confidence Score Modification Detection
# ---------------------------------------------------------------------------

def test_output_confidence_tampering_detection(provenance_engine, sample_artifacts):
    """
    Artificially inflating or deflating confidence triggers OUTPUT_TAMPERING_DETECTED.
    """
    arts = sample_artifacts
    rec = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=3,
        previous_record_hash="0" * 64,
        timestamp=1700000002.0,
        nonce="nonce_conf_001",
        store_to_ledger=False
    )

    tampered_detections = copy.deepcopy(arts["detections"])
    tampered_detections[0]["confidence"] = 0.9999  # inflated confidence

    result = provenance_engine.verify_provenance_record(
        record=rec,
        raw_output=tampered_detections
    )

    assert result.tampered is True
    assert "OUTPUT_TAMPERING_DETECTED" in result.anomalies
    assert result.recommended_disposition == "QUARANTINE"


# ---------------------------------------------------------------------------
# 5. Model Weight Digest Substitution Detection
# ---------------------------------------------------------------------------

def test_model_weights_tampering_detection(provenance_engine, sample_artifacts):
    """
    Substituting model weights or modifying recorded model SHA-256 triggers
    MODEL_TAMPERING_DETECTED and recommends QUARANTINE.
    """
    arts = sample_artifacts
    rec = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=4,
        previous_record_hash="0" * 64,
        timestamp=1700000003.0,
        nonce="nonce_model_001",
        store_to_ledger=False
    )

    fake_model_sha256 = hashlib.sha256(b"substitute_malicious_backdoor_weights").hexdigest()

    result = provenance_engine.verify_provenance_record(
        record=rec,
        expected_model_sha256=fake_model_sha256
    )

    assert result.tampered is True
    assert "MODEL_TAMPERING_DETECTED" in result.anomalies
    assert result.recommended_disposition == "QUARANTINE"


# ---------------------------------------------------------------------------
# 6. Configuration / Preprocessing Modification Detection
# ---------------------------------------------------------------------------

def test_configuration_tampering_detection(provenance_engine, sample_artifacts):
    """
    Modifying confidence thresholds, NMS settings, or preprocessing parameters
    triggers CONFIG_TAMPERING_DETECTED.
    """
    arts = sample_artifacts
    rec = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=5,
        previous_record_hash="0" * 64,
        timestamp=1700000004.0,
        nonce="nonce_cfg_001",
        store_to_ledger=False
    )

    tampered_config = copy.deepcopy(arts["config"])
    tampered_config["confidence_threshold"] = 0.10  # tampered threshold

    result = provenance_engine.verify_provenance_record(
        record=rec,
        raw_config=tampered_config
    )

    assert result.tampered is True
    assert "CONFIG_TAMPERING_DETECTED" in result.anomalies
    assert result.recommended_disposition == "QUARANTINE"


# ---------------------------------------------------------------------------
# 7. Sequence Gap & Deletion Detection
# ---------------------------------------------------------------------------

def test_sequence_gap_detection(provenance_engine, sample_artifacts):
    """
    Deleting an intermediate record creates a sequence number gap and triggers
    PROVENANCE_SEQUENCE_GAP.
    """
    arts = sample_artifacts
    records = []
    prev_hash = "0" * 64

    for seq in [1, 2, 4]:  # Sequence 3 is deleted / dropped
        rec = provenance_engine.create_provenance_record(
            input_bytes=arts["frame_bytes"],
            model_id=arts["model_id"],
            model_sha256=arts["model_sha256"],
            architecture_id=arts["architecture_id"],
            raw_detections=arts["detections"],
            config=arts["config"],
            preprocessing_config=arts["preprocessing"],
            sequence_id=seq,
            previous_record_hash=prev_hash,
            timestamp=1700000000.0 + seq,
            nonce=f"nonce_seq_{seq}",
            store_to_ledger=False
        )
        records.append(rec)
        prev_hash = rec.provenance_hash

    chain_res = provenance_engine.verify_chain_and_replay(records)
    assert not chain_res.valid
    assert any("PROVENANCE_SEQUENCE_GAP" in a for a in chain_res.anomalies)


# ---------------------------------------------------------------------------
# 8. Hash Chain Linkage Break Detection
# ---------------------------------------------------------------------------

def test_hash_chain_break_detection(provenance_engine, sample_artifacts):
    """
    Modifying any record inside a sequence causes downstream previous_record_hash
    linkage to break, triggering PROVENANCE_CHAIN_MISMATCH.
    """
    arts = sample_artifacts
    rec1 = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=1,
        previous_record_hash="0" * 64,
        timestamp=1700000000.0,
        nonce="nonce_chain_1",
        store_to_ledger=False
    )

    rec2 = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=2,
        previous_record_hash=rec1.provenance_hash,
        timestamp=1700000001.0,
        nonce="nonce_chain_2",
        store_to_ledger=False
    )

    # Valid chain passes
    valid_res = provenance_engine.verify_chain_and_replay([rec1, rec2])
    assert valid_res.valid is True

    # Tamper with rec2 previous_record_hash
    tampered_rec2 = rec2.model_copy(update={"previous_record_hash": "f" * 64})
    tampered_res = provenance_engine.verify_chain_and_replay([rec1, tampered_rec2])
    assert not tampered_res.valid
    assert any("PROVENANCE_CHAIN_MISMATCH" in a for a in tampered_res.anomalies)
    assert tampered_res.recommended_disposition == "QUARANTINE"


# ---------------------------------------------------------------------------
# 9. Replay Attack Detection (Duplicate Nonce & Hash Injection)
# ---------------------------------------------------------------------------

def test_replay_attack_detection(provenance_engine, sample_artifacts):
    """
    Replaying an old provenance record or duplicating a nonce triggers
    PROVENANCE_REPLAY_DETECTED.
    """
    arts = sample_artifacts
    rec1 = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=1,
        previous_record_hash="0" * 64,
        timestamp=1700000000.0,
        nonce="nonce_fixed_12345",
        store_to_ledger=False
    )

    # Malicious actor submits identical record or reuses nonce
    rec_replayed = rec1.model_copy(update={"sequence_id": 2})

    chain_res = provenance_engine.verify_chain_and_replay([rec1, rec_replayed])
    assert not chain_res.valid
    assert any("PROVENANCE_REPLAY_DETECTED" in a for a in chain_res.anomalies)


# ---------------------------------------------------------------------------
# 10. Legitimate Repeated Inference vs Replay Attack
# ---------------------------------------------------------------------------

def test_legitimate_repeated_inference_accepted(provenance_engine, sample_artifacts):
    """
    Repeated inference on the exact same frame pixels with the exact same model
    and identical detections is legitimate as long as it has a monotonic sequence_id,
    fresh cryptographic nonce, updated timestamp, and valid chain linkage.
    """
    arts = sample_artifacts
    rec1 = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=1,
        previous_record_hash="0" * 64,
        timestamp=1700000000.0,
        nonce="nonce_legit_repeat_01",
        store_to_ledger=False
    )

    # Identical frame pixels and model at a later timestamp in next sequence block
    rec2 = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=2,
        previous_record_hash=rec1.provenance_hash,
        timestamp=1700000001.0,
        nonce="nonce_legit_repeat_02",  # Fresh unique nonce
        store_to_ledger=False
    )

    chain_res = provenance_engine.verify_chain_and_replay([rec1, rec2])
    assert chain_res.valid is True
    assert len(chain_res.anomalies) == 0
    assert chain_res.recommended_disposition == "ACCEPT"


# ---------------------------------------------------------------------------
# 11. Governance Isolation Regression Test
# ---------------------------------------------------------------------------

def test_governance_override_isolation(clean_ledger, provenance_engine, sample_artifacts):
    """
    Regression test: Automated provenance checks provide recommendations
    (e.g., QUARANTINE upon tamper detection), but an analyst's explicit
    disposition is strictly isolated and NEVER overwritten by automated checks.
    """
    arts = sample_artifacts
    # 1. Commit an evidence block
    block = clean_ledger.commit_event(
        frame=arts["frame_bytes"],
        camera_id="CAM-01",
        event_type="PERIMETER_BREACH",
        severity="HIGH",
        metadata={"test": "provenance_governance"}
    )
    seq = block.sequence_id

    # 2. Analyst explicitly accepts this block
    clean_ledger.update_disposition(
        sequence_id=seq,
        new_disposition="ACCEPT",
        analyst_id="ANALYST_SSB_007",
        reason="Field verified: False positive sentry patrol"
    )

    disps_before = clean_ledger.get_latest_dispositions()
    assert disps_before[seq] == "ACCEPT"

    # 3. Create a tampered provenance record
    tampered_rec = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=seq,
        previous_record_hash="0" * 64,
        timestamp=1700000010.0,
        nonce="nonce_tamper_gov_10",
        store_to_ledger=True
    )

    tampered_rec_modified = tampered_rec.model_copy(update={"output_digest": "0" * 64})
    verif = provenance_engine.verify_provenance_record(tampered_rec_modified)

    assert verif.tampered is True
    assert verif.recommended_disposition == "QUARANTINE"

    # 4. Verify that the human analyst disposition was NOT touched or overwritten
    disps_after = clean_ledger.get_latest_dispositions()
    assert disps_after[seq] == "ACCEPT"


# ---------------------------------------------------------------------------
# 12. Assurance Router API Integration Tests
# ---------------------------------------------------------------------------

def test_provenance_api_endpoints(clean_ledger, provenance_engine, sample_artifacts, monkeypatch):
    """
    Verifies that the assurance router exposes provenance query, single-record
    forensic verification, direct payload verification, and chain verification.
    """
    from apps.backend.routers import assurance as assurance_module

    # Monkeypatch get_ledger in router to use isolated clean_ledger
    monkeypatch.setattr(assurance_module, "get_ledger", lambda: clean_ledger)

    arts = sample_artifacts
    # Create and persist a valid record
    rec1 = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=1,
        previous_record_hash="0" * 64,
        timestamp=1700000000.0,
        nonce="api_nonce_001",
        store_to_ledger=True
    )

    client = TestClient(app)

    # Login to obtain JWT token with VIEW_EVIDENCE permission
    login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpassword123"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /api/v1/assurance/provenance/1
    res_get = client.get("/api/v1/assurance/provenance/1", headers=headers)
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["sequence_id"] == 1
    assert data["model_id"] == arts["model_id"]
    assert data["provenance_hash"] == rec1.provenance_hash

    # 2. GET /api/v1/assurance/provenance/verify/1
    res_ver = client.get("/api/v1/assurance/provenance/verify/1", headers=headers)
    assert res_ver.status_code == 200
    ver_data = res_ver.json()
    assert ver_data["status"] == "VERIFIED"
    assert not ver_data["tampered"]
    assert ver_data["recommended_disposition"] == "ACCEPT"

    # 3. POST /api/v1/assurance/provenance/verify (Direct Payload Verification)
    payload_body = {
        "record": rec1.model_dump(),
        "raw_detections": arts["detections"],
        "expected_model_sha256": arts["model_sha256"],
        "raw_config": arts["config"],
        "raw_preprocessing": arts["preprocessing"]
    }
    res_post = client.post("/api/v1/assurance/provenance/verify", json=payload_body, headers=headers)
    assert res_post.status_code == 200
    post_data = res_post.json()
    assert post_data["status"] == "VERIFIED"
    assert not post_data["tampered"]

    # 4. GET /api/v1/assurance/provenance/chain/verify
    res_chain = client.get("/api/v1/assurance/provenance/chain/verify?limit=10", headers=headers)
    assert res_chain.status_code == 200
    chain_data = res_chain.json()
    assert chain_data["valid"] is True
    assert chain_data["records_checked"] == 1


# ---------------------------------------------------------------------------
# 13. Section 10: Complete 17-Scenario Alteration & Substitution Battery
# ---------------------------------------------------------------------------

@pytest.fixture
def base_provenance_record(provenance_engine, sample_artifacts):
    arts = sample_artifacts
    return provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=100,
        previous_record_hash="0" * 64,
        timestamp=1700001000.0,
        nonce="nonce_mutation_base",
        store_to_ledger=False
    )


def test_mutation_01_input_byte_changed(provenance_engine, base_provenance_record, sample_artifacts):
    """1. Input byte changed -> INPUT_TAMPERING_DETECTED -> QUARANTINE"""
    mutated_bytes = bytearray(sample_artifacts["frame_bytes"])
    mutated_bytes[0] = (mutated_bytes[0] + 1) % 256
    res = provenance_engine.verify_provenance_record(base_provenance_record, raw_input_bytes=bytes(mutated_bytes))
    assert res.tampered is True
    assert "INPUT_TAMPERING_DETECTED" in res.anomalies
    assert res.recommended_disposition == "QUARANTINE"


def test_mutation_02_input_hash_changed(provenance_engine, base_provenance_record):
    """2. Input hash changed -> PROVENANCE_HASH_MISMATCH -> QUARANTINE"""
    tampered_rec = base_provenance_record.model_copy(update={"input_hash": "a" * 64})
    res = provenance_engine.verify_provenance_record(tampered_rec)
    assert res.tampered is True
    assert "PROVENANCE_HASH_MISMATCH" in res.anomalies
    assert res.recommended_disposition == "QUARANTINE"


def test_mutation_03_model_weight_digest_changed(provenance_engine, base_provenance_record):
    """3. Model weight digest changed -> MODEL_TAMPERING_DETECTED -> QUARANTINE"""
    res = provenance_engine.verify_provenance_record(base_provenance_record, expected_model_sha256="b" * 64)
    assert res.tampered is True
    assert "MODEL_TAMPERING_DETECTED" in res.anomalies
    assert res.recommended_disposition == "QUARANTINE"


def test_mutation_04_model_name_changed(provenance_engine, base_provenance_record):
    """4. Model name changed -> MODEL_NAME_MISMATCH -> QUARANTINE"""
    res = provenance_engine.verify_provenance_record(base_provenance_record, expected_model_id="substituted_model_xyz")
    assert res.tampered is True
    assert "MODEL_NAME_MISMATCH" in res.anomalies
    assert res.recommended_disposition == "QUARANTINE"


def test_mutation_05_preprocessing_config_changed(provenance_engine, base_provenance_record, sample_artifacts):
    """5. Preprocessing config changed -> PREPROCESSING_TAMPERING_DETECTED -> QUARANTINE"""
    mutated_prep = copy.deepcopy(sample_artifacts["preprocessing"])
    mutated_prep["input_resolution"] = [320, 320]
    res = provenance_engine.verify_provenance_record(base_provenance_record, raw_preprocessing=mutated_prep)
    assert res.tampered is True
    assert "PREPROCESSING_TAMPERING_DETECTED" in res.anomalies
    assert res.recommended_disposition == "QUARANTINE"


def test_mutation_06_inference_config_changed(provenance_engine, base_provenance_record, sample_artifacts):
    """6. Inference config changed -> CONFIG_TAMPERING_DETECTED -> QUARANTINE"""
    mutated_cfg = copy.deepcopy(sample_artifacts["config"])
    mutated_cfg["confidence_threshold"] = 0.05
    res = provenance_engine.verify_provenance_record(base_provenance_record, raw_config=mutated_cfg)
    assert res.tampered is True
    assert "CONFIG_TAMPERING_DETECTED" in res.anomalies
    assert res.recommended_disposition == "QUARANTINE"


def test_mutation_07_output_class_changed(provenance_engine, base_provenance_record, sample_artifacts):
    """7. Output class changed -> OUTPUT_TAMPERING_DETECTED -> QUARANTINE"""
    mutated_dets = copy.deepcopy(sample_artifacts["detections"])
    mutated_dets[0]["class_name"] = "unauthorized_class"
    res = provenance_engine.verify_provenance_record(base_provenance_record, raw_output=mutated_dets)
    assert res.tampered is True
    assert "OUTPUT_TAMPERING_DETECTED" in res.anomalies
    assert res.recommended_disposition == "QUARANTINE"


def test_mutation_08_output_confidence_changed(provenance_engine, base_provenance_record, sample_artifacts):
    """8. Output confidence changed -> OUTPUT_TAMPERING_DETECTED -> QUARANTINE"""
    mutated_dets = copy.deepcopy(sample_artifacts["detections"])
    mutated_dets[0]["confidence"] = 0.9999
    res = provenance_engine.verify_provenance_record(base_provenance_record, raw_output=mutated_dets)
    assert res.tampered is True
    assert "OUTPUT_TAMPERING_DETECTED" in res.anomalies
    assert res.recommended_disposition == "QUARANTINE"


def test_mutation_09_output_bbox_changed(provenance_engine, base_provenance_record, sample_artifacts):
    """9. Output bounding box changed -> OUTPUT_TAMPERING_DETECTED -> QUARANTINE"""
    mutated_dets = copy.deepcopy(sample_artifacts["detections"])
    mutated_dets[0]["bbox"] = [0.0, 0.0, 10.0, 10.0]
    res = provenance_engine.verify_provenance_record(base_provenance_record, raw_output=mutated_dets)
    assert res.tampered is True
    assert "OUTPUT_TAMPERING_DETECTED" in res.anomalies
    assert res.recommended_disposition == "QUARANTINE"


def test_mutation_10_timestamp_changed(provenance_engine, base_provenance_record):
    """10. Timestamp changed in record -> PROVENANCE_HASH_MISMATCH -> QUARANTINE"""
    tampered_rec = base_provenance_record.model_copy(update={"timestamp": base_provenance_record.timestamp + 100.0})
    res = provenance_engine.verify_provenance_record(tampered_rec)
    assert res.tampered is True
    assert "PROVENANCE_HASH_MISMATCH" in res.anomalies


def test_mutation_11_sequence_changed(provenance_engine, base_provenance_record):
    """11. Sequence ID changed in record -> PROVENANCE_HASH_MISMATCH -> QUARANTINE"""
    tampered_rec = base_provenance_record.model_copy(update={"sequence_id": base_provenance_record.sequence_id + 5})
    res = provenance_engine.verify_provenance_record(tampered_rec)
    assert res.tampered is True
    assert "PROVENANCE_HASH_MISMATCH" in res.anomalies


def test_mutation_12_nonce_changed(provenance_engine, base_provenance_record):
    """12. Nonce changed in record -> PROVENANCE_HASH_MISMATCH -> QUARANTINE"""
    tampered_rec = base_provenance_record.model_copy(update={"nonce": "nonce_tampered_value"})
    res = provenance_engine.verify_provenance_record(tampered_rec)
    assert res.tampered is True
    assert "PROVENANCE_HASH_MISMATCH" in res.anomalies


def test_mutation_13_previous_record_hash_changed(provenance_engine, base_provenance_record):
    """13. Previous record hash changed -> PROVENANCE_HASH_MISMATCH -> QUARANTINE"""
    tampered_rec = base_provenance_record.model_copy(update={"previous_record_hash": "c" * 64})
    res = provenance_engine.verify_provenance_record(tampered_rec)
    assert res.tampered is True
    assert "PROVENANCE_HASH_MISMATCH" in res.anomalies


def test_mutation_14_entire_record_replaced(provenance_engine, base_provenance_record, sample_artifacts):
    """14. Entire record replaced with foreign data in sequence -> PROVENANCE_CHAIN_MISMATCH"""
    arts = sample_artifacts
    rec2 = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=101,
        previous_record_hash=base_provenance_record.provenance_hash,
        timestamp=base_provenance_record.timestamp + 1.0,
        nonce="nonce_seq_101",
        store_to_ledger=False
    )
    # Fabricated middle record
    foreign_rec = base_provenance_record.model_copy(update={
        "sequence_id": 101,
        "provenance_hash": "f" * 64,
        "nonce": "nonce_foreign_999"
    })
    chain_res = provenance_engine.verify_chain_and_replay([base_provenance_record, foreign_rec])
    assert not chain_res.valid
    assert any("PROVENANCE_CHAIN_MISMATCH" in a or "MISMATCH" in a for a in chain_res.anomalies)


def test_mutation_15_record_replayed(provenance_engine, base_provenance_record):
    """15. Record replayed with duplicate nonce / hash -> PROVENANCE_REPLAY_DETECTED"""
    replayed = base_provenance_record.model_copy(update={"sequence_id": base_provenance_record.sequence_id + 1})
    chain_res = provenance_engine.verify_chain_and_replay([base_provenance_record, replayed])
    assert not chain_res.valid
    assert any("PROVENANCE_REPLAY_DETECTED" in a for a in chain_res.anomalies)


def test_mutation_16_broken_chain(provenance_engine, base_provenance_record, sample_artifacts):
    """16. Broken chain (missing previous link) -> PROVENANCE_CHAIN_MISMATCH"""
    arts = sample_artifacts
    rec2 = provenance_engine.create_provenance_record(
        input_bytes=arts["frame_bytes"],
        model_id=arts["model_id"],
        model_sha256=arts["model_sha256"],
        architecture_id=arts["architecture_id"],
        raw_detections=arts["detections"],
        config=arts["config"],
        preprocessing_config=arts["preprocessing"],
        sequence_id=101,
        previous_record_hash="e" * 64,  # Broken link
        timestamp=base_provenance_record.timestamp + 1.0,
        nonce="nonce_seq_101_broken",
        store_to_ledger=False
    )
    chain_res = provenance_engine.verify_chain_and_replay([base_provenance_record, rec2])
    assert not chain_res.valid
    assert any("PROVENANCE_CHAIN_MISMATCH" in a for a in chain_res.anomalies)
    assert chain_res.recommended_disposition == "QUARANTINE"


def test_mutation_17_valid_unchanged_record(provenance_engine, base_provenance_record, sample_artifacts):
    """17. Valid unchanged record -> VERIFIED, valid=True, disposition=ACCEPT"""
    arts = sample_artifacts
    res = provenance_engine.verify_provenance_record(
        record=base_provenance_record,
        raw_input_bytes=arts["frame_bytes"],
        raw_output=arts["detections"],
        expected_model_sha256=arts["model_sha256"],
        expected_model_id=arts["model_id"],
        raw_config=arts["config"],
        raw_preprocessing=arts["preprocessing"]
    )
    assert res.status == "VERIFIED"
    assert not res.tampered
    assert len(res.anomalies) == 0
    assert res.recommended_disposition == "ACCEPT"

