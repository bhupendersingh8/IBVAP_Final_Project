"""
Comprehensive deterministic unit and integration tests for
SIH26228 / TCVIAF Data Integrity and Distribution Shift Assurance.
All tests use deterministic seeded data (np.random.default_rng) with zero random flakiness.
"""
import pytest
import os
import json
import numpy as np
import cv2
from pathlib import Path
from fastapi.testclient import TestClient

import sys
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from services.assurance.data_integrity import (
    DataIntegrityAssurance,
    AssuranceFinding,
    compute_dhash,
    compute_hamming_distance
)
from crypto_ledger import CryptoEvidenceLedger
from apps.backend.main import app


@pytest.fixture
def clean_ledger(tmp_path):
    """Isolated SQLite test ledger with assurance schema."""
    db_path = tmp_path / "test_assurance.sqlite3"
    ledger = CryptoEvidenceLedger(db_path=db_path, use_sqlite_fallback=True)
    return ledger


@pytest.fixture
def integrity_engine(clean_ledger):
    return DataIntegrityAssurance(ledger=clean_ledger)


# ---------------------------------------------------------------------------
# 1. Exact Duplicate Detection Tests
# ---------------------------------------------------------------------------

def test_exact_duplicate_detection(integrity_engine, tmp_path):
    """Verifies SHA-256 byte digest matching detects identical image files."""
    img_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    img_file = tmp_path / "img_exact.png"
    img_file.write_bytes(img_bytes)

    import hashlib
    ref_hash = hashlib.sha256(img_bytes).hexdigest()

    finding = integrity_engine.check_exact_duplicate("asset_001", str(img_file), {ref_hash}, sequence_id=10)
    assert finding is not None
    assert finding.status == "POTENTIAL_DUPLICATE"
    assert finding.method == "SHA-256 Exact Match"
    assert finding.score == 1.0
    assert "Matches reference digest" in finding.evidence

    # Recommendation for duplicate should be REVIEW
    rec = integrity_engine.recommend_governance_disposition(finding)
    assert rec == "REVIEW"


def test_unique_sample_not_flagged_as_duplicate(integrity_engine, tmp_path):
    """Verifies unique files are classified as NORMAL."""
    img_file = tmp_path / "img_unique.png"
    img_file.write_bytes(b"unique_byte_stream_4096")

    finding = integrity_engine.check_exact_duplicate("asset_002", str(img_file), {"unrelated_hash"}, sequence_id=11)
    assert finding is not None
    assert finding.status == "NORMAL"
    assert finding.score == 0.0

    rec = integrity_engine.recommend_governance_disposition(finding)
    assert rec == "ACCEPT"


# ---------------------------------------------------------------------------
# 2. Perceptual Near-Duplicate Detection Tests
# ---------------------------------------------------------------------------

def test_perceptual_near_duplicate_detection(integrity_engine):
    """Verifies 64-bit dHash perceptual similarity detects compressed/slightly perturbed duplicates."""
    # Deterministic base image (black with a white square)
    base_img = np.zeros((120, 120, 3), dtype=np.uint8)
    base_img[20:80, 20:80] = 255
    base_hash = compute_dhash(base_img)

    # Slightly perturbed image (shifted by 1 pixel, slight noise)
    perturbed_img = base_img.copy()
    perturbed_img[21:81, 21:81] = 250
    perturbed_hash = compute_dhash(perturbed_img)

    hamming_dist = compute_hamming_distance(base_hash, perturbed_hash)
    assert hamming_dist <= 5, f"Expected close perceptual hash, got distance {hamming_dist}"

    ref_map = {"ref_base": base_hash}
    finding = integrity_engine.check_perceptual_near_duplicate(
        "asset_perturbed",
        perturbed_img,
        ref_map,
        max_hamming_distance=5,
        sequence_id=12
    )
    assert finding is not None
    assert finding.status == "POTENTIAL_NEAR_DUPLICATE"
    assert finding.method == "Perceptual Difference Hash (dHash-64)"
    assert finding.score >= 0.90
    assert integrity_engine.recommend_governance_disposition(finding) == "REVIEW"


def test_perceptual_distinct_images(integrity_engine):
    """Verifies completely distinct image patterns have large Hamming distance and are NORMAL."""
    rng = np.random.default_rng(101)
    img_a = np.zeros((100, 100, 3), dtype=np.uint8)
    img_a[:, :50] = 255  # Left half white

    img_b = np.zeros((100, 100, 3), dtype=np.uint8)
    img_b[:50, :] = 255  # Top half white

    hash_a = compute_dhash(img_a)
    hash_b = compute_dhash(img_b)

    dist = compute_hamming_distance(hash_a, hash_b)
    assert dist > 10, f"Expected distinct hashes, got distance {dist}"

    finding = integrity_engine.check_perceptual_near_duplicate("asset_b", img_b, {"ref_a": hash_a}, max_hamming_distance=5)
    assert finding.status == "NORMAL"
    assert integrity_engine.recommend_governance_disposition(finding) == "ACCEPT"


