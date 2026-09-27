import os
import cv2
import time
import threading
from datetime import datetime, timezone
from typing import Optional
import structlog

from .camera_source import CameraSource, CameraHealth, CameraStats
from .frame_buffer import FrameBuffer, CameraFrame

logger = structlog.get_logger()

class RTSPSource(CameraSource):
    """
    RTSP Camera Source using OpenCV. 
    Maintains a background thread that continuously reads frames, measures FPS, 
    and handles automatic reconnections gracefully.
    """
    
    def __init__(self, camera_id: str, config: dict):
        super().__init__(camera_id, config)
        self.rtsp_url = config.get("rtsp_url", "")
        self.fps_limit = config.get("fps_limit", 10)
        self.reconnect_delay = config.get("reconnect_delay_seconds", 2.0)
        self.max_reconnect = config.get("max_reconnect_attempts", 0)  # 0 = indefinite auto-reconnect
        
        self.buffer = FrameBuffer(maxsize=config.get("buffer_size", 30))
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # Telemetry
        self._health = CameraHealth.DISCONNECTED
        self._total_frames = 0
        self._reconnect_count = 0
        self._last_frame_time: Optional[datetime] = None
        self._error_msg: Optional[str] = None
        self._fps_measured = 0.0
        self._frame_times = []  # For rolling FPS calculation

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Camera thread already running", camera_id=self.camera_id)
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, name=f"CameraThread-{self.camera_id}", daemon=True)
        self._thread.start()
        logger.info("Camera source started", camera_id=self.camera_id)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        self._health = CameraHealth.DISCONNECTED
        logger.info("Camera source stopped", camera_id=self.camera_id)

    def get_frame(self) -> Optional[CameraFrame]:
        return self.buffer.get()
        
    def get_latest_frame(self) -> Optional[CameraFrame]:
        return self.buffer.get_latest()

    def get_stats(self) -> CameraStats:
        return CameraStats(
            camera_id=self.camera_id,
            health=self._health,
            fps_measured=round(self._fps_measured, 1),
            last_frame_at=self._last_frame_time,
            total_frames=self._total_frames,
            dropped_frames=self.buffer.dropped_count,
            reconnect_count=self._reconnect_count,
            error_message=self._error_msg
        )

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _sanitize_url(self, url: str) -> str:
        """Never log passwords present in RTSP URLs."""
        if "@" in url:
            return f"rtsp://***MASKED***@{url.split('@')[-1]}"
        return url

    def _update_fps(self, now: float):
        self._frame_times.append(now)
        # Keep rolling window of last 20 frames
        if len(self._frame_times) > 20:
            self._frame_times.pop(0)
        if len(self._frame_times) > 1:
            time_diff = self._frame_times[-1] - self._frame_times[0]
            if time_diff > 0:
                self._fps_measured = (len(self._frame_times) - 1) / time_diff

    def _capture_loop(self):
        cap = None
        target_frame_time = 1.0 / self.fps_limit if self.fps_limit > 0 else 0
        
        while not self._stop_event.is_set():
            try:
                self._health = CameraHealth.CONNECTING
                sanitized = self._sanitize_url(self.rtsp_url)
                logger.debug("Connecting to stream", camera_id=self.camera_id, url=sanitized)
                
                # Setup OpenCV VideoCapture: use TCP only for rtsp://; standard options for http://
                if self.rtsp_url.startswith("rtsp://"):
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|timeout;5000000"
                    cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                else:
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;3000000"
                    cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                    if not cap.isOpened():
                        cap = cv2.VideoCapture(self.rtsp_url)
                
                if not cap.isOpened():
                    raise ConnectionError(f"Failed to open video stream at {sanitized}")

                # Minimize internal frame buffering to 1 frame for real-time low latency
                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass
                    
                self._health = CameraHealth.CONNECTED
                self._reconnect_count = 0
                self._error_msg = None
                consecutive_failures = 0
                
                logger.info("Connected to stream", camera_id=self.camera_id)

                # For phone camera or HTTP streams, drain continuously without artificial sleep
                is_phone_or_http = self.camera_id.startswith("PHONE") or self.rtsp_url.startswith("http")
                target_frame_time = 0.0 if is_phone_or_http else (1.0 / self.fps_limit if self.fps_limit > 0 else 0.0)
                
                while not self._stop_event.is_set():
                    loop_start = time.time()
                    ret, frame = cap.read()
                    
                    if not ret or frame is None:
                        consecutive_failures += 1
                        if consecutive_failures < 4:
                            time.sleep(0.02)
                            continue
                        logger.warning("Stream ended or failed to read frame", camera_id=self.camera_id)
                        break
                    consecutive_failures = 0
                        
                    now = datetime.now(timezone.utc)
                    self._total_frames += 1
                    self._last_frame_time = now
                    self._update_fps(time.time())
                    
                    h, w = frame.shape[:2]
                    cam_frame = CameraFrame(
                        camera_id=self.camera_id,
                        frame_id=self._total_frames,
                        frame=frame,
                        timestamp=now,
                        width=w,
                        height=h
                    )
                    self.buffer.put(cam_frame)
                    
                    # Sleep only if rate-limiting is explicitly configured and not a live phone stream
                    if target_frame_time > 0:
                        elapsed = time.time() - loop_start
                        if elapsed < target_frame_time:
                            time.sleep(target_frame_time - elapsed)
                        
            except Exception as e:
                self._health = CameraHealth.ERROR
                self._error_msg = str(e)
                logger.error("Camera connection error", camera_id=self.camera_id, error=self._error_msg)
                
            finally:
                if cap is not None:
                    cap.release()
                    
            if not self._stop_event.is_set():
                self._reconnect_count += 1
                if self.max_reconnect > 0 and self._reconnect_count > self.max_reconnect:
                    logger.error("Max reconnects reached. Suspending camera.", camera_id=self.camera_id)
                    self._health = CameraHealth.ERROR
                    self._stop_event.set()
                    break
                
                backoff = min(self.reconnect_delay * (1.2 ** min(self._reconnect_count - 1, 5)), 5.0)
                logger.info(f"Reconnecting in {backoff:.1f}s...", camera_id=self.camera_id)
                time.sleep(backoff)
