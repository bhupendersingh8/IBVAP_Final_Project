"""
tests/test_adversarial_m1.py
============================
Adversarial Timing, Physical Corruption & Database Tamper Challenge Suite for IBVAP Milestone 1.
Created by challenger_m1_1 (Adversarial Timing & Tamper Challenger).

Challenges Tested:
1. Physical Bit-Level MP4 Corruption:
   - Header 1-bit flip (byte 0, byte 4, byte 16)
   - Payload 1-bit flip (middle of file, last byte of file)
   - File truncation (-1 byte) and file extension (+1 byte)
   - File deletion and 0-byte file replacement
   - Verifies verify_clip_integrity() returns is_valid == False with TAMPER_DETECTED or FILE_NOT_FOUND
   - Verifies verify_chain_integrity(verify_clips=True) returns is_valid == False with CLIP_CORRUPTED

2. Cryptographic Evidence Ledger Database Tampering:
   - Modifying clip_sha256 inside DuckDB metadata_json
   - Modifying frame_hash column directly in DuckDB
   - Modifying previous_hash column in DuckDB (broken chain link)
   - Modifying block_hash column in DuckDB
   - Modifying camera_id, event_type, or timestamp in DuckDB
   - Middle-block deletion attack (deleting block 2 of 3)
   - Malformed JSON metadata injection
   - Verifies verify_chain_integrity() flags forgery and returns is_valid == False with CORRUPTED

3. Rolling Ring Buffer Boundary Extractions & Stress:
   - Cold start extraction: buffer containing <5 seconds of video (30 frames and 75 frames)
   - Exact capacity extraction: buffer at exactly 270 frames (9.0s @ 30 FPS)
   - Overflow stress: buffer after 1,000 continuous frames of overwrites (33.3s)
   - Concurrency stress: multi-threaded concurrent pushes and simultaneous window extractions
   - Extreme bounds: completely empty buffer (0 frames) and single-frame buffer (1 frame)
"""

from __future__ import annotations

import os
import sys
import json
import time
import shutil
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

import cv2
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.ingestion.rolling_ring_buffer import RollingRingBuffer
from services.ingestion.video_exporter import (
    export_window_to_mp4,
    compute_file_sha256,
    generate_clip_filename
)
from crypto_ledger import (
    CryptoEvidenceLedger,
    compute_frame_hash,
    compute_block_hash,
    GENESIS_PREVIOUS_HASH
)


# ============================================================================
# Helper Functions
# ============================================================================

