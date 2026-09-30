import cv2
import numpy as np
from dataclasses import dataclass
from typing import Tuple
import structlog
import time

logger = structlog.get_logger()

@dataclass
class FrameQuality:
    brightness: float
    contrast: float
    blur_score: float
    quality_category: str  # 'good', 'low_light', 'blurry'
    needs_enhancement: bool
    drop_frame: bool

class QualityAssessor:
    """Evaluates video frame quality (brightness, contrast, blur) to decide if enhancement is needed."""
    
    def __init__(self, low_light_thresh=80.0, blur_thresh=15.0):
        self.low_light_thresh = low_light_thresh
        self.blur_thresh = blur_thresh

    def assess(self, frame: np.ndarray) -> FrameQuality:
        # Convert to grayscale for analysis
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        brightness = np.mean(gray)
        contrast = np.std(gray)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

        needs_enhancement = brightness < self.low_light_thresh
        drop_frame = blur_score < (self.blur_thresh / 2) and brightness < (self.low_light_thresh / 2)
        
        category = "good"
        if drop_frame:
            category = "unusable"
        elif needs_enhancement:
            category = "low_light"
        elif blur_score < self.blur_thresh:
            category = "blurry"

        return FrameQuality(
            brightness=brightness,
            contrast=contrast,
            blur_score=blur_score,
            quality_category=category,
            needs_enhancement=needs_enhancement,
            drop_frame=drop_frame
        )

class CLAHEEnhancer:
    """Enhances low-light or low-contrast frames using CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
    
    def __init__(self, clip_limit=2.0, tile_grid_size=(8, 8), enabled=True):
        self.enabled = enabled
        self.clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)

    def enhance(self, frame: np.ndarray, quality: FrameQuality) -> np.ndarray:
        if not self.enabled or not quality.needs_enhancement:
            return frame

        start_time = time.time()
        
        if len(frame.shape) == 3:
            # Convert BGR to LAB color space
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)
            
            # Apply CLAHE only to the L (Lightness) channel
            cl = self.clahe.apply(l_channel)
            
            # Merge back and convert to BGR
            merged = cv2.merge((cl, a, b))
            enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        else:
            enhanced = self.clahe.apply(frame)

        latency = (time.time() - start_time) * 1000
        logger.debug("Applied CLAHE enhancement", latency_ms=round(latency, 2))
        
        return enhanced

class PreprocessingPipeline:
    """Combines Quality Assessment and Enhancement into a single pipeline."""
    
    def __init__(self, assessor: QualityAssessor, enhancer: CLAHEEnhancer, enabled=True):
        self.assessor = assessor
        self.enhancer = enhancer
        self.enabled = enabled
        
        self.stats = {
            "total_frames": 0,
            "enhanced_frames": 0,
            "dropped_frames": 0
        }

    def process(self, frame: np.ndarray) -> Tuple[np.ndarray, FrameQuality]:
        self.stats["total_frames"] += 1
        
        if not self.enabled:
            dummy_q = FrameQuality(128.0, 50.0, 100.0, 'good', False, False)
            return frame, dummy_q

        quality = self.assessor.assess(frame)
        
        if quality.drop_frame:
            self.stats["dropped_frames"] += 1
            return frame, quality
            
        enhanced_frame = self.enhancer.enhance(frame, quality)
        if quality.needs_enhancement:
            self.stats["enhanced_frames"] += 1
            
        return enhanced_frame, quality
        
    def get_stats(self) -> dict:
        return self.stats.copy()
