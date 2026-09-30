"""
Camera health monitoring — PHASE 16.
Tracks per-camera state: ONLINE / DEGRADED / OFFLINE / RECONNECTING.
"""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional
import structlog

logger = structlog.get_logger()


class CameraHealthState(Enum):
    ONLINE = "ONLINE"           # Frames arriving normally
    DEGRADED = "DEGRADED"       # Frames arriving but FPS is below threshold
    OFFLINE = "OFFLINE"         # No frames received beyond timeout
    RECONNECTING = "RECONNECTING"  # Attempting reconnect


@dataclass
class CameraHealth:
    camera_id: str
    state: CameraHealthState = CameraHealthState.OFFLINE
    fps: float = 0.0
    last_frame_at: Optional[datetime] = None
    reconnect_count: int = 0
    error_count: int = 0
    frames_received: int = 0
    frames_dropped: int = 0
    state_changed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict:
        return {
            "camera_id": self.camera_id,
            "state": self.state.value,
            "fps": round(self.fps, 2),
            "last_frame_at": self.last_frame_at.isoformat() if self.last_frame_at else None,
            "reconnect_count": self.reconnect_count,
            "error_count": self.error_count,
            "frames_received": self.frames_received,
            "frames_dropped": self.frames_dropped,
            "state_changed_at": self.state_changed_at.isoformat(),
        }


class CameraHealthMonitor:
    """
    Tracks health state for each registered camera.
    Thread-safe for single-process use (asyncio-compatible).
    """
    OFFLINE_TIMEOUT_SECONDS = 10.0   # No frame → OFFLINE
    DEGRADED_FPS_THRESHOLD = 3.0     # FPS below this → DEGRADED

    def __init__(self):
        self._cameras: Dict[str, CameraHealth] = {}

    def register(self, camera_id: str) -> None:
        if camera_id not in self._cameras:
            self._cameras[camera_id] = CameraHealth(camera_id=camera_id)
            logger.info("Camera registered for health monitoring", camera_id=camera_id)

    def _set_state(self, health: CameraHealth, new_state: CameraHealthState) -> None:
        if health.state != new_state:
            logger.info(
                "Camera health state change",
                camera_id=health.camera_id,
                old=health.state.value,
                new=new_state.value,
            )
            health.state = new_state
            health.state_changed_at = datetime.now(timezone.utc)

    def update(
        self,
        camera_id: str,
        frame_received: bool,
        fps: float = 0.0,
        dropped: bool = False,
    ) -> CameraHealthState:
        if camera_id not in self._cameras:
            self.register(camera_id)
        health = self._cameras[camera_id]
        now = datetime.now(timezone.utc)

        if frame_received:
            health.frames_received += 1
            health.last_frame_at = now
            health.fps = fps
            if fps < self.DEGRADED_FPS_THRESHOLD and fps > 0:
                self._set_state(health, CameraHealthState.DEGRADED)
            else:
                self._set_state(health, CameraHealthState.ONLINE)
        else:
            if dropped:
                health.frames_dropped += 1
            # Check timeout
            if health.last_frame_at is not None:
                elapsed = (now - health.last_frame_at).total_seconds()
                if elapsed > self.OFFLINE_TIMEOUT_SECONDS:
                    if health.state != CameraHealthState.RECONNECTING:
                        self._set_state(health, CameraHealthState.OFFLINE)

        return health.state

    def mark_reconnecting(self, camera_id: str) -> None:
        if camera_id not in self._cameras:
            self.register(camera_id)
        health = self._cameras[camera_id]
        health.reconnect_count += 1
        self._set_state(health, CameraHealthState.RECONNECTING)

    def mark_error(self, camera_id: str) -> None:
        if camera_id in self._cameras:
            self._cameras[camera_id].error_count += 1

    def get_health(self, camera_id: str) -> Optional[Dict]:
        if camera_id in self._cameras:
            return self._cameras[camera_id].to_dict()
        return None

    def get_all_health(self) -> Dict[str, Dict]:
        return {cid: h.to_dict() for cid, h in self._cameras.items()}


# Module-level singleton — shared across inference worker and health API
camera_health_monitor = CameraHealthMonitor()
