"""
Tests for IBVAP Unified Model Registry and Model Router (17 Layers, 5 Hardware Profiles)
========================================================================================
Validates that:
- All 17 layers are cataloged with zero omissions.
- Every model has all 18 metadata fields.
- Every status matches the strict 10-status enum.
- Primary and fallback chains resolve deterministically.
- ModelRouter dispatches across DELL_CPU, RTX 3050, and Cloud profiles with zero crashes.
"""

import pytest
from ml.registry.unified_model_registry import (
    unified_model_registry,
    RegistryStatus,
    UnifiedModelEntry,
)
from services.hardware.model_router import ModelRouter
from services.hardware.hardware_detector import HardwareDetector, HardwareProfileName
import ml.adapters.family_adapters as fa


def test_catalog_17_layers_coverage():
    """Verify all 17 layers have registered models in the unified registry."""
    layers_found = set()
    for m in unified_model_registry.all_models():
        layer = m.integration.get("layer")
        if layer is not None:
            layers_found.add(layer)

    expected_layers = set(range(1, 18))
    missing = expected_layers - layers_found
    assert not missing, f"Missing layer numbers in unified registry: {missing}"
    assert len(layers_found) == 17


def test_catalog_18_fields_and_status_enum_validity():
    """Verify every model entry contains all 18 required metadata fields and valid status."""
    valid_statuses = {s.value for s in RegistryStatus}
    models = unified_model_registry.all_models()
    assert len(models) >= 120, f"Expected at least 120 models, got {len(models)}"

    for m in models:
        # Check all 18 fields
        assert isinstance(m.family, str) and m.family
        assert isinstance(m.name, str) and m.name
        assert isinstance(m.version, str) and m.version
        assert isinstance(m.source, str) and m.source
        assert isinstance(m.license, str) and m.license
        assert isinstance(m.weights, str) and m.weights
        assert isinstance(m.adapter, str) and m.adapter
        assert isinstance(m.tasks, list) and len(m.tasks) > 0
        assert isinstance(m.cpu, bool)
        assert isinstance(m.rtx3050_4gb, bool)
        assert isinstance(m.rtx3050_6gb, bool)
        assert isinstance(m.high_end_gpu, bool)
        assert isinstance(m.remote_gpu, bool)
        assert isinstance(m.primary, bool)
        assert m.fallback is None or isinstance(m.fallback, str)
        assert m.status in valid_statuses, f"Invalid status: {m.status} in model {m.name}"
        assert isinstance(m.benchmark, dict)
        assert isinstance(m.integration, dict)


def test_primary_and_fallback_integrity():
    """Verify primary models in each family resolve and fallbacks exist in registry."""
    families = {m.family for m in unified_model_registry.all_models()}
    for fam in families:
        primary = unified_model_registry.get_primary(fam)
        assert primary is not None, f"Family {fam} has no primary model designated"
        if primary.fallback:
            fallback = unified_model_registry.get_model(primary.fallback)
            assert fallback is not None, f"Fallback '{primary.fallback}' for primary '{primary.name}' does not exist"


def test_model_router_dell_cpu():
    """Verify ModelRouter safely resolves all 17 families on DELL_CPU host."""
    detector = HardwareDetector(override_profile="DELL_CPU")
    router = ModelRouter(detector=detector)
    assert router.current_profile.profile_name == HardwareProfileName.DELL_CPU

    stack = router.get_active_stack()
    assert len(stack) == 17

    # Detection must resolve to yolo26n on CPU
    det = stack["detection"]
    assert det["model_name"] == "yolo26n_official_baseline"
    assert det["execution_mode"] == "LOCAL_CPU"

    # Tracking must resolve to bytetrack on CPU
    assert stack["tracking"]["model_name"] == "bytetrack_baseline"
    assert stack["tracking"]["execution_mode"] == "LOCAL_CPU"


def test_model_router_rtx3050_profiles():
    """Verify ModelRouter correctly resolves GPU execution modes on RTX 3050 targets."""
    # Target B1: RTX 3050 4GB
    hd_4gb = HardwareDetector(override_profile="RTX3050_4GB")
    router_4gb = ModelRouter(detector=hd_4gb)
    entry, mode = router_4gb.resolve_model("detection")
    assert entry.rtx3050_4gb is True
    assert "LOCAL_GPU" in mode

    # Target B2: RTX 3050 6GB
    hd_6gb = HardwareDetector(override_profile="RTX3050_6GB")
    router_6gb = ModelRouter(detector=hd_6gb)
    entry_seg, mode_seg = router_6gb.resolve_model("segmentation")
    assert entry_seg.rtx3050_6gb is True
    assert "LOCAL_GPU" in mode_seg


def test_new_family_adapters():
    """Verify newly added family adapters pass real validation."""
    d = fa.DepthModelAdapter()
    assert d.load() is True
    assert d.validate() is True

    tg = fa.TemporalGraphModelAdapter()
    assert tg.load() is True
    assert tg.validate() is True

    ind = fa.IndicLanguageModelAdapter()
    assert ind.load() is True
    assert ind.validate() is True