# ---------------------------------------------------------------------------
# 3. Label Consistency / Annotation Sanity Tests
# ---------------------------------------------------------------------------

def test_yolo_label_anomaly_detection(integrity_engine, tmp_path):
    """Detects invalid class IDs, impossible bounding boxes, and malformed syntax."""
    # Line 1: Valid
    # Line 2: Impossible Bbox (cx = 1.8 > 1.0)
    # Line 3: Impossible Bbox (w = -0.1 <= 0)
    # Line 4: Invalid Class ID (99 not in {0, 1})
    # Line 5: Malformed Arity (missing height)
    annotation_text = (
        "0 0.5 0.5 0.2 0.2\n"
        "1 1.8 0.5 0.2 0.2\n"
        "0 0.5 0.5 -0.1 0.2\n"
        "99 0.5 0.5 0.2 0.2\n"
        "1 0.5 0.5 0.2\n"
    )
    lbl_file = tmp_path / "bad_labels.txt"
    lbl_file.write_text(annotation_text)

    findings = integrity_engine.check_yolo_labels("ann_001", str(lbl_file), valid_classes={0, 1}, sequence_id=20)
    assert len(findings) == 4

    statuses = [f.status for f in findings]
    assert statuses.count("IMPOSSIBLE_BBOX") == 2
    assert "INVALID_CLASS" in statuses
    assert "MALFORMED_FORMAT" in statuses

    # All malformed annotations should strictly recommend QUARANTINE
    for f in findings:
        assert integrity_engine.recommend_governance_disposition(f) == "QUARANTINE"


def test_yolo_label_clean(integrity_engine, tmp_path):
    """Clean YOLO annotation produces zero anomaly findings."""
    clean_text = "0 0.5 0.5 0.2 0.2\n1 0.2 0.3 0.1 0.4\n"
    lbl_file = tmp_path / "clean_labels.txt"
    lbl_file.write_text(clean_text)

    findings = integrity_engine.check_yolo_labels("ann_clean", str(lbl_file), valid_classes={0, 1})
    assert len(findings) == 0


# ---------------------------------------------------------------------------
# 4. Centroid-Distance Anomaly Indicator (OOD) Tests
# ---------------------------------------------------------------------------

def test_ood_with_deterministic_reference_baseline(integrity_engine):
    """Verifies centroid distance flags true outliers beyond 3-sigma without fabricating confidence."""
    rng = np.random.default_rng(42)
    # 100 reference samples centered at 0 with std 1
    ref_features = rng.normal(loc=0.0, scale=1.0, size=(100, 8))

    # In-distribution sample
    in_dist_sample = rng.normal(loc=0.0, scale=1.0, size=(8,))
    finding_normal = integrity_engine.check_ood("sample_norm", in_dist_sample, ref_features)
    assert finding_normal.status == "IN_DISTRIBUTION"
    assert finding_normal.confidence is None  # Must NOT invent calibrated confidence
    assert integrity_engine.recommend_governance_disposition(finding_normal) == "ACCEPT"

    # Outlier sample (mean 15.0 >> 3-sigma threshold)
    outlier_sample = np.full((8,), 15.0)
    finding_ood = integrity_engine.check_ood("sample_outlier", outlier_sample, ref_features)
    assert finding_ood.status == "POTENTIAL_OOD"
    assert finding_ood.confidence is None
    assert finding_ood.score > finding_ood.threshold
    assert integrity_engine.recommend_governance_disposition(finding_ood) == "REVIEW"


def test_ood_no_reference_baseline_refuses_fabrication(integrity_engine):
    """Refuses to score OOD if reference baseline is missing, reports NO_REFERENCE_BASELINE."""
    sample = np.array([1.0, 2.0, 3.0])
    finding = integrity_engine.check_ood("sample_orphan", sample, None)
    assert finding.status == "NO_REFERENCE_BASELINE"
    assert finding.score is None
    assert finding.threshold is None
    assert finding.confidence is None
    assert "unavailable" in finding.evidence
    assert integrity_engine.recommend_governance_disposition(finding) == "REVIEW"


# ---------------------------------------------------------------------------
# 5. Distribution Shift Monitoring Tests (KS Test)
# ---------------------------------------------------------------------------

