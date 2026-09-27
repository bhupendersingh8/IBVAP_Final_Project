"""
IBVAP Base Model Adapter Standard
=================================
Defines the standard contract for all IBVAP models across all 17 pools:
- load()
- predict()
- validate()
- metadata()
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np


class BaseModelAdapter(ABC):
    """Abstract Base Class for all model adapters in IBVAP."""

    def __init__(self, model_id: str, hardware_target: str = "CPU"):
        self.model_id = model_id
        self.hardware_target = hardware_target
        self.is_loaded = False
        self.weights_path: Optional[str] = None
        self._last_latency_ms: float = 0.0

    @abstractmethod
    def load(self, weights_path: Optional[str] = None) -> bool:
        """Loads model weights/runtime into memory."""
        pass

    @abstractmethod
    def predict(self, input_data: Any) -> Dict[str, Any]:
        """Runs forward inference on real input and returns normalized dictionary."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Executes a self-test with sample or real data to verify readiness."""
        pass

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Returns normalized metadata describing the model, parameters, and status."""
        pass
