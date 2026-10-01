"""
Non-Blocking Asynchronous Threaded Camera Stream (SIH26228 / TCVIAF)
===================================================================
Decouples camera socket / RTSP frame decoding into a background daemon thread.
Ensures cv2.VideoCapture.read() never stalls the main GPU/CPU inference loop.
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
    Non-blocking, background-threaded camera ingestion stream.
    Eliminates cv2.VideoCapture.read() I/O blocking from the main inference loop.
    """

    def __init__(self, src: Union[int, str] = 0, name: str = "CAM-01"):
        self.src = src
        self.name = name
        self.stopped = False
        self.ret = False
        self.frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self.fps_measured = 0.0
        self.frame_count = 0
        self._fps_counter = 0
        self._last_fps_time = time.time()

        if isinstance(src, str) and src.startswith("rtsp://"):
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;2000000|timeout;2000000"
            self.cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
        else:
            self.cap = cv2.VideoCapture(src)

        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        if self.cap.isOpened():
            self.ret, self.frame = self.cap.read()

        self.thread = threading.Thread(target=self.update, name=f"ThreadedCamera-{name}", daemon=True)
        self.thread.start()
        logger.info("ThreadedCamera stream initialized and running in background", src=src, name=name)

    def update(self) -> None:
        """Background thread grabbing frames continuously at native camera rate."""
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
                    time.sleep(0.002)
            else:
                time.sleep(0.002)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Non-blocking instant access to the latest captured frame."""
        with self._lock:
            if self.frame is not None:
                return self.ret, self.frame.copy()
            return False, None

    def get_frame(self) -> Optional[np.ndarray]:
        """Convenience method returning current frame buffer."""
        with self._lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self) -> None:
        self.stopped = True
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap.isOpened():
            self.cap.release()

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass
