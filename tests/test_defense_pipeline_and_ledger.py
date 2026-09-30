"""
tests/test_defense_pipeline_and_ledger.py
=========================================
Unit and integration tests for:
1. Cryptographic SHA-256 Merkle Ledger (crypto_ledger.py)
2. Physical Weights & Border Datasets (download_weights_and_datasets.py)
3. IBVAP Unified Defense Execution Pipeline (main_pipeline.py)
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pytest
import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crypto_ledger import (
    CryptoEvidenceLedger,
    compute_frame_hash,
    compute_block_hash,
    compute_merkle_root,
    GENESIS_PREVIOUS_HASH
)
from main_pipeline import PipelineConfig, IBVAPUnifiedPipeline, ThreadedVideoSource


# ---------------------------------------------------------------------------
# Test Suite 1: Cryptographic Evidence Ledger & Merkle Chaining
# ---------------------------------------------------------------------------

def test_frame_hash_determinism():
    """Verify that identical frames generate identical SHA-256 digests."""
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    h1 = compute_frame_hash(frame)
    h2 = compute_frame_hash(frame)
    assert h1 == h2
    assert len(h1) == 64

    # Different frame produces different digest
    frame_diff = np.ones((100, 100, 3), dtype=np.uint8)
    h3 = compute_frame_hash(frame_diff)
    assert h1 != h3


def test_merkle_root_calculation():
    """Verify binary Merkle tree root calculation."""
    h1 = "a" * 64
    h2 = "b" * 64
    root = compute_merkle_root([h1, h2])
    assert len(root) == 64

    # Empty list returns genesis hash
    assert compute_merkle_root([]) == GENESIS_PREVIOUS_HASH


def test_ledger_sequential_linking_and_tamper_detection(tmp_path):
    """Verify sequential block chaining and tamper detection in an isolated database."""
    db_file = tmp_path / "test_ledger.duckdb"
    ledger = CryptoEvidenceLedger(db_path=db_file)

    test_frame = np.full((100, 100, 3), 128, dtype=np.uint8)

    # 1. Commit block 1
    b1 = ledger.commit_event(
        frame=test_frame,
        camera_id="CAM_TEST_01",
        event_type="PERIMETER_BREACH",
        metadata={"intruder": "person_01"}
    )
    assert b1.sequence_id == 1
    assert b1.previous_hash == GENESIS_PREVIOUS_HASH
    assert len(b1.block_hash) == 64

    # 2. Commit block 2
    b2 = ledger.commit_event(
        frame=test_frame,
        camera_id="CAM_TEST_01",
        event_type="VEHICLE_ALERT",
        metadata={"plate": "DL01AA0001"}
    )
    assert b2.sequence_id == 2
    assert b2.previous_hash == b1.block_hash

    # 3. Verify integrity
    audit = ledger.verify_chain_integrity()
    assert audit["is_valid"] is True
    assert audit["total_blocks"] == 2
    assert audit["status"] == "VERIFIED"

    # 4. Tamper with block 1 and verify tamper detection
    tamper_audit = ledger.tamper_test_simulation(block_seq_id=1)
    assert tamper_audit["is_valid"] is False
    assert tamper_audit["corrupted_block_id"] == 1
    assert tamper_audit["status"] == "CORRUPTED"


def test_audit_certificate_generation(tmp_path):
    """Verify Section 65B certificate generation."""
    db_file = tmp_path / "cert_ledger.duckdb"
    cert_file = tmp_path / "cert.json"
    ledger = CryptoEvidenceLedger(db_path=db_file)

    test_frame = np.zeros((50, 50, 3), dtype=np.uint8)
    ledger.commit_event(test_frame, "CAM_01", "TEST_ALERT")

    cert = ledger.export_audit_certificate(output_path=cert_file)
    assert cert["is_tamper_free"] is True
    assert cert["total_evidence_blocks"] == 1
    assert cert_file.exists()


# ---------------------------------------------------------------------------
# Test Suite 2: Physical Weights & Datasets Staging
# ---------------------------------------------------------------------------

def test_physical_weights_present():
    """Verify all four production model checkpoints exist and meet minimum size."""
    weights_dir = PROJECT_ROOT / "weights"
    assert (weights_dir / "yolo11n.pt").exists()
    assert (weights_dir / "yolo11n.pt").stat().st_size >= 5_000_000

    assert (weights_dir / "rtdetr-l.pt").exists()
    assert (weights_dir / "rtdetr-l.pt").stat().st_size >= 60_000_000

    assert (weights_dir / "mobile_sam.pt").exists()
    assert (weights_dir / "mobile_sam.pt").stat().st_size >= 38_000_000

    assert (weights_dir / "arcface_w600k_r50.onnx").exists()
    assert (weights_dir / "arcface_w600k_r50.onnx").stat().st_size >= 160_000_000


def test_datasets_scaffold_present():
    """Verify border dataset directories and metadata exist."""
    datasets_dir = PROJECT_ROOT / "datasets"

    # ExDark
    assert (datasets_dir / "exdark" / "classes.txt").exists()
    assert (datasets_dir / "exdark" / "dataset_info.json").exists()

    # LLVIP
    assert (datasets_dir / "llvip" / "dataset_info.json").exists()

    # RESIDE-RTTS
    assert (datasets_dir / "reside_rtts" / "dataset_info.json").exists()


# ---------------------------------------------------------------------------
# Test Suite 3: Unified Pipeline Execution
# ---------------------------------------------------------------------------

def test_threaded_video_source():
    """Verify non-blocking threaded video source generation."""
    source = ThreadedVideoSource(source="synthetic", queue_size=8).start()
    ret, frame_id, frame = source.read(timeout=1.0)
    source.stop()

    assert ret is True
    assert frame_id >= 1
    assert frame is not None
    assert frame.shape == (480, 640, 3)


def test_pipeline_single_frame_execution():
    """Verify full 7-stage processing on a synthetic frame."""
    config = PipelineConfig(
        source="synthetic",
        model_name="yolo11n",
        tracker_type="bytetrack",
        enable_ws=False,
        max_frames=1
    )
    pipeline = IBVAPUnifiedPipeline(config)

    # Low light frame (luminance < 40)
    dark_frame = np.full((480, 640, 3), 20, dtype=np.uint8)
    summary = pipeline.process_frame(dark_frame, frame_id=1)

    assert summary["frame_id"] == 1
    assert summary["restoration_applied"] is True  # Zero-DCE++ was triggered
    assert "latencies_ms" in summary
    assert "restoration_ms" in summary["latencies_ms"]
    assert "detection_ms" in summary["latencies_ms"]
    assert "tracking_ms" in summary["latencies_ms"]


def test_concurrent_ledger_commits(tmp_path):
    """Verify thread safety and atomic Merkle chaining under high-concurrency multi-threaded writes."""
    from concurrent.futures import ThreadPoolExecutor

    db_file = tmp_path / "concurrent_ledger.duckdb"
    ledger = CryptoEvidenceLedger(db_path=db_file)
    test_frame = np.full((100, 100, 3), 150, dtype=np.uint8)

    num_threads = 5
    commits_per_thread = 4
    total_events = num_threads * commits_per_thread

    def _worker(thread_id: int):
        for i in range(commits_per_thread):
            ledger.commit_event(
                frame=test_frame,
                camera_id=f"CAM_{thread_id}",
                event_type="CONCURRENT_EVENT",
                metadata={"thread": thread_id, "idx": i},
                severity="INFO"
            )

    with ThreadPoolExecutor(max_workers=num_threads) as pool:
        futures = [pool.submit(_worker, tid) for tid in range(num_threads)]
        for fut in futures:
            fut.result()

    audit = ledger.verify_chain_integrity()
    assert audit["is_valid"] is True
    assert audit["total_blocks"] == total_events
    assert audit["status"] == "VERIFIED"


def test_tamper_simulation_non_destructive(tmp_path):
    """Verify that tamper_test_simulation with restore=True leaves the ledger valid afterwards."""
    db_file = tmp_path / "tamper_restore_ledger.duckdb"
    ledger = CryptoEvidenceLedger(db_path=db_file)
    test_frame = np.full((100, 100, 3), 80, dtype=np.uint8)

    ledger.commit_event(test_frame, "CAM_01", "EVENT_1")
    ledger.commit_event(test_frame, "CAM_01", "EVENT_2")

    # Run tamper simulation with restore=True
    tamper_audit = ledger.tamper_test_simulation(block_seq_id=1, restore=True)
    assert tamper_audit["is_valid"] is False
    assert tamper_audit["corrupted_block_id"] == 1
    assert tamper_audit.get("restored") is True

    # Ledger must be back to 100% valid state
    post_restore = ledger.verify_chain_integrity()
    assert post_restore["is_valid"] is True
    assert post_restore["total_blocks"] == 2


def test_pipeline_real_cctv_frame_detection_and_tracking():
    """Verify that the unified pipeline detects and tracks targets on real border CCTV frames."""
    test_img = PROJECT_ROOT / "dataset" / "images" / "test" / "frame_0820.jpg"
    if not test_img.exists():
        pytest.skip("Test CCTV image not found")

    frame = cv2.imread(str(test_img))
    assert frame is not None

    config = PipelineConfig(
        source=str(test_img),
        model_name="yolo11n",
        tracker_type="bytetrack",
        enable_ws=False,
        max_frames=1
    )
    pipeline = IBVAPUnifiedPipeline(config)
    res = pipeline.process_frame(frame, frame_id=1)

    assert res["frame_id"] == 1
    assert "tracks" in res
    assert res["active_tracks_count"] > 0
    first_track = res["tracks"][0]
    assert "bbox" in first_track
    assert "class_name" in first_track
    assert first_track["confidence"] > 0.20
