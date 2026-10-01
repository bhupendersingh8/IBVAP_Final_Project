"""
Test Suite: Dataset Provenance & Open-Data Compliance (SIH26228)
================================================================
Verifies compliance with the strict SIH26228 requirement:
"All development and evaluation data will be publicly available under applicable
 licences or synthetically generated. No classified, operational or service-generated
 data will be used."
"""

import os
import json
import tempfile
import pytest
from pathlib import Path

from services.assurance.dataset_hashing import (
    compute_file_sha256,
    compute_directory_manifest,
    DatasetComplianceAuditor,
    DatasetAuditReport,
)
from services.assurance.synthetic_eval import evaluate_synthetic_case


@pytest.fixture
def manifest_path():
    root = Path(__file__).resolve().parents[1]
    return root / "configs" / "dataset_manifest.json"


@pytest.fixture
def synthetic_dir():
    root = Path(__file__).resolve().parents[1]
    return root / "data" / "synthetic_eval"


def test_open_data_strict_compliance(manifest_path):
    """
    SIH26228 Mandate Verification:
    Verify that 100% of registered datasets strictly adhere to open/synthetic rules:
    - is_classified must be False
    - is_operational must be False
    - is_service_generated must be False
    """
    assert manifest_path.is_file(), f"Manifest missing at {manifest_path}"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "compliance_statement" in data
    assert "No classified, operational or service-generated data will be used" in data["compliance_statement"]

    datasets = data.get("datasets", [])
    assert len(datasets) > 0, "No datasets declared in manifest"

    for ds in datasets:
        ds_id = ds["dataset_id"]
        assert ds.get("is_classified") is False, f"Violation: {ds_id} marked as classified!"
        assert ds.get("is_operational") is False, f"Violation: {ds_id} marked as operational data!"
        assert ds.get("is_service_generated") is False, f"Violation: {ds_id} marked as service generated!"
        lic = ds.get("license") or ds.get("license_type")
        assert lic, f"Dataset {ds_id} missing license specification"
        purpose = ds.get("intended_use") or ds.get("purpose")
        assert purpose, f"Dataset {ds_id} missing intended_use/purpose"



def test_deterministic_file_and_directory_hashing():
    """
    Verifies that compute_file_sha256 and compute_directory_manifest produce
    deterministic and reproducible outputs across different OS environments.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create deterministic test files
        (tmp_path / "b_file.txt").write_bytes(b"hello world\n")
        (tmp_path / "a_file.txt").write_bytes(b"foo bar baz\n")
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "c_file.txt").write_bytes(b"sample bytes\n")

        manifest1 = compute_directory_manifest(tmp_path)
        manifest2 = compute_directory_manifest(tmp_path)

        assert manifest1.manifest_sha256 == manifest2.manifest_sha256
        assert manifest1.merkle_root == manifest2.merkle_root
        assert manifest1.total_files == 3

        # Ordering must be deterministic: a_file.txt before b_file.txt
        rel_paths = [f.relative_path for f in manifest1.files]
        assert rel_paths == sorted(rel_paths)


def test_synthetic_evaluation_suite_provenance(synthetic_dir):
    """
    Verifies that the synthetic evaluation suite exists, has valid provenance,
    and all 7 required attack/evaluation cases are present.
    """
    assert synthetic_dir.is_dir(), f"Synthetic eval dir missing at {synthetic_dir}"
    prov_file = synthetic_dir / "synthetic_provenance.json"
    assert prov_file.is_file(), "synthetic_provenance.json missing"

    with open(prov_file, "r", encoding="utf-8") as f:
        prov = json.load(f)

    assert prov.get("is_classified") is False
    assert prov.get("is_operational") is False
    assert prov.get("is_synthetic") is True
    assert prov.get("total_cases") >= 7

    case_ids = {c["case_id"] for c in prov["cases"]}
    expected_cases = {
        "case_01_label_flip",
        "case_02_bbox_tamper",
        "case_03_ood_sample",
        "case_04_badnets_trigger",
        "case_05_low_light_shift",
        "case_06_fog_haze_shift",
        "case_07_replay_attack",
    }
    assert expected_cases.issubset(case_ids), f"Missing cases: {expected_cases - case_ids}"


def test_dataset_compliance_auditor_full_run():
    """
    Executes the DatasetComplianceAuditor and validates report integrity.
    """
    auditor = DatasetComplianceAuditor()
    report: DatasetAuditReport = auditor.run_audit()

    assert report.overall_compliant is True
    assert report.non_compliant_count == 0
    assert report.total_datasets >= 7
    assert report.open_data_compliant_count == report.total_datasets

    # Verify synthetic dataset has verified hash
    synthetic_entry = next((e for e in report.entries if e.dataset_id == "synthetic-border-eval-v1"), None)
    assert synthetic_entry is not None
    assert synthetic_entry.hash_verified is True
    assert synthetic_entry.status == "SYNTHETIC_GENERATED"

    # Verify external references are honest
    coco_entry = next((e for e in report.entries if e.dataset_id == "coco-2017-val"), None)
    assert coco_entry is not None
    assert coco_entry.status == "REGISTERED_BUT_NOT_EXECUTED"
    assert "Public reference registered" in coco_entry.message


def test_synthetic_case_defense_evaluations(synthetic_dir):
    """
    Executes automated defense evaluations across synthetic attack cases:
    - Bounding box tampering must trigger QUARANTINE
    - BadNets trigger must trigger QUARANTINE
    - Label flip must trigger QUARANTINE
    - OOD sample must trigger REVIEW
    """
    res_bbox = evaluate_synthetic_case("case_02_bbox_tamper", synthetic_dir)
    assert res_bbox.status == "PASSED_DEFENSE_TRIGGERED"
    assert res_bbox.governance_decision == "QUARANTINE"

    res_badnets = evaluate_synthetic_case("case_04_badnets_trigger", synthetic_dir)
    assert res_badnets.status == "PASSED_DEFENSE_TRIGGERED"
    assert res_badnets.governance_decision == "QUARANTINE"

    res_label = evaluate_synthetic_case("case_01_label_flip", synthetic_dir)
    assert res_label.status == "PASSED_DEFENSE_TRIGGERED"
    assert res_label.governance_decision == "QUARANTINE"

    res_ood = evaluate_synthetic_case("case_03_ood_sample", synthetic_dir)
    assert res_ood.status == "PASSED_DEFENSE_TRIGGERED"
    assert res_ood.governance_decision == "REVIEW"
