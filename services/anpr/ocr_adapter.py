from abc import ABC, abstractmethod
import re
import time
from typing import Optional, List, Tuple
import cv2
import numpy as np
import structlog

from .schemas import OCRResult

logger = structlog.get_logger()

def normalize_plate_text(raw_text: str) -> str:
    """
    Conservatively normalizes license plate text.
    - Converts to uppercase.
    - Strips whitespace and non-alphanumeric punctuation.
    - DOES NOT invent missing characters or make speculative substitutions.
    """
    if not raw_text:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_text.upper())
    return cleaned

class OCREngine(ABC):
    """
    Abstract interface for license plate OCR.
    Permits hot-swapping between EasyOCR, Tesseract, PaddleOCR, or custom models.
    """
    @abstractmethod
    def read_plate(self, plate_crop: np.ndarray) -> OCRResult:
        """
        Extracts plate text from cropped plate image.
        Returns OCRResult with raw_text, normalized_text, confidence, and status.
        """
        pass

    def normalize_plate_text(self, raw_text: str) -> str:
        return normalize_plate_text(raw_text)

class EasyOCREngine(OCREngine):
    """
    EasyOCR implementation (Apache-2.0).
    Runs CPU-optimized English alphanumeric recognition with blur and size pre-checks.
    """
    def __init__(
        self, 
        languages: Optional[List[str]] = None, 
        min_confidence: float = 0.45,
        blur_threshold: float = 12.0
    ):
        self.languages = languages or ["en"]
        self.min_confidence = min_confidence
        self.blur_threshold = blur_threshold
        self._reader = None

    def _ensure_reader(self):
        if self._reader is None:
            try:
                import easyocr
                logger.info("Initializing EasyOCR reader (CPU mode)...")
                # Suppress easyocr debug logs
                self._reader = easyocr.Reader(self.languages, gpu=False, verbose=False)
                logger.info("EasyOCR reader initialized successfully")
            except (ImportError, ModuleNotFoundError):
                logger.warning("EasyOCR is not installed. Defaulting OCR results to UNREADABLE.")
                self._reader = False

    def read_plate(self, plate_crop: np.ndarray) -> OCRResult:
        t0 = time.time()
        if plate_crop is None or plate_crop.size == 0:
            return OCRResult(
                raw_text="",
                normalized_text="",
                confidence=0.0,
                processing_time_ms=0.0,
                status="UNREADABLE"
            )

        self._ensure_reader()
        if self._reader is False:
            return OCRResult(
                raw_text="",
                normalized_text="",
                confidence=0.0,
                processing_time_ms=round((time.time() - t0) * 1000, 2),
                status="UNREADABLE"
            )

        h, w = plate_crop.shape[:2]
        if w < 30 or h < 10:
            return OCRResult(
                raw_text="",
                normalized_text="",
                confidence=0.0,
                processing_time_ms=(time.time() - t0) * 1000,
                status="UNREADABLE"
            )

        # Pre-check: Blur check via Laplacian variance
        gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY) if len(plate_crop.shape) == 3 else plate_crop
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score < self.blur_threshold:
            # Extreme blur: Do not hallucinate or guess characters
            return OCRResult(
                raw_text="",
                normalized_text="",
                confidence=0.0,
                processing_time_ms=(time.time() - t0) * 1000,
                status="UNREADABLE"
            )

        self._ensure_reader()

        try:
            # Pre-processing: Dynamic CLAHE and upscale for border night/low-light plate readability
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 4))
            enhanced_gray = clahe.apply(gray)
            
            # Upscale if plate resolution is low (improves character segmentation)
            if h < 60 or w < 160:
                scale = max(2.0, 160.0 / w)
                enhanced_gray = cv2.resize(enhanced_gray, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

            # Read text with EasyOCR
            results = self._reader.readtext(
                enhanced_gray,
                allowlist="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                paragraph=False,
                detail=1
            )
            if not results:
                # Fallback to original gray
                results = self._reader.readtext(
                    gray,
                    allowlist="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                    paragraph=False,
                    detail=1
                )
        except Exception as e:
            logger.warning("OCR processing error", error=str(e))
            return OCRResult(
                raw_text="",
                normalized_text="",
                confidence=0.0,
                processing_time_ms=(time.time() - t0) * 1000,
                status="UNREADABLE"
            )

        t_ms = (time.time() - t0) * 1000

        if not results:
            return OCRResult(
                raw_text="",
                normalized_text="",
                confidence=0.0,
                processing_time_ms=t_ms,
                status="UNREADABLE"
            )

        # Combine text segments sorted left-to-right
        # results format: [ (bbox, text, confidence), ... ]
        sorted_results = sorted(results, key=lambda r: r[0][0][0])
        combined_raw = " ".join(r[1] for r in sorted_results)
        normalized = normalize_plate_text(combined_raw)

        # Average confidence of detected segments
        confidences = [float(r[2]) for r in sorted_results]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        if not normalized or len(normalized) < 3:
            return OCRResult(
                raw_text=combined_raw,
                normalized_text="",
                confidence=avg_conf,
                processing_time_ms=t_ms,
                status="UNREADABLE"
            )

        status = "SUCCESS" if avg_conf >= self.min_confidence else "LOW_CONFIDENCE"

        return OCRResult(
            raw_text=combined_raw,
            normalized_text=normalized,
            confidence=avg_conf,
            processing_time_ms=t_ms,
            status=status
        )

class MockOCREngine(OCREngine):
    """
    Deterministic mock OCR engine for automated testing and edge case simulation.
    """
    def __init__(
        self,
        mock_text: str = "DL01AB1234",
        confidence: float = 0.92,
        status: str = "SUCCESS",
        mock_conf: Optional[float] = None
    ):
        self.mock_text = mock_text
        self.confidence = mock_conf if mock_conf is not None else confidence
        self.status = status

    def read_plate(self, plate_crop: np.ndarray) -> OCRResult:
        if self.status == "UNREADABLE":
            return OCRResult(
                raw_text="",
                normalized_text="",
                confidence=0.0,
                processing_time_ms=5.0,
                status="UNREADABLE"
            )
        return OCRResult(
            raw_text=self.mock_text,
            normalized_text=normalize_plate_text(self.mock_text),
            confidence=self.confidence,
            processing_time_ms=12.0,
            status=self.status
        )