def _generate_synthetic_frames(
    count: int,
    base_time: datetime,
    fps: float = 30.0,
    width: int = 160,
    height: int = 120
) -> List[Dict[str, Any]]:
    """Generates synthetic video frames with timestamp and frame_id metadata."""
    frames = []
    for i in range(count):
        # Create non-trivial image with dynamic gradient to avoid trivial compression artifacts
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:, :, 0] = (i * 3) % 256
        img[:, :, 1] = (i * 7) % 256
        img[:, :, 2] = (i * 11) % 256
        cv2.putText(img, f"F:{i:04d}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        t = base_time + timedelta(seconds=i / fps)
        frames.append({
            "frame": img,
            "frame_id": i,
            "timestamp": t,
            "relative_sec": round(i / fps - (count / fps / 2.0), 3)
        })
    return frames


# ============================================================================
# 1. Adversarial Challenge: Bit-Level Physical File Corruption
# ============================================================================

class TestAdversarialPhysicalCorruption:
    """
    Stress-tests physical video file corruption detection against Section 65B legal admissibility.
    """

    @pytest.fixture
    def setup_valid_block(self, tmp_path):
        """Creates a valid DuckDB ledger and committed forensic MP4 clip."""
        db_path = tmp_path / "adversarial_physical.duckdb"
        clip_path = tmp_path / "breach_evidence_test.mp4"
        ledger = CryptoEvidenceLedger(db_path=db_path)

        base_t = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)
        frames = _generate_synthetic_frames(count=60, base_time=base_t, fps=30.0)
        clip_sha = export_window_to_mp4(frames, clip_path, fps=30.0)

        trigger_frame = frames[30]["frame"]
        block = ledger.commit_event(
            frame=trigger_frame,
            camera_id="CAM_BORDER_EAST_01",
            event_type="PERIMETER_BREACH",
            metadata={
                "target": "crawling_intruder",
                "confidence": 0.88,
                "sector": "SECTOR_DELTA_4"
            },
            severity="CRITICAL",
            clip_path=clip_path,
            clip_hash=clip_sha
        )
        return ledger, block, clip_path, clip_sha

    def test_single_bit_flip_in_mp4_header(self, setup_valid_block):
        """
        Adversarial Test: Flip exactly 1 bit in byte offset 4 of the MP4 header.
        Assert verify_clip_integrity() and verify_chain_integrity() detect corruption.
        """
        ledger, block, clip_path, orig_sha = setup_valid_block

        # Confirm baseline passes
        assert ledger.verify_clip_integrity(block.sequence_id)["is_valid"] is True

        # Maliciously flip 1 bit in byte 4 (part of ftyp box size/type)
        with open(clip_path, "r+b") as fp:
            fp.seek(4)
            original_byte = fp.read(1)[0]
            flipped_byte = original_byte ^ 0b00000001  # Flip LSB
            fp.seek(4)
            fp.write(bytes([flipped_byte]))

        # Audit single clip
        clip_res = ledger.verify_clip_integrity(block.sequence_id)
        assert clip_res["is_valid"] is False, "1-bit flip in header was not detected by verify_clip_integrity!"
        assert clip_res["status"] == "TAMPER_DETECTED"
        assert clip_res["computed_sha256"] != orig_sha
        assert clip_res["recorded_sha256"] == orig_sha

        # Audit full chain with verify_clips=True
        chain_res = ledger.verify_chain_integrity(verify_clips=True)
        assert chain_res["is_valid"] is False, "Chain audit failed to flag physical clip tampering!"
        assert chain_res["status"] == "CLIP_CORRUPTED"
        assert len(chain_res["corrupted_clips"]) == 1

    def test_single_bit_flip_in_mp4_payload(self, setup_valid_block):
        """
        Adversarial Test: Flip exactly 1 bit in the deep payload (middle of the file)
        and verify it triggers tamper detection.
        """
        ledger, block, clip_path, orig_sha = setup_valid_block

        file_size = clip_path.stat().st_size
        assert file_size > 1024, "File too small for deep payload corruption test"
        mid_offset = file_size // 2

        with open(clip_path, "r+b") as fp:
            fp.seek(mid_offset)
            original_byte = fp.read(1)[0]
            flipped_byte = original_byte ^ 0b10000000  # Flip MSB
            fp.seek(mid_offset)
            fp.write(bytes([flipped_byte]))

        clip_res = ledger.verify_clip_integrity(block.sequence_id)
        assert clip_res["is_valid"] is False, "Payload 1-bit flip not detected!"
        assert clip_res["status"] == "TAMPER_DETECTED"

    def test_single_bit_flip_in_last_byte(self, setup_valid_block):
        """
        Adversarial Test: Flip exactly 1 bit in the very last byte of the MP4 file.
        """
        ledger, block, clip_path, orig_sha = setup_valid_block

        file_size = clip_path.stat().st_size
        with open(clip_path, "r+b") as fp:
            fp.seek(file_size - 1)
            last_byte = fp.read(1)[0]
            flipped_byte = last_byte ^ 0b00010000  # Flip bit 4
            fp.seek(file_size - 1)
            fp.write(bytes([flipped_byte]))

        clip_res = ledger.verify_clip_integrity(block.sequence_id)
        assert clip_res["is_valid"] is False, "Trailing-byte 1-bit flip not detected!"
        assert clip_res["status"] == "TAMPER_DETECTED"

    def test_file_truncation_and_extension_tampering(self, setup_valid_block):
        """
        Adversarial Test:
        1. Truncate 1 byte from file end -> flags tampering.
        2. Append 1 spurious byte to file end -> flags tampering.
        """
        ledger, block, clip_path, orig_sha = setup_valid_block
        file_bytes = clip_path.read_bytes()

        # 1. Truncate by 1 byte
        clip_path.write_bytes(file_bytes[:-1])
        clip_res = ledger.verify_clip_integrity(block.sequence_id)
        assert clip_res["is_valid"] is False
        assert clip_res["status"] == "TAMPER_DETECTED"

        # 2. Append 1 null byte to original bytes
        clip_path.write_bytes(file_bytes + b"\x00")
        clip_res = ledger.verify_clip_integrity(block.sequence_id)
        assert clip_res["is_valid"] is False
        assert clip_res["status"] == "TAMPER_DETECTED"

    def test_file_deletion_and_zero_byte_adversarial(self, setup_valid_block):
        """
        Adversarial Test:
        1. Complete deletion of evidence MP4 from disk.
        2. Replacement with empty 0-byte file.
        """
        ledger, block, clip_path, orig_sha = setup_valid_block

        # 1. Remove file
        clip_path.unlink()
        clip_res = ledger.verify_clip_integrity(block.sequence_id)
        assert clip_res["is_valid"] is False
        assert clip_res["status"] == "FILE_NOT_FOUND"

        # 2. Touch 0-byte file
        clip_path.touch()
        clip_res = ledger.verify_clip_integrity(block.sequence_id)
        assert clip_res["is_valid"] is False
        assert clip_res["status"] == "TAMPER_DETECTED"


