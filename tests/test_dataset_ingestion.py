"""
Comprehensive Unit Tests for Phase B Dataset Ingestion & Annotation Pipeline.
Tests:
- Quality filtering (resolution, blur, contrast, corrupted frames)
- Duplicate detection across sequential frames
- Frame extraction tool with SHA-256 calculation
- JSON Lines frames manifest verification
- Sequence-aware dataset splitting (temporal leakage prevention)
- YOLO annotation import & pre-validation
- Dataset versioning metadata & honest status reporting
- ANPR directory separation check
"""
import os
import shutil
import tempfile
import json
import hashlib
import pytest
import numpy as np
import cv2

from ml.dataset.quality import QualityFilter, QualityThresholds, QualityStatus, LightingCondition
from ml.dataset.splitter import DatasetSplitter, extract_sequence_key
from ml.dataset.versioning import DatasetVersionManager, DatasetVersionMeta
from scripts.collect_dataset_frames import collect_frames, sanitize_source_id
from scripts.import_yolo_dataset import import_dataset

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# ── 1. Quality Filter Tests ──────────────────────────────────────────────────

def test_quality_filter_good_frame():
    """Sharp, well-exposed frame passes as GOOD."""
    qf = QualityFilter(thresholds=QualityThresholds(min_width=640, min_height=360))
    # Create a 640x360 frame with sharp high-contrast text and geometric structures
    frame = np.full((360, 640, 3), 128, dtype=np.uint8)
    cv2.putText(frame, "IBVAP HIGH-RES CAM", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
    cv2.putText(frame, "PERIMETER MONITORING", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    cv2.rectangle(frame, (400, 50), (600, 250), (240, 240, 240), -1)
    cv2.circle(frame, (500, 150), 40, (10, 10, 10), -1)

    assessment = qf.assess_frame(frame)
    assert assessment.status == QualityStatus.GOOD
    assert assessment.is_corrupt is False
    assert assessment.width == 640
    assert assessment.height == 360
    assert assessment.blur_score > 30.0


def test_quality_filter_corrupt_and_empty():
    """None or empty frame is immediately rejected with corrupt flag."""
    qf = QualityFilter()
    res1 = qf.assess_frame(None)
    assert res1.status == QualityStatus.REJECTED
    assert res1.is_corrupt is True

    res2 = qf.assess_frame(np.zeros((0, 0, 3), dtype=np.uint8))
    assert res2.status == QualityStatus.REJECTED
    assert res2.is_corrupt is True


def test_quality_filter_blurry_and_low_contrast():
    """Flat, blurry frame is flagged as LOW_QUALITY."""
    qf = QualityFilter()
    # Uniform gray frame: zero blur score and zero contrast
    flat_frame = np.full((360, 640, 3), 128, dtype=np.uint8)
    assessment = qf.assess_frame(flat_frame)

    assert assessment.status == QualityStatus.LOW_QUALITY
    assert assessment.blur_score < 1.0
    assert assessment.contrast < 1.0
    assert any("Blur score" in r for r in assessment.rejection_reasons)


def test_quality_filter_duplicate_detection():
    """Near-identical frame in sequence is correctly identified as DUPLICATE."""
    qf = QualityFilter(thresholds=QualityThresholds(duplicate_sim_threshold=0.95))
    frame1 = np.full((360, 640, 3), 120, dtype=np.uint8)
    cv2.rectangle(frame1, (100, 50), (300, 250), (250, 250, 250), -1)
    cv2.rectangle(frame1, (350, 50), (550, 250), (10, 10, 10), -1)
    cv2.putText(frame1, "BASE SEQ FRAME", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)

    # First frame -> GOOD
    res1 = qf.assess_frame(frame1)
    assert res1.status == QualityStatus.GOOD

    # Near identical frame (1 pixel difference) -> DUPLICATE
    frame2 = frame1.copy()
    frame2[0, 0, 0] = (frame2[0, 0, 0] + 1) % 255
    res2 = qf.assess_frame(frame2)
    assert res2.status == QualityStatus.DUPLICATE
    assert res2.is_duplicate is True


# ── 2. Frame Extraction & SHA-256 Manifest Tests ─────────────────────────────

def test_frame_collector_video_extraction_and_manifest():
    """Extracts frames from video, computes SHA-256, and writes JSONL manifest."""
    tmp_dir = tempfile.mkdtemp()
    try:
        # Create a small synthetic video with 10 frames
        vid_path = os.path.join(tmp_dir, "synth_feed.avi")
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        out_vid = cv2.VideoWriter(vid_path, fourcc, 10.0, (640, 360))
        for i in range(10):
            f = np.zeros((360, 640, 3), dtype=np.uint8)
            f[i * 20:(i + 1) * 20, :, :] = 200
            out_vid.write(f)
        out_vid.release()

        frames_out = os.path.join(tmp_dir, "extracted")
        manifest_out = os.path.join(tmp_dir, "frames.jsonl")

        stats = collect_frames(
            input_source=vid_path,
            output_dir=frames_out,
            fps_sample=5.0,
            max_frames=3,
            min_width=640,
            min_height=360,
            source_id="SYNTH-CAM",
            manifest_path=manifest_out,
        )

        assert stats["frames_extracted"] == 3
        assert os.path.isfile(manifest_out)

        # Read manifest and verify SHA-256 matches disk file
        with open(manifest_out, "r", encoding="utf-8") as mf:
            lines = [json.loads(l) for l in mf if l.strip()]

        assert len(lines) == 3
        first_record = lines[0]
        assert first_record["source_id"] == "SYNTH-CAM"
        assert "source_path_hash" in first_record
        assert "frame_number" in first_record
        assert "timestamp" in first_record
        assert "collection_time" in first_record
        assert first_record["provenance_status"] == "PROVENANCE_UNKNOWN"
        assert first_record["width"] == 640
        assert first_record["height"] == 360

        # Verify disk file sha256
        saved_file = os.path.join(frames_out, os.path.basename(first_record["path"]))
        assert os.path.isfile(saved_file)
        with open(saved_file, "rb") as sf:
            actual_sha = hashlib.sha256(sf.read()).hexdigest()
        assert actual_sha == first_record["sha256"]

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_sanitize_source_id():
    """Removes passwords from RTSP URLs and cleans unsafe characters."""
    clean1 = sanitize_source_id("rtsp://admin:secretPass123@192.168.1.50:554/live")
    assert "secretPass123" not in clean1
    assert "admin" not in clean1

    clean2 = sanitize_source_id("CAM-01:East Gate!")
    assert ":" not in clean2
    assert "!" not in clean2


# ── 3. Sequence-Aware Dataset Splitting Tests ────────────────────────────────

def test_sequence_aware_splitting():
    """Frames from the same sequence cluster stay together to prevent leakage."""
    tmp_src_img = tempfile.mkdtemp()
    tmp_src_lbl = tempfile.mkdtemp()
    tmp_dst = tempfile.mkdtemp()

    try:
        # Create 2 distinct sequence groups: CAM-01 (6 frames) and CAM-02 (6 frames)
        for i in range(6):
            p1 = os.path.join(tmp_src_img, f"CAM-01_f{i:03d}.jpg")
            p2 = os.path.join(tmp_src_img, f"CAM-02_f{i:03d}.jpg")
            cv2.imwrite(p1, np.zeros((100, 100, 3), dtype=np.uint8))
            cv2.imwrite(p2, np.zeros((100, 100, 3), dtype=np.uint8))

        splitter = DatasetSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42)
        splits = splitter.split_dataset(
            source_images_dir=tmp_src_img,
            source_labels_dir=tmp_src_lbl,
            target_dataset_root=tmp_dst,
            copy_files=False,
            sequence_aware=True,
        )

        # Check that CAM-01 frames do NOT leak across train and test
        cam1_splits = set()
        cam2_splits = set()
        for split_name, files in splits.items():
            for f in files:
                if "CAM-01" in f:
                    cam1_splits.add(split_name)
                elif "CAM-02" in f:
                    cam2_splits.add(split_name)

        # In sequence-aware mode with 2 sources, each source belongs to exactly 1 split
        assert len(cam1_splits) == 1
        assert len(cam2_splits) == 1

    finally:
        shutil.rmtree(tmp_src_img, ignore_errors=True)
        shutil.rmtree(tmp_src_lbl, ignore_errors=True)
        shutil.rmtree(tmp_dst, ignore_errors=True)


# ── 4. Annotation Import Tests ──────────────────────────────────────────────

def test_import_yolo_dataset_workflow():
    """Validates and stages incoming YOLO annotation pairs."""
    tmp_src_img = tempfile.mkdtemp()
    tmp_src_lbl = tempfile.mkdtemp()
    tmp_target = tempfile.mkdtemp()

    try:
        # Valid pair
        f1 = np.zeros((360, 640, 3), dtype=np.uint8)
        f1[:100, :100] = 255
        cv2.imwrite(os.path.join(tmp_src_img, "frame_01.jpg"), f1)
        with open(os.path.join(tmp_src_lbl, "frame_01.txt"), "w", encoding="utf-8") as f:
            f.write("0 0.5 0.5 0.2 0.3\n")

        # Invalid pair (malformed coordinates)
        f2 = np.zeros((360, 640, 3), dtype=np.uint8)
        f2[200:, 200:] = 255
        cv2.imwrite(os.path.join(tmp_src_img, "frame_02.jpg"), f2)
        with open(os.path.join(tmp_src_lbl, "frame_02.txt"), "w", encoding="utf-8") as f:
            f.write("0 1.8 0.5 0.2 0.3\n")  # x=1.8 out of bounds

        # Strict import should fail
        res_fail = import_dataset(
            source_images=tmp_src_img,
            source_labels=tmp_src_lbl,
            target_dataset=tmp_target,
            strict=True,
        )
        assert res_fail is False

        # Fix bad pair
        with open(os.path.join(tmp_src_lbl, "frame_02.txt"), "w", encoding="utf-8") as f:
            f.write("1 0.4 0.4 0.3 0.3\n")

        res_pass = import_dataset(
            source_images=tmp_src_img,
            source_labels=tmp_src_lbl,
            target_dataset=tmp_target,
            strict=True,
        )
        assert res_pass is True

    finally:
        shutil.rmtree(tmp_src_img, ignore_errors=True)
        shutil.rmtree(tmp_src_lbl, ignore_errors=True)
        shutil.rmtree(tmp_target, ignore_errors=True)


# ── 5. Dataset Versioning & Governance Tests ─────────────────────────────────

def test_dataset_versioning_manager_unpopulated():
    """Unpopulated dataset accurately reports unpopulated status and NOT_AVAILABLE for night/ir."""
    tmp_ds = tempfile.mkdtemp()
    try:
        for s in ["train", "val", "test"]:
            os.makedirs(os.path.join(tmp_ds, "images", s), exist_ok=True)
            os.makedirs(os.path.join(tmp_ds, "labels", s), exist_ok=True)

        vm = DatasetVersionManager(dataset_root=tmp_ds)
        meta = vm.compute_metadata("v1.0.0")

        assert meta.status == "UNPOPULATED_AWAITING_FIELD_DATA"
        assert meta.provenance == "PROVENANCE_UNKNOWN_AWAITING_FIELD_DATA"
        assert meta.total_images == 0
        assert meta.total_annotations == 0
        assert meta.night_data_status == "NOT_AVAILABLE"
        assert meta.ir_data_status == "NOT_AVAILABLE"

    finally:
        shutil.rmtree(tmp_ds, ignore_errors=True)


def test_anpr_directory_separation():
    """ANPR dataset directory is distinct and contains specifications."""
    anpr_readme = os.path.join(PROJECT_ROOT, "dataset", "anpr", "README.md")
    assert os.path.isfile(anpr_readme)
    with open(anpr_readme, "r", encoding="utf-8") as f:
        content = f.read()
    assert "SEPARATED" in content
    assert "license_plate" in content
