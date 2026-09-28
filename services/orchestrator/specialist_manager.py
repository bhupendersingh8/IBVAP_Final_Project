"""
IBVAP Event-Triggered Specialist Pipeline Manager
=================================================
Implements Phase 12 requirements:
- Executes expensive specialist AI models strictly on-demand when an event trigger occurs.
- Fast path (Normal frame): Primary Detector + ByteTracker
- Heavy path (Event candidate):
    Detector + Tracker
    → Pose Estimation
    → Relative Depth
    → ANPR / OCR
    → Re-ID / Identity
    → Segmentation (if justified)
    → Threat / Weapon verification
- Isolated execution: If one module fails or is unavailable, the pipeline
  continues gracefully using remaining evidence without crashing.
- Every module execution reports:
    started, completed, failed, latency, confidence, reason, attributes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class SpecialistModuleType(str, Enum):
    POSE = "POSE"
    DEPTH = "DEPTH"
    ANPR = "ANPR"
    IDENTITY = "IDENTITY"
    SEGMENTATION = "SEGMENTATION"
    WEAPON_THREAT = "WEAPON_THREAT"


@dataclass
class SpecialistExecutionReport:
    module_name: str
    module_type: SpecialistModuleType
    started: bool
    completed: bool
    failed: bool
    latency_ms: float
    confidence: float
    reason: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class SpecialistPipelineRunResult:
    target_id: int
    camera_id: str
    reports: List[SpecialistExecutionReport]
    total_specialist_latency_ms: float
    modules_succeeded: int
    modules_failed: int


class SpecialistPipelineManager:
    """
    Coordinates event-triggered specialist execution with complete failure isolation.
    """

    def __init__(self):
        self._handlers: Dict[SpecialistModuleType, Callable] = {}
        self.total_invocations = 0

    def register_handler(self, module_type: SpecialistModuleType, handler: Callable) -> None:
        """Registers a specialist execution handler."""
        self._handlers[module_type] = handler

    def execute_specialist_safe(
        self,
        module_type: SpecialistModuleType,
        *args,
        **kwargs
    ) -> SpecialistExecutionReport:
        """Executes a single specialist module with strict isolation and telemetry."""
        module_name = module_type.value
        t0 = time.perf_counter()

        if module_type not in self._handlers:
            return SpecialistExecutionReport(
                module_name=module_name,
                module_type=module_type,
                started=False,
                completed=False,
                failed=False,
                latency_ms=0.0,
                confidence=0.0,
                reason="Module not configured or registered",
                attributes={"status": "BYPASS_UNCONFIGURED"},
            )

        handler = self._handlers[module_type]
        try:
            res = handler(*args, **kwargs)
            latency_ms = (time.perf_counter() - t0) * 1000.0

            conf = float(res.get("confidence", 0.85) if isinstance(res, dict) else 0.85)
            reason = str(res.get("reason", "Specialist verification completed") if isinstance(res, dict) else "Done")
            attrs = res.get("attributes", {}) if isinstance(res, dict) else {}

            return SpecialistExecutionReport(
                module_name=module_name,
                module_type=module_type,
                started=True,
                completed=True,
                failed=False,
                latency_ms=round(latency_ms, 2),
                confidence=round(conf, 3),
                reason=reason,
                attributes=attrs,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            logger.warning("Specialist module failed gracefully", module=module_name, error=str(e))
            return SpecialistExecutionReport(
                module_name=module_name,
                module_type=module_type,
                started=True,
                completed=False,
                failed=True,
                latency_ms=round(latency_ms, 2),
                confidence=0.0,
                reason=f"Graceful degradation: {str(e)}",
                error_message=str(e),
                attributes={"status": "FAILED_GRACEFUL_DEGRADATION"},
            )

    def trigger_event_specialists(
        self,
        target_id: int,
        camera_id: str,
        class_name: str,
        crop: Optional[np.ndarray],
        requested_modules: List[SpecialistModuleType],
        context: Optional[Dict[str, Any]] = None,
    ) -> SpecialistPipelineRunResult:
        """
        Executes all requested specialist modules for an interesting event candidate.
        """
        self.total_invocations += 1
        t0 = time.perf_counter()
        reports: List[SpecialistExecutionReport] = []
        ctx = context or {}

        for mod in requested_modules:
            report = self.execute_specialist_safe(mod, crop=crop, target_id=target_id, camera_id=camera_id, context=ctx)
            reports.append(report)

        total_ms = (time.perf_counter() - t0) * 1000.0
        succeeded = sum(1 for r in reports if r.completed and not r.failed)
        failed = sum(1 for r in reports if r.failed)

        return SpecialistPipelineRunResult(
            target_id=target_id,
            camera_id=camera_id,
            reports=reports,
            total_specialist_latency_ms=round(total_ms, 2),
            modules_succeeded=succeeded,
            modules_failed=failed,
        )
