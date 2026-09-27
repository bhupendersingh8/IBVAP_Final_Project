"""
tests/test_evidence_retention.py
================================
Unit tests for IBVAP Evidence Retention Manager and FIFO Circular Eviction Policy.
"""
from __future__ import annotations

import os
import time
import shutil
import tempfile
import pytest
from services.evidence.retention_manager import EvidenceRetentionManager
from ml.continuous_learning.auto_curator import AutoCurator


@pytest.fixture
def temp_evidence_dir():
    tmp = tempfile.mkdtemp()
    evidence_dir = os.path.join(tmp, "data", "evidence")
    labeled_dir = os.path.join(tmp, "data", "labeled")
    os.makedirs(evidence_dir, exist_ok=True)
    os.makedirs(labeled_dir, exist_ok=True)
    yield tmp, evidence_dir, labeled_dir
    shutil.rmtree(tmp, ignore_errors=True)


def test_retention_under_limit(temp_evidence_dir):
    tmp_root, evidence_dir, _ = temp_evidence_dir
    retention = EvidenceRetentionManager(
        evidence_dir=evidence_dir,
        max_photos=100,
        project_root=tmp_root,
    )

    # Create 50 dummy evidence files
    for i in range(50):
        fpath = os.path.join(evidence_dir, f"evidence_{i:04d}.jpg")
        with open(fpath, "wb") as f:
            f.write(b"\xFF\xD8\xFF\xE0" + b"\x00" * 32)

    stats = retention.get_stats()
    assert stats["total_evidence_photos"] == 50
    assert stats["excess_photos"] == 0
    assert not stats["is_overflowing"]

    # Enforce retention - should delete 0 files
    deleted = retention.enforce_retention()
    assert deleted == 0
    assert retention.get_stats()["total_evidence_photos"] == 50


def test_fifo_pruning_over_limit(temp_evidence_dir):
    tmp_root, evidence_dir, _ = temp_evidence_dir
    retention = EvidenceRetentionManager(
        evidence_dir=evidence_dir,
        max_photos=20,  # Test threshold = 20
        project_root=tmp_root,
    )

    # Create 35 dummy files with distinct timestamps
    base_time = 1700000000.0
    created_files = []
    for i in range(35):
        fpath = os.path.join(evidence_dir, f"evidence_{i:04d}.jpg")
        with open(fpath, "wb") as f:
            f.write(b"\xFF\xD8\xFF\xE0" + b"\x00" * 32)
        # Explicit mtime
        file_mtime = base_time + (i * 10)
        os.utime(fpath, (file_mtime, file_mtime))
        created_files.append((fpath, file_mtime))

    stats = retention.get_stats()
    assert stats["total_evidence_photos"] == 35
    assert stats["excess_photos"] == 15
    assert stats["is_overflowing"]

    # Enforce retention: should delete 15 oldest (indices 0..14)
    deleted = retention.enforce_retention()
    assert deleted == 15

    final_stats = retention.get_stats()
    assert final_stats["total_evidence_photos"] == 20
    assert final_stats["excess_photos"] == 0

    # Verify that the 15 oldest are gone
    for i in range(15):
        assert not os.path.exists(created_files[i][0]), f"Oldest file {created_files[i][0]} was not pruned"

    # Verify that the 20 newest remain intact
    for i in range(15, 35):
        assert os.path.exists(created_files[i][0]), f"Recent file {created_files[i][0]} was incorrectly pruned"


def test_preserved_files_immunity(temp_evidence_dir):
    tmp_root, evidence_dir, _ = temp_evidence_dir
    retention = EvidenceRetentionManager(
        evidence_dir=evidence_dir,
        max_photos=5,
        project_root=tmp_root,
    )

    # Create live preview files with very old timestamps
    live_1 = os.path.join(evidence_dir, "live_CAM-01.jpg")
    live_2 = os.path.join(evidence_dir, "live_annotated_CAM-01.jpg")
    with open(live_1, "wb") as f:
        f.write(b"\xFF\xD8\xFF\xE0" + b"\x00" * 32)
    with open(live_2, "wb") as f:
        f.write(b"\xFF\xD8\xFF\xE0" + b"\x00" * 32)

    old_time = 1600000000.0
    os.utime(live_1, (old_time, old_time))
    os.utime(live_2, (old_time, old_time))

    # Create 10 regular evidence files with newer timestamps
    for i in range(10):
        fpath = os.path.join(evidence_dir, f"evidence_{i:04d}.jpg")
        with open(fpath, "wb") as f:
            f.write(b"\xFF\xD8\xFF\xE0" + b"\x00" * 32)

    stats = retention.get_stats()
    assert stats["preserved_preview_files"] == 2
    assert stats["total_evidence_photos"] == 10

    # Prune down to 5
    deleted = retention.enforce_retention()
    assert deleted == 5

    # Immunity check: live preview files must STILL exist!
    assert os.path.exists(live_1)
    assert os.path.exists(live_2)
    assert retention.get_stats()["total_evidence_photos"] == 5


def test_curate_and_prune_integration(temp_evidence_dir):
    tmp_root, evidence_dir, labeled_dir = temp_evidence_dir
    import numpy as np
    import cv2

    curator = AutoCurator(
        project_root=tmp_root,
        evidence_dir=os.path.relpath(evidence_dir, tmp_root),
        labeled_dir=os.path.relpath(labeled_dir, tmp_root),
        manifest_path="data/manifest.json",
    )

    # Write 8 dummy images
    for i in range(8):
        img = np.full((160, 160, 3), 100 + i * 10, dtype=np.uint8)
        cv2.imwrite(os.path.join(evidence_dir, f"evidence_{i:03d}.jpg"), img)

    # Curate and prune to max 4 photos
    res = curator.curate_and_prune(max_evidence_photos=4)
    assert res["pruned_evidence_count"] == 4
    assert res["remaining_evidence_photos"] == 4
    assert res["max_photos_limit"] == 4
