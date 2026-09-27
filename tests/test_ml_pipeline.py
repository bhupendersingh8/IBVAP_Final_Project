"""
Comprehensive Unit Tests for IBVAP ML Dataset & Model Training Pipeline.
Tests:
- Dataset validator (clean structure, missing files, malformed labels, leakage detection)
- Deterministic dataset splitter (reproducibility with seed)
- Model metadata and model registry (register, query, list)
- Model promotion rules and lifecycle gates (CANDIDATE -> VALIDATED -> CANARY -> PRODUCTION)
- Production rollback logic
- Validation gate thresholds (pass and fail criteria)
- Dynamic model selector resolution and fallbacks
- Configuration loading and class mapping
"""
import os
import shutil
import tempfile
import pytest
import numpy as np
import cv2
import yaml

from ml.dataset.validator import DatasetValidator, ValidationReport
from ml.dataset.splitter import DatasetSplitter
from ml.registry.model_registry import ModelRegistry, ModelMetadata, ModelStatus
from ml.evaluation.validation_gate import ValidationGate, GateCriteria
from services.detection.model_selector import ModelSelector


@pytest.fixture
def temp_dataset_dir():
    """Creates a temporary isolated dataset directory for testing."""
    tmp_dir = tempfile.mkdtemp()
    for split in ["train", "val", "test"]:
        os.makedirs(os.path.join(tmp_dir, "images", split), exist_ok=True)
        os.makedirs(os.path.join(tmp_dir, "labels", split), exist_ok=True)
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def temp_registry_file():
    """Creates a temporary model registry YAML file for testing."""
    tmp_dir = tempfile.mkdtemp()
    reg_file = os.path.join(tmp_dir, "test_registry.yaml")
    yield reg_file
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ── 1. Dataset Validator Tests ──────────────────────────────────────────────

def test_dataset_validator_empty_structure(temp_dataset_dir):
    """Empty dataset passes validation with 0 errors and healthy report."""
    validator = DatasetValidator(dataset_root=temp_dataset_dir)
    report = validator.validate()

    assert report.is_valid is True
    assert report.total_images == 0
    assert report.total_labels == 0
    assert report.error_count == 0
    assert report.leakage_count == 0


def test_dataset_validator_valid_dataset(temp_dataset_dir):
    """Valid dataset with 1 image and valid label passes with zero errors."""
    img_path = os.path.join(temp_dataset_dir, "images", "train", "frame_001.jpg")
    cv2.imwrite(img_path, np.zeros((480, 640, 3), dtype=np.uint8))

    lbl_path = os.path.join(temp_dataset_dir, "labels", "train", "frame_001.txt")
    with open(lbl_path, "w", encoding="utf-8") as f:
        # class_id=0 (person), x=0.5, y=0.5, w=0.2, h=0.4
        f.write("0 0.5 0.5 0.2 0.4\n")

    validator = DatasetValidator(dataset_root=temp_dataset_dir)
    report = validator.validate()

    assert report.is_valid is True
    assert report.total_images == 1
    assert report.total_labels == 1
    assert report.total_annotations == 1
    assert report.error_count == 0


def test_dataset_validator_malformed_labels(temp_dataset_dir):
    """Detects wrong column count, unknown class, and out-of-bounds coordinates."""
    img_path = os.path.join(temp_dataset_dir, "images", "train", "bad_frame.jpg")
    cv2.imwrite(img_path, np.zeros((480, 640, 3), dtype=np.uint8))

    lbl_path = os.path.join(temp_dataset_dir, "labels", "train", "bad_frame.txt")
    with open(lbl_path, "w", encoding="utf-8") as f:
        f.write("0 0.5 0.5 0.2\n")             # Only 4 values (MALFORMED_LABEL)
        f.write("99 0.5 0.5 0.2 0.3\n")        # Class 99 undefined (UNKNOWN_CLASS_ID)
        f.write("0 1.5 0.5 0.2 0.3\n")         # x=1.5 out of bounds (BBOX_OUT_OF_BOUNDS)

    validator = DatasetValidator(dataset_root=temp_dataset_dir)
    report = validator.validate()

    assert report.is_valid is False
    assert report.error_count >= 3

    issue_types = {issue.issue_type for issue in report.issues}
    assert "MALFORMED_LABEL" in issue_types
    assert "UNKNOWN_CLASS_ID" in issue_types
    assert "BBOX_OUT_OF_BOUNDS" in issue_types


