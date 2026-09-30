"""
tests/test_clip_ledger_integration.py
=====================================
Integration and unit tests for IBVAP Milestone 1:
1. Ring buffer 8-second frame retention at 30 FPS.
2. Temporal window [t-5s, t+3s] extraction & MP4 export.
3. Cryptographic SHA-256 clip hashing & DuckDB ledger linking.
4. Tamper-evidence verification & Section 65B compliance.
"""

from __future__ import annotations

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple

import cv2
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.ingestion.rolling_ring_buffer import RollingRingBuffer
from services.ingestion.video_exporter import export_window_to_mp4, compute_file_sha256
from crypto_ledger import (
    CryptoEvidenceLedger,
    compute_frame_hash,
    compute_block_hash,
    GENESIS_PREVIOUS_HASH
)


# ============================================================================
# Unit & Integration Tests
# ============================================================================

def test_ring_buffer_retains_8_seconds_at_30fps():
    """
    Requirement 1: Verify the ring buffer retains 8 seconds of frames at 30 FPS
    without unbounded memory growth.
    """
    buf = RollingRingBuffer(window_seconds=8.0, fps=30.0)
    # Capacity is int(8.0 * 30.0) + 30 = 270 frames
    assert buf.capacity == 270

    base_time = datetime(2026, 9, 29, 10, 0, 0, tzinfo=timezone.utc)
    dummy_frame = np.full((120, 160, 3), 100, dtype=np.uint8)

    # Push 330 frames (11.0 seconds at 30 FPS)
    for i in range(330):
        t = base_time + timedelta(seconds=i / 30.0)
        buf.push_frame(dummy_frame, timestamp=t, frame_id=i)

    # Buffer must be strictly bounded at capacity
    assert buf.size() == 270
    assert buf.size() <= buf.capacity

    # Total duration span held must be at least 8.0 seconds
    duration = buf.duration_seconds()
    assert duration >= 8.0
    assert buf.get_latest_frame() is not None


def test_ring_buffer_exact_slice_extraction():
    """
    Requirement 2: Extract an exact 8-second slice [t-5s, t+3s] around event trigger timestamp.
    """
    buf = RollingRingBuffer(window_seconds=8.0, fps=30.0)
    base_time = datetime(2026, 9, 29, 10, 0, 0, tzinfo=timezone.utc)

    # Push 280 frames (~9.33 seconds), representing streaming up to t + 3.2s after trigger
    for i in range(280):
        t = base_time + timedelta(seconds=i / 30.0)
        f = np.full((60, 80, 3), i % 255, dtype=np.uint8)
        buf.push_frame(f, timestamp=t, frame_id=i)

    # Event triggered at t = 6.0 seconds (frame 180).
    # Background harvester wakes up at t = 6.0 + 3.2s = 9.2s (frame 276).
    event_time = base_time + timedelta(seconds=6.0)

    # Extract [t-5.0s, t+3.0s] at 30 FPS (sample_interval_sec = None for full frames)
    window = buf.extract_window(
        center_timestamp=event_time,
        pre_seconds=5.0,
        post_seconds=3.0,
        sample_interval_sec=None
    )

    # 8 seconds at 30 FPS is ~240 frames
    assert len(window) >= 235
    assert len(window) <= 245

    # Check timestamps: earliest should be ~1.0s (t-5s), latest should be ~9.0s (t+3s)
    earliest_rel = window[0]["relative_sec"]
    latest_rel = window[-1]["relative_sec"]

    assert earliest_rel <= -4.9
    assert latest_rel >= 2.9


def test_export_window_to_valid_mp4(tmp_path):
    """
    Requirement 3: Export extracted frames to a playable standard MP4 file.
    """
    out_file = tmp_path / "breach_CAM01_test.mp4"

    # Generate 240 frames (8 seconds at 30 FPS)
    frames_meta = []
    base_t = datetime.now(timezone.utc)
    for i in range(240):
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(img, f"Frame {i:03d}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        frames_meta.append({
            "frame": img,
            "frame_id": i,
            "timestamp": base_t + timedelta(seconds=i / 30.0),
            "relative_sec": round(i / 30.0 - 5.0, 2)
        })

    clip_sha256 = export_window_to_mp4(frames_meta, out_file, fps=30.0)

    assert out_file.exists()
    assert out_file.stat().st_size > 1024
    assert len(clip_sha256) == 64

    # Verify with OpenCV VideoCapture
    cap = cv2.VideoCapture(str(out_file))
    assert cap.isOpened() is True
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    assert total_frames == 240
    assert abs(fps - 30.0) < 0.1

    # Read all frames to ensure 0 decoding errors
    read_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        read_count += 1
        assert frame.shape == (240, 320, 3)
    cap.release()

    assert read_count == 240


