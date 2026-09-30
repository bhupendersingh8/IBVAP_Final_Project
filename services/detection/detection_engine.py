from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np

from .schemas import DetectionBatch
from ..ingestion.frame_buffer import CameraFrame

class DetectionEngine(ABC):
    """
    Abstract interface for object detection models. 
    The application must never depend directly on a specific detector vendor (like Ultralytics).
    This ensures licensing agility and ease of upgrades.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self._config = config
        
    @abstractmethod
    def load_model(self) -> None:
        """Load the model weights into memory/VRAM."""
        pass

    @abstractmethod
    def detect(self, frame: np.ndarray, camera_id: str, frame_id: int, timestamp) -> DetectionBatch:
        """
        Run inference on a raw numpy BGR image array.
        Must return normalized bounding boxes via the DetectionBatch schema.
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Return metadata about the loaded model.
        Expected keys: model_name, model_version, device, input_size, confidence_threshold
        """
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if the model is fully loaded and ready for inference."""
        pass

    @abstractmethod
    def warmup(self, iterations: int = 3) -> None:
        """Run dummy inference to initialize caches/compilers (like TensorRT)."""
        pass

    def detect_from_camera_frame(self, camera_frame: CameraFrame) -> DetectionBatch:
        """Convenience wrapper to extract data from a CameraFrame object."""
        return self.detect(
            frame=camera_frame.frame,
            camera_id=camera_frame.camera_id,
            frame_id=camera_frame.frame_id,
            timestamp=camera_frame.timestamp
        )

    def health(self) -> Dict[str, Any]:
        """Return operational health status."""
        return {
            "status": "healthy" if self.is_loaded() else "not_loaded",
            "model_info": self.get_model_info() if self.is_loaded() else None
        }

    def unload(self) -> None:
        """Release weights and VRAM."""
        pass

    def benchmark(self, iterations: int = 10) -> Dict[str, float]:
        """Run standardized benchmark to measure average inference latency and FPS."""
        import time
        from datetime import datetime, timezone
        if not self.is_loaded():
            return {"avg_latency_ms": 0.0, "estimated_fps": 0.0}
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        now_ts = datetime.now(timezone.utc)
        times = []
        for i in range(iterations):
            t0 = time.perf_counter()
            self.detect(dummy, "BENCHMARK", i, now_ts)
            times.append((time.perf_counter() - t0) * 1000.0)
        avg_ms = sum(times) / len(times) if times else 0.0
        return {
            "avg_latency_ms": round(avg_ms, 2),
            "estimated_fps": round(1000.0 / avg_ms, 1) if avg_ms > 0 else 0.0
        }
