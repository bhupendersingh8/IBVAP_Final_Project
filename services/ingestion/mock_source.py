import cv2
import numpy as np
import time
import threading
from datetime import datetime, timezone
from typing import Optional
import structlog

from .camera_source import CameraSource, CameraHealth, CameraStats
from .frame_buffer import FrameBuffer, CameraFrame

logger = structlog.get_logger()

class MockSource(CameraSource):
    """
    Mock camera source for unit testing. Generates synthetic frames (blank color with text)
    without requiring a real video file or RTSP stream.
    """
    
    def __init__(self, camera_id: str, width: int = 640, height: int = 480, fps: int = 10, total_frames: Optional[int] = None):
        super().__init__(camera_id, {})
        self.width = width
        self.height = height
        self.fps = fps
        self.max_frames = total_frames
        
        self.buffer = FrameBuffer(maxsize=30)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        self._health = CameraHealth.DISCONNECTED
        self._total_frames = 0
        self._last_frame_time: Optional[datetime] = None
        self._error_msg: Optional[str] = None
        
        # Test simulation states
        self._disconnect_until: float = 0
        self._inject_corrupt_next = False

    def simulate_disconnect(self, duration_seconds: float):
        """Simulate a network disconnect for testing."""
        self._disconnect_until = time.time() + duration_seconds
        
    def inject_corrupt_frame(self):
        """Inject an empty frame to simulate corruption."""
        self._inject_corrupt_next = True

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._generate_loop, name=f"MockCam-{self.camera_id}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self._health = CameraHealth.DISCONNECTED

    def get_frame(self) -> Optional[CameraFrame]:
        return self.buffer.get()

    def get_latest_frame(self) -> Optional[CameraFrame]:
        return self.buffer.get_latest()

    def get_stats(self) -> CameraStats:
        return CameraStats(
            camera_id=self.camera_id,
            health=self._health,
            fps_measured=float(self.fps) if self._health == CameraHealth.CONNECTED else 0.0,
            last_frame_at=self._last_frame_time,
            total_frames=self._total_frames,
            dropped_frames=self.buffer.dropped_count,
            reconnect_count=0,
            error_message=self._error_msg
        )

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _generate_loop(self):
        target_time = 1.0 / self.fps
        
        while not self._stop_event.is_set():
            loop_start = time.time()
            
            if time.time() < self._disconnect_until:
                self._health = CameraHealth.ERROR
                self._error_msg = "Simulated network disconnect"
                time.sleep(target_time)
                continue
                
            self._health = CameraHealth.CONNECTED
            self._error_msg = None
            self._total_frames += 1
            now = datetime.now(timezone.utc)
            self._last_frame_time = now
            
            if self._inject_corrupt_next:
                frame = None
                self._inject_corrupt_next = False
            else:
                # Create a simple synthetic frame (grey background, text with frame number)
                frame = np.ones((self.height, self.width, 3), dtype=np.uint8) * 100
                text = f"CAM: {self.camera_id} | FRAME: {self._total_frames}"
                cv2.putText(frame, text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            cam_frame = CameraFrame(
                camera_id=self.camera_id,
                frame_id=self._total_frames,
                frame=frame,
                timestamp=now,
                width=self.width,
                height=self.height
            )
            
            self.buffer.put(cam_frame)
            
            if self.max_frames and self._total_frames >= self.max_frames:
                self.stop()
                break
                
            elapsed = time.time() - loop_start
            if elapsed < target_time:
                time.sleep(target_time - elapsed)
