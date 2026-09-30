"""
IBVAP Hardware-Aware Model Router
==================================
SIH Problem Statement 26187 — Intelligent Border Video Analytics Platform

Provides autonomous, hardware-aware model selection across 5 execution tiers:
- DELL_CPU (Edge Host Fallback)
- RTX3050_4GB (Target Deployment B1)
- RTX3050_6GB (Target Deployment B2)
- HIGH_VRAM_NVIDIA (Command Post Cluster)
- REMOTE_GPU (Cloud / High-VRAM Coprocessor)

Features:
- Zero-crash fallback routing: if a GPU model is requested on CPU, gracefully delegates
  to the verified CPU baseline.
- Automatic integration with HardwareDetector and UnifiedModelRegistry.
- Full layer-by-layer dynamic model dispatch.
"""

from __future__ import annotations
import os
import structlog
from typing import Dict, Any, Optional, List, Tuple

from services.hardware.hardware_detector import (
    HardwareDetector,
    HardwareProfile,
    HardwareProfileName,
    hardware_detector
)
from ml.registry.unified_model_registry import (
    UnifiedModelRegistry,
    UnifiedModelEntry,
    RegistryStatus,
    unified_model_registry
)

logger = structlog.get_logger()


class ModelRouter:
    """
    Dynamically routes model inference across hardware profiles with deterministic fallbacks.
    """

    def __init__(
        self,
        detector: Optional[HardwareDetector] = None,
        registry: Optional[UnifiedModelRegistry] = None,
    ):
        self.detector = detector or hardware_detector
        self.registry = registry or unified_model_registry
        self._current_profile: HardwareProfile = self.detector.resolve_profile()

    @property
    def current_profile(self) -> HardwareProfile:
        return self._current_profile

    def refresh_profile(self) -> HardwareProfile:
        self._current_profile = self.detector.resolve_profile()
        return self._current_profile

    def resolve_model(
        self,
        family: str,
        preferred_model_name: Optional[str] = None
    ) -> Tuple[UnifiedModelEntry, str]:
        """
        Resolves the appropriate model for a given family and hardware environment.
        Returns: (UnifiedModelEntry, execution_mode: str)
        execution_mode is one of: 'LOCAL_CPU', 'LOCAL_GPU_TENSORRT', 'LOCAL_GPU_CUDA', 'REMOTE_GPU'
        """
        p_name = self._current_profile.profile_name

        # If a specific preferred model was requested, check compatibility
        if preferred_model_name:
            entry = self.registry.get_model(preferred_model_name)
            if entry:
                if p_name == HardwareProfileName.DELL_CPU and entry.cpu:
                    return entry, "LOCAL_CPU"
                elif p_name in {HardwareProfileName.RTX3050_4GB, HardwareProfileName.RTX3050_6GB}:
                    if (p_name == HardwareProfileName.RTX3050_4GB and entry.rtx3050_4gb) or \
                       (p_name == HardwareProfileName.RTX3050_6GB and entry.rtx3050_6gb):
                        mode = "LOCAL_GPU_TENSORRT" if self._current_profile.runtime.tensorrt_available else "LOCAL_GPU_CUDA"
                        return entry, mode
                elif p_name == HardwareProfileName.HIGH_VRAM_NVIDIA and entry.high_end_gpu:
                    return entry, "LOCAL_GPU_CUDA"
                elif p_name == HardwareProfileName.REMOTE_GPU and entry.remote_gpu:
                    return entry, "REMOTE_GPU"

        # Otherwise resolve by family primary
        primary = self.registry.get_primary(family)
        if not primary:
            # Fallback to any model in the family
            models = self.registry.get_by_family(family)
            if not models:
                raise ValueError(f"No models registered for family '{family}'")
            primary = models[0]

        # Check if primary is executable on host
        if p_name == HardwareProfileName.DELL_CPU:
            if primary.cpu:
                return primary, "LOCAL_CPU"
            # If primary requires GPU, fall back to registered fallback or first CPU model
            fb = self.registry.get_fallback(family)
            if fb and fb.cpu:
                logger.info("Primary requires GPU; routing to verified CPU fallback", primary=primary.name, fallback=fb.name)
                return fb, "LOCAL_CPU"
            cpu_candidates = [m for m in self.registry.get_by_family(family) if m.cpu]
            if cpu_candidates:
                return cpu_candidates[0], "LOCAL_CPU"
            # If no CPU model exists, must route remotely
            return primary, "REMOTE_GPU"

        elif p_name in {HardwareProfileName.RTX3050_4GB, HardwareProfileName.RTX3050_6GB}:
            supports_4gb = primary.rtx3050_4gb
            supports_6gb = primary.rtx3050_6gb
            if (p_name == HardwareProfileName.RTX3050_4GB and supports_4gb) or \
               (p_name == HardwareProfileName.RTX3050_6GB and supports_6gb):
                mode = "LOCAL_GPU_TENSORRT" if self._current_profile.runtime.tensorrt_available else "LOCAL_GPU_CUDA"
                return primary, mode
            # Check fallback
            fb = self.registry.get_fallback(family)
            if fb:
                return fb, "LOCAL_CPU" if fb.cpu else "REMOTE_GPU"
            return primary, "LOCAL_CPU" if primary.cpu else "REMOTE_GPU"

        elif p_name == HardwareProfileName.HIGH_VRAM_NVIDIA:
            return primary, "LOCAL_GPU_CUDA" if primary.high_end_gpu else "LOCAL_CPU"

        else:  # REMOTE_GPU
            return primary, "REMOTE_GPU"

    def get_active_stack(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns the resolved active model stack across all 17 operational layers.
        """
        families = [
            "detection",
            "tracking",
            "reid",
            "face_identity",
            "anpr",
            "segmentation",
            "pose_behavior",
            "behaviour",
            "anomaly",
            "restoration",
            "vlm",
            "foundation",
            "indian_ai",
            "temporal_event",
            "multi_camera",
            "evidence_security",
            "edge_stack",
        ]
        stack = {}
        for fam in families:
            try:
                entry, mode = self.resolve_model(fam)
                stack[fam] = {
                    "model_name": entry.name,
                    "version": entry.version,
                    "weights": entry.weights,
                    "adapter": entry.adapter,
                    "execution_mode": mode,
                    "status": entry.status,
                    "primary": entry.primary,
                    "benchmark": entry.benchmark,
                }
            except Exception as e:
                stack[fam] = {"error": str(e)}
        return stack


# Singleton Router Instance
model_router = ModelRouter()
