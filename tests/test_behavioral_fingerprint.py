"""
Comprehensive deterministic unit and integration tests for
SIH26228 / TCVIAF Behavioral Model Fingerprinting & Model Integrity Assurance.
All randomness uses np.random.default_rng with fixed seeds for 100% reproducible tests.
"""
import pytest
import os
import json
import time
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient

import sys
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from services.assurance.model_fingerprint import (
    ModelFingerprintEngine,
    ProbeBattery,
    ReferenceModelProfile,
    BehavioralComparisonResult
)
from crypto_ledger import CryptoEvidenceLedger
from apps.backend.main import app


@pytest.fixture
def clean_ledger(tmp_path):
    """Isolated SQLite test ledger with model profile and assurance schemas."""
    db_path = tmp_path / "test_fingerprint_ledger.sqlite3"
    ledger = CryptoEvidenceLedger(db_path=db_path, use_sqlite_fallback=True)
    return ledger


@pytest.fixture
def fingerprint_engine(clean_ledger):
    battery = ProbeBattery(probe_set_id="ibvap-behavior-v1", seed=42)
    return ModelFingerprintEngine(ledger=clean_ledger, probe_battery=battery, divergence_threshold=0.15)


def make_mock_detector(class_name="person", conf=0.92, box=(0.1, 0.2, 0.4, 0.8), count_per_probe=2):
    """Deterministic mock detector returning predictable detections."""
    def detect(img: np.ndarray):
        dets = []
        for i in range(count_per_probe):
            dets.append({
                "class_name": class_name,
                "confidence": conf,
                "bbox": {"width": box[2] - box[0], "height": box[3] - box[1], "x1": box[0], "y1": box[1], "x2": box[2], "y2": box[3]}
            })
        return dets
    return detect


# ---------------------------------------------------------------------------
# 1. Reference Fingerprint Creation & Determinism
# ---------------------------------------------------------------------------

def test_reference_fingerprint_creation_and_determinism(fingerprint_engine):
    """Verifies reference fingerprint extraction is deterministic and produces identical digests."""
    mock_fn = make_mock_detector("person", 0.90, (0.1, 0.1, 0.3, 0.7), count_per_probe=2)

    profile_1 = fingerprint_engine.extract_model_fingerprint(
        model_name="yolo11n_ref",
        detect_fn=mock_fn,
        model_sha256="a" * 64,
        architecture_id="yolo11n"
    )

    profile_2 = fingerprint_engine.extract_model_fingerprint(
        model_name="yolo11n_ref",
        detect_fn=mock_fn,
        model_sha256="a" * 64,
        architecture_id="yolo11n"
    )

    assert profile_1.fingerprint_digest == profile_2.fingerprint_digest
    assert profile_1.metrics_summary["total_detections"] == 10  # 2 dets * 5 probes
    assert profile_1.metrics_summary["class_distribution"] == {"person": 10}
    assert profile_1.metrics_summary["confidence_stats"]["mean"] == 0.90


# ---------------------------------------------------------------------------
# 2. Same Model + Same Probe Battery -> NORMAL
# ---------------------------------------------------------------------------

def test_same_model_comparison_normal(fingerprint_engine):
    """Verifies that evaluating an identical candidate model yields status NORMAL with 0.0 divergence."""
    mock_fn = make_mock_detector("person", 0.90, (0.1, 0.1, 0.3, 0.7), count_per_probe=2)

    ref_profile = fingerprint_engine.extract_model_fingerprint("model_a", mock_fn, model_sha256="a" * 64)
    cand_profile = fingerprint_engine.extract_model_fingerprint("model_a", mock_fn, model_sha256="a" * 64)

    res = fingerprint_engine.compare_fingerprints(ref_profile, cand_profile)
    assert res.status == "NORMAL"
    assert res.divergence_score == 0.0
    assert res.recommended_disposition == "ACCEPT"
    assert res.confidence is None  # Uncalibrated; null by design


# ---------------------------------------------------------------------------
# 3. Model Identity Mismatch (Binary Tampering / Substitution)
# ---------------------------------------------------------------------------

