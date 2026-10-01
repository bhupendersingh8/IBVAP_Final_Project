import time
import numpy as np
from typing import Dict, Any
import structlog

from .detection_engine import DetectionEngine
from .schemas import DetectionBatch, Detection, BBox

logger = structlog.get_logger()

# Map COCO classes to standard IBVAP classes
YOLO_CLASS_MAP = {
    'person': 'person',
    'car': 'vehicle',
    'truck': 'vehicle',
    'bus': 'vehicle',
    'motorcycle': 'vehicle',
    'bicycle': 'vehicle',
    # COCO lacks 'pen' & 'watch'; slender cylinders misclassify as 'toothbrush', wristwatches as 'clock'
    'toothbrush': 'equipment',
    'pen': 'equipment',
    'clock': 'equipment',
    'watch': 'equipment',
    # Tactical Weapons & Threats
    'knife': 'weapon',
    'gun': 'weapon',
    'pistol': 'weapon',
    'rifle': 'weapon',
    'grenade': 'weapon',
    'explosive': 'weapon',
}

class YOLOAdapter(DetectionEngine):
    """
    Adapter for Ultralytics YOLOv8.
    Note: YOLOv8 is AGPL-3.0 for open-source use. Proprietary/closed-source 
    commercial deployment requires an Ultralytics Enterprise license.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_path = config.get("model_path", "yolov8n.pt")
        self.device = config.get("device", "cpu")
        self.conf_thresh = config.get("confidence_threshold", 0.25)
        self.input_size = config.get("input_size", 640)
        self.model_name = config.get("model_name", "yolov8n")
        self.model_version = config.get("model_version", "1.0.0")
        
        self._model = None
        
    def load_model(self) -> None:
        import os
        os.environ["YOLO_OFFLINE"] = "True"
        os.environ["YOLO_VERBOSE"] = "False"
        os.environ["ULTRALYTICS_AUTOINSTALL"] = "0"
        logger.info("Loading YOLO model...", path=self.model_path, device=self.device)

        # Ensure CPU-first default and graceful fallback
        try:
            import torch
            torch.set_num_threads(2)
            if self.device and "cuda" in str(self.device).lower() and not torch.cuda.is_available():
                logger.warning("CUDA requested but not available; using CPU runtime fallback")
                self.device = "cpu"
        except Exception:
            self.device = "cpu"

        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError(
                "ultralytics is not installed. Run `pip install ultralytics` "
                "or use MockDetector if testing without AI models."
            )
            
        logger.info("Loading YOLO model...", path=self.model_path, device=self.device)
        # Suppress ultralytics verbose logging
        import logging
        logging.getLogger("ultralytics").setLevel(logging.WARNING)
        
        self._model = YOLO(self.model_path)
        # We don't force self._model.to(device) here, ultralytics handles it in predict()
        logger.info("YOLO model loaded successfully")
        
        try:
            self.warmup(iterations=1)
        except Exception as e:
            if "cuda" in str(self.device).lower():
                logger.warning("CUDA execution unsupported or failed on this device, falling back to CPU", error=str(e))
                self.device = "cpu"
                self.warmup(iterations=1)
            else:
                raise

    def is_loaded(self) -> bool:
        return self._model is not None

    def warmup(self, iterations: int = 1) -> None:
        if not self.is_loaded():
            return
        logger.debug("Warming up model", iterations=iterations)
        dummy_frame = np.zeros((320, 320, 3), dtype=np.uint8)
        for _ in range(iterations):
            self._model.predict(dummy_frame, device=self.device, verbose=False, imgsz=320)

    def detect(self, frame: np.ndarray, camera_id: str, frame_id: int, timestamp) -> DetectionBatch:
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load_model() first.")
            
        start_time = time.time()
        
        # Inference with automatic FP16 half-precision on NVIDIA CUDA GPUs
        use_half = bool(self.device and "cuda" in str(self.device).lower())
        results = self._model.predict(
            frame, 
            device=self.device, 
            half=use_half,
            conf=self.conf_thresh, 
            verbose=False, 
            imgsz=self.input_size
        )
        
        inference_ms = (time.time() - start_time) * 1000
        
        detections = []
        result = results[0]  # We only passed one frame
        
        img_h, img_w = frame.shape[:2]
        
        if result.boxes:
            boxes = result.boxes.xyxyn.cpu().numpy()  # Normalized coordinates [0-1]
            confs = result.boxes.conf.cpu().numpy()
            clss = result.boxes.cls.cpu().numpy()
            
            for box, conf, cls_idx in zip(boxes, confs, clss):
                coco_class_name = self._model.names[int(cls_idx)]
                ibvap_class_name = YOLO_CLASS_MAP.get(coco_class_name, coco_class_name)
                # Calibrate COCO limitation: 'toothbrush' -> 'pen', 'clock' -> 'watch'
                if coco_class_name == "toothbrush":
                    subclass_name = "pen"
                elif coco_class_name == "clock":
                    subclass_name = "watch"
                else:
                    subclass_name = coco_class_name
                    
                x1, y1, x2, y2 = box.tolist()
                
                # Clamp values just in case
                x1, y1 = max(0.0, x1), max(0.0, y1)
                x2, y2 = min(1.0, x2), min(1.0, y2)
                
                # Check for valid box dimensions
                if x1 >= x2 or y1 >= y2:
                    continue
                
                bbox = BBox(x1=x1, y1=y1, x2=x2, y2=y2)
                
                det = Detection(
                    camera_id=camera_id,
                    frame_id=frame_id,
                    timestamp=timestamp,
                    class_name=ibvap_class_name,
                    subclass=subclass_name,
                    confidence=float(conf),
                    bbox=bbox,
                    model_name=self.model_name,
                    model_version=self.model_version,
                    inference_latency_ms=inference_ms
                )
                detections.append(det)

        return DetectionBatch(
            camera_id=camera_id,
            frame_id=frame_id,
            timestamp=timestamp,
            detections=detections,
            total_inference_ms=inference_ms
        )

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "device": self.device,
            "input_size": self.input_size,
            "confidence_threshold": self.conf_thresh
        }
