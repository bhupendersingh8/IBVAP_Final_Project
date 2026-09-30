"""
tests/test_label_quality_assurance.py
=====================================
Unit and integration tests for Cleanlab-inspired Label Quality Assurance:
1. Aspect ratio outlier detection.
2. Bounding box area anomaly detection.
3. Duplicate/overlapping annotation collision detection.
4. Confident learning prediction discrepancy / label flipping detection.
5. FastAPI endpoint integration for label quality analysis.
"""
import pytest
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
    db_path = tmp_path / "test_label_assurance.sqlite3"
    return CryptoEvidenceLedger(db_path=db_path, use_sqlite_fallback=True)


@pytest.fixture
def engine(clean_ledger):
    return DataIntegrityAssurance(ledger=clean_ledger)


def test_aspect_ratio_outlier_detection(engine):
    """Verifies detection of extreme aspect ratio bounding boxes."""
    # Ultra-skinny needle box (aspect ratio 20:1)
    annotations = [
        {"class_id": 0, "bbox": [0.5, 0.5, 0.01, 0.20]}
    ]
    findings = engine.check_label_quality("img_aspect", annotations)
    assert len(findings) == 1
    assert findings[0].status == "SUSPICIOUS_ASPECT_RATIO"
    assert findings[0].score >= 20.0
    assert engine.recommend_governance_disposition(findings[0]) == "REVIEW"


def test_bbox_area_anomaly_detection(engine):
    """Verifies detection of tiny noise boxes or full-canvas bounding boxes."""
    annotations = [
        {"class_id": 0, "bbox": [0.5, 0.5, 0.005, 0.005]},  # area = 0.000025 < 0.0001
        {"class_id": 1, "bbox": [0.5, 0.5, 0.99, 0.99]}     # area = 0.9801 > 0.98
    ]
    findings = engine.check_label_quality("img_area", annotations)
    area_findings = [f for f in findings if f.status == "SUSPICIOUS_BBOX_AREA"]
    assert len(area_findings) == 2


def test_duplicate_annotation_collision(engine):
    """Verifies detection of overlapping/duplicate bounding box annotations."""
    annotations = [
        {"class_id": 0, "bbox": [0.4, 0.4, 0.2, 0.3]},
        {"class_id": 0, "bbox": [0.405, 0.402, 0.198, 0.299]}  # > 90% IoU duplicate
    ]
    findings = engine.check_label_quality("img_dup", annotations)
    collision_findings = [f for f in findings if f.status == "DUPLICATE_ANNOTATION_COLLISION"]
    assert len(collision_findings) == 1
    assert collision_findings[0].score > 0.85


def test_confident_learning_label_flipping(engine):
    """
    Verifies detection of label noise where a high-confidence model prediction
    conflicts with the annotated class (e.g. annotated as person, but model detects car with 95% conf).
    """
    annotations = [
        {"class_id": 0, "bbox": [0.5, 0.5, 0.3, 0.3]}  # Annotated as Class 0 (person)
    ]
    predictions = [
        {"class_id": 2, "confidence": 0.94, "bbox": [0.505, 0.502, 0.295, 0.301]}  # Model says Class 2 (car) @ 94%
    ]
    findings = engine.check_label_quality("img_flip", annotations, predictions=predictions)
    flip_findings = [f for f in findings if f.status == "LABEL_NOISE_CLASS_FLIP_SUSPECTED"]
    assert len(flip_findings) == 1
    assert flip_findings[0].score == 0.94
    assert "Suspected label flip error" in flip_findings[0].evidence


def test_clean_annotations_no_findings(engine):
    """Verifies that well-formed, non-colliding annotations produce zero anomalies."""
    annotations = [
        {"class_id": 0, "bbox": [0.2, 0.3, 0.1, 0.2]},
        {"class_id": 1, "bbox": [0.7, 0.6, 0.2, 0.2]}
    ]
    predictions = [
        {"class_id": 0, "confidence": 0.88, "bbox": [0.2, 0.3, 0.1, 0.2]},
        {"class_id": 1, "confidence": 0.92, "bbox": [0.7, 0.6, 0.2, 0.2]}
    ]
    findings = engine.check_label_quality("img_clean", annotations, predictions=predictions)
    assert len(findings) == 0


def test_api_label_quality_endpoint(engine, monkeypatch):
    """Verifies the REST API endpoint for label quality assessment."""
    from apps.backend.routers import assurance as assurance_module
    from apps.backend.auth.jwt_auth import require_permission
    from apps.backend.auth.rbac import Permission

    monkeypatch.setattr(assurance_module, "get_ledger", lambda: engine.ledger)
    app.dependency_overrides[require_permission(Permission.VIEW_EVIDENCE)] = lambda: {"sub": "analyst_1", "role": "ADMIN"}

    try:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/assurance/labels/quality",
            json={
                "asset_id": "test_img_api",
                "annotations": [
                    {"class_id": 0, "bbox": [0.5, 0.5, 0.005, 0.20]}  # 40:1 aspect ratio!
                ]
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ANOMALIES_DETECTED"
        assert data["total_findings"] >= 1
    finally:
        app.dependency_overrides.clear()
