"""
Unit and Integration Tests for Continuous Self-Training Subsystem in IBVAP.
Tests:
- AutoCurator ingestion, YOLO annotation generation, and SHA-256 deduplication
- AutoTrainer status, dataset partitioning, and threshold gating
"""
from __future__ import annotations

import os
import shutil
import tempfile
import cv2
import numpy as np
import pytest

from ml.continuous_learning.auto_curator import AutoCurator
from ml.continuous_learning.auto_trainer import AutoTrainer, ContinuousLearningConfig


@pytest.fixture
def temp_env():
    tmp_root = tempfile.mkdtemp()
    evidence_dir = os.path.join(tmp_root, "data", "evidence")
    labeled_dir = os.path.join(tmp_root, "data", "labeled")
    dataset_dir = os.path.join(tmp_root, "dataset")

    os.makedirs(evidence_dir, exist_ok=True)
    os.makedirs(labeled_dir, exist_ok=True)
    os.makedirs(dataset_dir, exist_ok=True)

    # Sample dataset.yaml
    with open(os.path.join(dataset_dir, "dataset.yaml"), "w") as f:
        f.write("path: .\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: person\nnc: 1\n")

    yield tmp_root
    shutil.rmtree(tmp_root, ignore_errors=True)


def test_auto_curator_deduplication(temp_env):
    curator = AutoCurator(
        project_root=temp_env,
        evidence_dir="data/evidence",
        labeled_dir="data/labeled",
        manifest_path="data/dataset_manifest.json"
    )

    # Create dummy image
    img = np.full((320, 320, 3), 128, dtype=np.uint8)
    cv2.circle(img, (160, 160), 40, (255, 255, 255), -1)
    test_path = os.path.join(temp_env, "data", "evidence", "test_frame.jpg")
    cv2.imwrite(test_path, img)

    # First curation
    entry1 = curator.curate_image(test_path, camera_id="CAM-01")
    assert entry1 is not None
    assert "sample_id" in entry1
    assert os.path.exists(os.path.join(temp_env, "data", "labeled", "images", f"{entry1['sample_id']}.jpg"))
    assert os.path.exists(os.path.join(temp_env, "data", "labeled", "labels", f"{entry1['sample_id']}.txt"))

    # Second curation on identical image (must be skipped by deduplication)
    entry2 = curator.curate_image(test_path, camera_id="CAM-01")
    assert entry2 is None


def test_auto_curator_curate_all(temp_env):
    curator = AutoCurator(
        project_root=temp_env,
        evidence_dir="data/evidence",
        labeled_dir="data/labeled",
        manifest_path="data/dataset_manifest.json"
    )

    # Create 3 distinct images
    for i in range(3):
        img = np.full((240, 240, 3), 50 + i * 40, dtype=np.uint8)
        cv2.putText(img, f"Frame {i}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.imwrite(os.path.join(temp_env, "data", "evidence", f"evidence_{i}.jpg"), img)

    res = curator.curate_all_evidence()
    assert res["curated"] == 3
    assert res["total_labeled_available"] == 3


def test_auto_trainer_status_and_threshold_gate(temp_env):
    cfg = ContinuousLearningConfig(
        min_samples_to_train=5,
        epochs=1,
        batch=2,
        dataset_yaml="dataset/dataset.yaml"
    )
    trainer = AutoTrainer(project_root=temp_env, config=cfg)

    status = trainer.get_status()
    assert status["state"] == "idle"
    assert status["ready_to_train"] is False
    assert status["curated_samples_available"] == 0

    # Running training without force should skip cleanly
    res = trainer.run_self_training_cycle(force=False)
    assert res["status"] == "SKIPPED_INSUFFICIENT_SAMPLES"


def test_auto_trainer_dataset_partitioning(temp_env):
    cfg = ContinuousLearningConfig(min_samples_to_train=2)
    trainer = AutoTrainer(project_root=temp_env, config=cfg)

    # Create 4 synthetic labeled pairs in data/labeled
    img_dir = os.path.join(temp_env, "data", "labeled", "images")
    lbl_dir = os.path.join(temp_env, "data", "labeled", "labels")

    for i in range(4):
        img = np.full((200, 200, 3), 100 + i * 20, dtype=np.uint8)
        cv2.imwrite(os.path.join(img_dir, f"sample_{i}.jpg"), img)
        with open(os.path.join(lbl_dir, f"sample_{i}.txt"), "w") as f:
            f.write("0 0.5 0.5 0.3 0.3\n")

    ok = trainer.partition_dataset()
    assert ok is True
    assert os.path.exists(os.path.join(temp_env, "dataset", "images", "train"))
    assert os.path.exists(os.path.join(temp_env, "dataset", "labels", "train"))
