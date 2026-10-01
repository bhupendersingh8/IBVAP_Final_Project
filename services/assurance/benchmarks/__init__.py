"""
TCVIAF / SIH26228 Reference Attack Benchmarks & Assurance Adapters
===================================================================
Provides reproducible adapters and registries for NIST TrojAI, BackdoorBench,
and deterministic synthetic attack suites.
"""

from .registry import (
    AttackCategory,
    BenchmarkExecutionStatus,
    BenchmarkRegistration,
    get_benchmark_registry,
)
from .trojai_adapter import TrojAIAdapter, TrojAIArtifact
from .backdoorbench_adapter import BackdoorBenchAdapter, BackdoorAttackSpec

__all__ = [
    "AttackCategory",
    "BenchmarkExecutionStatus",
    "BenchmarkRegistration",
    "get_benchmark_registry",
    "TrojAIAdapter",
    "TrojAIArtifact",
    "BackdoorBenchAdapter",
    "BackdoorAttackSpec",
]