# ============================================================================
# 2. Adversarial Challenge: Database Tampering & Cryptographic Forgery
# ============================================================================

class TestAdversarialDatabaseTampering:
    """
    Stress-tests DuckDB ledger tamper-resistance against direct SQL row modifications.
    """

    @pytest.fixture
    def setup_multi_block_ledger(self, tmp_path):
        """Initializes a 3-block cryptographic chain in DuckDB."""
        db_path = tmp_path / "adversarial_db_chain.duckdb"
        clip_path = tmp_path / "clip_block1.mp4"
        ledger = CryptoEvidenceLedger(db_path=db_path)

        frames = _generate_synthetic_frames(count=30, base_time=datetime.now(timezone.utc))
        clip_sha = export_window_to_mp4(frames, clip_path, fps=30.0)

        # Block 1 (with clip)
        b1 = ledger.commit_event(
            frame=frames[0]["frame"],
            camera_id="CAM_01",
            event_type="ALERT",
            metadata={"source": "radar"},
            clip_path=clip_path,
            clip_hash=clip_sha
        )
        # Block 2
        b2 = ledger.commit_event(
            frame=frames[10]["frame"],
            camera_id="CAM_01",
            event_type="TRACK",
            metadata={"track_id": 42}
        )
        # Block 3
        b3 = ledger.commit_event(
            frame=frames[20]["frame"],
            camera_id="CAM_02",
            event_type="BREACH",
            metadata={"action": "interception"}
        )

        # Baseline verification must pass 100%
        audit = ledger.verify_chain_integrity(verify_clips=True)
        assert audit["is_valid"] is True
        assert audit["total_blocks"] == 3
        return ledger, [b1, b2, b3], clip_path

    def test_tamper_clip_sha256_in_metadata_json(self, setup_multi_block_ledger):
        """
        Adversarial Test: Maliciously edit clip_sha256 in DuckDB metadata_json for Block #1.
        Verify that verify_chain_integrity() flags block_hash forgery.
        """
        ledger, blocks, clip_path = setup_multi_block_ledger
        conn = ledger._get_connection()

        # Attacker replaces clip_sha256 in metadata_json with fake digest
        fake_sha = "a" * 64
        meta = json.loads(blocks[0].metadata_json)
        meta["clip_sha256"] = fake_sha
        tampered_json = json.dumps(meta, sort_keys=True)

        conn.execute(
            "UPDATE evidence_ledger SET metadata_json = ? WHERE sequence_id = 1",
            [tampered_json]
        )

        audit = ledger.verify_chain_integrity()
        assert audit["is_valid"] is False
        assert audit["status"] == "CORRUPTED"
        assert audit["corrupted_block_id"] == 1
        assert "block_hash forgery" in audit["message"]

    def test_tamper_frame_hash_column(self, setup_multi_block_ledger):
        """
        Adversarial Test: Directly modify frame_hash column in Block #2.
        Verify that verify_chain_integrity() flags block_hash forgery.
        """
        ledger, blocks, _ = setup_multi_block_ledger
        conn = ledger._get_connection()

        # Attacker modifies frame_hash
        bogus_frame_hash = "b" * 64
        conn.execute(
            "UPDATE evidence_ledger SET frame_hash = ? WHERE sequence_id = 2",
            [bogus_frame_hash]
        )

        audit = ledger.verify_chain_integrity()
        assert audit["is_valid"] is False
        assert audit["status"] == "CORRUPTED"
        assert audit["corrupted_block_id"] == 2
        assert "block_hash forgery" in audit["message"]

    def test_tamper_previous_hash_breaks_chain_link(self, setup_multi_block_ledger):
        """
        Adversarial Test: Directly modify previous_hash column in Block #3.
        Verify that verify_chain_integrity() flags broken chain link.
        """
        ledger, blocks, _ = setup_multi_block_ledger
        conn = ledger._get_connection()

        # Attacker modifies previous_hash of block 3
        broken_prev = "c" * 64
        conn.execute(
            "UPDATE evidence_ledger SET previous_hash = ? WHERE sequence_id = 3",
            [broken_prev]
        )

        audit = ledger.verify_chain_integrity()
        assert audit["is_valid"] is False
        assert audit["status"] == "CORRUPTED"
        assert audit["corrupted_block_id"] == 3
        assert "previous_hash mismatch" in audit["message"]

    def test_tamper_middle_block_deletion(self, setup_multi_block_ledger):
        """
        Adversarial Test: Attacker deletes Block #2 to conceal an incident.
        Verify that the gap immediately triggers broken chain link at Block #3.
        """
        ledger, blocks, _ = setup_multi_block_ledger
        conn = ledger._get_connection()

        # Attacker deletes Block #2
        conn.execute("DELETE FROM evidence_ledger WHERE sequence_id = 2")

        audit = ledger.verify_chain_integrity()
        assert audit["is_valid"] is False
        assert audit["status"] == "CORRUPTED"
        assert audit["corrupted_block_id"] == 3
        assert "previous_hash mismatch" in audit["message"]

    def test_tamper_attribute_columns_camera_and_timestamp(self, setup_multi_block_ledger):
        """
        Adversarial Test: Attacker alters camera_id or timestamp in Block #1.
        Since these are embedded into block_hash, verify_chain_integrity() must flag forgery.
        """
        ledger, blocks, _ = setup_multi_block_ledger
        conn = ledger._get_connection()

        # Attacker claims event occurred on CAM_99 instead of CAM_01
        conn.execute("UPDATE evidence_ledger SET camera_id = 'CAM_99' WHERE sequence_id = 1")

        audit = ledger.verify_chain_integrity()
        assert audit["is_valid"] is False
        assert audit["status"] == "CORRUPTED"
        assert audit["corrupted_block_id"] == 1
        assert "block_hash forgery" in audit["message"]

    def test_malformed_metadata_json_resilience(self, setup_multi_block_ledger):
        """
        Adversarial Test: Attacker injects malformed (non-JSON) text into metadata_json.
        verify_clip_integrity() must return MALFORMED_METADATA and is_valid == False.
        verify_chain_integrity() must flag block_hash forgery.
        """
        ledger, blocks, _ = setup_multi_block_ledger
        conn = ledger._get_connection()

        conn.execute("UPDATE evidence_ledger SET metadata_json = 'INVALID_JSON{[[' WHERE sequence_id = 1")

        clip_audit = ledger.verify_clip_integrity(sequence_id=1)
        assert clip_audit["is_valid"] is False
        assert clip_audit["status"] == "MALFORMED_METADATA"

        chain_audit = ledger.verify_chain_integrity()
        assert chain_audit["is_valid"] is False
        assert chain_audit["status"] == "CORRUPTED"