def test_model_identity_mismatch_detected(fingerprint_engine):
    """Verifies that if model weights SHA-256 differs from reference, it is flagged as MODEL_IDENTITY_MISMATCH."""
    mock_fn = make_mock_detector("person", 0.90)

    ref_profile = fingerprint_engine.extract_model_fingerprint("model_prod", mock_fn, model_sha256="1" * 64)
    cand_profile = fingerprint_engine.extract_model_fingerprint("model_prod", mock_fn, model_sha256="2" * 64)  # Changed SHA

    res = fingerprint_engine.compare_fingerprints(ref_profile, cand_profile)
    assert res.status == "MODEL_IDENTITY_MISMATCH"
    assert res.recommended_disposition == "QUARANTINE"
    assert "MODEL IDENTITY MISMATCH" in res.evidence


# ---------------------------------------------------------------------------
# 4. Behavioral Deviation (Weight Shift / Model Replacement with Same Hash)
# ---------------------------------------------------------------------------

def test_behavioral_deviation_detected(fingerprint_engine):
    """
    Simulates a modified model (e.g. outputs vehicle instead of person, lower confidence, different count).
    Verifies that BEHAVIORAL_DEVIATION is flagged with recommendation REVIEW.
    """
    detector_ref = make_mock_detector("person", 0.95, (0.1, 0.1, 0.3, 0.7), count_per_probe=2)
    # Substituted / degraded model: detects vehicle with low confidence and different count
    detector_shifted = make_mock_detector("vehicle", 0.45, (0.4, 0.4, 0.9, 0.9), count_per_probe=4)

    ref_profile = fingerprint_engine.extract_model_fingerprint("model_sec", detector_ref, model_sha256="f" * 64)
    cand_profile = fingerprint_engine.extract_model_fingerprint("model_sec", detector_shifted, model_sha256="f" * 64)

    res = fingerprint_engine.compare_fingerprints(ref_profile, cand_profile, threshold=0.15)
    assert res.status == "BEHAVIORAL_DEVIATION"
    assert res.divergence_score > 0.15
    assert res.recommended_disposition == "REVIEW"
    assert res.metric_breakdown["class_divergence"] > 0.50
    assert "BEHAVIORAL DEVIATION" in res.evidence


# ---------------------------------------------------------------------------
# 5. Missing Reference Profile -> NO_REFERENCE_FINGERPRINT
# ---------------------------------------------------------------------------

def test_missing_reference_profile_handled(fingerprint_engine):
    """When a model has no reference profile registered, reports NO_REFERENCE_FINGERPRINT without crashing."""
    mock_fn = make_mock_detector()
    res = fingerprint_engine.verify_candidate_model(
        model_name="unregistered_experimental_model",
        detect_fn=mock_fn
    )
    assert res.status == "NO_REFERENCE_FINGERPRINT"
    assert res.divergence_score is None
    assert res.recommended_disposition == "REVIEW"
    assert "No reference profile registered" in res.evidence


# ---------------------------------------------------------------------------
# 6. Changed Probe-Set Version -> PROBE_SET_MISMATCH
# ---------------------------------------------------------------------------

def test_changed_probe_set_mismatch(clean_ledger):
    """Detects when reference and candidate were evaluated on different probe batteries."""
    engine_v1 = ModelFingerprintEngine(ledger=clean_ledger, probe_battery=ProbeBattery("probe-v1"))
    engine_v2 = ModelFingerprintEngine(ledger=clean_ledger, probe_battery=ProbeBattery("probe-v2"))

    mock_fn = make_mock_detector()
    ref_prof = engine_v1.extract_model_fingerprint("model_test", mock_fn, model_sha256="c" * 64)
    cand_prof = engine_v2.extract_model_fingerprint("model_test", mock_fn, model_sha256="c" * 64)

    res = engine_v1.compare_fingerprints(ref_prof, cand_prof)
    assert res.status == "PROBE_SET_MISMATCH"
    assert res.recommended_disposition == "REVIEW"


# ---------------------------------------------------------------------------
# 7. Model Execution Error Gracefully Handled
# ---------------------------------------------------------------------------

def test_execution_error_handled(fingerprint_engine, clean_ledger):
    """If candidate model inference throws an exception, logs EXECUTION_ERROR and recommends REVIEW."""
    # First register reference profile
    good_fn = make_mock_detector()
    ref_prof = fingerprint_engine.extract_model_fingerprint("crash_model", good_fn, model_sha256="0" * 64)
    clean_ledger.register_model_profile(ref_prof.model_dump())

    def crashing_detector(img):
        raise RuntimeError("CUDA Device Assert Failed: invalid tensor dimension")

    res = fingerprint_engine.verify_candidate_model("crash_model", crashing_detector)
    assert res.status == "EXECUTION_ERROR"
    assert res.recommended_disposition == "REVIEW"
    assert "Inference execution failed" in res.evidence


