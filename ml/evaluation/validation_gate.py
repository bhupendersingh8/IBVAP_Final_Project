"""
Automated Model Validation Gate for IBVAP.
Enforces strict quality criteria before candidate models can be promoted:
- Minimum mAP50 threshold (>= 0.70)
- Maximum False Positive Rate (<= 0.10)
- Maximum CPU Inference Latency (<= 100 ms)
- Superiority or parity with baseline model
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import structlog

logger = structlog.get_logger()


@dataclass
class GateCriteria:
    min_mAP50: float = 0.70
    min_mAP50_95: float = 0.50
    max_false_positive_rate: float = 0.10
    max_inference_ms: float = 100.0
    require_superior_to_baseline: bool = True


class ValidationGate:
    """
    Evaluates candidate model metrics against defined acceptance gates.
    """

    def __init__(self, criteria: Optional[GateCriteria] = None):
        self.criteria = criteria or GateCriteria()

    def evaluate(
        self,
        candidate_metrics: Dict[str, float],
        baseline_metrics: Optional[Dict[str, float]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Verifies whether candidate meets all acceptance gates.
        Returns: (passed: bool, reasons: List[str])
        """
        reasons: List[str] = []
        passed = True

        # Check 1: mAP50
        cand_map50 = candidate_metrics.get("mAP50")
        if cand_map50 is None:
            passed = False
            reasons.append("FAIL: Candidate mAP50 metric is missing or NOT_AVAILABLE.")
        elif cand_map50 < self.criteria.min_mAP50:
            passed = False
            reasons.append(f"FAIL: Candidate mAP50 ({cand_map50:.3f}) below required threshold ({self.criteria.min_mAP50:.3f}).")
        else:
            reasons.append(f"PASS: mAP50 ({cand_map50:.3f}) >= {self.criteria.min_mAP50:.3f}.")

        # Check 2: False Positive Rate
        cand_fpr = candidate_metrics.get("false_positive_rate")
        if cand_fpr is not None and cand_fpr > self.criteria.max_false_positive_rate:
            passed = False
            reasons.append(f"FAIL: Candidate FPR ({cand_fpr:.3f}) exceeds threshold ({self.criteria.max_false_positive_rate:.3f}).")

        # Check 3: Inference Latency
        cand_latency = candidate_metrics.get("inference_latency_ms") or candidate_metrics.get("inference_ms_cpu")
        if cand_latency is not None and cand_latency > self.criteria.max_inference_ms:
            passed = False
            reasons.append(f"FAIL: Candidate latency ({cand_latency:.1f}ms) exceeds limit ({self.criteria.max_inference_ms:.1f}ms).")
        elif cand_latency is not None:
            reasons.append(f"PASS: Latency ({cand_latency:.1f}ms) <= {self.criteria.max_inference_ms:.1f}ms.")

        # Check 4: Baseline Comparison
        if self.criteria.require_superior_to_baseline and baseline_metrics:
            base_map50 = baseline_metrics.get("mAP50") or baseline_metrics.get("mAP50_coco", 0.0)
            if cand_map50 is not None and base_map50 is not None and cand_map50 < base_map50:
                passed = False
                reasons.append(f"FAIL: Candidate mAP50 ({cand_map50:.3f}) is inferior to baseline ({base_map50:.3f}).")
            elif cand_map50 is not None and base_map50 is not None:
                reasons.append(f"PASS: Candidate mAP50 ({cand_map50:.3f}) exceeds/matches baseline ({base_map50:.3f}).")

        return passed, reasons
