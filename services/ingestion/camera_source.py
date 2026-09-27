from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from .frame_buffer import CameraFrame

class CameraHealth(Enum):
    CONNECTED = "CONNECTED"
    CONNECTING = "CONNECTING"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"

@dataclass
class CameraStats:
    camera_id: str
    health: CameraHealth
    fps_measured: float
    last_frame_at: Optional[datetime]
    total_frames: int
    dropped_frames: int
    reconnect_count: int
    error_message: Optional[str] = None

class CameraSource(ABC):
    """Abstract interface for all video ingestion sources (RTSP, Mock, Video File)."""
    
    def __init__(self, camera_id: str, config: dict):
        self._camera_id = camera_id
        self._config = config
        
    @property
    def camera_id(self) -> str:
        return self._camera_id

    @abstractmethod
    def start(self) -> None:
        """Start capturing frames in a background thread."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop capturing frames and clean up resources."""
        pass

    @abstractmethod
    def get_frame(self) -> Optional[CameraFrame]:
        """Return the next frame from the buffer, or None if empty."""
        pass
        
    @abstractmethod
    def get_latest_frame(self) -> Optional[CameraFrame]:
        """Return the newest frame and drop older ones. Used for real-time AI processing."""
        pass

    @abstractmethod
    def get_stats(self) -> CameraStats:
        """Return current health and telemetry stats for this camera."""
        pass

    @abstractmethod
    def is_alive(self) -> bool:
        """Check if the ingestion thread is actively running."""
        pass