# ---------------------------------------------------------------------------
# 8. Governance Integration & Analyst Override Isolation
# ---------------------------------------------------------------------------

def test_analyst_override_preserved_against_model_anomaly(fingerprint_engine, clean_ledger):
    """
    Regression Test:
    Automated behavioral findings must NEVER overwrite human analyst override in governance_audit.
    """
    dummy_frame = np.zeros((64, 64, 3), dtype=np.uint8)
    block = clean_ledger.commit_event(frame=dummy_frame, camera_id="CAM_01")
    seq_id = block.sequence_id

    # 1. Analyst explicitly marks block as ACCEPT
    clean_ledger.update_disposition(seq_id, "ACCEPT", analyst_id="analyst_priya", reason="Manual inspection approved.")
    assert clean_ledger.get_latest_dispositions()[seq_id] == "ACCEPT"

    # 2. Automated behavioral deviation finding is logged on this sequence
    comp_result = BehavioralComparisonResult(
        model_name="yolo11n",
        reference_sha256="ref_sha",
        candidate_sha256="ref_sha",
        probe_set_id="ibvap-behavior-v1",
        status="BEHAVIORAL_DEVIATION",
        divergence_score=0.45,
        threshold=0.15,
        confidence=None,
        recommended_disposition="REVIEW",
        metric_breakdown={"class_divergence": 0.45},
        evidence="Simulated behavioral shift",
        limitations="Probe divergence heuristic"
    )
    fingerprint_engine._persist_finding(comp_result, sequence_id=seq_id)

    # 3. VERIFY: Human analyst disposition in governance_audit is still ACCEPT!
    current_disposition = clean_ledger.get_latest_dispositions()[seq_id]
    assert current_disposition == "ACCEPT"

    # 4. Verify finding is recorded in assurance_findings table
    findings = clean_ledger.get_assurance_findings(limit=5, sequence_id=seq_id)
    assert len(findings) == 1
    assert findings[0]["check_type"] == "BEHAVIORAL_MODEL_FINGERPRINT"
    assert findings[0]["status"] == "BEHAVIORAL_DEVIATION"


# ---------------------------------------------------------------------------
# 9. API Router Integration & Validation Tests
# ---------------------------------------------------------------------------

