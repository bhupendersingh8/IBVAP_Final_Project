"""
Attack Taxonomy & Reference Benchmark Registry (SIH26228)
=========================================================
Standardizes attack categories, defense capabilities, and reference benchmark
registry records.

Requirements:
- Distinguish explicitly between REGISTERED_BUT_NOT_EXECUTED, LOCAL_AVAILABLE,
  and EXECUTED_VERIFIED.
- Zero fabrication of benchmark runs: only real local executions produce metrics.
- Comprehensive mapping of all 6 required attack domains:
  1. TRIGGER_INJECTION (BadNets, Patch, Polygonal)
  2. BACKDOOR_TROJAN (WaNet, Blended, Clean-label)
  3. LABEL_POISONING (Label Flipping, Cleanlab Confident Learning)
  4. INFERENCE_TAMPERING (Coordinate injection, confidence spoofing)
  5. REPLAY_ATTACK (Stale frame re-injection, timestamp regression)
  6. OUT_OF_DISTRIBUTION (ArcFace cosine distance, MMD shift)
"""

from __future__ import annotations

import enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class AttackCategory(str, enum.Enum):
    TRIGGER_INJECTION = "TRIGGER_INJECTION"
    BACKDOOR_TROJAN = "BACKDOOR_TROJAN"
    LABEL_POISONING = "LABEL_POISONING"
    INFERENCE_TAMPERING = "INFERENCE_TAMPERING"
    REPLAY_ATTACK = "REPLAY_ATTACK"
    OUT_OF_DISTRIBUTION = "OUT_OF_DISTRIBUTION"


class BenchmarkExecutionStatus(str, enum.Enum):
    REGISTERED_BUT_NOT_EXECUTED = "REGISTERED_BUT_NOT_EXECUTED"
    LOCAL_AVAILABLE = "LOCAL_AVAILABLE"
    EXECUTED_VERIFIED = "EXECUTED_VERIFIED"
    FAILED = "FAILED"


class BenchmarkRegistration(BaseModel):
    benchmark_id: str
    name: str
    version: str
    organization: str
    license: str
    license_url: str
    primary_attack_categories: List[AttackCategory]
    defenses_evaluated: List[str]
    is_open_access: bool
    status: BenchmarkExecutionStatus
    local_path: Optional[str] = None
    citation: str
    description: str


