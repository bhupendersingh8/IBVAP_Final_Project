from typing import Optional, Dict
import structlog
from .camera_source import CameraSource, CameraHealth, CameraStats
from .frame_buffer import CameraFrame

logger = structlog.get_logger()

class CameraManager:
    """Manages multiple camera ingestion sources in a thread-safe manner."""
    
    def __init__(self):
        self._cameras: Dict[str, CameraSource] = {}
        
    def add_camera(self, source: CameraSource) -> None:
        if source.camera_id in self._cameras:
            logger.warning("Overwriting existing camera", camera_id=source.camera_id)
            self.remove_camera(source.camera_id)
        self._cameras[source.camera_id] = source
        logger.info("Camera added to manager", camera_id=source.camera_id)

    def remove_camera(self, camera_id: str) -> None:
        if camera_id in self._cameras:
            source = self._cameras.pop(camera_id)
            source.stop()
            logger.info("Camera removed from manager", camera_id=camera_id)

    def start_all(self) -> None:
        for cid, source in self._cameras.items():
            source.start()

    def stop_all(self) -> None:
        for cid, source in self._cameras.items():
            source.stop()

    def get_frame(self, camera_id: str) -> Optional[CameraFrame]:
        if camera_id in self._cameras:
            return self._cameras[camera_id].get_frame()
        return None

    def get_latest_frame(self, camera_id: str) -> Optional[CameraFrame]:
        if camera_id in self._cameras:
            return self._cameras[camera_id].get_latest_frame()
        return None

    def get_all_stats(self) -> Dict[str, CameraStats]:
        stats = {}
        for cid, source in self._cameras.items():
            stats[cid] = source.get_stats()
        return stats

    def get_health_summary(self) -> dict:
        summary = {
            "total": len(self._cameras),
            "connected": 0,
            "disconnected": 0,
            "error": 0,
            "connecting": 0,
            "unknown": 0
        }
        for cid, source in self._cameras.items():
            health = source.get_stats().health
            if health == CameraHealth.CONNECTED:
                summary["connected"] += 1
            elif health == CameraHealth.DISCONNECTED:
                summary["disconnected"] += 1
            elif health == CameraHealth.ERROR:
                summary["error"] += 1
            elif health == CameraHealth.CONNECTING:
                summary["connecting"] += 1
            else:
                summary["unknown"] += 1
        return summary