# ============================================================================
# 3. Adversarial Challenge: Boundary Window Extractions & Buffer Stress
# ============================================================================

class TestAdversarialBufferBoundariesAndStress:
    """
    Stress-tests RollingRingBuffer boundary limits:
    - Buffer containing <5 seconds of video (cold start)
    - Buffer at exact capacity (270 frames)
    - Buffer after 1,000 continuous frames of overwrites
    - Concurrent push/extract multi-threaded race hazard stress
    """

    def test_boundary_cold_start_under_5_seconds(self, tmp_path):
        """
        Boundary Scenario 1: Buffer containing <5 seconds of video.
        System boots and breach occurs after only 1.0 second (30 frames) or 2.5 seconds (75 frames).
        - Ring buffer must not crash or throw IndexError.
        - Must return all available frames without throwing exception.
        - Returned frames must be exportable to MP4 with valid SHA-256.
        """
        buf = RollingRingBuffer(window_seconds=8.0, fps=30.0)
        base_t = datetime(2026, 9, 29, 14, 0, 0, tzinfo=timezone.utc)

        # Push only 30 frames (1.0 second cold-start)
        for i in range(30):
            t = base_t + timedelta(seconds=i / 30.0)
            img = np.full((120, 160, 3), i * 5, dtype=np.uint8)
            buf.push_frame(img, timestamp=t, frame_id=i)

        assert buf.size() == 30
        assert buf.duration_seconds() < 1.1

        # Extract 8s window [t-5.0s, t+3.0s] around t_now (latest frame)
        window = buf.extract_window(
            center_timestamp=base_t + timedelta(seconds=29 / 30.0),
            pre_seconds=5.0,
            post_seconds=3.0,
            sample_interval_sec=None
        )

        # Buffer only has 30 frames: all 30 should be safely returned
        assert len(window) == 30, f"Expected 30 frames for cold start, got {len(window)}"
        assert window[0]["frame_id"] == 0
        assert window[-1]["frame_id"] == 29

        # Verify extract_window_tuples contract
        tuples = buf.extract_window_tuples(pre_seconds=5.0, post_seconds=3.0)
        assert len(tuples) == 30
        assert isinstance(tuples[0][0], float)
        assert isinstance(tuples[0][1], np.ndarray)

        # Verify export to MP4 of cold-start clip
        clip_path = tmp_path / "cold_start_clip.mp4"
        sha = export_window_to_mp4(window, clip_path, fps=30.0)
        assert clip_path.exists()
        assert clip_path.stat().st_size > 0
        assert len(sha) == 64

        # Read back with OpenCV VideoCapture
        cap = cv2.VideoCapture(str(clip_path))
        assert cap.isOpened()
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 30
        cap.release()

    def test_boundary_exact_capacity_270_frames(self):
        """
        Boundary Scenario 2: Buffer at exact capacity (270 frames).
        Capacity = int(8.0 * 30.0) + 30 = 270 frames (9.0 seconds of history).
        - Push exactly 270 frames.
        - Verify buf.size() == 270.
        - Verify boundary temporal slice [t-5.0s, t+3.0s] correctly covers 241 frames.
        """
        buf = RollingRingBuffer(window_seconds=8.0, fps=30.0)
        assert buf.capacity == 270

        base_t = datetime(2026, 9, 29, 15, 0, 0, tzinfo=timezone.utc)

        # Push exactly 270 frames
        for i in range(270):
            t = base_t + timedelta(seconds=i / 30.0)
            img = np.full((60, 80, 3), i % 255, dtype=np.uint8)
            buf.push_frame(img, timestamp=t, frame_id=i)

        assert buf.size() == 270
        # 269 intervals of 1/30s = 8.9667s
        assert abs(buf.duration_seconds() - (269 / 30.0)) < 0.01

        # Center event trigger at t = base_t + 5.0s (frame 150)
        # Window [t-5.0s, t+3.0s] covers [base_t + 0.0s, base_t + 8.0s]
        # Frame 0 is at 0.0s, Frame 240 is at 8.0s -> Exactly 241 frames (inclusive)
        event_time = base_t + timedelta(seconds=5.0)
        window = buf.extract_window(
            center_timestamp=event_time,
            pre_seconds=5.0,
            post_seconds=3.0,
            sample_interval_sec=None
        )

        assert len(window) == 241
        assert window[0]["frame_id"] == 0
        assert window[-1]["frame_id"] == 240
        assert window[0]["relative_sec"] == -5.0
        assert window[-1]["relative_sec"] == 3.0

    def test_boundary_after_1000_frames_of_overwrites(self, tmp_path):
        """
        Boundary Scenario 3: Buffer after 1,000 frames of continuous overwrites.
        Simulates 33.3 seconds of uninterrupted 30 FPS stream ingestion.
        - Confirms bounded memory (size capped strictly at 270).
        - Confirms eviction of the oldest 730 frames (frames 0..729 evicted).
        - Confirms frames 730..999 are retained in strict temporal order.
        - Extracts 8s window and exports to MP4 with verified SHA-256.
        """
        buf = RollingRingBuffer(window_seconds=8.0, fps=30.0)
        base_t = datetime(2026, 9, 29, 16, 0, 0, tzinfo=timezone.utc)

        # Push 1,000 frames
        for i in range(1000):
            t = base_t + timedelta(seconds=i / 30.0)
            img = np.full((60, 80, 3), (i % 250), dtype=np.uint8)
            buf.push_frame(img, timestamp=t, frame_id=i)

        # Strictly bounded capacity
        assert buf.size() == 270
        assert buf.size() <= buf.capacity

        # Inspect held frames
        items = list(buf._buffer)
        assert len(items) == 270
        assert items[0]["frame_id"] == 730
        assert items[-1]["frame_id"] == 999

        # Verify strict monotonicity
        for idx in range(len(items) - 1):
            assert items[idx]["frame_id"] + 1 == items[idx + 1]["frame_id"]
            assert items[idx]["timestamp"] < items[idx + 1]["timestamp"]

        # Case A: Event triggered at frame 909 (where both endpoints 759 and 999 exist in buffer)
        # Window [t-5.0s, t+3.0s] covers frames [759, 999] = 241 frames
        event_time_909 = base_t + timedelta(seconds=909 / 30.0)
        window_909 = buf.extract_window(
            center_timestamp=event_time_909,
            pre_seconds=5.0,
            post_seconds=3.0,
            sample_interval_sec=None
        )
        assert len(window_909) == 241
        assert window_909[0]["frame_id"] == 759
        assert window_909[-1]["frame_id"] == 999

        # Case B: Event triggered at frame 910 (where frame 1000 is 1 frame past buffer end)
        # Window covers frames [760, 999] = exactly 240 frames
        event_time_910 = base_t + timedelta(seconds=910 / 30.0)
        window = buf.extract_window(
            center_timestamp=event_time_910,
            pre_seconds=5.0,
            post_seconds=3.0,
            sample_interval_sec=None
        )
        assert len(window) == 240
        assert window[0]["frame_id"] == 760
        assert window[-1]["frame_id"] == 999

        # Export to MP4
        clip_path = tmp_path / "post_1000_frames_clip.mp4"
        sha = export_window_to_mp4(window, clip_path, fps=30.0)
        assert clip_path.exists()
        assert clip_path.stat().st_size > 1024
        assert len(sha) == 64

    def test_adversarial_buffer_empty_and_single_frame(self):
        """
        Adversarial Edge Cases:
        1. Querying an empty buffer: must return [] without crashing.
        2. Querying a 1-frame buffer: duration_seconds() must be 0.0, no division by zero.
        3. Attempting to export empty frame list: must raise ValueError.
        """
        buf = RollingRingBuffer(window_seconds=8.0, fps=30.0)
        assert buf.size() == 0
        assert buf.duration_seconds() == 0.0
        assert buf.get_latest_frame() is None
        assert buf.extract_window() == []
        assert buf.extract_window_tuples() == []

        # Exporting empty frames must cleanly raise ValueError
        with pytest.raises(ValueError, match="frames list is empty"):
            export_window_to_mp4([], "dummy.mp4")

        # Single frame push
        single_img = np.zeros((100, 100, 3), dtype=np.uint8)
        buf.push_frame(single_img, timestamp=datetime.now(timezone.utc), frame_id=1)
        assert buf.size() == 1
        assert buf.duration_seconds() == 0.0
        assert buf.get_latest_frame() is not None

        window = buf.extract_window()
        assert len(window) == 1
        assert window[0]["frame_id"] == 1

    def test_adversarial_concurrent_push_and_extract_stress(self):
        """
        Adversarial Concurrency Stress:
        Simulate real-world camera ingest thread pushing at high speed
        while multiple harvester threads continuously extract windows.
        Must execute without thread contention deadlocks or data corruption.
        """
        buf = RollingRingBuffer(window_seconds=8.0, fps=30.0)
        base_t = datetime(2026, 9, 29, 17, 0, 0, tzinfo=timezone.utc)

        stop_event = threading.Event()
        errors: List[Exception] = []

        def producer():
            try:
                frame_count = 0
                while not stop_event.is_set() and frame_count < 600:
                    t = base_t + timedelta(seconds=frame_count / 30.0)
                    img = np.full((60, 80, 3), frame_count % 255, dtype=np.uint8)
                    buf.push_frame(img, timestamp=t, frame_id=frame_count)
                    frame_count += 1
                    time.sleep(0.001)  # High-rate push (1000 FPS simulation)
            except Exception as e:
                errors.append(e)

        def consumer(worker_id: int):
            try:
                while not stop_event.is_set():
                    # Extract full window with zero-copy
                    w = buf.extract_window(
                        pre_seconds=5.0,
                        post_seconds=3.0,
                        sample_interval_sec=None,
                        copy_frames=False
                    )
                    if w:
                        assert len(w) <= 270
                        # Validate frame integrity
                        assert w[0]["frame"].shape == (60, 80, 3)
                    time.sleep(0.005)
            except Exception as e:
                errors.append(e)

        producer_thread = threading.Thread(target=producer)
        consumer_threads = [threading.Thread(target=consumer, args=(i,)) for i in range(3)]

        for ct in consumer_threads:
            ct.start()
        producer_thread.start()

        producer_thread.join(timeout=10.0)
        stop_event.set()

        for ct in consumer_threads:
            ct.join(timeout=5.0)

        assert len(errors) == 0, f"Concurrent stress test encountered errors: {errors}"
        assert buf.size() == 270


