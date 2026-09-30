"""
tests/test_advanced_ood_and_mmd.py
==================================
Unit and integration tests for advanced assurance capabilities:
1. Multivariate Mahalanobis Distance OOD detection with regularized covariance.
2. k-Nearest Neighbors (kNN) feature density OOD detection.
3. Multivariate Kernel Maximum Mean Discrepancy (MMD) distribution shift detection with permutation testing.
4. FastAPI endpoint integrations for all three capabilities.
"""
import pytest
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient

import sys
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from services.assurance.data_integrity import DataIntegrityAssurance
from crypto_ledger import CryptoEvidenceLedger
from apps.backend.main import app


@pytest.fixture
def clean_ledger(tmp_path):
    db_path = tmp_path / "test_advanced_assurance.sqlite3"
    return CryptoEvidenceLedger(db_path=db_path, use_sqlite_fallback=True)


@pytest.fixture
def engine(clean_ledger):
    return DataIntegrityAssurance(ledger=clean_ledger)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer mock-analyst-token"}


# ---------------------------------------------------------------------------
# 1. Mahalanobis Distance Tests
# ---------------------------------------------------------------------------

def test_mahalanobis_ood_detection(engine):
    """
    Verifies that Mahalanobis distance correctly detects outliers that violate
    the covariance structure of correlated features.
    """
    rng = np.random.default_rng(42)
    # 2D distribution with strong positive correlation
    cov = [[1.0, 0.9], [0.9, 1.0]]
    ref = rng.multivariate_normal([0.0, 0.0], cov, size=150)

    # In-distribution sample near the correlation axis
    in_sample = np.array([1.0, 0.95])
    finding_in = engine.check_ood_mahalanobis("sample_in", in_sample, ref, significance_level=0.01)
    assert finding_in.status == "IN_DISTRIBUTION"
    assert finding_in.score is not None
    assert finding_in.score < finding_in.threshold

    # Out-of-distribution sample violating the correlation axis
    # (Euclidean distance is small, but Mahalanobis distance is enormous!)
    out_sample = np.array([2.0, -2.0])
    finding_out = engine.check_ood_mahalanobis("sample_out", out_sample, ref, significance_level=0.01)
    assert finding_out.status == "POTENTIAL_OOD"
    assert finding_out.score > finding_out.threshold
    assert finding_out.confidence is not None
    assert finding_out.confidence > 0.95

    # Recommendation should be REVIEW
    rec = engine.recommend_governance_disposition(finding_out)
    assert rec == "REVIEW"


def test_mahalanobis_no_baseline(engine):
    """Verifies that Mahalanobis refuses to fabricate baselines when missing."""
    sample = np.array([1.0, 2.0])
    finding = engine.check_ood_mahalanobis("sample_none", sample, None)
    assert finding.status == "NO_REFERENCE_BASELINE"
    assert finding.score is None


# ---------------------------------------------------------------------------
# 2. kNN Density Tests
# ---------------------------------------------------------------------------

def test_knn_ood_detection(engine):
    """
    Verifies that kNN feature density detects samples located in sparse regions.
    """
    rng = np.random.default_rng(42)
    ref = rng.normal(0.0, 1.0, size=(100, 3))

    # Dense cluster sample
    in_sample = np.array([0.1, 0.0, -0.1])
    finding_in = engine.check_ood_knn_density("sample_in", in_sample, ref, k=5, threshold_percentile=95.0)
    assert finding_in.status == "IN_DISTRIBUTION"
    assert finding_in.score < finding_in.threshold

    # Distant isolated outlier
    out_sample = np.array([5.0, 5.0, 5.0])
    finding_out = engine.check_ood_knn_density("sample_out", out_sample, ref, k=5, threshold_percentile=95.0)
    assert finding_out.status == "POTENTIAL_OOD"
    assert finding_out.score > finding_out.threshold


# ---------------------------------------------------------------------------
# 3. Kernel MMD Distribution Shift Tests
# ---------------------------------------------------------------------------

def test_kernel_mmd_shift_detection(engine):
    """
    Verifies that Kernel Maximum Mean Discrepancy detects multivariate distribution shifts.
    """
    rng = np.random.default_rng(42)
    ref = rng.normal(0.0, 1.0, size=(40, 4))
    shifted = rng.normal(0.9, 1.0, size=(40, 4))

    finding = engine.check_distribution_shift_mmd(shifted, ref, alpha=0.05, n_permutations=50)
    assert finding.status == "DISTRIBUTION_SHIFT_DETECTED"
    assert finding.score is not None
    assert finding.score > 0.0
    assert "Kernel MMD^2 statistic" in finding.evidence

    rec = engine.recommend_governance_disposition(finding)
    assert rec == "REVIEW"


def test_kernel_mmd_in_distribution(engine):
    """
    Verifies that Kernel MMD classifies samples from the same distribution as IN_DISTRIBUTION.
    """
    rng = np.random.default_rng(42)
    ref = rng.normal(0.0, 1.0, size=(40, 4))
    same = rng.normal(0.0, 1.0, size=(40, 4))

    finding = engine.check_distribution_shift_mmd(same, ref, alpha=0.05, n_permutations=50)
    assert finding.status == "IN_DISTRIBUTION"


# ---------------------------------------------------------------------------
# 4. REST API Endpoint Tests
# ---------------------------------------------------------------------------

def test_api_mahalanobis_and_mmd_endpoints(engine, monkeypatch):
    """Verifies FastAPI endpoints for Mahalanobis OOD and MMD shift."""
    from apps.backend.routers import assurance as assurance_module
    from apps.backend.auth.jwt_auth import require_permission
    from apps.backend.auth.rbac import Permission

    monkeypatch.setattr(assurance_module, "get_ledger", lambda: engine.ledger)
    app.dependency_overrides[require_permission(Permission.VIEW_EVIDENCE)] = lambda: {"sub": "analyst_1", "role": "ADMIN"}

    try:
        client = TestClient(app)

        # Test Mahalanobis endpoint
        resp = client.post(
            "/api/v1/assurance/ood/mahalanobis",
            json={
                "asset_id": "test_asset",
                "features": [0.1, 0.2],
                "reference_features": [[0.0, 0.0], [0.1, 0.1], [-0.1, -0.1], [0.2, 0.2]],
                "significance_level": 0.05
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["check_type"] == "OOD_MAHALANOBIS"
        assert "score" in data

        # Test MMD endpoint
        rng = np.random.default_rng(42)
        ref = rng.normal(0, 1, size=(20, 2)).tolist()
        curr = rng.normal(1.5, 1, size=(20, 2)).tolist()

        resp_mmd = client.post(
            "/api/v1/assurance/distribution_shift/mmd",
            json={
                "current_features": curr,
                "reference_features": ref,
                "alpha": 0.05,
                "n_permutations": 30
            }
        )
        assert resp_mmd.status_code == 200
        mmd_data = resp_mmd.json()
        assert mmd_data["check_type"] == "DISTRIBUTION_SHIFT_MMD"
        assert mmd_data["status"] == "DISTRIBUTION_SHIFT_DETECTED"
    finally:
        app.dependency_overrides.clear()

