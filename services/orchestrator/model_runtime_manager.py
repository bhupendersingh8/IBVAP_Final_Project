"""
IBVAP Model Runtime Manager
===========================
Grand Finale Master Architecture - Section 2 & Section 5
Dynamic, resource-aware model lifecycle and VRAM budget scheduling across:
- LOW_VRAM_4GB (RTX 3050 4GB)
- LOW_VRAM_6GB (RTX 3050 6GB)
- STANDARD_8GB (RTX 5050 8GB / RTX 4060)
- DELL_CPU (Fallback CPU)
"""
from __future__ import annotations

import os
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
import structlog

from services.hardware.hardware_detector import HardwareDetector, HardwareProfile, HardwareProfileName
from services.ingestion.frame_packet import FramePacket

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logger = structlog.get_logger()


class ModelTier(str, Enum):
    TIER_CORE = "TIER_CORE"             # 100% continuous (Detection, Tracking) - Never evicted
    TIER_SPECIALIST = "TIER_SPECIALIST" # Event-triggered (ANPR, Pose, Re-ID, Depth)
    TIER_HEAVY = "TIER_HEAVY"           # Heavy vision embeddings
    TIER_REASONER = "TIER_REASONER"     # Tactical VLM / LLM copilot


class ModelResidency(str, Enum):
    RESIDENT_VRAM = "RESIDENT_VRAM"
    RESIDENT_CPU = "RESIDENT_CPU"
    ON_DEMAND = "ON_DEMAND"
    FALLBACK_ACTIVE = "FALLBACK_ACTIVE"
    MISSING_WEIGHTS = "MISSING_WEIGHTS"


@dataclass
class ModelRegistration:
    model_name: str
    tier: ModelTier
    weight_path: Optional[str] = None
    estimated_vram_mb: int = 200
    residency: ModelResidency = ModelResidency.ON_DEMAND
    loader: Optional[Callable] = None
    unloader: Optional[Callable] = None
    instance: Optional[Any] = None
    total_calls: int = 0
    total_latency_ms: float = 0.0
    last_called_time: float = 0.0


