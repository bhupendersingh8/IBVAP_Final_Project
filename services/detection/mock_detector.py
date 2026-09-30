import time
import random
import numpy as np
from typing import Dict, Any, List, Optional

from .detection_engine import DetectionEngine
from .schemas import DetectionBatch, Detection, BBox

class MockDetector(DetectionEngine):
    """
    Mock detector for unit testing and development without downloading model weights.
    Returns random or pre-configured detections.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {}
        super().__init__(config)
        self.latency_ms = config.get("latency_ms", 15.0)
        self.inject_detections: Optional[List[Dict]] = config.get("inject_detections")
        
        self.model_name = "mock_detector"
        self.model_version = "0.0.1"
        self._loaded = False

    def load_model(self) -> None:
        # Simulate quick load
        time.sleep(0.01)
        self._loaded = True

    def is_loaded(self) -> bool:
        return self._loaded

    def warmup(self, iterations: int = 3) -> None:
        pass

    def detect(self, frame: np.ndarray, camera_id: str, frame_id: int, timestamp) -> DetectionBatch:
        if not self._loaded:
            raise RuntimeError("Model not loaded")
            
        # Simulate inference delay
        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000.0)
            
        detections = []
        
        if self.inject_detections is not None:
            # Use provided fake detections
            for d in self.inject_detections:
                bbox_dict = d["bbox"]
                detections.append(Detection(
                    camera_id=camera_id,
                    frame_id=frame_id,
                    timestamp=timestamp,
                    class_name=d.get("class_name", "person"),
                    confidence=d.get("confidence", 0.9),
                    bbox=BBox(**bbox_dict),
                    model_name=self.model_name,
                    model_version=self.model_version,
                    inference_latency_ms=self.latency_ms
                ))
        else:
            # Generate 1-3 random person detections
            num_dets = random.randint(1, 3)
            for _ in range(num_dets):
                w = random.uniform(0.05, 0.2)
                h = random.uniform(0.1, 0.4)
                x1 = random.uniform(0.1, 0.9 - w)
                y1 = random.uniform(0.1, 0.9 - h)
                
                detections.append(Detection(
                    camera_id=camera_id,
                    frame_id=frame_id,
                    timestamp=timestamp,
                    class_name="person",
                    confidence=random.uniform(0.5, 0.99),
                    bbox=BBox(x1=x1, y1=y1, x2=x1+w, y2=y1+h),
                    model_name=self.model_name,
                    model_version=self.model_version,
                    inference_latency_ms=self.latency_ms
                ))

        return DetectionBatch(
            camera_id=camera_id,
            frame_id=frame_id,
            timestamp=timestamp,
            detections=detections,
            total_inference_ms=self.latency_ms
        )

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "device": "cpu",
            "input_size": 640,
            "confidence_threshold": 0.5
        }
