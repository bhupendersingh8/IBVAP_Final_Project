"""
tests/test_video_exporter.py
============================
Unit & Integration Tests for IBVAP Forensic MP4 Video Clip Exporter.
"""

import os
import sys
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta

import cv2
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.ingestion.video_exporter import (
    export_window_to_mp4,
    export_window_to_mp4_async,
    generate_clip_filename,
    compute_file_sha256,
    sanitize_filename_component,
    VideoClipExporter
)
from services.ingestion.rolling_ring_buffer import RollingRingBuffer


def test_filename_sanitization_and_windows_safety():
    """Verify that generated filenames have zero illegal Windows characters (colons, slashes)."""
    now = datetime(2026, 9, 29, 10, 45, 0, tzinfo=timezone.utc)
    fname = generate_clip_filename("CAM:01/EAST", now, "TRK#104")
    
    assert ":" not in fname
    assert "/" not in fname
    assert "\\" not in fname
    assert fname.endswith(".mp4")
    assert "CAM_01_EAST" in fname
    assert "20260929T104500Z" in fname
    assert "trackTRK_104" in fname


def test_rolling_ring_buffer_full_vs_sampled():
    """Verify extract_window returns all frames when sample_interval_sec=None."""
    buf = RollingRingBuffer(window_seconds=8.0, fps=30.0)
    base_time = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    # Push 240 frames (8 seconds @ 30 FPS)
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(240):
        t = base_time + timedelta(seconds=i / 30.0)
        buf.push_frame(dummy_frame, timestamp=t, frame_id=i)

    event_time = base_time + timedelta(seconds=5.0)

    # 1. Full 30 FPS extraction (for forensic MP4 video)
    full_window = buf.extract_window(
        center_timestamp=event_time,
        pre_seconds=5.0,
        post_seconds=3.0,
        sample_interval_sec=None
    )
    assert len(full_window) == 240

    # 2. Sparse sampling (for VLM reasoning)
    sparse_window = buf.extract_window(
        center_timestamp=event_time,
        pre_seconds=5.0,
        post_seconds=3.0,
        sample_interval_sec=0.5
    )
    assert len(sparse_window) <= 20
    assert len(sparse_window) >= 15


def test_export_window_to_mp4_opencv_mp4v(tmp_path):
    """Verify export using OpenCV VideoWriter with 'mp4v'."""
    out_file = tmp_path / "test_cv_mp4v.mp4"
    frames = [np.full((120, 160, 3), i * 4, dtype=np.uint8) for i in range(60)]

    sha256_hash = export_window_to_mp4(frames, out_file, fps=30.0, codec="mp4v")

    assert out_file.exists()
    assert out_file.stat().st_size > 0
    assert len(sha256_hash) == 64
    assert sha256_hash == compute_file_sha256(out_file)

    # Verify video can be read back with OpenCV
    cap = cv2.VideoCapture(str(out_file))
    assert cap.isOpened()
    read_count = 0
    while True:
        ret, _ = cap.read()
        if not ret:
            break
        read_count += 1
    cap.release()
    assert read_count == 60


def test_export_window_to_mp4_ffmpeg(tmp_path):
    """Verify export using FFmpeg pipe (H.264 / faststart)."""
    out_file = tmp_path / "test_ffmpeg.mp4"
    frames = [np.full((120, 160, 3), i * 4, dtype=np.uint8) for i in range(60)]

    sha256_hash = export_window_to_mp4(frames, out_file, fps=30.0, codec="ffmpeg")

    assert out_file.exists()
    assert out_file.stat().st_size > 0
    assert len(sha256_hash) == 64
    assert sha256_hash == compute_file_sha256(out_file)

    # Verify reading back
    cap = cv2.VideoCapture(str(out_file))
    assert cap.isOpened()
    read_count = 0
    while True:
        ret, _ = cap.read()
        if not ret:
            break
        read_count += 1
    cap.release()
    assert read_count == 60


def test_export_polymorphic_inputs(tmp_path):
    """Verify exporter handles Dicts, Tuples, and plain NumPy arrays."""
    # 1. Dict input (extract_window output)
    dict_frames = [{"frame": np.zeros((60, 80, 3), dtype=np.uint8), "timestamp": time.time()} for _ in range(10)]
    hash1 = export_window_to_mp4(dict_frames, tmp_path / "dict_test.mp4")
    assert len(hash1) == 64

    # 2. Tuple input (Contract format: (timestamp, frame))
    tuple_frames = [(time.time(), np.zeros((60, 80, 3), dtype=np.uint8)) for _ in range(10)]
    hash2 = export_window_to_mp4(tuple_frames, tmp_path / "tuple_test.mp4")
    assert len(hash2) == 64

    # 3. Plain ndarray list
    arr_frames = [np.zeros((60, 80, 3), dtype=np.uint8) for _ in range(10)]
    hash3 = export_window_to_mp4(arr_frames, tmp_path / "arr_test.mp4")
    assert len(hash3) == 64


def test_export_async_non_blocking(tmp_path):
    """Verify asynchronous dispatch takes < 15ms without stalling main thread."""
    out_file = tmp_path / "async_clip.mp4"
    frames = [np.zeros((240, 320, 3), dtype=np.uint8) for _ in range(90)]

    t0 = time.perf_counter()
    future = export_window_to_mp4_async(frames, out_file, fps=30.0)
    dispatch_time_ms = (time.perf_counter() - t0) * 1000.0

    # Dispatch overhead must be less than 15ms (well within frame budget)
    assert dispatch_time_ms < 15.0

    # Await result
    sha256_hash = future.result(timeout=10.0)
    assert len(sha256_hash) == 64
    assert out_file.exists()
    assert out_file.stat().st_size > 0


def test_export_empty_frames_raises_value_error(tmp_path):
    """Verify exporting empty frame list raises ValueError."""
    with pytest.raises(ValueError):
        export_window_to_mp4([], tmp_path / "empty.mp4")


def test_ring_buffer_export_clip_method(tmp_path):
    """Verify RollingRingBuffer.export_clip() method directly produces valid hashed MP4."""
    buf = RollingRingBuffer(window_seconds=4.0, fps=30.0)
    base_t = time.time()
    for i in range(60):
        buf.push_frame(np.full((80, 80, 3), i, dtype=np.uint8), timestamp=base_t + i * (1/30.0), frame_id=i)

    out_file = tmp_path / "buffer_clip.mp4"
    clip_hash = buf.export_clip(out_file, center_timestamp=base_t + 1.0, pre_seconds=1.0, post_seconds=1.0)
    assert len(clip_hash) == 64
    assert out_file.exists()
