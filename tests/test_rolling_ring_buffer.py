"""
tests/test_rolling_ring_buffer.py
=================================
Unit tests for IBVAP In-Memory Rolling Frame Ring Buffer.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
import numpy as np
import pytest

from services.ingestion.rolling_ring_buffer import RollingRingBuffer


def test_buffer_push_and_capacity():
    """Verify that buffer wraps around and never exceeds configured capacity."""
    buf = RollingRingBuffer(window_seconds=2.0, fps=10.0)
    assert buf.size() == 0

    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        buf.push_frame(dummy_frame, frame_id=i)

    # Capacity is max(30, int(2.0 * 10) + 30) = 50
    assert buf.size() <= buf.capacity
    assert buf.size() == 50


def test_buffer_extract_window():
    """Verify window extraction around trigger timestamp."""
    buf = RollingRingBuffer(window_seconds=8.0, fps=10.0)
    base_time = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)

    # Push 8 seconds of frames (80 frames, 0.1s apart)
    for i in range(80):
        t = base_time + timedelta(seconds=i * 0.1)
        dummy_frame = np.full((50, 50, 3), i, dtype=np.uint8)
        buf.push_frame(dummy_frame, timestamp=t, frame_id=i)

    # Event triggers at t = 5.0s (frame_id 50)
    event_time = base_time + timedelta(seconds=5.0)

    # Extract 5s pre-event + 3s post-event with 0.5s sample interval
    window = buf.extract_window(
        center_timestamp=event_time,
        pre_seconds=5.0,
        post_seconds=3.0,
        sample_interval_sec=0.5
    )

    assert len(window) > 0
    # Every extracted frame has relative_sec relative to event_time
    rel_times = [item["relative_sec"] for item in window]
    assert min(rel_times) <= 0.0  # covers pre-event
    assert max(rel_times) >= 0.0  # covers post-event


def test_buffer_thread_safety():
    """Verify concurrent push operations do not corrupt internal deque."""
    import concurrent.futures

    buf = RollingRingBuffer(window_seconds=4.0, fps=30.0)
    dummy_frame = np.zeros((30, 30, 3), dtype=np.uint8)

    def _worker(worker_id):
        for i in range(100):
            buf.push_frame(dummy_frame, frame_id=worker_id * 1000 + i)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_worker, w) for w in range(4)]
        for f in futures:
            f.result()

    assert buf.size() > 0
    assert buf.get_latest_frame() is not None


def test_buffer_add_frame_and_float_timestamps():
    """Verify add_frame alias and epoch float timestamp handling."""
    buf = RollingRingBuffer(window_seconds=8.0, fps=30.0)
    t0 = time.time()
    dummy = np.zeros((60, 80, 3), dtype=np.uint8)

    for i in range(60):
        buf.add_frame(dummy, timestamp=t0 + (i / 30.0), frame_id=i)

    assert buf.size() == 60
    window = buf.extract_window(center_timestamp=t0 + 1.0, pre_seconds=1.0, post_seconds=1.0, sample_interval_sec=None)
    assert len(window) >= 50
    assert isinstance(window[0]["timestamp"], datetime)


def test_buffer_full_extraction_and_zero_copy():
    """Verify full 30 FPS extraction (~240 frames) without copy bottlenecks (<5ms)."""
    buf = RollingRingBuffer(window_seconds=8.0, fps=30.0)
    base_t = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    dummy = np.full((120, 160, 3), 42, dtype=np.uint8)

    for i in range(240):
        buf.push_frame(dummy, timestamp=base_t + timedelta(seconds=i / 30.0), frame_id=i)

    event_t = base_t + timedelta(seconds=5.0)

    # Measure zero-copy extraction latency
    t_start = time.perf_counter()
    full_window = buf.extract_window(center_timestamp=event_t, pre_seconds=5.0, post_seconds=3.0, sample_interval_sec=None, copy_frames=False)
    extract_time_ms = (time.perf_counter() - t_start) * 1000.0

    assert len(full_window) == 240
    assert extract_time_ms < 5.0  # Zero-copy reference returning should be <5ms

    # Verify extract_window_tuples contract
    tuples = buf.extract_window_tuples(center_timestamp=event_t, pre_seconds=5.0, post_seconds=3.0, sample_interval_sec=None)
    assert len(tuples) == 240
    assert isinstance(tuples[0][0], float)
    assert isinstance(tuples[0][1], np.ndarray)


def test_buffer_duration_and_clear():
    """Verify duration_seconds calculation and clear operation."""
    buf = RollingRingBuffer(window_seconds=8.0, fps=30.0)
    base_t = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
    dummy = np.zeros((10, 10, 3), dtype=np.uint8)

    buf.push_frame(dummy, timestamp=base_t, frame_id=0)
    buf.push_frame(dummy, timestamp=base_t + timedelta(seconds=3.5), frame_id=1)

    assert abs(buf.duration_seconds() - 3.5) < 0.01
    buf.clear()
    assert buf.size() == 0
    assert buf.duration_seconds() == 0.0
