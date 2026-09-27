"""
IBVAP Dataset Frame Quality Assessment Engine.
Evaluates frame resolution, blur (sharpness), brightness, contrast,
corrupted byte structures, duplicate similarity, and lighting conditions.
"""
from __future__ import annotations

import os
import hashlib
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Tuple
import cv2
import numpy as np
import structlog

logger = structlog.get_logger()


class QualityStatus(str, Enum):
    GOOD = "GOOD"
    LOW_QUALITY = "LOW_QUALITY"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"


class LightingCondition(str, Enum):
    DAY = "DAY"
    NIGHT = "NIGHT"
    LOW_LIGHT = "LOW_LIGHT"
    IR = "IR"


@dataclass
class QualityThresholds:
    min_width: int = 640
    min_height: int = 360
    min_blur_score: float = 30.0         # Laplacian variance
    min_brightness: float = 25.0         # Under-exposure threshold
    max_brightness: float = 235.0        # Over-exposure threshold
    min_contrast: float = 18.0           # Minimum standard deviation of pixels
    duplicate_sim_threshold: float = 0.95 # Normalized similarity threshold


@dataclass
class FrameQualityAssessment:
    status: QualityStatus
    lighting: LightingCondition
    width: int
    height: int
    blur_score: float
    brightness: float
    contrast: float
    is_duplicate: bool
    is_corrupt: bool
    rejection_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["lighting"] = self.lighting.value
        return d


class QualityFilter:
    """
    Evaluates individual frames and rolling sequence windows for dataset curation.
    """

    def __init__(self, thresholds: Optional[QualityThresholds] = None):
        self.thresholds = thresholds or QualityThresholds()
        self._recent_hashes: List[str] = []
        self._recent_gray_small: List[np.ndarray] = []
        self._max_history = 50

    def reset_history(self) -> None:
        self._recent_hashes.clear()
        self._recent_gray_small.clear()

    def assess_frame(
        self,
        frame: Optional[np.ndarray],
        force_lighting: Optional[LightingCondition] = None,
    ) -> FrameQualityAssessment:
        reasons: List[str] = []

        # 1. Corrupt frame check
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return FrameQualityAssessment(
                status=QualityStatus.REJECTED,
                lighting=force_lighting or LightingCondition.DAY,
                width=0,
                height=0,
                blur_score=0.0,
                brightness=0.0,
                contrast=0.0,
                is_duplicate=False,
                is_corrupt=True,
                rejection_reasons=["Corrupt, empty or unreadable image frame."],
            )

        h, w = frame.shape[:2]

        # 2. Resolution check
        if w < self.thresholds.min_width or h < self.thresholds.min_height:
            reasons.append(
                f"Resolution {w}x{h} below minimum threshold {self.thresholds.min_width}x{self.thresholds.min_height}."
            )

        # 3. Convert to grayscale for metrics
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Check for Infrared (IR): All 3 BGR channels nearly identical and low color saturation
            diff_rg = np.abs(frame[:, :, 2].astype(int) - frame[:, :, 1].astype(int))
            diff_gb = np.abs(frame[:, :, 1].astype(int) - frame[:, :, 0].astype(int))
            mean_diff = float(np.mean(diff_rg) + np.mean(diff_gb))
            is_grayscale_look = (mean_diff < 3.0)
        else:
            gray = frame
            is_grayscale_look = True

        # 4. Brightness & Contrast
        brightness = float(np.mean(gray))
        contrast = float(np.std(gray))

        # 5. Sharpness (Laplacian variance)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # Determine Lighting Condition
        if force_lighting:
            lighting = force_lighting
        elif is_grayscale_look and brightness < 120.0:
            lighting = LightingCondition.IR
        elif brightness < 35.0:
            lighting = LightingCondition.NIGHT
        elif brightness < 70.0:
            lighting = LightingCondition.LOW_LIGHT
        else:
            lighting = LightingCondition.DAY

        # 6. Quality Checks
        is_low_quality = False
        if blur_score < self.thresholds.min_blur_score:
            is_low_quality = True
            reasons.append(f"Blur score {blur_score:.1f} below threshold {self.thresholds.min_blur_score:.1f}.")

        if brightness < self.thresholds.min_brightness:
            is_low_quality = True
            reasons.append(f"Under-exposed: brightness {brightness:.1f} below {self.thresholds.min_brightness:.1f}.")
        elif brightness > self.thresholds.max_brightness:
            is_low_quality = True
            reasons.append(f"Over-exposed: brightness {brightness:.1f} above {self.thresholds.max_brightness:.1f}.")

        if contrast < self.thresholds.min_contrast:
            is_low_quality = True
            reasons.append(f"Low contrast: {contrast:.1f} below {self.thresholds.min_contrast:.1f}.")

        # 7. Duplicate / Similarity check against recent window
        is_duplicate = False
        small_gray = cv2.resize(gray, (32, 32))
        for prev_small in self._recent_gray_small:
            # Normalized correlation coefficient
            res = cv2.matchTemplate(small_gray, prev_small, cv2.TM_CCOEFF_NORMED)
            sim = float(res[0][0])
            if sim >= self.thresholds.duplicate_sim_threshold:
                is_duplicate = True
                reasons.append(f"Near-duplicate frame detected (similarity {sim:.3f} >= {self.thresholds.duplicate_sim_threshold}).")
                break

        # Update rolling buffer
        self._recent_gray_small.append(small_gray)
        if len(self._recent_gray_small) > self._max_history:
            self._recent_gray_small.pop(0)

        # 8. Determine final Status
        if w < self.thresholds.min_width or h < self.thresholds.min_height:
            status = QualityStatus.REJECTED
        elif is_duplicate:
            status = QualityStatus.DUPLICATE
        elif is_low_quality:
            status = QualityStatus.LOW_QUALITY
        else:
            status = QualityStatus.GOOD

        return FrameQualityAssessment(
            status=status,
            lighting=lighting,
            width=w,
            height=h,
            blur_score=round(blur_score, 2),
            brightness=round(brightness, 2),
            contrast=round(contrast, 2),
            is_duplicate=is_duplicate,
            is_corrupt=False,
            rejection_reasons=reasons,
        )
