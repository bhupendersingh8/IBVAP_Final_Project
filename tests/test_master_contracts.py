"""
Tests for Canonical VerifiedEvent, EventGate, and Class Taxonomy Contracts (SIH26187 & SIH26228)
"""

import os
import yaml
import pytest
from datetime import datetime, timezone
from pathlib import Path

from services.evidence.verified_event import VerifiedEvent, BoundingBox, SpecialistEvidence
from services.orchestrator.event_gate import EventGate, SpecialistType, GatePriority


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_class_taxonomy_yaml_integrity():
    """Verifies that configs/class_taxonomy.yaml exists, loads, and defines required border categories."""
    tax_path = PROJECT_ROOT / "configs" / "class_taxonomy.yaml"
    assert tax_path.exists(), "configs/class_taxonomy.yaml missing!"
    
    with open(tax_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    assert "categories" in data
    cats = data["categories"]
    required_keys = ["PERSON", "CAR", "TWO_WHEELER", "TRUCK", "ARMED_THREAT_WEAPON", "EXPLOSIVE_HAZARD"]
    for k in required_keys:
        assert k in cats, f"Missing required category: {k}"
        assert "canonical_class" in cats[k]
        assert "confidence_threshold" in cats[k]
        assert "severity" in cats[k]


def test_verified_event_canonical_digest():
    """Verifies that VerifiedEvent schema instantiates cleanly and computes deterministic SHA-256."""
    event = VerifiedEvent(
        event_id="evt-test-101",
        camera_id="CAM-01",
        timestamp=datetime.now(timezone.utc).isoformat(),
        sequence_id=42,
        track_ids=[101],
        object_classifications=["tactical_personnel"],
        bounding_boxes=[BoundingBox(x1=0.1, y1=0.2, x2=0.3, y2=0.8)],
        confidence=0.94,
        zone_id="RESTRICTED_PERIMETER_01",
        event_type="PERIMETER_INTRUSION",
        severity="HIGH",
        explanation="Personnel detected within restricted border corridor for > 3.2s",
        input_hash="a" * 64,
        model_hashes={"primary_detector": "b" * 64},
        previous_provenance_hash="c" * 64,
        current_provenance_hash="d" * 64,
        governance_decision="ACCEPT",
        assurance_status="VERIFIED"
    )

    digest = event.compute_canonical_digest()
    assert len(digest) == 64
    assert isinstance(digest, str)
    # Determinism
    assert event.compute_canonical_digest() == digest


def test_event_gate_selective_specialists():
    """Verifies that EventGate selectively triggers specialists according to track type and conditions."""
    gate = EventGate()

    class MockTrack:
        def __init__(self, track_id, class_name, subclass=None, conf=0.85, bbox=None, age_frames=10):
            self.track_id = track_id
            self.class_name = class_name
            self.subclass = subclass
            self.avg_confidence = conf
            self.age_frames = age_frames
            class MockBBox:
                def __init__(self, b):
                    self.x1, self.y1, self.x2, self.y2 = b
            self.bbox = MockBBox(bbox or [0.1, 0.1, 0.5, 0.9])

    # 1. Vehicle Track -> ANPR scheduled
    vehicle_track = MockTrack(1, "vehicle", "car", age_frames=5)
    res_veh = gate.evaluate(frame_id=1, tracks=[vehicle_track])
    assert any(t.specialist_type == SpecialistType.ANPR_OCR for t in res_veh.scheduled_tasks)

    # 2. Person Track in Restricted Zone -> Pose and Face scheduled
    person_track = MockTrack(2, "person", age_frames=20)
    res_per = gate.evaluate(frame_id=30, tracks=[person_track], in_restricted_zone=True, is_gpu=False)
    types = [t.specialist_type for t in res_per.scheduled_tasks]
    assert SpecialistType.FACE_AUTHORIZATION in types
    assert SpecialistType.POSE_ESTIMATION in types

    # 3. Camouflaged / Crawling Silhouette -> MobileSAM scheduled
    crawling_person = MockTrack(3, "person", conf=0.45, bbox=[0.1, 0.1, 0.6, 0.25]) # Low aspect ratio
    res_sam = gate.evaluate(frame_id=4, tracks=[crawling_person])
    assert any(t.specialist_type == SpecialistType.MOBILE_SAM for t in res_sam.scheduled_tasks)


def test_evidence_package_exporter(tmp_path):
    """Verifies that EvidencePackageExporter generates a complete 9-artifact zip package."""
    from services.evidence.evidence_package_exporter import EvidencePackageExporter
    import zipfile

    exporter = EvidencePackageExporter(export_dir=tmp_path)
    event = VerifiedEvent(
        event_id="evt-export-test-01",
        camera_id="CAM-01",
        timestamp=datetime.now(timezone.utc).isoformat(),
        sequence_id=1,
        track_ids=[42],
        object_classifications=["recon_vehicle"],
        bounding_boxes=[BoundingBox(x1=0.2, y1=0.3, x2=0.5, y2=0.7)],
        confidence=0.92,
        zone_id="RESTRICTED_GATE_01",
        event_type="UNAUTHORIZED_VEHICLE_APPROACH",
        severity="HIGH",
        explanation="Vehicle breached buffer zone without clearance",
        input_hash="e" * 64,
        model_hashes={"primary_detector": "f" * 64},
        previous_provenance_hash="0" * 64,
        current_provenance_hash="1" * 64,
        governance_decision="ACCEPT",
        assurance_status="VERIFIED"
    )

    fake_frame = b"\xff\xd8\xff\xe0" + b"\x00" * 512 # JPEG signature
    zip_result = exporter.export_package(event=event, frame_bytes=fake_frame)

    assert zip_result.exists()
    assert zip_result.suffix == ".zip"

    # Verify all 9 artifacts inside the package
    with zipfile.ZipFile(zip_result, "r") as zf:
        namelist = zf.namelist()
        expected = [
            "event.json",
            "metadata/camera_metadata.json",
            "provenance.json",
            "model_manifest/manifest.json",
            "aibom/cyclonedx_aibom.json",
            "ledger_record.json",
            "verification.json",
            "certificate.json",
            "frame/committed_frame.jpg"
        ]
        for item in expected:
            assert item in namelist, f"Missing {item} in exported package!"


def test_export_evidence_package_api_endpoint():
    """Verifies POST /api/v1/evidence/packages/export/{event_id} returns valid application/zip."""
    from fastapi.testclient import TestClient
    from apps.backend.main import app

    client = TestClient(app)
    # Login as admin to obtain JWT
    login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpassword123"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/evidence/packages/export/evt-api-test-99", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert len(res.content) > 100


