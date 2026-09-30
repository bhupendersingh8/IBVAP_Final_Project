import queue
import time
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class CameraFrame:
    camera_id: str
    frame_id: int
    frame: Any  # numpy array (cv2 image)
    timestamp: datetime
    width: int
    height: int

class FrameBuffer:
    """Thread-safe bounded frame buffer to prevent memory leaks if processing is slow."""
    
    def __init__(self, maxsize: int = 30):
        self._queue = queue.Queue(maxsize=maxsize)
        self.dropped_count = 0
        
    def put(self, frame: CameraFrame) -> bool:
        """Put a frame, drop the oldest if full. Non-blocking."""
        try:
            self._queue.put_nowait(frame)
            return True
        except queue.Full:
            # Drop the oldest frame to make room
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(frame)
                self.dropped_count += 1
                return False
            except (queue.Empty, queue.Full):
                return False
                
    def get(self) -> Optional[CameraFrame]:
        """Get the next frame. Non-blocking."""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None
            
    def get_latest(self) -> Optional[CameraFrame]:
        """Drain the queue and return ONLY the newest frame. Good for real-time skipping."""
        latest = None
        while True:
            try:
                latest = self._queue.get_nowait()
            except queue.Empty:
                break
        return latest

    def size(self) -> int:
        return self._queue.qsize()
