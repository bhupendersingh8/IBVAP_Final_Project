"""
IBVAP Model Adapters Module
"""
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
from .base_adapter import BaseModelAdapter
from .family_adapters import (
    DetectionModelAdapter,
    TrackingModelAdapter,
    SegmentationModelAdapter,
    PoseModelAdapter,
    FaceModelAdapter,
    ReIDModelAdapter,
    ANPRModelAdapter,
    VisionEmbeddingModelAdapter,
    RestorationModelAdapter,
    VLMModelAdapter,
    DepthModelAdapter,
    TemporalGraphModelAdapter,
    IndicLanguageModelAdapter,
)

__all__ = [
    "ModelInterface",
    "ModelFamilyType",
    "DetectionResult",
    "TrackingResult",
    "IdentityResult",
    "OCRResult",
    "PoseResult",
    "SegmentationResult",
    "DepthResult",
    "VLMResult",
    "BaseModelAdapter",
    "DetectionModelAdapter",
    "TrackingModelAdapter",
    "SegmentationModelAdapter",
    "PoseModelAdapter",
    "FaceModelAdapter",
    "ReIDModelAdapter",
    "ANPRModelAdapter",
    "VisionEmbeddingModelAdapter",
    "RestorationModelAdapter",
    "VLMModelAdapter",
    "DepthModelAdapter",
    "TemporalGraphModelAdapter",
    "IndicLanguageModelAdapter",
]