class ModelRuntimeManager:
    """
    Orchestrates VRAM memory budgets and schedules model execution
    according to active hardware profile and priority tiers.
    """
    def __init__(self, hardware_profile: Optional[HardwareProfile] = None):
        self.detector = HardwareDetector()
        self.profile: HardwareProfile = hardware_profile or self.detector.detect()
        self.vram_budget_mb = self.profile.vram_budget_mb
        self.models: Dict[str, ModelRegistration] = {}

        logger.info(
            "ModelRuntimeManager initialized",
            profile=self.profile.profile_name.value,
            gpu_name=self.profile.gpu_name,
            total_vram_gb=self.profile.total_vram_gb,
            vram_budget_mb=self.vram_budget_mb,
            max_streams=self.profile.max_streams,
        )

    def register_model(
        self,
        model_name: str,
        tier: ModelTier,
        weight_path: Optional[str] = None,
        estimated_vram_mb: int = 200,
        loader: Optional[Callable] = None,
        unloader: Optional[Callable] = None,
    ) -> None:
        """Registers a model definition into the runtime scheduler."""
        file_exists = os.path.exists(weight_path) if weight_path else False
        residency = ModelResidency.ON_DEMAND if file_exists else ModelResidency.FALLBACK_ACTIVE

        self.models[model_name] = ModelRegistration(
            model_name=model_name,
            tier=tier,
            weight_path=weight_path,
            estimated_vram_mb=estimated_vram_mb,
            residency=residency,
            loader=loader,
            unloader=unloader,
        )

    def get_vram_telemetry(self) -> Dict[str, Any]:
        """Returns live physical and estimated PyTorch VRAM telemetry."""
        if HAS_TORCH and torch.cuda.is_available():
            allocated_mb = round(torch.cuda.memory_allocated() / (1024 * 1024), 2)
            reserved_mb = round(torch.cuda.memory_reserved() / (1024 * 1024), 2)
            max_mb = self.profile.total_vram
        else:
            allocated_mb = 0.0
            reserved_mb = 0.0
            max_mb = 0

        estimated_allocated = sum(
            m.estimated_vram_mb for m in self.models.values()
            if m.residency == ModelResidency.RESIDENT_VRAM
        )

        return {
            "gpu_name": self.profile.gpu_name,
            "profile": self.profile.profile_name.value,
            "physical_allocated_mb": allocated_mb,
            "physical_reserved_mb": reserved_mb,
            "estimated_resident_vram_mb": estimated_allocated,
            "budget_mb": self.vram_budget_mb,
            "total_vram_mb": max_mb,
            "utilization_pct": round((allocated_mb / max_mb * 100), 1) if max_mb > 0 else 0.0,
        }

    def request_model_execution(
        self,
        model_name: str,
        packet: Optional[FramePacket] = None,
        max_freshness_seconds: float = 0.5,
    ) -> bool:
        """
        Determines whether the model is authorized to execute based on:
        1. Frame freshness (drops stale frames to prevent queue backlog).
        2. VRAM headroom (offloads lower-priority models if budget exceeded).
        """
        # 1. Freshness check
        if packet is not None and packet.is_stale(max_freshness_seconds):
            logger.debug(
                "Dropping execution for stale frame",
                model=model_name,
                age=round(packet.age_seconds, 3),
                limit=max_freshness_seconds,
            )
            return False

        if model_name not in self.models:
            return True

        reg = self.models[model_name]

        # CORE models are always allowed to execute
        if reg.tier == ModelTier.TIER_CORE:
            return True

        # On LOW_VRAM_4GB, ensure only 1 specialist executes concurrently
        if self.profile.profile_name == HardwareProfileName.LOW_VRAM_4GB:
            active_specialists = [
                m for m in self.models.values()
                if m.tier in (ModelTier.TIER_SPECIALIST, ModelTier.TIER_HEAVY, ModelTier.TIER_REASONER)
                and m.residency == ModelResidency.RESIDENT_VRAM
            ]
            if len(active_specialists) >= 1:
                # Evict/offload other specialist
                for other in active_specialists:
                    if other.model_name != model_name:
                        self._evict_model_from_vram(other.model_name)

        # Check total estimated VRAM
        telemetry = self.get_vram_telemetry()
        projected = telemetry["estimated_resident_vram_mb"] + (0 if reg.residency == ModelResidency.RESIDENT_VRAM else reg.estimated_vram_mb)

        if projected > self.vram_budget_mb and self.vram_budget_mb > 0:
            logger.warning(
                "VRAM budget limit approached. Evicting non-core models",
                projected=projected,
                budget=self.vram_budget_mb,
            )
            self._free_vram_headroom(reg.estimated_vram_mb)

        return True

    def _evict_model_from_vram(self, model_name: str) -> None:
        """Evicts a model from VRAM to CPU or unloads it completely."""
        if model_name not in self.models:
            return
        reg = self.models[model_name]
        if reg.tier == ModelTier.TIER_CORE:
            return  # Never evict core models

        if reg.unloader:
            try:
                reg.unloader(reg.instance)
            except Exception as e:
                logger.warning("Error running model unloader", model=model_name, error=str(e))

        reg.residency = ModelResidency.ON_DEMAND
        reg.instance = None

        if HAS_TORCH and torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Evicted model from VRAM", model=model_name)

    def _free_vram_headroom(self, required_mb: int) -> None:
        """Evicts lower priority models (REASONER first, then HEAVY, then SPECIALIST)."""
        eviction_order = [ModelTier.TIER_REASONER, ModelTier.TIER_HEAVY, ModelTier.TIER_SPECIALIST]
        for tier in eviction_order:
            for name, reg in list(self.models.items()):
                if reg.tier == tier and reg.residency == ModelResidency.RESIDENT_VRAM:
                    self._evict_model_from_vram(name)
                    telemetry = self.get_vram_telemetry()
                    if telemetry["estimated_resident_vram_mb"] + required_mb <= self.vram_budget_mb:
                        return

    def record_execution(self, model_name: str, latency_ms: float) -> None:
        """Records telemetry for an execution run."""
        if model_name in self.models:
            reg = self.models[model_name]
            reg.total_calls += 1
            reg.total_latency_ms += latency_ms
            reg.last_called_time = time.time()

    def get_catalog_status(self) -> List[Dict[str, Any]]:
        """Returns the factual status of all registered models."""
        result = []
        for name, reg in self.models.items():
            result.append({
                "model_name": name,
                "tier": reg.tier.value,
                "weight_path": reg.weight_path,
                "weights_exist": os.path.exists(reg.weight_path) if reg.weight_path else False,
                "residency": reg.residency.value,
                "estimated_vram_mb": reg.estimated_vram_mb,
                "total_calls": reg.total_calls,
                "avg_latency_ms": round(reg.total_latency_ms / reg.total_calls, 2) if reg.total_calls > 0 else 0.0,
            })
        return result