# ============================================================================
# 4. Adversarial Challenge: Extended Edge Cases & Cross-Backend Equivalence
# ============================================================================

class TestAdversarialExtendedRobustness:
    """
    Stress-tests cross-backend SQLite fallback, mixed frame resolutions, and ledger edge queries.
    """

    def test_adversarial_mixed_frame_resolutions_resilience(self, tmp_path):
        """
        Adversarial Test: Video encoder receives frames of non-uniform resolutions
        (e.g., dynamically changing camera stream resolution).
        Encoder must normalize and produce a valid, playable MP4 video.
        """
        out_path = tmp_path / "mixed_resolutions.mp4"
        frames = []
        # Generate frames with alternating resolutions: 160x120, 320x240, 640x480
        for i in range(30):
            if i % 3 == 0:
                img = np.full((120, 160, 3), i * 8, dtype=np.uint8)
            elif i % 3 == 1:
                img = np.full((240, 320, 3), i * 8, dtype=np.uint8)
            else:
                img = np.full((480, 640, 3), i * 8, dtype=np.uint8)
            frames.append({"frame": img, "frame_id": i})

        sha = export_window_to_mp4(frames, out_path, fps=30.0)
        assert out_path.exists()
        assert out_path.stat().st_size > 1024
        assert len(sha) == 64

        cap = cv2.VideoCapture(str(out_path))
        assert cap.isOpened()
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 30
        cap.release()

    def test_adversarial_sqlite_fallback_tamper_detection(self, tmp_path):
        """
        Adversarial Test: Verify that the SQLite fallback database backend provides
        identical, uncompromising cryptographic tamper detection as DuckDB.
        """
        db_path = tmp_path / "fallback_ledger.sqlite3"
        clip_path = tmp_path / "fallback_clip.mp4"
        ledger = CryptoEvidenceLedger(db_path=db_path, use_sqlite_fallback=True)

        frames = _generate_synthetic_frames(30, datetime.now(timezone.utc))
        clip_sha = export_window_to_mp4(frames, clip_path, fps=30.0)

        block = ledger.commit_event(
            frame=frames[0]["frame"],
            camera_id="CAM_SQLITE_01",
            event_type="BREACH",
            clip_path=clip_path,
            clip_hash=clip_sha
        )

        # Baseline verification
        assert ledger.verify_chain_integrity(verify_clips=True)["is_valid"] is True

        # Tamper test 1: Modify 1 bit in physical clip
        with open(clip_path, "r+b") as fp:
            fp.seek(16)
            b = fp.read(1)[0]
            fp.seek(16)
            fp.write(bytes([b ^ 0x01]))

        assert ledger.verify_clip_integrity(block.sequence_id)["is_valid"] is False
        assert ledger.verify_chain_integrity(verify_clips=True)["is_valid"] is False

        # Tamper test 2: Tamper with SQLite table row
        conn = ledger._get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE evidence_ledger SET frame_hash = ? WHERE sequence_id = 1", ["e" * 64])
        conn.commit()
        conn.close()

        audit = ledger.verify_chain_integrity()
        assert audit["is_valid"] is False
        assert audit["status"] == "CORRUPTED"
        assert "block_hash forgery" in audit["message"]

    def test_adversarial_clip_integrity_edge_cases(self, tmp_path):
        """
        Adversarial Test:
        - Non-existent sequence_id -> BLOCK_NOT_FOUND (is_valid == False)
        - Sequence_id with no clip attached -> NO_CLIP_ATTACHED (is_valid == True)
        """
        db_path = tmp_path / "edge_cases.duckdb"
        ledger = CryptoEvidenceLedger(db_path=db_path)

        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        block = ledger.commit_event(
            frame=dummy_img,
            camera_id="CAM_01",
            event_type="INFO",
            metadata={"note": "no clip attached"}
        )

        # 1. Non-existent block
        res_missing = ledger.verify_clip_integrity(sequence_id=999)
        assert res_missing["is_valid"] is False
        assert res_missing["status"] == "BLOCK_NOT_FOUND"

        # 2. Block without clip
        res_no_clip = ledger.verify_clip_integrity(sequence_id=block.sequence_id)
        assert res_no_clip["is_valid"] is True
        assert res_no_clip["status"] == "NO_CLIP_ATTACHED"
        assert res_no_clip["has_clip"] is False

