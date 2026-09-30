"""
IBVAP Base Model Adapter Standard
=================================
Defines the standard contract for all IBVAP models across all 18 families:
- load()
- predict()
- validate()
- metadata()
- unload()

Inherits from and implements the canonical ModelInterface standard.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np

from .model_interface import (
    ModelInterface,
    ModelFamilyType,
    DetectionResult,
    TrackingResult,
    IdentityResult,
    OCRResult,
    PoseResult,
    SegmentationResult,
    DepthResult,
    VLMResult,
)


class BaseModelAdapter(ModelInterface):
    """Abstract Base Class for all model adapters in IBVAP."""

    def __init__(
        self,
        model_id: str,
        hardware_target: str = "CPU",
        family: ModelFamilyType = ModelFamilyType.DETECTION,
        weights_path: Optional[str] = None,
    ):
        super().__init__(
            model_name=model_id,
            family=family,
            device=hardware_target.lower(),
            weights_path=weights_path,
        )
        self.model_id = model_id
        self.hardware_target = hardware_target
        self._last_latency_ms: float = 0.0

    @property
    def last_latency_ms(self) -> float:
        return self._last_latency_ms

    @last_latency_ms.setter
    def last_latency_ms(self, val: float):
        self._last_latency_ms = val

    @abstractmethod
    def load(self, weights_path: Optional[str] = None) -> bool:
        """Loads model weights/runtime into memory."""
        pass

    @abstractmethod
    def predict(self, input_data: Any) -> Any:
        """Runs forward inference on real input and returns normalized dictionary or Result dataclass."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Executes a self-test with sample or real data to verify readiness."""
        pass

    def metadata(self) -> Dict[str, Any]:
        """Returns normalized metadata describing the model, parameters, and status."""
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "family": self.family.value if hasattr(self.family, "value") else str(self.family),
            "weights": self.weights_path,
            "is_loaded": self.is_loaded,
            "last_latency_ms": self._last_latency_ms,
            "hardware": self.hardware_target,
            "device": self.device,
            "total_calls": self.total_calls,
        }