def test_distribution_shift_ks_detection(integrity_engine):
    """Verifies two-sample Kolmogorov-Smirnov test accurately detects distribution shifts."""
    rng = np.random.default_rng(2026)
    ref_batch = rng.normal(loc=0.0, scale=1.0, size=(80, 6))

    # Shifted batch (mean shifted by +2.0 standard deviations)
    shifted_batch = rng.normal(loc=2.0, scale=1.0, size=(60, 6))
    finding_shift = integrity_engine.check_distribution_shift(shifted_batch, ref_batch, alpha=0.05)

    assert finding_shift.status == "DISTRIBUTION_SHIFT_DETECTED"
    assert finding_shift.score > 0.40  # KS statistic is large
    assert finding_shift.confidence is None  # Significance represented by p-value, not fake confidence
    assert "min p-value" in finding_shift.evidence
    assert integrity_engine.recommend_governance_disposition(finding_shift) == "REVIEW"


def test_distribution_no_shift_case(integrity_engine):
    """Identically distributed batches do NOT trigger a shift."""
    rng = np.random.default_rng(777)
    ref_batch = rng.normal(loc=0.0, scale=1.0, size=(100, 4))
    same_batch = rng.normal(loc=0.0, scale=1.0, size=(80, 4))

    finding_normal = integrity_engine.check_distribution_shift(same_batch, ref_batch, alpha=0.01)
    assert finding_normal.status == "IN_DISTRIBUTION"
    assert integrity_engine.recommend_governance_disposition(finding_normal) == "ACCEPT"


# ---------------------------------------------------------------------------
# 6. Governance Integration & Analyst Override Isolation
# ---------------------------------------------------------------------------

def test_analyst_override_preserved_against_automated_recommendation(integrity_engine, clean_ledger):
    """
    CRITICAL REGRESSION TEST:
    An automated integrity check that flags an anomaly (e.g. QUARANTINE or REVIEW)
    must NEVER overwrite the human analyst's explicit disposition in governance_audit.
    """
    # 1. Commit dummy frame block
    dummy_frame = np.zeros((80, 80, 3), dtype=np.uint8)
    block = clean_ledger.commit_event(frame=dummy_frame, camera_id="CAM_01", severity="HIGH")
    seq_id = block.sequence_id

    # 2. Analyst explicitly accepts the block after physical verification
    clean_ledger.update_disposition(seq_id, "ACCEPT", analyst_id="analyst_vikram", reason="Physical sentry clearance verified.")
    assert clean_ledger.get_latest_dispositions()[seq_id] == "ACCEPT"

    # 3. Later, an automated data integrity anomaly is logged on this sequence
    finding = AssuranceFinding(
        sequence_id=seq_id,
        asset_id=f"frame_{seq_id}",
        asset_type="IMAGE",
        check_type="OOD_ANOMALY_INDICATOR",
        method="Centroid-Distance Anomaly Indicator",
        score=99.0,
        threshold=10.0,
        status="POTENTIAL_OOD",
        confidence=None,
        evidence="Simulated severe optical anomaly",
        limitations="Centroid heuristic"
    )
    # Automated recommendation is REVIEW
    rec = integrity_engine.recommend_governance_disposition(finding)
    assert rec == "REVIEW"

    # Persist the finding
    integrity_engine._persist_finding(finding)

    # 4. VERIFY: The analyst disposition in the ledger remains unchanged as ACCEPT!
    current_analyst_disposition = clean_ledger.get_latest_dispositions()[seq_id]
    assert current_analyst_disposition == "ACCEPT", "Analyst disposition was illegally overwritten by automated check!"

    # 5. Verify the finding was persisted and linked to seq_id
    stored_findings = clean_ledger.get_assurance_findings(limit=10, sequence_id=seq_id)
    assert len(stored_findings) == 1
    assert stored_findings[0]["status"] == "POTENTIAL_OOD"
    assert stored_findings[0]["sequence_id"] == seq_id


# ---------------------------------------------------------------------------
# 7. Backend API Router Tests
# ---------------------------------------------------------------------------

def test_api_assurance_findings_endpoint(clean_ledger):
    """Tests the GET /api/v1/assurance/findings endpoint with auth and validation."""
    client = TestClient(app)

    # 1. Test unauthorized access fails with invalid token
    unauth_resp = client.get("/api/v1/assurance/findings", headers={"Authorization": "Bearer invalid_malformed_token"})
    assert unauth_resp.status_code == 401

    # 2. Test input validation (bounds on limit)
    # Login as admin to get auth headers
    login_resp = client.post("/api/v1/auth/login", data={"username": "admin", "password": "adminpassword123"})
    if login_resp.status_code == 200:
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Valid request
        res = client.get("/api/v1/assurance/findings?limit=10", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "findings" in data
        assert "storage_backend" in data

        # Out-of-bounds limit rejected
        bad_limit = client.get("/api/v1/assurance/findings?limit=9999", headers=headers)
        assert bad_limit.status_code == 422
