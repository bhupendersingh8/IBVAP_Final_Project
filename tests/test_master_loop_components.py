"""
Tests for Master Loop Components:
- Hardware Capability Detection & Profile Assignment
- Canonical Object Ontology Mapping
- Hardware Profile Configuration Validity
- Build Receipt Integrity
"""

import os
import yaml
import json
import pytest
from pathlib import Path

from services.hardware import hardware_detector, HardwareProfileName
from services.ontology import CanonicalObjectType, ontology_manager

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_hardware_detector_dell_cpu():
    """Verify hardware detector correctly recognizes the host environment."""
    profile = hardware_detector.resolve_profile()
    assert profile.profile_name in {
        HardwareProfileName.DELL_CPU,
        HardwareProfileName.LOW_VRAM_4GB,
        HardwareProfileName.LOW_VRAM_6GB,
        HardwareProfileName.STANDARD_8GB,
        HardwareProfileName.RTX3050_4GB,
        HardwareProfileName.RTX3050_6GB,
        HardwareProfileName.HIGH_VRAM_NVIDIA,
    }
    assert profile.cpu.logical_cores >= 2
    assert profile.ram_budget_mb > 0
    assert any(m in profile.primary_detection_model for m in ["yolo", "detr"])


def test_hardware_detector_explicit_override():
    """Verify hardware profile override works deterministically."""
    from services.hardware import HardwareDetector
    hd_4gb = HardwareDetector(override_profile="RTX3050_4GB")
    p_4gb = hd_4gb.resolve_profile()
    assert p_4gb.profile_name == HardwareProfileName.RTX3050_4GB
    assert p_4gb.vram_budget_mb == 3200.0
    assert p_4gb.max_streams_recommended == 2

    hd_6gb = HardwareDetector(override_profile="RTX3050_6GB")
    p_6gb = hd_6gb.resolve_profile()
    assert p_6gb.profile_name == HardwareProfileName.RTX3050_6GB
    assert p_6gb.vram_budget_mb == 5000.0
    assert p_6gb.max_streams_recommended == 4


def test_canonical_object_ontology_mapping():
    """Verify detector class IDs map deterministically to CanonicalObjectType."""
    # COCO ID tests
    assert ontology_manager.from_coco_id(0) == CanonicalObjectType.PERSON
    assert ontology_manager.from_coco_id(2) == CanonicalObjectType.CAR
    assert ontology_manager.from_coco_id(3) == CanonicalObjectType.MOTORCYCLE
    assert ontology_manager.from_coco_id(5) == CanonicalObjectType.BUS
    assert ontology_manager.from_coco_id(7) == CanonicalObjectType.TRUCK
    assert ontology_manager.from_coco_id(1) == CanonicalObjectType.BICYCLE
    assert ontology_manager.from_coco_id(999) == CanonicalObjectType.UNKNOWN

    # String normalization tests
    assert ontology_manager.from_name("person") == CanonicalObjectType.PERSON
    assert ontology_manager.from_name("automobile") == CanonicalObjectType.CAR
    assert ontology_manager.from_name("lorry") == CanonicalObjectType.TRUCK
    assert ontology_manager.from_name("scooter") == CanonicalObjectType.MOTORCYCLE
    assert ontology_manager.from_name("random_junk") == CanonicalObjectType.UNKNOWN

    # Property tests
    assert CanonicalObjectType.PERSON.is_person is True
    assert CanonicalObjectType.CAR.is_vehicle is True
    assert CanonicalObjectType.TRUCK.requires_anpr is True
    assert CanonicalObjectType.PERSON.requires_anpr is False


def test_hardware_profile_yaml_configs():
    """Verify hardware YAML configs are syntactically valid and contain mandatory budgets."""
    cpu_yaml = PROJECT_ROOT / "configs" / "hardware" / "cpu.yaml"
    rtx_4gb = PROJECT_ROOT / "configs" / "hardware" / "rtx3050_4gb.yaml"
    rtx_6gb = PROJECT_ROOT / "configs" / "hardware" / "rtx3050_6gb.yaml"

    for ypath in [cpu_yaml, rtx_4gb, rtx_6gb]:
        assert ypath.exists(), f"Missing config: {ypath}"
        with open(ypath, "r") as f:
            cfg = yaml.safe_load(f)
            assert "profile_name" in cfg
            assert "compute" in cfg
            assert "models" in cfg
            assert "preprocessing" in cfg


def test_build_receipt_integrity():
    """Verify TensorRT build receipts exist and record honest non-fabricated statuses."""
    r_4gb = PROJECT_ROOT / "artifacts" / "rtx3050_4gb" / "build_receipt.json"
    r_6gb = PROJECT_ROOT / "artifacts" / "rtx3050_6gb" / "build_receipt.json"

    for rpath in [r_4gb, r_6gb]:
        assert rpath.exists(), f"Missing receipt: {rpath}"
        with open(rpath, "r") as f:
            data = json.load(f)
            assert "status" in data
            assert data["status"] in {"PROFILE_READY_NOT_PHYSICALLY_VERIFIED", "REAL_RUNTIME_VERIFIED"}