def test_api_model_profiles_and_findings(clean_ledger):
    """Tests GET/POST endpoints for model behavioral profiles and assurance findings."""
    client = TestClient(app)

    # 1. Register a profile via API (with admin login)
    login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpassword123"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    reg_payload = {
        "model_name": "api_test_yolo",
        "model_format": "PYTORCH_PT",
        "model_sha256": "e" * 64,
        "architecture_id": "yolo11n",
        "config_digest": "c" * 64,
        "preprocessing_digest": "p" * 64,
        "probe_set_id": "ibvap-behavior-v1",
        "fingerprint_version": "v1.0",
        "fingerprint_digest": "d" * 64,
        "metrics_summary": {"total_detections": 12}
    }
    reg_res = client.post("/api/v1/assurance/models/register", json=reg_payload, headers=headers)
    assert reg_res.status_code == 200
    assert reg_res.json()["status"] == "REGISTERED"

    # 2. List profiles
    list_res = client.get("/api/v1/assurance/models/profiles", headers=headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] >= 1
    names = [p["model_name"] for p in data["profiles"]]
    assert "api_test_yolo" in names

    # 3. Get single profile
    get_res = client.get("/api/v1/assurance/models/profiles/api_test_yolo", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["model_sha256"] == "e" * 64

    # 4. Non-existent profile 404
    missing_res = client.get("/api/v1/assurance/models/profiles/non_existent_model_xyz", headers=headers)
    assert missing_res.status_code == 404


# ---------------------------------------------------------------------------
# 10. Explicit Scenarios Required by SIH26228 Specification
# ---------------------------------------------------------------------------

def test_filename_change_identical_weights_behavior_equivalent(fingerprint_engine):
    """
    Scenario 4: Changed model filename/identity, but identical weights SHA-256
    and identical behavioral execution -> behavioral comparison remains congruent.
    """
    mock_fn = make_mock_detector("person", 0.92, (0.1, 0.2, 0.4, 0.8), count_per_probe=2)

    profile_orig = fingerprint_engine.extract_model_fingerprint("model_prod_v1.pt", mock_fn, model_sha256="abc" * 21 + "a")
    profile_renamed = fingerprint_engine.extract_model_fingerprint("renamed_copy.pt", mock_fn, model_sha256="abc" * 21 + "a")

    res = fingerprint_engine.compare_fingerprints(profile_orig, profile_renamed)
    assert res.status == "NORMAL"
    assert res.divergence_score == 0.0
    assert res.recommended_disposition == "ACCEPT"


def test_preprocessing_config_change_alters_fingerprint_binding(fingerprint_engine):
    """
    Scenario 6: Changing preprocessing configuration (e.g. resolution or confidence threshold)
    alters the preprocessing digest and flags PREPROCESSING_MISMATCH.
    """
    mock_fn = make_mock_detector("person", 0.90)

    cfg_ref = {"imgsz": 640, "conf": 0.25, "normalization": "div_255"}
    cfg_altered = {"imgsz": 320, "conf": 0.50, "normalization": "none"}

    profile_ref = fingerprint_engine.extract_model_fingerprint("model_cfg", mock_fn, model_sha256="a" * 64, preprocessing_cfg=cfg_ref)
    profile_alt = fingerprint_engine.extract_model_fingerprint("model_cfg", mock_fn, model_sha256="a" * 64, preprocessing_cfg=cfg_altered)

    assert profile_ref.preprocessing_digest != profile_alt.preprocessing_digest

    res = fingerprint_engine.compare_fingerprints(profile_ref, profile_alt)
    assert res.status == "PREPROCESSING_MISMATCH"
    assert res.recommended_disposition == "REVIEW"
    assert "PREPROCESSING MISMATCH" in res.evidence


def test_unsupported_model_output_unavailable(fingerprint_engine):
    """
    Scenario 8: If a model format or output type cannot be fingerprinted,
    system returns BEHAVIORAL_FINGERPRINT_UNAVAILABLE rather than fabricating numbers.
    """
    mock_fn = make_mock_detector()
    res = fingerprint_engine.verify_candidate_model(
        model_name="audio_whisper_v1",
        detect_fn=mock_fn,
        model_format="UNSUPPORTED"
    )
    assert res.status == "BEHAVIORAL_FINGERPRINT_UNAVAILABLE"
    assert res.divergence_score is None
    assert res.recommended_disposition == "REVIEW"
    assert "limitations" in res.model_dump()


def test_api_authentication_unauthorized_rejected():
    """
    Scenario 11: Attempting to query or register model profiles with an
    invalid/tampered authentication token is rejected with 401 Unauthorized.
    """
    client = TestClient(app)
    unauth_res = client.get(
        "/api/v1/assurance/models/profiles",
        headers={"Authorization": "Bearer invalid_tampered_token_xyz"}
    )
    assert unauth_res.status_code == 401

    unauth_post = client.post(
        "/api/v1/assurance/models/register",
        json={},
        headers={"Authorization": "Bearer invalid_tampered_token_xyz"}
    )
    assert unauth_post.status_code == 401


# ---------------------------------------------------------------------------
# 11. Benchmarking / Latency Measurement
# ---------------------------------------------------------------------------

def test_fingerprint_overhead_benchmark(fingerprint_engine):
    """
    Measures and logs actual execution overhead of probe battery fingerprinting
    and comparison math to prevent unsubstantiated real-time claims.
    """
    detector = make_mock_detector("person", 0.90, count_per_probe=3)

    # 1. Time probe battery generation & fingerprint extraction
    t0 = time.perf_counter()
    ref_profile = fingerprint_engine.extract_model_fingerprint("bench_model", detector, model_sha256="a" * 64)
    t_extract = (time.perf_counter() - t0) * 1000.0  # ms

    # 2. Time comparison
    cand_profile = fingerprint_engine.extract_model_fingerprint("bench_model", detector, model_sha256="a" * 64)
    t1 = time.perf_counter()
    res = fingerprint_engine.compare_fingerprints(ref_profile, cand_profile)
    t_compare = (time.perf_counter() - t1) * 1000.0  # ms

    # Assert reasonable bounded latency (mock detector should complete in <50ms)
    assert t_extract < 150.0, f"Fingerprint extraction too slow: {t_extract:.2f}ms"
    assert t_compare < 10.0, f"Fingerprint comparison too slow: {t_compare:.2f}ms"
    assert res.status == "NORMAL"
