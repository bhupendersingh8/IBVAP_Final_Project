"""
services/ingestion/rolling_ring_buffer.py
=========================================
In-Memory Rolling Frame Ring Buffer for IBVAP.
Maintains a bounded circular queue of recent video frames (default 8 seconds:
5s pre-event + 3s post-event) to provide full temporal context upon incident trigger.
Zero disk I/O during streaming; lock-protected for multi-threaded safety.
"""
from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

import numpy as np


class RollingRingBuffer:
    """
    Circular in-memory frame buffer holding the last N seconds of camera frames.
    Thread-safe, bounded, zero disk I/O during continuous ingestion.
    """

    def __init__(self, window_seconds: float = 8.0, fps: float = 30.0):
        self.window_seconds = float(window_seconds)
        self.fps = float(fps)
        # Allocate 1 extra second of margin (default 270 frames for 8s @ 30fps)
        self.capacity = max(30, int(self.window_seconds * self.fps) + 30)
        self._buffer: deque = deque(maxlen=self.capacity)
        self._lock = threading.Lock()

    def push_frame(
        self,
        frame: np.ndarray,
        timestamp: Optional[Union[datetime, float, int]] = None,
        frame_id: int = 0,
    ) -> None:
        """Pushes a new video frame into the circular ring buffer."""
        if frame is None:
            return

        if timestamp is None:
            ts = datetime.now(timezone.utc)
        elif isinstance(timestamp, (int, float)):
            ts = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        elif isinstance(timestamp, datetime):
            ts = timestamp if timestamp.tzinfo is not None else timestamp.replace(tzinfo=timezone.utc)
        else:
            ts = datetime.now(timezone.utc)

        item = {
            "frame": frame,
            "timestamp": ts,
            "frame_id": frame_id,
        }
        with self._lock:
            self._buffer.append(item)

    def add_frame(
        self,
        frame: np.ndarray,
        timestamp: Optional[Union[datetime, float, int]] = None,
        frame_id: int = 0,
    ) -> None:
        """Alias for push_frame complying with M1/M2 interface contract."""
        self.push_frame(frame=frame, timestamp=timestamp, frame_id=frame_id)

    def extract_window(
        self,
        center_timestamp: Optional[Union[datetime, float, int]] = None,
        pre_seconds: float = 5.0,
        post_seconds: float = 3.0,
        sample_interval_sec: Optional[float] = 0.5,
        copy_frames: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Extracts temporal context slice around center_timestamp (defaults to latest frame).
        
        Args:
            center_timestamp: Event trigger time (datetime or epoch float).
            pre_seconds: Seconds of video to capture prior to trigger (default 5.0s).
            post_seconds: Seconds of video to capture after trigger (default 3.0s).
            sample_interval_sec: Subsampling interval.
                                 - Set to None or <=0 for FULL 30 FPS forensic video clip (~240 frames).
                                 - Set to 0.5s for sparse keyframes (VLM token conservation).
            copy_frames: If True, creates deep copies of frame arrays. If False (default),
                         returns shallow references (<0.01ms overhead, ref-counted safety).
        """
        items = None
        for _ in range(5):
            try:
                items = list(self._buffer)
                break
            except RuntimeError:
                continue
        if items is None:
            with self._lock:
                items = list(self._buffer)

        if not items:
            return []

        if center_timestamp is None:
            center_ts = items[-1]["timestamp"]
        elif isinstance(center_timestamp, (int, float)):
            center_ts = datetime.fromtimestamp(center_timestamp, tz=timezone.utc)
        elif isinstance(center_timestamp, datetime):
            center_ts = center_timestamp if center_timestamp.tzinfo is not None else center_timestamp.replace(tzinfo=timezone.utc)
        else:
            center_ts = items[-1]["timestamp"]

        start_ts = center_ts - timedelta(seconds=pre_seconds)
        end_ts = center_ts + timedelta(seconds=post_seconds)

        # Filter items within time window [start_ts, end_ts]
        window_items = [
            it for it in items
            if start_ts <= it["timestamp"] <= end_ts
        ]

        if not window_items:
            # Fallback: return the latest available frames if window filter is empty
            window_items = items[-min(len(items), 10):]

        # Case 1: Full 30 FPS extraction (no subsampling)
        if sample_interval_sec is None or sample_interval_sec <= 0.0:
            result = []
            for it in window_items:
                curr_ts = it["timestamp"]
                frame_data = it["frame"].copy() if copy_frames else it["frame"]
                result.append({
                    "timestamp": curr_ts,
                    "frame_id": it["frame_id"],
                    "frame": frame_data,
                    "relative_sec": round((curr_ts - center_ts).total_seconds(), 3),
                })
            return result

        # Case 2: Sparse sampling at sample_interval_sec (e.g. 0.5s for VLM)
        sampled: List[Dict[str, Any]] = []
        last_sampled_ts: Optional[datetime] = None

        for it in window_items:
            curr_ts = it["timestamp"]
            if last_sampled_ts is None or (curr_ts - last_sampled_ts).total_seconds() >= sample_interval_sec:
                frame_data = it["frame"].copy() if copy_frames else it["frame"]
                sampled.append({
                    "timestamp": curr_ts,
                    "frame_id": it["frame_id"],
                    "frame": frame_data,
                    "relative_sec": round((curr_ts - center_ts).total_seconds(), 2),
                })
                last_sampled_ts = curr_ts

        # Always include the last frame of the window if not already included
        if window_items and (not sampled or sampled[-1]["frame_id"] != window_items[-1]["frame_id"]):
            last_it = window_items[-1]
            frame_data = last_it["frame"].copy() if copy_frames else last_it["frame"]
            sampled.append({
                "timestamp": last_it["timestamp"],
                "frame_id": last_it["frame_id"],
                "frame": frame_data,
                "relative_sec": round((last_it["timestamp"] - center_ts).total_seconds(), 2),
            })

        return sampled

    def extract_window_tuples(
        self,
        center_timestamp: Optional[Union[datetime, float, int]] = None,
        pre_seconds: float = 5.0,
        post_seconds: float = 3.0,
        sample_interval_sec: Optional[float] = None,
    ) -> List[Tuple[float, np.ndarray]]:
        """
        Extracts temporal context slice returning List[Tuple[epoch_timestamp, frame_bgr]].
        Directly fulfills the M1-M2 interface contract.
        """
        window_dicts = self.extract_window(
            center_timestamp=center_timestamp,
            pre_seconds=pre_seconds,
            post_seconds=post_seconds,
            sample_interval_sec=sample_interval_sec,
            copy_frames=False,
        )
        return [(item["timestamp"].timestamp(), item["frame"]) for item in window_dicts]

    def export_clip(
        self,
        output_path: Union[str, Path],
        center_timestamp: Optional[Union[datetime, float, int]] = None,
        pre_seconds: float = 5.0,
        post_seconds: float = 3.0,
        fps: float = 30.0,
        codec: str = "auto",
    ) -> str:
        """
        Extracts full 8s window and directly encodes to MP4 file, returning SHA-256 hash.
        """
        from .video_exporter import export_window_to_mp4
        frames = self.extract_window(
            center_timestamp=center_timestamp,
            pre_seconds=pre_seconds,
            post_seconds=post_seconds,
            sample_interval_sec=None,
            copy_frames=False,
        )
        return export_window_to_mp4(frames, output_path=output_path, fps=fps, codec=codec)

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Returns the most recent frame in the buffer without removing it."""
        with self._lock:
            if not self._buffer:
                return None
            return self._buffer[-1]["frame"]

    def size(self) -> int:
        """Returns current number of buffered frames."""
        with self._lock:
            return len(self._buffer)

    def duration_seconds(self) -> float:
        """Returns total time span covered by the buffered frames."""
        with self._lock:
            if len(self._buffer) < 2:
                return 0.0
            return (self._buffer[-1]["timestamp"] - self._buffer[0]["timestamp"]).total_seconds()

    def clear(self) -> None:
        """Clears all buffered frames."""
        with self._lock:
            self._buffer.clear()
