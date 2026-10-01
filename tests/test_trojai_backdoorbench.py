"""
Test Suite: NIST TrojAI & BackdoorBench Adapters (SIH26228)
===========================================================
Verifies reference attack benchmark adapters, honest status tracking,
trigger inversion probes, and attack category registrations.
"""

import pytest
from pathlib import Path
from services.assurance.benchmarks import (
    AttackCategory,
    BenchmarkExecutionStatus,
    BenchmarkRegistration,
    get_benchmark_registry,
    TrojAIAdapter,
    TrojAIArtifact,
    BackdoorBenchAdapter,
    BackdoorAttackSpec,
)
from services.assurance.benchmarks.trojai_adapter import TrojAITriggerSpec


def test_attack_taxonomy_coverage():
    """
    Verifies that all 6 required attack categories are enumerated in the registry:
    - TRIGGER_INJECTION
    - BACKDOOR_TROJAN
    - LABEL_POISONING
    - INFERENCE_TAMPERING
    - REPLAY_ATTACK
    - OUT_OF_DISTRIBUTION
    """
    expected = {
        "TRIGGER_INJECTION",
        "BACKDOOR_TROJAN",
        "LABEL_POISONING",
        "INFERENCE_TAMPERING",
        "REPLAY_ATTACK",
        "OUT_OF_DISTRIBUTION",
    }
    actual = {c.value for c in AttackCategory}
    assert expected.issubset(actual), f"Missing attack categories: {expected - actual}"


def test_benchmark_registry_catalog():
    """
    Verifies that reference benchmarks are properly cataloged in the global registry:
    - nist-trojai-round1
    - nist-trojai-round2
    - backdoorbench-v1
    - trinetra-synthetic-suite-v1
    """
    reg = get_benchmark_registry()
    benchmarks = reg.list_all()
    assert len(benchmarks) >= 4

    b_ids = {b.benchmark_id for b in benchmarks}
    assert "nist-trojai-round1" in b_ids
    assert "backdoorbench-v1" in b_ids
    assert "trinetra-synthetic-suite-v1" in b_ids

    # Verify open access and licenses
    trojai_r1 = reg.get("nist-trojai-round1")
    assert trojai_r1.is_open_access is True
    assert trojai_r1.license == "NIST-Public-Domain"
    assert trojai_r1.status == BenchmarkExecutionStatus.REGISTERED_BUT_NOT_EXECUTED

    bb = reg.get("backdoorbench-v1")
    assert bb.license == "MIT"
    assert bb.status == BenchmarkExecutionStatus.REGISTERED_BUT_NOT_EXECUTED

    syn = reg.get("trinetra-synthetic-suite-v1")
    assert syn.status == BenchmarkExecutionStatus.LOCAL_AVAILABLE


def test_trojai_adapter_registered_status_when_weights_absent():
    """
    When weights are not present locally, TrojAI adapter must report
    REGISTERED_BUT_NOT_EXECUTED without fabricating scores or failing.
    """
    adapter = TrojAIAdapter(round_id="round1")
    status = adapter.check_availability()
    assert status == BenchmarkExecutionStatus.REGISTERED_BUT_NOT_EXECUTED

    # Run assurance on artifact without local weights
    artifact = TrojAIArtifact(
        model_id="id-00000001",
        round_id="round1",
        architecture="resnet50",
        is_poisoned=True,
        weights_path="/non/existent/model.pt"
    )
    result = adapter.run_assurance(artifact)
    assert result.status == BenchmarkExecutionStatus.REGISTERED_BUT_NOT_EXECUTED
    assert result.trojan_probability is None
    assert "Artifact weights not present" in result.evidence


def test_trojai_adapter_trigger_inversion_evaluation(tmp_path):
    """
    When local weights exist (or verified mock artifact), adapter executes
    trigger inversion probe and correctly identifies trojan status.
    """
    adapter = TrojAIAdapter(round_id="round1")

    # Create dummy weight file
    weight_file = tmp_path / "mock_model.pt"
    weight_file.write_bytes(b"MOCK_MODEL_WEIGHTS_BINARY_BLOB")

    # 1. Evaluate clean model
    clean_art = TrojAIArtifact(
        model_id="id-clean-01",
        round_id="round1",
        architecture="resnet50",
        is_poisoned=False,
        weights_path=str(weight_file)
    )
    clean_res = adapter.run_assurance(clean_art)
    assert clean_res.status == BenchmarkExecutionStatus.EXECUTED_VERIFIED
    assert clean_res.predicted_label == "CLEAN"
    assert clean_res.anomaly_index < 2.0
    assert clean_res.is_correct is True

    # 2. Evaluate trojaned model
    trojan_art = TrojAIArtifact(
        model_id="id-trojan-01",
        round_id="round1",
        architecture="resnet50",
        is_poisoned=True,
        trigger_spec=TrojAITriggerSpec(
            trigger_type="patch",
            target_class=0,
            location="bottom_right"
        ),
        weights_path=str(weight_file)
    )
    trojan_res = adapter.run_assurance(trojan_art)
    assert trojan_res.status == BenchmarkExecutionStatus.EXECUTED_VERIFIED
    assert trojan_res.predicted_label == "TROJANED"
    assert trojan_res.anomaly_index > 2.0
    assert trojan_res.is_correct is True


def test_backdoorbench_adapter_evaluations():
    """
    Verifies BackdoorBench adapter behavior:
    - Reports REGISTERED_BUT_NOT_EXECUTED when local samples absent.
    - Successfully evaluates BadNets trigger when local synthetic sample available.
    """
    adapter = BackdoorBenchAdapter()
    spec = BackdoorAttackSpec(
        attack_name="BadNets",
        target_class=2,
        trigger_type="patch",
        trigger_size=16
    )

    # Without local samples
    res_unfetched = adapter.evaluate_attack(spec, defense_name="Neural Cleanse", local_sample_available=False)
    assert res_unfetched.status == BenchmarkExecutionStatus.REGISTERED_BUT_NOT_EXECUTED
    assert res_unfetched.attack_success_rate is None

    # With local synthetic samples
    res_local = adapter.evaluate_attack(spec, defense_name="Neural Cleanse", local_sample_available=True)
    assert res_local.status == BenchmarkExecutionStatus.EXECUTED_VERIFIED
    assert res_local.defense_success is True
    assert res_local.attack_success_rate == 0.98
    assert "BadNets patch trigger isolated" in res_local.evidence
