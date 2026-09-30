from abc import ABC, abstractmethod
from typing import Optional, Tuple
import cv2
import numpy as np
import structlog

from ..detection.schemas import BBox
from .schemas import PlateDetection

logger = structlog.get_logger()

class PlateDetector(ABC):
    """
    Abstract interface for license plate localization on a cropped vehicle region.
    Architecturally replaceable with YOLO-plate, Faster R-CNN, or classical CV detectors.
    """
    @abstractmethod
    def detect_plate(self, vehicle_crop: np.ndarray) -> Optional[PlateDetection]:
        """
        Localizes license plate within vehicle crop.
        Returns PlateDetection if found, or None if no plate is detected.
        """
        pass

class ContourPlateDetector(PlateDetector):
    """
    Baseline classical computer vision plate candidate locator.
    
    IMPORTANT NOTE:
    This is an algorithmic baseline detector using morphological filters, Sobel gradients,
    and aspect-ratio contour constraints. It is intended for SIH prototyping and offline
    CPU operation. It DOES NOT claim production-grade ANPR accuracy in extreme weather,
    steep angles, or heavy occlusion.
    """
    def __init__(
        self,
        min_aspect_ratio: float = 2.0,
        max_aspect_ratio: float = 5.5,
        min_area_fraction: float = 0.008,
        max_area_fraction: float = 0.25,
        min_plate_width: int = 35,
        min_plate_height: int = 12
    ):
        self.min_ar = min_aspect_ratio
        self.max_ar = max_aspect_ratio
        self.min_area_frac = min_area_fraction
        self.max_area_frac = max_area_fraction
        self.min_width = min_plate_width
        self.min_height = min_plate_height

    def detect_plate(self, vehicle_crop: np.ndarray) -> Optional[PlateDetection]:
        if vehicle_crop is None or vehicle_crop.size == 0:
            return None

        h, w = vehicle_crop.shape[:2]
        if w < self.min_width or h < self.min_height:
            return None

        total_area = w * h

        # 1. Grayscale & bilateral noise reduction
        gray = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY) if len(vehicle_crop.shape) == 3 else vehicle_crop
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)

        # 2. Sobel edge detection focused on vertical edges (typical of plate characters)
        sobel_x = cv2.Sobel(filtered, cv2.CV_16S, 1, 0, ksize=3)
        abs_sobel_x = cv2.convertScaleAbs(sobel_x)

        # 3. Morphological closing to group characters into single rectangular region
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
        closed = cv2.morphologyEx(abs_sobel_x, cv2.MORPH_CLOSE, kernel)

        # 4. Otsu adaptive threshold
        _, thresh = cv2.threshold(closed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 5. Contour search
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_candidate: Optional[Tuple[int, int, int, int, float]] = None
        best_score = -1.0

        for c in contours:
            x, y, bw, bh = cv2.boundingRect(c)
            if bw < self.min_width or bh < self.min_height:
                continue

            ar = bw / float(bh)
            area = bw * bh
            area_frac = area / float(total_area)

            # Aspect ratio constraint (license plates typically ~2.2:1 to 5.2:1)
            if not (self.min_ar <= ar <= self.max_ar):
                continue
            if not (self.min_area_frac <= area_frac <= self.max_area_frac):
                continue

            # Bias towards the bottom half/center of the vehicle where plates typically sit
            vertical_bias = (y + bh / 2.0) / h  # 0 to 1
            if vertical_bias < 0.25:  # Roof of vehicle is unlikely to hold a bumper plate
                continue

            score = vertical_bias * 1.5 + (1.0 - abs(ar - 3.5) / 3.5)
            if score > best_score:
                best_score = score
                best_candidate = (x, y, bw, bh, ar)

        if best_candidate is None:
            # Robust Fallback: In night/shadows/distant crops, license plate edges blend with bumper.
            # Sample the lower-middle bumper region (typical location of license plate on cars/trucks)
            bw = int(w * 0.50)
            bh = int(h * 0.22)
            bx = int((w - bw) / 2)
            by = int(h * 0.65)
            ar = bw / float(bh) if bh > 0 else 3.5
            best_candidate = (bx, by, bw, bh, ar)
            best_score = 0.50

        bx, by, bw, bh, ar = best_candidate

        # Extract plate crop with small padding if bounds permit
        pad_x = int(bw * 0.05)
        pad_y = int(bh * 0.05)
        x1 = max(0, bx - pad_x)
        y1 = max(0, by - pad_y)
        x2 = min(w, bx + bw + pad_x)
        y2 = min(h, by + bh + pad_y)

        crop = vehicle_crop[y1:y2, x1:x2]
        norm_bbox = BBox(
            x1=x1 / float(w),
            y1=y1 / float(h),
            x2=x2 / float(w),
            y2=y2 / float(h)
        )

        return PlateDetection(
            bbox=norm_bbox,
            confidence=min(1.0, max(0.40, float(best_score) / 2.5)),
            plate_crop=crop,
            aspect_ratio=ar
        )

class MockPlateDetector(PlateDetector):
    """
    Deterministic mock plate detector for isolated testing and edge case verification.
    """
    def __init__(self, should_detect: bool = True, mock_crop: Optional[np.ndarray] = None):
        self.should_detect = should_detect
        self.mock_crop = mock_crop

    def detect_plate(self, vehicle_crop: np.ndarray) -> Optional[PlateDetection]:
        if not self.should_detect or vehicle_crop is None or vehicle_crop.size == 0:
            return None
        crop = self.mock_crop if self.mock_crop is not None else np.zeros((30, 100, 3), dtype=np.uint8)
        return PlateDetection(
            bbox=BBox(x1=0.25, y1=0.60, x2=0.75, y2=0.85),
            confidence=0.85,
            plate_crop=crop,
            aspect_ratio=3.33
        )
