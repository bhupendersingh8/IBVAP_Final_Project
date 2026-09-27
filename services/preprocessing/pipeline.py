"""
IBVAP — Preprocessing Pipeline
=================================
Combines :class:`~services.preprocessing.quality_assessor.QualityAssessor`
and :class:`~services.preprocessing.clahe_enhancer.CLAHEEnhancer` into a
single, composable processing step that precedes the detector.

Behaviour
---------
1. Assess frame quality → produce :class:`FrameQuality`.
2. If ``quality.drop_frame`` is ``True``: return the frame *as-is* together
   with the quality report.  The caller can check ``quality.drop_frame`` and
   skip detection/tracking for that frame.
3. Otherwise: pass the frame through the enhancer (which itself checks
   ``quality.needs_enhancement`` before doing anything).
4. Return ``(processed_frame, quality_report)``.

Statistics
----------
Call :meth:`PreprocessingPipeline.get_stats` at any time to retrieve
cumulative counters for monitoring and dashboards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

import numpy as np
import structlog

from services.preprocessing.clahe_enhancer import CLAHEEnhancer
from services.preprocessing.quality_assessor import FrameQuality, QualityAssessor

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class PreprocessingPipeline:
    """
    Ordered preprocessing pipeline: quality assessment → CLAHE enhancement.

    Parameters
    ----------
    quality_assessor:
        Configured :class:`QualityAssessor` instance.
    enhancer:
        Configured :class:`CLAHEEnhancer` instance.
    enabled:
        When ``False``, :meth:`process` returns the original frame and a
        quality report without applying any enhancement.  Assessment still
        runs so callers can act on the quality metadata.  Default: ``True``.
    """

    def __init__(
        self,
        quality_assessor: QualityAssessor,
        enhancer: CLAHEEnhancer,
        enabled: bool = True,
    ) -> None:
        self._assessor = quality_assessor
        self._enhancer = enhancer
        self._enabled = enabled

        # Counters
        self._total_frames: int = 0
        self._enhanced_frames: int = 0
        self._dropped_frames: int = 0

        logger.info(
            "preprocessing_pipeline.initialized",
            enabled=enabled,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, frame: np.ndarray) -> Tuple[np.ndarray, FrameQuality]:
        """
        Assess and (conditionally) enhance a single video frame.

        Parameters
        ----------
        frame:
            BGR or greyscale ``uint8`` numpy array as produced by OpenCV.

        Returns
        -------
        processed_frame:
            The (possibly enhanced) frame, or the original frame if the
            pipeline is disabled, enhancement was not needed, or the frame
            was flagged for dropping.
        quality:
            The :class:`FrameQuality` report produced during assessment.
            Callers **must** check ``quality.drop_frame`` and decide whether
            to pass the returned frame downstream.
        """
        self._total_frames += 1

        quality = self._assessor.assess(frame)

        if quality.drop_frame:
            self._dropped_frames += 1
            logger.debug(
                "preprocessing_pipeline.frame_dropped",
                brightness=round(quality.brightness, 2),
                blur_score=round(quality.blur_score, 2),
                quality_category=quality.quality_category,
                total_dropped=self._dropped_frames,
            )
            # Return early — do not attempt enhancement on an unusable frame.
            return frame, quality

        if not self._enabled:
            return frame, quality

        enhanced = self._enhancer.enhance(frame, quality)

        if enhanced is not frame:
            # The enhancer returned a new array → enhancement was applied.
            self._enhanced_frames += 1

        logger.debug(
            "preprocessing_pipeline.processed",
            quality_category=quality.quality_category,
            needs_enhancement=quality.needs_enhancement,
            was_enhanced=(enhanced is not frame),
            total_frames=self._total_frames,
            enhanced_frames=self._enhanced_frames,
            dropped_frames=self._dropped_frames,
        )

        return enhanced, quality

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """
        Return a snapshot of pipeline processing counters.

        Returns
        -------
        dict
            Keys:

            * ``"total_frames"`` — total frames passed to :meth:`process`.
            * ``"enhanced_frames"`` — frames where CLAHE was applied.
            * ``"dropped_frames"`` — frames flagged as unusable.
            * ``"passed_frames"`` — frames passed downstream without dropping.
            * ``"enhancement_rate"`` — ratio of enhanced to passed frames
              (``0.0`` when no frames have been passed).
            * ``"drop_rate"`` — ratio of dropped to total frames.
            * ``"pipeline_enabled"`` — current ``enabled`` flag value.
        """
        passed = self._total_frames - self._dropped_frames
        enhancement_rate = (
            self._enhanced_frames / passed if passed > 0 else 0.0
        )
        drop_rate = (
            self._dropped_frames / self._total_frames
            if self._total_frames > 0
            else 0.0
        )
        return {
            "total_frames": self._total_frames,
            "enhanced_frames": self._enhanced_frames,
            "dropped_frames": self._dropped_frames,
            "passed_frames": passed,
            "enhancement_rate": round(enhancement_rate, 4),
            "drop_rate": round(drop_rate, 4),
            "pipeline_enabled": self._enabled,
        }
