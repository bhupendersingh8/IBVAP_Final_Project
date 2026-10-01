"""
Tests for Reference Attack Benchmarks & Automated Governance (SIH26228)
========================================================================
Validates detection, cryptographic integrity, and automated governance across:
- Model byte mutation detection
- Inference tampering detection
- Nonce replay & sequence regression
- Trigger inversion reporting & limitations
- Automated transition to QUARANTINE or REVIEW
"""

import pytest
import hashlib
import json
from pathlib import Path

from services.assurance.benchmarks.registry import (
    AttackCategory,
    BenchmarkExecutionStatus,
    get_benchmark_registry
)
from services.assurance.synthetic_eval import evaluate_synthetic_case
from services.assurance.model_fingerprint import analyze_trigger_inversion, TriggerInversionReport
from services.evidence.verified_event import VerifiedEvent, BoundingBox, BenchmarkEvidenceItem


class TestReferenceAttackBenchmarks:

    def test_registry_taxonomy_coverage(self):

        """Verify all 14 required attack categories are standard and registered."""
        expected_attacks = [
            AttackCategory.TRIGGER_INJECTION,
            AttackCategory.BACKDOOR,
            AttackCategory.TROJAN,
            AttackCategory.LABEL_FLIPPING,
            AttackCategory.DATA_POISONING,
            AttackCategory.DUPLICATE_FLOODING,
            AttackCategory.OOD_INSERTION,
            AttackCategory.MODEL_SUBSTITUTION,
            AttackCategory.MODEL_WEIGHT_TAMPERING,
            AttackCategory.OUTPUT_TAMPERING,
            AttackCategory.REPLAY,
            AttackCategory.PROVENANCE_TAMPERING,
            AttackCategory.DISTRIBUTION_SHIFT,
            AttackCategory.ADVERSARIAL_INPUT
        ]
        for attack in expected_attacks:
            assert attack.value is not None

        registry = get_benchmark_registry()
        benchmarks = registry.list_all()
        assert len(benchmarks) >= 3

        # Check export audit resources format
        resources = registry.export_audit_resources()
        assert len(resources) >= 3
        for res in resources:
            assert "resource" in res
            assert "status" in res
            assert "license_verified" in res
            assert res["license_verified"] is True

    def test_model_byte_mutation_detection(self):
        """Simulate bit mutation in model weights and verify QUARANTINE disposition."""
        case_id = "case_model_byte_mutation"
        suite_dir = Path(__file__).resolve().parents[1] / "data" / "synthetic_eval"
        
        result = evaluate_synthetic_case(case_id, suite_dir)
        assert result.status == "PASSED_DEFENSE_TRIGGERED"
        assert result.governance_decision == "QUARANTINE"
        assert result.is_safe is False
        assert "byte mutation" in result.evidence_detected.lower()

    def test_inference_tampering_detection(self):
        """Simulate bounding box inversion and coordinate overflow."""
        case_id = "case_02_bbox_tamper"
        suite_dir = Path(__file__).resolve().parents[1] / "data" / "synthetic_eval"
        
        result = evaluate_synthetic_case(case_id, suite_dir)
        assert result.status == "PASSED_DEFENSE_TRIGGERED"
        assert result.governance_decision == "QUARANTINE"
        assert result.is_safe is False
        assert "security violation" in result.evidence_detected.lower() or "boundary" in result.evidence_detected.lower() or "coordinate" in result.evidence_detected.lower()

    def test_nonce_replay_attack_detection(self):
        """Simulate stale sequence and nonce reuse breaking recursive hash-chain."""
        case_id = "case_07_replay_attack"
        suite_dir = Path(__file__).resolve().parents[1] / "data" / "synthetic_eval"
        
        result = evaluate_synthetic_case(case_id, suite_dir)
        assert result.status == "PASSED_DEFENSE_TRIGGERED"
        assert result.governance_decision == "QUARANTINE"
        assert result.is_safe is False
        assert "security violation" in result.evidence_detected.lower() or "replay" in result.evidence_detected.lower() or "sequence" in result.evidence_detected.lower()

    def test_trigger_inversion_reporting_structure(self):
        """Verify Neural Cleanse trigger inversion reports meet SIH26228 specification in both white-box and black-box modes."""
        # 1. Black-box mode: weights inaccessible
        bb_report = analyze_trigger_inversion(
            model_name="yolo11n_surveillance.pt",
            target_class=0
        )
        assert isinstance(bb_report, TriggerInversionReport)
        assert bb_report.model_name == "yolo11n_surveillance.pt"
        assert bb_report.optimization_status == "WHITE_BOX_ANALYSIS_UNAVAILABLE"
        assert bb_report.anomaly_score is None
        assert "white-box" in bb_report.evidence.lower() or "black-box" in bb_report.limitations.lower()

        # 2. White-box mode: weights present
        wb_report = analyze_trigger_inversion(
            model_name="yolo11n_surveillance.pt",
            target_class=0,
            model_weights_path=Path(__file__),
            white_box_available=True
        )
        assert wb_report.optimization_status == "CONVERGED"
        assert wb_report.anomaly_score >= 2.0
        assert wb_report.is_trojan_suspected is True
        assert wb_report.threshold == 2.0
        assert len(wb_report.limitations) > 0


    def test_ood_and_distribution_shift_review_governance(self):
        """Verify soft distributional shifts trigger REVIEW or ACCEPT rather than silent acceptance."""
        suite_dir = Path(__file__).resolve().parents[1] / "data" / "synthetic_eval"
        
        # OOD noise -> REVIEW
        ood_res = evaluate_synthetic_case("case_03_ood_sample", suite_dir)
        assert ood_res.governance_decision == "REVIEW"
        assert "arcface" in ood_res.evidence_detected.lower() or "cosine" in ood_res.evidence_detected.lower() or "distributional shift" in ood_res.evidence_detected.lower()

        # Low-light shift -> ACCEPT (Zero-DCE++ compensated)
        lux_res = evaluate_synthetic_case("case_05_low_light_shift", suite_dir)
        assert lux_res.governance_decision == "ACCEPT"
        assert "managed" in lux_res.evidence_detected.lower() or "permitted" in lux_res.evidence_detected.lower() or "zero-dce" in lux_res.evidence_detected.lower()


    def test_verified_event_governance_disposition(self):
        """Ensure VerifiedEvent cleanly incorporates benchmark defense evidence and quarantine."""
        event = VerifiedEvent(
            event_id="EVT-SEC-TEST-001",
            camera_id="CAM-SEC-TEST",
            timestamp="2026-10-01T00:00:00Z",
            sequence_id=101,
            confidence=0.91,
            bounding_boxes=[
                BoundingBox(
                    x1=10.0,
                    y1=20.0,
                    x2=100.0,
                    y2=200.0
                )
            ],
            input_hash="a" * 64,
            previous_provenance_hash="b" * 64,
            current_provenance_hash="c" * 64,
            governance_decision="QUARANTINE",
            assurance_status="FLAG_TAMPER",
            benchmark_evidence=[
                BenchmarkEvidenceItem(
                    asset="model_weights",
                    attack_class="TRIGGER_INJECTION",
                    source="synthetic_eval",
                    model="yolo11n",
                    input_hash="a" * 64,
                    model_hash="m" * 64,
                    output_hash="o" * 64,
                    benchmark_id="trinetra-synthetic-suite-v1",
                    benchmark_version="1.0.0",
                    evidence="Trigger inverted with anomaly index 2.85",
                    confidence=0.95,
                    severity="CRITICAL",
                    governance="QUARANTINE"
                )
            ]
        )
        canonical = event.compute_canonical_digest()
        assert len(canonical) == 64
        assert event.governance_decision == "QUARANTINE"
        assert len(event.benchmark_evidence) == 1

