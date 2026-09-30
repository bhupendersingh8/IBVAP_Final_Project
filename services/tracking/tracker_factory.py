"""
IBVAP Multi-Object Tracker Factory
==================================
Provides unified instantiation and dynamic runtime switching among:
- 'bytetrack': Two-stage IoU association with low-confidence recovery
- 'botsort': BoT-SORT with Camera Motion Compensation and Kalman filtering
- 'ocsort': Observation-Centric SORT with momentum direction consistency
- 'iou': Lightweight pure-Python fallback IoU tracker
"""

import os
from typing import Dict, Any, Optional
import structlog

from .tracker import MultiObjectTracker
from .bytetrack_adapter import FallbackIoUTracker, ByteTrackAdapter
from .botsort_adapter import BoTSORTAdapter
from .ocsort_adapter import OCSORTAdapter

logger = structlog.get_logger()


class TrackerFactory:
    """
    Factory creating MultiObjectTracker instances based on configuration or environment.
    """

    AVAILABLE_TRACKERS = {
        "bytetrack": ByteTrackAdapter,
        "botsort": BoTSORTAdapter,
        "ocsort": OCSORTAdapter,
        "iou": FallbackIoUTracker,
        "fallback_iou": FallbackIoUTracker,
    }

    @classmethod
    def create_tracker(
        cls,
        tracker_type: Optional[str] = None,
        **kwargs
    ) -> MultiObjectTracker:
        resolved_type = (
            tracker_type
            or os.environ.get("IBVAP_TRACKER_TYPE", "bytetrack")
        ).lower().strip()

        tracker_cls = cls.AVAILABLE_TRACKERS.get(resolved_type)
        if tracker_cls is None:
            logger.warning(
                "Unknown tracker type requested, defaulting to bytetrack",
                requested=resolved_type,
                available=list(cls.AVAILABLE_TRACKERS.keys())
            )
            tracker_cls = ByteTrackAdapter

        logger.info("Initializing multi-object tracker", tracker_type=resolved_type, tracker_class=tracker_cls.__name__)
        return tracker_cls(**kwargs)

    @classmethod
    def list_available_trackers(cls) -> list[str]:
        return list(cls.AVAILABLE_TRACKERS.keys())
