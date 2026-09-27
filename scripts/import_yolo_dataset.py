"""
IBVAP Annotation Import & Staging Utility.
Imports authorized YOLO-format annotations (from CVAT, Label Studio, or local labeling):
- Validates image/label pairing
- Verifies normalized coordinate boundaries
- Validates class IDs against classes.yaml
- Rejects malformed bounding boxes or corrupted images
- Splits deterministically into train/val/test using sequence-aware partitioning
- Re-runs DatasetValidator to verify final target integrity
"""
from __future__ import annotations

import os
import sys
import argparse
import tempfile
import yaml
import structlog

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.dataset.validator import DatasetValidator
from ml.dataset.splitter import DatasetSplitter

logger = structlog.get_logger()


def import_dataset(
    source_images: str,
    source_labels: str,
    target_dataset: str = "dataset",
    classes_config: str = "dataset/metadata/classes.yaml",
    sequence_aware: bool = True,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    strict: bool = True,
) -> bool:
    if not os.path.isabs(target_dataset):
        target_dataset = os.path.join(PROJECT_ROOT, target_dataset)
    if not os.path.isabs(classes_config):
        classes_config = os.path.join(PROJECT_ROOT, classes_config)

    if not os.path.isdir(source_images):
        raise FileNotFoundError(f"Source images directory not found: {source_images}")
    if not os.path.isdir(source_labels):
        raise FileNotFoundError(f"Source labels directory not found: {source_labels}")

    logger.info("Initiating YOLO annotation import", source_images=source_images, source_labels=source_labels)

    # 1. Pre-validation in temporary staging container
    with tempfile.TemporaryDirectory() as tmp_stage:
        # Create staging layout to run validator
        stage_img_dir = os.path.join(tmp_stage, "images", "staging")
        stage_lbl_dir = os.path.join(tmp_stage, "labels", "staging")
        os.makedirs(stage_img_dir, exist_ok=True)
        os.makedirs(stage_lbl_dir, exist_ok=True)

        # Copy pairs into staging
        img_files = [f for f in os.listdir(source_images) if f.lower().endswith((".jpg", ".png", ".jpeg"))]
        for img_name in img_files:
            stem = os.path.splitext(img_name)[0]
            shutil_src = os.path.join(source_images, img_name)
            shutil_dst = os.path.join(stage_img_dir, img_name)
            with open(shutil_src, "rb") as sf, open(shutil_dst, "wb") as df:
                df.write(sf.read())

            lbl_name = f"{stem}.txt"
            src_lbl = os.path.join(source_labels, lbl_name)
            if os.path.isfile(src_lbl):
                dst_lbl = os.path.join(stage_lbl_dir, lbl_name)
                with open(src_lbl, "rb") as slf, open(dst_lbl, "wb") as dlf:
                    dlf.write(slf.read())

        # Validate staging
        validator = DatasetValidator(
            dataset_root=tmp_stage,
            classes_config_path=classes_config,
            splits=["staging"],
        )
        report = validator.validate()

        if report.error_count > 0:
            logger.error("Pre-import validation failed with errors", error_count=report.error_count)
            for err in report.issues:
                if err.severity == "ERROR":
                    print(f"[ERROR] {err.issue_type}: {err.filename} -> {err.message}")
            if strict:
                print("ABORTED: Source annotations contained validation errors.")
                return False

    # 2. Sequence-Aware Splitting directly into target dataset
    splitter = DatasetSplitter(
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        seed=seed,
    )
    splits = splitter.split_dataset(
        source_images_dir=source_images,
        source_labels_dir=source_labels,
        target_dataset_root=target_dataset,
        copy_files=True,
        sequence_aware=sequence_aware,
    )

    # 3. Final Target Integrity Validation
    final_validator = DatasetValidator(
        dataset_root=target_dataset,
        classes_config_path=classes_config,
    )
    final_report = final_validator.validate()

    audit_path = os.path.join(PROJECT_ROOT, "docs", "ml", "DATASET_AUDIT.md")
    with open(audit_path, "w", encoding="utf-8") as af:
        af.write(final_report.generate_markdown())

    logger.info(
        "Import complete and audit written",
        total_images=final_report.total_images,
        total_labels=final_report.total_labels,
        annotations=final_report.total_annotations,
    )
    return final_report.is_valid


def main():
    parser = argparse.ArgumentParser(description="Import and validate YOLO dataset")
    parser.add_argument("--source-images", required=True, help="Directory containing source images")
    parser.add_argument("--source-labels", required=True, help="Directory containing source .txt labels")
    parser.add_argument("--target-dataset", default="dataset", help="Destination dataset folder")
    parser.add_argument("--classes", default="dataset/metadata/classes.yaml", help="Path to classes.yaml")
    parser.add_argument("--sequence-aware", action="store_true", default=True, help="Enable sequence-aware splitting")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting")
    parser.add_argument("--strict", action="store_true", default=True, help="Abort on any validation error")
    args = parser.parse_args()

    success = import_dataset(
        source_images=args.source_images,
        source_labels=args.source_labels,
        target_dataset=args.target_dataset,
        classes_config=args.classes,
        sequence_aware=args.sequence_aware,
        seed=args.seed,
        strict=args.strict,
    )
    if success:
        print("IMPORT_STATUS: SUCCESS")
    else:
        print("IMPORT_STATUS: FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
