"""
IBVAP — CLAHE Frame Enhancer
==============================
Applies Contrast-Limited Adaptive Histogram Equalisation (CLAHE) to video
frames that the :class:`~services.preprocessing.quality_assessor.QualityAssessor`
has flagged as needing enhancement.

Design decisions
----------------
* CLAHE is applied only when :attr:`FrameQuality.needs_enhancement` is
  ``True`` — it is **never** applied blindly to every frame.  This avoids
  degrading already-good frames and saves CPU cycles.
* For colour frames, CLAHE is applied **only to the L channel** of the
  CIE L*a*b* colour space.  This preserves hue and saturation while lifting
  local luminance, which is the correct approach for surveillance footage.
* For greyscale frames, CLAHE is applied directly to the single channel.
* Enhancement can be disabled globally via the ``enabled`` constructor flag.
* Latency is measured per call and emitted at DEBUG level via structlog.
"""

from __future__ import annotations

import time

import cv2
import numpy as np
import structlog

from services.preprocessing.quality_assessor import FrameQuality

logger = structlog.get_logger(__name__)


class CLAHEEnhancer:
    """
    CLAHE-based frame contrast enhancer.

    Parameters
    ----------
    clip_limit:
        Threshold for contrast limiting.  Higher values give more contrast
        but risk amplifying noise.  Default: ``2.0``.
    tile_grid_size:
        Size of the grid for histogram equalisation, expressed as
        ``(cols, rows)``.  Default: ``(8, 8)``.
    enabled:
        Master switch.  When ``False``, :meth:`enhance` always returns the
        original frame unchanged, regardless of quality flags.
        Default: ``True``.
    """

    def __init__(
        self,
        clip_limit: float = 2.0,
        tile_grid_size: tuple[int, int] = (8, 8),
        enabled: bool = True,
    ) -> None:
        self._clip_limit = clip_limit
        self._tile_grid_size = tile_grid_size
        self._enabled = enabled

        # Pre-create the CLAHE object once — it is reusable across frames.
        self._clahe = cv2.createCLAHE(
            clipLimit=clip_limit,
            tileGridSize=tile_grid_size,
        )

        logger.info(
            "clahe_enhancer.initialized",
            clip_limit=clip_limit,
            tile_grid_size=tile_grid_size,
            enabled=enabled,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enhance(self, frame: np.ndarray, quality: FrameQuality) -> np.ndarray:
        """
        Optionally apply CLAHE to *frame* based on the *quality* report.

        Parameters
        ----------
        frame:
            BGR or greyscale ``uint8`` numpy array as produced by OpenCV.
        quality:
            Quality report for *frame* as returned by
            :class:`~services.preprocessing.quality_assessor.QualityAssessor`.

        Returns
        -------
        np.ndarray
            Enhanced frame (new array) when enhancement was applied, or the
            **original frame object** unchanged when enhancement was skipped.
            Callers must not assume the returned array is a copy.
        """
        if not self._enabled:
            logger.debug("clahe_enhancer.skipped", reason="disabled")
            return frame

        if not quality.needs_enhancement:
            logger.debug(
                "clahe_enhancer.skipped",
                reason="enhancement_not_needed",
                quality_category=quality.quality_category,
            )
            return frame

        t_start = time.perf_counter()

        if frame.ndim == 2 or (frame.ndim == 3 and frame.shape[2] == 1):
            enhanced = self._enhance_gray(frame)
        else:
            enhanced = self._enhance_color(frame)

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        logger.debug(
            "clahe_enhancer.enhanced",
            quality_category=quality.quality_category,
            clip_limit=self._clip_limit,
            tile_grid_size=self._tile_grid_size,
            elapsed_ms=round(elapsed_ms, 3),
        )

        return enhanced

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _enhance_gray(self, frame: np.ndarray) -> np.ndarray:
        """Apply CLAHE to a single-channel (greyscale) frame."""
        gray = frame if frame.ndim == 2 else frame[:, :, 0]
        equalized = self._clahe.apply(gray)
        if frame.ndim == 3:
            return equalized[:, :, np.newaxis]
        return equalized

    def _enhance_color(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE to the L channel of the LAB representation of *frame*.

        Steps
        -----
        1. Convert BGR → LAB.
        2. Apply CLAHE to the L channel only.
        3. Convert LAB → BGR.
        """
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        l_equalized = self._clahe.apply(l_channel)
        lab_enhanced = cv2.merge([l_equalized, a_channel, b_channel])
        return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
