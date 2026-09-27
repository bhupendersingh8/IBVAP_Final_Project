"""
IBVAP — Adaptive Night Vision & Low-Light Enhancement Engine (SIH PS-26187)
============================================================================
Provides multi-stage non-linear contrast enhancement, adaptive gamma stretching,
and bilateral noise suppression for pitch-black, low-light, and monochrome IR
border surveillance cameras.
"""

from __future__ import annotations

from enum import Enum
import time
from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional
import cv2
import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class NightMode(str, Enum):
    DAYLIGHT = "DAYLIGHT"
    LOW_LIGHT = "LOW_LIGHT"
    PITCH_NIGHT = "PITCH_NIGHT"
    INFRARED_MONOCHROME = "INFRARED_MONOCHROME"


@dataclass
class NightEnhancementResult:
    frame: np.ndarray
    is_night: bool
    mode: str  # "DAYLIGHT", "LOW_LIGHT", "PITCH_NIGHT", "INFRARED_MONOCHROME"
    mean_luminance: float
    mean_saturation: float
    contrast: float
    latency_ms: float
    gamma_applied: float = 1.0
    clahe_applied: bool = False

    @property
    def mean_brightness(self) -> float:
        return self.mean_luminance


class NightVisionEnhancer:
    """
    High-speed, adaptive night vision enhancer.
    Combines:
    1. Photometric classification (Luminance + Saturation)
    2. Adaptive Non-Linear Gamma Lookup Table (LUT)
    3. CIE L*a*b* Contrast-Limited Adaptive Histogram Equalization (CLAHE)
    4. Edge-preserving noise suppression
    """

    def __init__(
        self,
        low_light_thresh: float = 75.0,
        pitch_dark_thresh: float = 38.0,
        ir_saturation_thresh: float = 18.0,
        clahe_clip_limit: float = 2.8,
        gamma: float = 0.55,
        enabled: bool = True,
        daylight_thresh: Optional[float] = None,
        pitch_night_thresh: Optional[float] = None
    ):
        if daylight_thresh is not None:
            low_light_thresh = daylight_thresh
        if pitch_night_thresh is not None:
            pitch_dark_thresh = pitch_night_thresh

        self.low_light_thresh = low_light_thresh
        self.pitch_dark_thresh = pitch_dark_thresh
        self.ir_saturation_thresh = ir_saturation_thresh
        self.clahe_clip_limit = clahe_clip_limit
        self.gamma = gamma
        self.enabled = enabled

        # Reusable CLAHE engine in CIE L*a*b* space
        self._clahe = cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=(8, 8))

        # Pre-computed Gamma Look-Up Table (LUT) for microsecond speed
        self._gamma_lut = np.array([
            ((i / 255.0) ** gamma) * 255 for i in range(256)
        ]).astype(np.uint8)

        # Extreme darkness LUT (gamma = 0.42 for pitch night)
        self._extreme_gamma_lut = np.array([
            ((i / 255.0) ** 0.42) * 255 for i in range(256)
        ]).astype(np.uint8)

        logger.info(
            "night_vision_enhancer.initialized",
            low_light_thresh=low_light_thresh,
            pitch_dark_thresh=pitch_dark_thresh,
            gamma=gamma,
            enabled=enabled
        )

    def enhance(self, frame: np.ndarray) -> NightEnhancementResult:
        """
        Evaluates illumination and applies optimal night-vision enhancement.
        If the frame is in broad daylight, passes through unchanged without CPU penalty.
        """
        if not self.enabled or frame is None or frame.size == 0:
            return NightEnhancementResult(
                frame=frame,
                is_night=False,
                mode="DAYLIGHT",
                mean_luminance=100.0,
                mean_saturation=100.0,
                contrast=50.0,
                latency_ms=0.0
            )

        t_start = time.perf_counter()

        # Assess illumination in HSV color space (subsampled for ultra-fast evaluation)
        h, w = frame.shape[:2]
        small_sample = cv2.resize(frame, (min(160, w), min(120, h)))
        hsv_sample = cv2.cvtColor(small_sample, cv2.COLOR_BGR2HSV)
        sat_channel = hsv_sample[:, :, 1]
        val_channel = hsv_sample[:, :, 2]

        mean_lum = float(np.mean(val_channel))
        mean_sat = float(np.mean(sat_channel))
        contrast = float(np.std(val_channel))

        is_ir = mean_sat < self.ir_saturation_thresh
        is_pitch_dark = mean_lum < self.pitch_dark_thresh
        is_low_light = mean_lum < self.low_light_thresh

        # Determine mode
        if is_pitch_dark:
            mode = "PITCH_NIGHT"
            is_night = True
        elif is_ir:
            mode = "INFRARED_MONOCHROME"
            is_night = True
        elif is_low_light:
            mode = "LOW_LIGHT"
            is_night = True
        else:
            mode = "DAYLIGHT"
            is_night = False

        if not is_night:
            elapsed = (time.perf_counter() - t_start) * 1000.0
            return NightEnhancementResult(
                frame=frame,
                is_night=False,
                mode="DAYLIGHT",
                mean_luminance=round(mean_lum, 1),
                mean_saturation=round(mean_sat, 1),
                contrast=round(contrast, 1),
                latency_ms=round(elapsed, 2)
            )

        # Multi-stage Night Vision Enhancement:
        # Stage 1: Adaptive Gamma Lift to reveal deep shadows
        lut = self._extreme_gamma_lut if is_pitch_dark else self._gamma_lut
        lifted = cv2.LUT(frame, lut)

        # Stage 2: Dual-Domain LAB CLAHE
        lab = cv2.cvtColor(lifted, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        l_enhanced = self._clahe.apply(l_channel)

        if is_ir:
            # Monochrome IR camera: equalize L and neutralize chromatic sensor noise
            enhanced = cv2.cvtColor(l_enhanced, cv2.COLOR_GRAY2BGR)
        else:
            enhanced = cv2.cvtColor(cv2.merge([l_enhanced, a_channel, b_channel]), cv2.COLOR_LAB2BGR)

        # Stage 3: Mild high-ISO night sensor noise suppression on severe darkness
        if is_pitch_dark and contrast < 25.0:
            enhanced = cv2.medianBlur(enhanced, 3)

        elapsed = (time.perf_counter() - t_start) * 1000.0

        return NightEnhancementResult(
            frame=enhanced,
            is_night=True,
            mode=mode,
            mean_luminance=round(mean_lum, 1),
            mean_saturation=round(mean_sat, 1),
            contrast=round(contrast, 1),
            latency_ms=round(elapsed, 2),
            gamma_applied=0.42 if is_pitch_dark else self.gamma,
            clahe_applied=True
        )
