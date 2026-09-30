"""
IBVAP Canonical Source Adapters
================================
Grand Finale Master Architecture - Section 3
Standardizes all video sources into an identical, immutable FramePacket data contract.
No downstream model or pipeline stage depends directly on camera hardware or transport protocol.
"""
from __future__ import annotations

import os
import cv2
import time
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union
import structlog
import numpy as np

from .frame_packet import FramePacket, SourceType
from .camera_source import CameraSource, CameraHealth, CameraStats
from .frame_buffer import CameraFrame
from .rtsp_security import mask_rtsp_url

logger = structlog.get_logger()


class BaseSourceAdapter(CameraSource):
    """
    Abstract Base Source Adapter.
    Unifies all camera protocols/sources and outputs canonical FramePackets.
    Maintains 100% backward compatibility with CameraSource / CameraFrame.
    """
    def __init__(self, camera_id: str, source_type: SourceType, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        super().__init__(camera_id, cfg)
        self._source_type = source_type
        self._total_packets = 0
        self._last_packet_time: Optional[datetime] = None
        self._health = CameraHealth.DISCONNECTED
        self._error_msg: Optional[str] = None
        self._reconnect_count = 0
        self._fps_measured = 0.0
        self._frame_times: list = []
        self._last_capture_latency_ms = 0.0

    @property
    def source_type(self) -> SourceType:
        return self._source_type

    @abstractmethod
    def get_next_packet(self) -> Optional[FramePacket]:
        """Return the next canonical FramePacket from the bounded buffer."""
        pass

    @abstractmethod
    def get_latest_packet(self) -> Optional[FramePacket]:
        """Return the newest canonical FramePacket, dropping older frames for real-time inference."""
        pass

    def get_frame(self) -> Optional[CameraFrame]:
        """Backward-compatible access returning CameraFrame."""
        pkt = self.get_next_packet()
        if pkt is None:
            return None
        return CameraFrame(
            camera_id=pkt.camera_id,
            frame_id=pkt.frame_id,
            frame=pkt.raw_bgr,
            timestamp=datetime.fromtimestamp(pkt.timestamp, tz=timezone.utc),
            width=pkt.width,
            height=pkt.height
        )

    def get_latest_frame(self) -> Optional[CameraFrame]:
        """Backward-compatible access returning newest CameraFrame."""
        pkt = self.get_latest_packet()
        if pkt is None:
            return None
        return CameraFrame(
            camera_id=pkt.camera_id,
            frame_id=pkt.frame_id,
            frame=pkt.raw_bgr,
            timestamp=datetime.fromtimestamp(pkt.timestamp, tz=timezone.utc),
            width=pkt.width,
            height=pkt.height
        )

    def get_stats(self) -> CameraStats:
        return CameraStats(
            camera_id=self.camera_id,
            health=self._health,
            fps_measured=round(self._fps_measured, 1),
            last_frame_at=self._last_packet_time,
            total_frames=self._total_packets,
            dropped_frames=getattr(self, "_dropped_count", 0),
            reconnect_count=self._reconnect_count,
            error_message=self._error_msg,
            capture_latency_ms=round(self._last_capture_latency_ms, 2),
            queue_depth=getattr(self, "_packet_buffer_size", 0)
        )

    def _update_fps(self, now: float) -> None:
        self._frame_times.append(now)
        if len(self._frame_times) > 20:
            self._frame_times.pop(0)
        if len(self._frame_times) > 1:
            time_diff = self._frame_times[-1] - self._frame_times[0]
            if time_diff > 0:
                self._fps_measured = (len(self._frame_times) - 1) / time_diff


class WebcamAdapter(BaseSourceAdapter):
    """
    Adapter for local USB / Laptop Webcam via OpenCV VideoCapture.
    Emits canonical FramePacket with SourceType.WEBCAM.
    """
    def __init__(self, camera_id: str = "WEBCAM-01", device_index: int = 0, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        super().__init__(camera_id, SourceType.WEBCAM, cfg)
        self.device_index = cfg.get("device_index", device_index)
        self.fps_limit = cfg.get("fps_limit", 30)
        self.target_width = cfg.get("width", 640)
        self.target_height = cfg.get("height", 480)
        self.buffer_size = cfg.get("buffer_size", 20)

        import queue
        self._buffer: queue.Queue = queue.Queue(maxsize=self.buffer_size)
        self._dropped_count = 0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def _packet_buffer_size(self) -> int:
        return self._buffer.qsize()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, name=f"WebcamAdapter-{self.camera_id}", daemon=True)
        self._thread.start()
        logger.info("WebcamAdapter started", camera_id=self.camera_id, device=self.device_index)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        self._health = CameraHealth.DISCONNECTED
        logger.info("WebcamAdapter stopped", camera_id=self.camera_id)

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def get_next_packet(self) -> Optional[FramePacket]:
        import queue
        try:
            return self._buffer.get_nowait()
        except queue.Empty:
            return None

    def get_latest_packet(self) -> Optional[FramePacket]:
        import queue
        latest = None
        while True:
            try:
                latest = self._buffer.get_nowait()
            except queue.Empty:
                break
        return latest

    def _push_packet(self, packet: FramePacket) -> None:
        import queue
        try:
            self._buffer.put_nowait(packet)
        except queue.Full:
            try:
                self._buffer.get_nowait()
                self._buffer.put_nowait(packet)
                self._dropped_count += 1
            except (queue.Empty, queue.Full):
                pass

    def _capture_loop(self) -> None:
        import sys
        target_frame_time = 1.0 / self.fps_limit if self.fps_limit > 0 else 0
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if sys.platform == "win32" else [cv2.CAP_ANY]

        while not self._stop_event.is_set():
            cap = None
            try:
                self._health = CameraHealth.CONNECTING
                indices_to_try = [self.device_index]
                for alt_idx in [0, 1, 2]:
                    if alt_idx not in indices_to_try:
                        indices_to_try.append(alt_idx)

                for b_end in backends:
                    for idx in indices_to_try:
                        try:
                            test_cap = cv2.VideoCapture(idx, b_end)
                            if test_cap.isOpened():
                                if self.target_width and self.target_height:
                                    test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
                                    test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
                                ret, test_frame = test_cap.read()
                                if ret and test_frame is not None:
                                    cap = test_cap
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

                consecutive_drops = 0
                while not self._stop_event.is_set():
                    loop_start = time.time()
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        consecutive_drops += 1
                        if consecutive_drops >= 3:
                            break
                        time.sleep(0.05)
                        continue
                    consecutive_drops = 0

                    now_epoch = time.time()
                    self._total_packets += 1
                    self._last_packet_time = datetime.fromtimestamp(now_epoch, tz=timezone.utc)
                    self._update_fps(now_epoch)

                    h, w = frame.shape[:2]
                    packet = FramePacket(
                        camera_id=self.camera_id,
                        frame_id=self._total_packets,
                        source_type=SourceType.WEBCAM,
                        timestamp=now_epoch,
                        raw_bgr=frame,
                        width=w,
                        height=h,
                        fps=self._fps_measured or float(self.fps_limit),
                        camera_metadata={"device_index": self.device_index, "backend": str(cap.getBackendName())}
                    )
                    self._last_capture_latency_ms = (time.time() - loop_start) * 1000.0
                    self._push_packet(packet)

                    elapsed = time.time() - loop_start
                    if elapsed < target_frame_time:
                        time.sleep(target_frame_time - elapsed)

            except Exception as e:
                self._health = CameraHealth.ERROR
                self._error_msg = str(e)
                self._reconnect_count += 1
                time.sleep(3.0)
            finally:
                if cap is not None:
                    cap.release()


class VideoFileAdapter(BaseSourceAdapter):
    """
    Adapter for local video files (e.g. test_video.mp4).
    Loops continuously or runs for a single pass, pacing at video's native FPS.
    Emits canonical FramePacket with SourceType.VIDEO_FILE.
    """
    def __init__(self, camera_id: str, file_path: str, loop: bool = True, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        super().__init__(camera_id, SourceType.VIDEO_FILE, cfg)
        self.file_path = file_path
        self.loop = cfg.get("loop", loop)
        self.buffer_size = cfg.get("buffer_size", 30)
        self.fps_override = cfg.get("fps_limit", None)

        import queue
        self._buffer: queue.Queue = queue.Queue(maxsize=self.buffer_size)
        self._dropped_count = 0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def _packet_buffer_size(self) -> int:
        return self._buffer.qsize()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._read_loop, name=f"VideoFileAdapter-{self.camera_id}", daemon=True)
        self._thread.start()
        logger.info("VideoFileAdapter started", camera_id=self.camera_id, path=self.file_path)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        self._health = CameraHealth.DISCONNECTED
        logger.info("VideoFileAdapter stopped", camera_id=self.camera_id)

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def get_next_packet(self) -> Optional[FramePacket]:
        import queue
        try:
            return self._buffer.get_nowait()
        except queue.Empty:
            return None

    def get_latest_packet(self) -> Optional[FramePacket]:
        import queue
        latest = None
        while True:
            try:
                latest = self._buffer.get_nowait()
            except queue.Empty:
                break
        return latest

    def _push_packet(self, packet: FramePacket) -> None:
        import queue
        try:
            self._buffer.put_nowait(packet)
        except queue.Full:
            try:
                self._buffer.get_nowait()
                self._buffer.put_nowait(packet)
                self._dropped_count += 1
            except (queue.Empty, queue.Full):
                pass

    def _read_loop(self) -> None:
        if not os.path.exists(self.file_path):
            self._health = CameraHealth.ERROR
            self._error_msg = f"Video file not found: {self.file_path}"
            logger.error("Video file does not exist", path=self.file_path)
            return

        while not self._stop_event.is_set():
            cap = cv2.VideoCapture(self.file_path)
            if not cap.isOpened():
                self._health = CameraHealth.ERROR
                self._error_msg = f"Failed to open video file: {self.file_path}"
                time.sleep(2.0)
                continue

            self._health = CameraHealth.CONNECTED
            self._error_msg = None

            video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            target_fps = float(self.fps_override or video_fps)
            frame_delay = 1.0 / target_fps if target_fps > 0 else 0.033

            try:
                while not self._stop_event.is_set():
                    loop_start = time.time()
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        if self.loop:
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            continue
                        else:
                            break

                    now_epoch = time.time()
                    self._total_packets += 1
                    self._last_packet_time = datetime.fromtimestamp(now_epoch, tz=timezone.utc)
                    self._update_fps(now_epoch)

                    h, w = frame.shape[:2]
                    packet = FramePacket(
                        camera_id=self.camera_id,
                        frame_id=self._total_packets,
                        source_type=SourceType.VIDEO_FILE,
                        timestamp=now_epoch,
                        raw_bgr=frame,
                        width=w,
                        height=h,
                        fps=target_fps,
                        camera_metadata={"file_path": self.file_path, "loop": self.loop}
                    )
                    self._last_capture_latency_ms = (time.time() - loop_start) * 1000.0
                    self._push_packet(packet)

                    elapsed = time.time() - loop_start
                    if elapsed < frame_delay:
                        time.sleep(frame_delay - elapsed)
            finally:
                cap.release()

            if not self.loop:
                break


class RTSPAdapter(BaseSourceAdapter):
    """
    Adapter for network RTSP streams.
    Emits canonical FramePacket with SourceType.RTSP.
    """
    def __init__(self, camera_id: str, rtsp_url: str, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        super().__init__(camera_id, SourceType.RTSP, cfg)
        self.rtsp_url = rtsp_url
        self.fps_limit = cfg.get("fps_limit", 15)
        self.buffer_size = cfg.get("buffer_size", 30)
        self.reconnect_delay = cfg.get("reconnect_delay_seconds", 2.0)

        import queue
        self._buffer: queue.Queue = queue.Queue(maxsize=self.buffer_size)
        self._dropped_count = 0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def _packet_buffer_size(self) -> int:
        return self._buffer.qsize()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, name=f"RTSPAdapter-{self.camera_id}", daemon=True)
        self._thread.start()
        logger.info("RTSPAdapter started", camera_id=self.camera_id, url=self._sanitize_url(self.rtsp_url))

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        self._health = CameraHealth.DISCONNECTED
        logger.info("RTSPAdapter stopped", camera_id=self.camera_id)

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def get_next_packet(self) -> Optional[FramePacket]:
        import queue
        try:
            return self._buffer.get_nowait()
        except queue.Empty:
            return None

    def get_latest_packet(self) -> Optional[FramePacket]:
        import queue
        latest = None
        while True:
            try:
                latest = self._buffer.get_nowait()
            except queue.Empty:
                break
        return latest

    def _push_packet(self, packet: FramePacket) -> None:
        import queue
        try:
            self._buffer.put_nowait(packet)
        except queue.Full:
            try:
                self._buffer.get_nowait()
                self._buffer.put_nowait(packet)
                self._dropped_count += 1
            except (queue.Empty, queue.Full):
                pass

    def _sanitize_url(self, url: str) -> str:
        return mask_rtsp_url(url)

    def _capture_loop(self) -> None:
        target_frame_time = 1.0 / self.fps_limit if self.fps_limit > 0 else 0

        while not self._stop_event.is_set():
            cap = None
            try:
                self._health = CameraHealth.CONNECTING
                if self.rtsp_url.startswith("rtsp://"):
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|timeout;5000000"
                    cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                else:
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;3000000"
                    cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                    if not cap.isOpened():
                        cap = cv2.VideoCapture(self.rtsp_url)

                if not cap.isOpened():
                    raise ConnectionError(f"Failed to open video stream at {self._sanitize_url(self.rtsp_url)}")

                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass

                self._health = CameraHealth.CONNECTED
                self._reconnect_count = 0
                self._error_msg = None

                consecutive_failures = 0
                while not self._stop_event.is_set():
                    loop_start = time.time()
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        consecutive_failures += 1
                        if consecutive_failures < 4:
                            time.sleep(0.02)
                            continue
                        break
                    consecutive_failures = 0

                    now_epoch = time.time()
                    self._total_packets += 1
                    self._last_packet_time = datetime.fromtimestamp(now_epoch, tz=timezone.utc)
                    self._update_fps(now_epoch)

                    h, w = frame.shape[:2]
                    packet = FramePacket(
                        camera_id=self.camera_id,
                        frame_id=self._total_packets,
                        source_type=self.source_type,
                        timestamp=now_epoch,
                        raw_bgr=frame,
                        width=w,
                        height=h,
                        fps=self._fps_measured or float(self.fps_limit),
                        camera_metadata={"url": self._sanitize_url(self.rtsp_url)}
                    )
                    self._last_capture_latency_ms = (time.time() - loop_start) * 1000.0
                    self._push_packet(packet)

                    if target_frame_time > 0:
                        elapsed = time.time() - loop_start
                        if elapsed < target_frame_time:
                            time.sleep(target_frame_time - elapsed)

            except Exception as e:
                self._health = CameraHealth.ERROR
                self._error_msg = mask_rtsp_url(str(e))
                self._reconnect_count += 1
            finally:
                if cap is not None:
                    cap.release()

            if not self._stop_event.is_set():
                backoff = min(self.reconnect_delay * (1.2 ** min(self._reconnect_count - 1, 5)), 5.0)
                time.sleep(backoff)


class MediaMTXAdapter(RTSPAdapter):
    """
    Adapter for local/cluster MediaMTX RTSP and WebRTC endpoints.
    Emits canonical FramePacket with SourceType.MEDIAMTX.
    """
    def __init__(self, camera_id: str, mediamtx_rtsp_url: str = "rtsp://127.0.0.1:8554/CAM-01", config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        super().__init__(camera_id, mediamtx_rtsp_url, cfg)
        self._source_type = SourceType.MEDIAMTX
        self.api_url = cfg.get("api_url", "http://127.0.0.1:9997")

    def get_mediamtx_path_info(self) -> Dict[str, Any]:
        """Queries MediaMTX API for stream diagnostics."""
        try:
            import urllib.request
            import json
            req = urllib.request.Request(f"{self.api_url}/v3/paths/get/{self.camera_id}")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode())
        except Exception:
            pass
        return {"status": "unavailable", "path": self.camera_id}


class SourceAdapterFactory:
    """
    Factory creating canonical source adapters based on URI and configuration.
    """
    @staticmethod
    def create_adapter(
        camera_id: str,
        source_uri: Union[str, int],
        source_type: Optional[Union[str, SourceType]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseSourceAdapter:
        cfg = config or {}

        # If source_type is specified explicitly
        if source_type:
            st = str(source_type).upper()
            if "WEBCAM" in st:
                idx = int(source_uri) if str(source_uri).isdigit() else 0
                return WebcamAdapter(camera_id=camera_id, device_index=idx, config=cfg)
            elif "MEDIAMTX" in st:
                return MediaMTXAdapter(camera_id=camera_id, mediamtx_rtsp_url=str(source_uri), config=cfg)
            elif "VIDEO" in st or "FILE" in st:
                return VideoFileAdapter(camera_id=camera_id, file_path=str(source_uri), config=cfg)
            elif "RTSP" in st:
                return RTSPAdapter(camera_id=camera_id, rtsp_url=str(source_uri), config=cfg)

        # Automatic detection from URI pattern
        uri_str = str(source_uri).strip()
        if uri_str.isdigit() or uri_str.lower().startswith("webcam"):
            idx = int(uri_str) if uri_str.isdigit() else 0
            return WebcamAdapter(camera_id=camera_id, device_index=idx, config=cfg)

        if uri_str.startswith("rtsp://"):
            if "127.0.0.1:8554" in uri_str or "localhost:8554" in uri_str:
                return MediaMTXAdapter(camera_id=camera_id, mediamtx_rtsp_url=uri_str, config=cfg)
            return RTSPAdapter(camera_id=camera_id, rtsp_url=uri_str, config=cfg)

        if os.path.exists(uri_str) or any(uri_str.lower().endswith(ext) for ext in [".mp4", ".avi", ".mkv", ".mov"]):
            return VideoFileAdapter(camera_id=camera_id, file_path=uri_str, config=cfg)

        # Default fallback: RTSP
        return RTSPAdapter(camera_id=camera_id, rtsp_url=uri_str, config=cfg)