class ReferenceBenchmarkRegistry:
    """
    Registry of validated open-source reference attack benchmarks.
    Maintains clean state tracking without fabricating execution results.
    """

    def __init__(self):
        self._benchmarks: Dict[str, BenchmarkRegistration] = {}
        self._init_defaults()

    def _init_defaults(self):
        # 1. NIST TrojAI Round 1
        self.register(BenchmarkRegistration(
            benchmark_id="nist-trojai-round1",
            name="NIST TrojAI Benchmark (Round 1)",
            version="Round 1",
            organization="National Institute of Standards and Technology (NIST) / IARPA",
            license="NIST-Public-Domain",
            license_url="https://pages.nist.gov/trojai/",
            primary_attack_categories=[
                AttackCategory.TRIGGER_INJECTION,
                AttackCategory.BACKDOOR_TROJAN
            ],
            defenses_evaluated=[
                "Neural Cleanse (L1 Inversion)",
                "Trigger Reverse Engineering",
                "Behavioral Divergence"
            ],
            is_open_access=True,
            status=BenchmarkExecutionStatus.REGISTERED_BUT_NOT_EXECUTED,
            local_path=None,
            citation="Karra et al., 'The TrojAI Software Framework: An Overview', NIST Technical Report, 2020.",
            description="NIST TrojAI challenge round evaluating trojan detection algorithms on vision architectures with polygonal and patch triggers."
        ))

        # 2. NIST TrojAI Round 2
        self.register(BenchmarkRegistration(
            benchmark_id="nist-trojai-round2",
            name="NIST TrojAI Benchmark (Round 2)",
            version="Round 2",
            organization="NIST / IARPA",
            license="NIST-Public-Domain",
            license_url="https://pages.nist.gov/trojai/",
            primary_attack_categories=[
                AttackCategory.TRIGGER_INJECTION,
                AttackCategory.BACKDOOR_TROJAN
            ],
            defenses_evaluated=[
                "Spectral Signature Analysis",
                "Filter Inversion",
                "Activation Clustering"
            ],
            is_open_access=True,
            status=BenchmarkExecutionStatus.REGISTERED_BUT_NOT_EXECUTED,
            local_path=None,
            citation="NIST TrojAI Round 2 Competition Overview, 2021.",
            description="Second round of TrojAI evaluating Instagram/Instagram-filter triggers and multi-target backdoors."
        ))

        # 3. BackdoorBench
        self.register(BenchmarkRegistration(
            benchmark_id="backdoorbench-v1",
            name="BackdoorBench: A Comprehensive Benchmark of Backdoor Learning",
            version="v1.0",
            organization="Tsinghua University & BackdoorBench Contributors",
            license="MIT",
            license_url="https://github.com/SCLBD/BackdoorBench/blob/main/LICENSE",
            primary_attack_categories=[
                AttackCategory.TRIGGER_INJECTION,
                AttackCategory.BACKDOOR_TROJAN,
                AttackCategory.LABEL_POISONING
            ],
            defenses_evaluated=[
                "Neural Cleanse",
                "STRIP",
                "Fine-Pruning",
                "Spectral Signatures",
                "Cleanlab Confident Learning"
            ],
            is_open_access=True,
            status=BenchmarkExecutionStatus.REGISTERED_BUT_NOT_EXECUTED,
            local_path=None,
            citation="Wu et al., 'BackdoorBench: A Comprehensive Benchmark of Backdoor Learning', NeurIPS 2022.",
            description="Standardized benchmark implementing 80+ attack and defense combinations with verifiable code and public weights."
        ))

        # 4. TRINETRA Synthetic Attack Suite
        self.register(BenchmarkRegistration(
            benchmark_id="trinetra-synthetic-suite-v1",
            name="TRINETRA Synthetic Attack & Tampering Evaluation Suite",
            version="1.0.0",
            organization="IBVAP / TRINETRA Engineering Team",
            license="Apache-2.0",
            license_url="https://www.apache.org/licenses/LICENSE-2.0",
            primary_attack_categories=[
                AttackCategory.TRIGGER_INJECTION,
                AttackCategory.LABEL_POISONING,
                AttackCategory.INFERENCE_TAMPERING,
                AttackCategory.REPLAY_ATTACK,
                AttackCategory.OUT_OF_DISTRIBUTION
            ],
            defenses_evaluated=[
                "Recursive Merkle Block Hashing (H_n)",
                "Coordinate Range & Boundary Guardrails",
                "BadNets Patch Detector",
                "Zero-DCE++ Illumination Curve",
                "ArcFace Cosine Distance",
                "Non-blocking Ring Buffer Integrity"
            ],
            is_open_access=True,
            status=BenchmarkExecutionStatus.LOCAL_AVAILABLE,
            local_path="data/synthetic_eval",
            citation="TRINETRA TCVIAF Assurance Specifications, SIH26228, 2026.",
            description="Offline-capable, reproducible synthetic attack battery with exact SHA-256 Merkle proofs for CI and air-gapped deployment."
        ))

    def register(self, reg: BenchmarkRegistration):
        self._benchmarks[reg.benchmark_id] = reg

    def get(self, benchmark_id: str) -> Optional[BenchmarkRegistration]:
        return self._benchmarks.get(benchmark_id)

    def list_all(self) -> List[BenchmarkRegistration]:
        return list(self._benchmarks.values())

    def update_status(self, benchmark_id: str, status: BenchmarkExecutionStatus, local_path: Optional[str] = None):
        if benchmark_id in self._benchmarks:
            self._benchmarks[benchmark_id].status = status
            if local_path:
                self._benchmarks[benchmark_id].local_path = local_path


_global_registry = ReferenceBenchmarkRegistry()

def get_benchmark_registry() -> ReferenceBenchmarkRegistry:
    return _global_registry