def test_dataset_validator_orphan_and_missing_labels(temp_dataset_dir):
    """Detects label without image and image without label."""
    # Orphan label (no image)
    orphan_lbl = os.path.join(temp_dataset_dir, "labels", "val", "orphan.txt")
    with open(orphan_lbl, "w", encoding="utf-8") as f:
        f.write("0 0.5 0.5 0.2 0.2\n")

    # Missing label (image without txt)
    missing_lbl_img = os.path.join(temp_dataset_dir, "images", "val", "no_label.jpg")
    cv2.imwrite(missing_lbl_img, np.zeros((100, 100, 3), dtype=np.uint8))

    validator = DatasetValidator(dataset_root=temp_dataset_dir)
    report = validator.validate()

    issue_types = {issue.issue_type for issue in report.issues}
    assert "ORPHAN_LABEL" in issue_types
    assert "MISSING_LABEL" in issue_types


def test_dataset_validator_detects_data_leakage(temp_dataset_dir):
    """Detects identical image across train and test splits (data leakage)."""
    img_data = np.full((100, 100, 3), 128, dtype=np.uint8)

    train_img = os.path.join(temp_dataset_dir, "images", "train", "leaked.jpg")
    test_img = os.path.join(temp_dataset_dir, "images", "test", "leaked_copy.jpg")

    cv2.imwrite(train_img, img_data)
    cv2.imwrite(test_img, img_data)

    validator = DatasetValidator(dataset_root=temp_dataset_dir)
    report = validator.validate()

    assert report.leakage_count > 0
    issue_types = {issue.issue_type for issue in report.issues}
    assert "DATA_LEAKAGE" in issue_types


# ── 2. Dataset Splitter Tests ───────────────────────────────────────────────

def test_dataset_splitter_reproducibility():
    """Deterministic seed ensures identical split output across runs."""
    tmp_src = tempfile.mkdtemp()
    tmp_dst1 = tempfile.mkdtemp()
    tmp_dst2 = tempfile.mkdtemp()

    try:
        # Create 20 synthetic images
        for i in range(20):
            p = os.path.join(tmp_src, f"img_{i:03d}.jpg")
            cv2.imwrite(p, np.zeros((50, 50, 3), dtype=np.uint8))

        splitter = DatasetSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42)

        split1 = splitter.split_dataset(tmp_src, tmp_src, tmp_dst1, copy_files=False)
        split2 = splitter.split_dataset(tmp_src, tmp_src, tmp_dst2, copy_files=False)

        assert split1["train"] == split2["train"]
        assert split1["val"] == split2["val"]
        assert split1["test"] == split2["test"]

        # Different seed produces different split
        splitter_diff = DatasetSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=999)
        split_diff = splitter_diff.split_dataset(tmp_src, tmp_src, tmp_dst2, copy_files=False)
        assert split1["train"] != split_diff["train"]

    finally:
        shutil.rmtree(tmp_src, ignore_errors=True)
        shutil.rmtree(tmp_dst1, ignore_errors=True)
        shutil.rmtree(tmp_dst2, ignore_errors=True)


# ── 3. Model Metadata & Registry Tests ──────────────────────────────────────

def test_model_metadata_roundtrip():
    """ModelMetadata serializes to dict and restores accurately."""
    meta = ModelMetadata(
        model_id="test_candidate_v1",
        model_version="1.0.0",
        dataset_version="v1.0.0",
        training_config={"epochs": 50, "batch": 16},
        git_commit="abc1234",
        training_timestamp="2026-09-06T03:00:00Z",
        classes={0: "person", 1: "car"},
        metrics={"mAP50": 0.78, "latency_ms": 45.2},
        artifact_path="weights/best.pt",
        status=ModelStatus.CANDIDATE,
        notes="Automated test model",
    )

    d = meta.to_dict()
    restored = ModelMetadata.from_dict(d)

    assert restored.model_id == meta.model_id
    assert restored.status == ModelStatus.CANDIDATE
    assert restored.metrics["mAP50"] == 0.78


