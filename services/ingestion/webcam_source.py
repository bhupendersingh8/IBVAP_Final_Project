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

class WebcamSource(CameraSource):
    """
    Local USB / Laptop Webcam Source using OpenCV VideoCapture(device_index).
    Provides a low-latency, phone-free development and local testing adapter.
    """
    
    def __init__(self, camera_id: str = "WEBCAM-01", config: Optional[dict] = None):
        cfg = config or {}
        super().__init__(camera_id, cfg)
        self.device_index = cfg.get("device_index", 0)
        self.fps_limit = cfg.get("fps_limit", 30)
        self.width = cfg.get("width", 640)
        self.height = cfg.get("height", 480)
        
        self.buffer = FrameBuffer(maxsize=cfg.get("buffer_size", 20))
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Zero-Disk-I/O RAM Frame Bus (Decoupled live stream publishing directly from capture thread)
        try:
            from .shared_frame_buffer import SharedFrameWriter
            self.shm_writer: Optional[SharedFrameWriter] = SharedFrameWriter(self.camera_id)
        except Exception:
            self.shm_writer = None
        
        # Telemetry
        self._health = CameraHealth.DISCONNECTED
        self._total_frames = 0
        self._reconnect_count = 0
        self._last_frame_time: Optional[datetime] = None
        self._error_msg: Optional[str] = None
        self._fps_measured = 0.0
        self._frame_times = []

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, name=f"WebcamThread-{self.camera_id}", daemon=True)
        self._thread.start()
        logger.info("Webcam source started", camera_id=self.camera_id, device=self.device_index)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        if hasattr(self, 'shm_writer') and self.shm_writer is not None:
            try:
                self.shm_writer.close()
            except Exception:
                pass
        self._health = CameraHealth.DISCONNECTED
        logger.info("Webcam source stopped", camera_id=self.camera_id)

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

    def _update_fps(self, now: float):
        self._frame_times.append(now)
        if len(self._frame_times) > 20:
            self._frame_times.pop(0)
        if len(self._frame_times) > 1:
            time_diff = self._frame_times[-1] - self._frame_times[0]
            if time_diff > 0:
                self._fps_measured = (len(self._frame_times) - 1) / time_diff

    def _capture_loop(self):
        target_frame_time = 1.0 / self.fps_limit if self.fps_limit > 0 else 0
        cap = None
        
        while not self._stop_event.is_set():
            try:
                self._health = CameraHealth.CONNECTING
                import sys
                backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if sys.platform == "win32" else [cv2.CAP_ANY]
                
                indices_to_try = [self.device_index]
                for alt_idx in [0, 1, 2]:
                    if alt_idx not in indices_to_try:
                        indices_to_try.append(alt_idx)
                
                cap = None
                opened_idx = None
                for b_end in backends:
                    for idx in indices_to_try:
                        try:
                            test_cap = cv2.VideoCapture(idx, b_end)
                            if test_cap.isOpened():
                                try:
                                    test_cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                                    test_cap.set(cv2.CAP_PROP_FPS, float(self.fps_limit or 30))
                                except Exception:
                                    pass
                                if self.width and self.height:
                                    test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                                    test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                                ret, test_frame = test_cap.read()
                                if ret and test_frame is not None:
                                    cap = test_cap
                                    opened_idx = idx
                                    break
                            test_cap.release()
                        except Exception:
                            pass
                    if cap is not None:
                        break
                
                if cap is None:
                    raise ConnectionError(f"Failed to open any webcam device among {indices_to_try}")
                
                self._health = CameraHealth.CONNECTED
                self._reconnect_count = 0
                self._error_msg = None
                logger.info("Webcam connected successfully", camera_id=self.camera_id, device=opened_idx)

                consecutive_drops = 0
                while not self._stop_event.is_set():
                    loop_start = time.time()
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        consecutive_drops += 1
                        logger.warning("Webcam frame drop", camera_id=self.camera_id, drops=consecutive_drops)
                        if consecutive_drops >= 3:
                            logger.error("Webcam exceeded max frame drops, reconnecting...", camera_id=self.camera_id)
                            break
                        time.sleep(0.05)
                        continue
                    consecutive_drops = 0

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

                    # Decoupled Stream Delivery: Publish directly to SharedMemory at capture rate
                    if self.shm_writer is not None:
                        try:
                            ok, enc_buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                            if ok:
                                self.shm_writer.write_frame(enc_buf.tobytes())
                        except Exception:
                            pass

                    elapsed = time.time() - loop_start
                    if elapsed < target_frame_time:
                        time.sleep(target_frame_time - elapsed)

            except Exception as e:
                self._health = CameraHealth.ERROR
                self._error_msg = str(e)
                self._reconnect_count += 1
                logger.warning("Webcam error, retrying in 3s", camera_id=self.camera_id, error=str(e))
                time.sleep(3.0)
            finally:
                if cap is not None:
                    cap.release()
