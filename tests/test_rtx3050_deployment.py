"""
Unit & Integration Tests for RTX 3050 Deployment & Compatibility Suite
SIH Problem Statement: 26187 | Intelligent Border Video Analytics Platform
"""

import os
from pathlib import Path
import pytest
from services.hardware.hardware_detector import HardwareDetector, HardwareProfileName
from deployment.rtx3050.test_rtx3050_compatibility import RTX3050CompatibilityAuditor


def test_rtx3050_deployment_bundle_files_exist():
    """Verifies that all required scripts, manifests, and guides are present."""
    base_dir = Path(__file__).resolve().parent.parent
    expected_files = [
        base_dir / "deployment" / "rtx3050" / "OFFLINE_WHEELS_MANIFEST.txt",
        base_dir / "deployment" / "rtx3050" / "download_rtx3050_wheels.ps1",
        base_dir / "deployment" / "rtx3050" / "setup_rtx3050_env.ps1",
        base_dir / "deployment" / "rtx3050" / "export_tensorrt_engines.py",
        base_dir / "deployment" / "rtx3050" / "test_rtx3050_compatibility.py",
        base_dir / "deployment" / "rtx3050" / "README_AIRGAPPED_DEPLOYMENT.md",
        base_dir / "start_ibvap_rtx3050.ps1",
        base_dir / "start_ibvap_rtx3050.bat",
    ]
    for p in expected_files:
        assert p.exists(), f"Required deployment file missing: {p}"


def test_hardware_detector_profile_resolution():
    """Ensures hardware detector resolves a valid hardware profile without exception."""
    detector = HardwareDetector()
    profile = detector.resolve_profile()
    assert profile is not None
    assert profile.profile_name in [
        HardwareProfileName.DELL_CPU,
        HardwareProfileName.RTX3050_4GB,
        HardwareProfileName.RTX3050_6GB,
        HardwareProfileName.HIGH_VRAM_NVIDIA,
        HardwareProfileName.REMOTE_GPU,
        HardwareProfileName.STANDARD_8GB,
        HardwareProfileName.LOW_VRAM_4GB,
        HardwareProfileName.LOW_VRAM_6GB,
    ]
    assert profile.max_streams_recommended >= 1
    assert profile.ram_budget_mb > 0


def test_rtx3050_compatibility_auditor_runs_cleanly():
    """Runs all 4 audit checks and verifies zero-crash completion."""
    auditor = RTX3050CompatibilityAuditor()
    success = auditor.run_all_checks()
    assert success is True, "RTX 3050 compatibility audit failed"
    assert len(auditor.results) == 4
    for r in auditor.results:
        assert r.passed is True, f"Check failed: {r.test_name} with error: {r.error}"
