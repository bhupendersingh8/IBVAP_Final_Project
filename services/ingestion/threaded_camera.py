"""
Threaded Camera Stream Reader (Non-Blocking Zero-Latency Capture)
================================================================
Decouples camera I/O from the AI inference loop.
Continuously grabs frames in a background thread to prevent cv2.VideoCapture.read()
from blocking the main processing loop and dropping FPS to single digits.
"""

import os
import cv2
import time
import threading
from typing import Optional, Tuple, Union
import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class ThreadedCamera:
    """
    High-Performance Background-Threaded Camera Ingestion.
    Ensures main inference loop never waits on network/camera socket I/O.
    """

    def __init__(self, src: Union[int, str] = 0, name: str = "CAM-01"):
        self.src = src
        self.name = name
        self.stopped = False
        self.frame: Optional[np.ndarray] = None
        self.ret = False
        self._lock = threading.Lock()
        self.fps_measured = 0.0
        self.frame_count = 0
        self._last_fps_time = time.time()
        self._fps_counter = 0

        # Optimization for RTSP streams: Low latency TCP transport and 1-frame buffer
        if isinstance(src, str) and src.startswith("rtsp://"):
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;2000000|timeout;2000000"
            self.cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
        else:
            self.cap = cv2.VideoCapture(src)

        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        # Read initial frame
        if self.cap.isOpened():
            self.ret, self.frame = self.cap.read()
        else:
            self.ret = False
            self.frame = None

        self.thread = threading.Thread(target=self.update, name=f"ThreadedCamera-{name}", daemon=True)

    def start(self) -> "ThreadedCamera":
        if not self.thread.is_alive():
            self.stopped = False
            self.thread.start()
            logger.info("Threaded camera stream started", src=self.src, name=self.name)
        return self

    def update(self) -> None:
        """Background loop reading frames at maximum stream rate."""
        while not self.stopped:
            if not self.cap.isOpened():
                time.sleep(0.01)
                continue

            grabbed = self.cap.grab()
            if grabbed:
                ret, frame = self.cap.retrieve()
                if ret and frame is not None:
                    with self._lock:
                        self.ret = ret
                        self.frame = frame
                        self.frame_count += 1
                        self._fps_counter += 1

                    now = time.time()
                    if now - self._last_fps_time >= 1.0:
                        self.fps_measured = round(self._fps_counter / (now - self._last_fps_time), 1)
                        self._fps_counter = 0
                        self._last_fps_time = now
                else:
                    time.sleep(0.005)
            else:
                time.sleep(0.005)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Non-blocking instant access to the freshest frame."""
        with self._lock:
            if self.frame is not None:
                return self.ret, self.frame.copy()
            return False, None

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Convenience accessor returning just the frame array."""
        with self._lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self) -> None:
        self.stopped = True
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.cap.isOpened():
            self.cap.release()
        logger.info("Threaded camera stream stopped", name=self.name)

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass
