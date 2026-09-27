from abc import ABC, abstractmethod
from typing import List, Optional, Dict

from ..detection.schemas import DetectionBatch
from .schemas import Track, TrackingResult

class MultiObjectTracker(ABC):
    """
    Abstract interface for Multi-Object Tracking algorithms.
    Decouples the tracking logic from the specific implementation (ByteTrack, DeepSORT, etc).
    """

    @abstractmethod
    def update(self, detections: DetectionBatch) -> TrackingResult:
        """
        Takes a new batch of detections for a frame and updates all tracked objects.
        Must return the current active tracks and lifecycle events (new/lost).
        """
        pass

    @abstractmethod
    def get_track(self, track_id: int) -> Optional[Track]:
        """Retrieve a specific track by its ID."""
        pass

    @abstractmethod
    def get_active_tracks(self, camera_id: str) -> List[Track]:
        """Return all currently active tracks for a given camera."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Clear all tracking state (e.g., if a camera reconnects)."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, int]:
        """Return tracking telemetry (active count, total seen, etc)."""
        pass