def test_mp4_sha256_matches_duckdb_ledger_and_chain_integrity(tmp_path):
    """
    Requirement 4 & 5:
    - MP4 file's SHA-256 matches the hash stored in the DuckDB ledger.
    - verify_chain_integrity() succeeds 100%.
    """
    db_file = tmp_path / "evidence_ledger.duckdb"
    clip_file = tmp_path / "breach_CAM_SSB_01.mp4"

    ledger = CryptoEvidenceLedger(db_path=db_file)

    # 1. Create and export valid 8-second MP4 clip
    frames_meta = []
    base_t = datetime(2026, 9, 29, 10, 30, 0, tzinfo=timezone.utc)
    for i in range(240):
        img = np.full((120, 160, 3), (i * 2) % 255, dtype=np.uint8)
        frames_meta.append({
            "frame": img,
            "frame_id": i,
            "timestamp": base_t + timedelta(seconds=i / 30.0),
            "relative_sec": round(i / 30.0 - 5.0, 2)
        })

    computed_clip_hash = export_window_to_mp4(frames_meta, clip_file, fps=30.0)

    # Trigger frame at t_event (150th frame or trigger instant)
    trigger_frame = frames_meta[150]["frame"]

    # 2. Commit event into cryptographic ledger
    block = ledger.commit_event(
        frame=trigger_frame,
        camera_id="CAM_SSB_01",
        event_type="PERIMETER_BREACH",
        metadata={
            "track_id": 104,
            "class_name": "person",
            "confidence": 0.91,
            "is_crawling": True,
            "bbox": [100, 150, 250, 380],
            "clip_duration_sec": 8.0,
            "clip_fps": 30.0,
            "clip_frame_count": 240
        },
        severity="CRITICAL",
        custom_timestamp=base_t + timedelta(seconds=5.0),
        clip_path=clip_file,
        clip_hash=computed_clip_hash
    )

    assert block.sequence_id == 1
    assert block.clip_path == str(clip_file)
    assert block.clip_hash == computed_clip_hash
    assert block.has_clip is True

    # 3. Verify that physical file hash matches ledger hash exactly
    file_sha = compute_file_sha256(clip_file)
    assert file_sha == computed_clip_hash
    assert file_sha == block.clip_hash

    # 4. Commit a second block to test chaining
    block2 = ledger.commit_event(
        frame=trigger_frame,
        camera_id="CAM_SSB_01",
        event_type="UNAUTHORIZED_VEHICLE",
        metadata={"license_plate": "UK07AB1234"},
        severity="HIGH"
    )
    assert block2.sequence_id == 2
    assert block2.previous_hash == block.block_hash

    # 5. Verify chain integrity 100%
    audit = ledger.verify_chain_integrity(verbose=True, verify_clips=True)
    assert audit["is_valid"] is True
    assert audit["status"] == "VERIFIED"
    assert audit["total_blocks"] == 2
    assert audit["total_clips_checked"] == 1
    assert audit["valid_clips_count"] == 1
    assert len(audit["corrupted_clips"]) == 0

    # 6. Verify single clip integrity helper
    clip_audit = ledger.verify_clip_integrity(sequence_id=1)
    assert clip_audit["is_valid"] is True
    assert clip_audit["status"] == "VERIFIED"
    assert clip_audit["computed_sha256"] == computed_clip_hash


def test_physical_file_tamper_detection(tmp_path):
    """
    Section 65B Legal Admissibility Test:
    Altering even a single byte of the exported MP4 video file triggers immediate
    tamper detection during forensic audit.
    """
    db_file = tmp_path / "tamper_test.duckdb"
    clip_file = tmp_path / "tamper_clip.mp4"
    ledger = CryptoEvidenceLedger(db_path=db_file)

    frames = [{"frame": np.zeros((100, 100, 3), dtype=np.uint8)} for _ in range(60)]
    clip_sha = export_window_to_mp4(frames, clip_file, fps=30.0)

    trigger_frame = np.full((100, 100, 3), 50, dtype=np.uint8)
    block = ledger.commit_event(
        frame=trigger_frame,
        camera_id="CAM_01",
        event_type="PERIMETER_BREACH",
        clip_path=clip_file,
        clip_hash=clip_sha
    )

    # Initial verification passes
    initial_check = ledger.verify_clip_integrity(block.sequence_id)
    assert initial_check["is_valid"] is True

    # Tamper with 1 byte in the MP4 file
    with open(clip_file, "r+b") as fp:
        fp.seek(64)
        b = fp.read(1)
        fp.seek(64)
        fp.write(bytes([b[0] ^ 0xFF]))

    # Clip verification must now fail
    tampered_check = ledger.verify_clip_integrity(block.sequence_id)
    assert tampered_check["is_valid"] is False
    assert tampered_check["status"] == "TAMPER_DETECTED"
    assert tampered_check["computed_sha256"] != clip_sha

    # Overall chain audit with verify_clips=True also detects tampering
    deep_audit = ledger.verify_chain_integrity(verify_clips=True)
    assert deep_audit["is_valid"] is False
    assert len(deep_audit["corrupted_clips"]) == 1


def test_duckdb_metadata_tamper_detection(tmp_path):
    """
    Section 65B Legal Admissibility Test:
    Altering the clip_sha256 stored in DuckDB breaks the Merkle block hash.
    """
    db_file = tmp_path / "db_tamper.duckdb"
    clip_file = tmp_path / "db_clip.mp4"
    ledger = CryptoEvidenceLedger(db_path=db_file)

    frames = [{"frame": np.zeros((100, 100, 3), dtype=np.uint8)} for _ in range(30)]
    clip_sha = export_window_to_mp4(frames, clip_file, fps=30.0)
    trigger = np.zeros((100, 100, 3), dtype=np.uint8)

    block = ledger.commit_event(
        frame=trigger,
        camera_id="CAM_01",
        event_type="ALERT",
        clip_path=clip_file,
        clip_hash=clip_sha
    )

    # Directly tamper with metadata_json in DuckDB
    conn = ledger._get_connection()
    conn.execute("UPDATE evidence_ledger SET metadata_json = ? WHERE sequence_id = ?", [
        json.dumps({"clip_path": str(clip_file), "clip_sha256": "f" * 64}),
        block.sequence_id
    ])

    # Re-audit: block hash forgery detected
    audit = ledger.verify_chain_integrity()
    assert audit["is_valid"] is False
    assert audit["corrupted_block_id"] == 1
    assert "Cryptographic tampering detected" in audit["message"]