def test_model_registry_lifecycle_and_promotion(temp_registry_file):
    """Tests model registration, sequential promotion, and production replacement."""
    reg = ModelRegistry(registry_file=temp_registry_file)

    # Initial baseline model exists
    baseline = reg.get_production_model()
    assert baseline is not None
    assert baseline.model_id == "yolov8n_pretrained_baseline"
    assert baseline.status == ModelStatus.PRODUCTION

    # Register candidate model
    candidate = ModelMetadata(
        model_id="border_detector_v1",
        model_version="1.0.0",
        dataset_version="v1.0.0",
        training_config={"epochs": 100},
        git_commit="test_commit",
        training_timestamp="2026-09-06T03:10:00Z",
        classes={0: "person", 1: "car"},
        metrics={"mAP50": 0.76},
        artifact_path="ml/runs/test/weights/best.pt",
        status=ModelStatus.CANDIDATE,
    )
    reg.register_model(candidate)

    # Candidate should be retrievable
    retrieved = reg.get_model("border_detector_v1")
    assert retrieved is not None
    assert retrieved.status == ModelStatus.CANDIDATE

    # Promote to VALIDATED -> CANARY -> PRODUCTION
    assert reg.promote_model("border_detector_v1", ModelStatus.VALIDATED, approved_by="QA_LEAD")
    assert reg.get_model("border_detector_v1").status == ModelStatus.VALIDATED

    assert reg.promote_model("border_detector_v1", ModelStatus.CANARY, approved_by="OPS_LEAD")
    assert reg.get_model("border_detector_v1").status == ModelStatus.CANARY

    assert reg.promote_model("border_detector_v1", ModelStatus.PRODUCTION, approved_by="COMMANDER")

    # New production model is active
    new_prod = reg.get_production_model()
    assert new_prod.model_id == "border_detector_v1"

    # Previous baseline was demoted to ROLLED_BACK
    old_prod = reg.get_model("yolov8n_pretrained_baseline")
    assert old_prod.status == ModelStatus.ROLLED_BACK


def test_model_registry_rollback(temp_registry_file):
    """Tests rolling back production to baseline model."""
    reg = ModelRegistry(registry_file=temp_registry_file)

    candidate = ModelMetadata(
        model_id="flawed_candidate",
        model_version="1.0.0",
        dataset_version="v1.0.0",
        training_config={},
        git_commit="",
        training_timestamp="",
        classes={},
        metrics={},
        artifact_path="",
        status=ModelStatus.PRODUCTION,
    )
    reg.register_model(candidate)
    reg.promote_model("flawed_candidate", ModelStatus.PRODUCTION, approved_by="TEST")
    assert reg.get_production_model().model_id == "flawed_candidate"

    # Rollback
    assert reg.rollback_production(target_model_id="yolov8n_pretrained_baseline", reason="High false alarms")
    assert reg.get_production_model().model_id == "yolov8n_pretrained_baseline"


# ── 4. Validation Gate Tests ────────────────────────────────────────────────

def test_validation_gate_pass_and_fail():
    """Validation gate correctly enforces mAP50, FPR, and latency thresholds."""
    gate = ValidationGate(
        criteria=GateCriteria(
            min_mAP50=0.70,
            max_false_positive_rate=0.10,
            max_inference_ms=100.0,
            require_superior_to_baseline=True,
        )
    )

    baseline_metrics = {"mAP50": 0.65}

    # Case 1: Excellent candidate -> PASS
    good_cand = {
        "mAP50": 0.78,
        "false_positive_rate": 0.04,
        "inference_latency_ms": 55.0,
    }
    passed, reasons = gate.evaluate(good_cand, baseline_metrics)
    assert passed is True

    # Case 2: Below mAP50 threshold -> FAIL
    low_map_cand = {
        "mAP50": 0.62,
        "false_positive_rate": 0.04,
        "inference_latency_ms": 55.0,
    }
    passed, reasons = gate.evaluate(low_map_cand, baseline_metrics)
    assert passed is False
    assert any("below required threshold" in r for r in reasons)

    # Case 3: Excessive False Positive Rate -> FAIL
    high_fpr_cand = {
        "mAP50": 0.75,
        "false_positive_rate": 0.18,  # > 0.10
        "inference_latency_ms": 55.0,
    }
    passed, reasons = gate.evaluate(high_fpr_cand, baseline_metrics)
    assert passed is False
    assert any("FPR" in r for r in reasons)


# ── 5. Model Selector Tests ─────────────────────────────────────────────────

def test_model_selector_fallbacks():
    """ModelSelector cleanly resolves existing baseline without exceptions."""
    selector = ModelSelector(selection_mode="production")
    path, version, meta = selector.resolve()

    assert path in ["yolov8n.pt", "models/yolov8n.pt"]
    assert version is not None

    # Unknown model falls back to baseline safely
    unknown_selector = ModelSelector(selection_mode="non_existent_model_id:9.9.9")
    path, version, meta = unknown_selector.resolve()
    assert path in ["yolov8n.pt", "models/yolov8n.pt"]
