"""
Dataset Validation Engine for IBVAP.
Performs comprehensive audits on YOLO format object detection datasets:
- Missing images / labels
- Malformed annotations and syntax errors
- Out-of-bounds bounding boxes
- Invalid class IDs
- Corrupt / unreadable images
- Duplicate images and train/val/test leakage
- Class and resolution distributions
"""
from __future__ import annotations

import os
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
import cv2
import yaml
import structlog

logger = structlog.get_logger()

VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass
class ValidationIssue:
    split: str
    filename: str
    issue_type: str
    message: str
    severity: str  # "ERROR", "WARNING"


@dataclass
class ValidationReport:
    is_valid: bool
    total_images: int
    total_labels: int
    total_annotations: int
    split_counts: Dict[str, Dict[str, int]]
    class_distribution: Dict[str, Dict[str, int]]
    resolution_distribution: Dict[str, Dict[str, float]]
    issues: List[ValidationIssue]
    leakage_count: int
    duplicate_count: int

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "WARNING")

    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "total_images": self.total_images,
            "total_labels": self.total_labels,
            "total_annotations": self.total_annotations,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "leakage_count": self.leakage_count,
            "duplicate_count": self.duplicate_count,
            "split_counts": self.split_counts,
            "class_distribution": self.class_distribution,
            "resolution_distribution": self.resolution_distribution,
            "issues": [
                {
                    "split": i.split,
                    "filename": i.filename,
                    "issue_type": i.issue_type,
                    "message": i.message,
                    "severity": i.severity,
                }
                for i in self.issues
            ],
        }

    def generate_markdown(self) -> str:
        lines = [
            "# DATASET_AUDIT.md — Empirical Dataset Audit Report",
            "",
            f"**Audit Status:** {'PASS' if self.is_valid else 'FAIL'}",
            f"**Total Images:** {self.total_images}",
            f"**Total Labels:** {self.total_labels}",
            f"**Total Annotations:** {self.total_annotations}",
            f"**Errors Detected:** {self.error_count}",
            f"**Warnings Detected:** {self.warning_count}",
            f"**Data Leakage Across Splits:** {self.leakage_count}",
            f"**Duplicate Images:** {self.duplicate_count}",
            "",
            "---",
            "",
            "## 1. Split Distribution",
            "",
            "| Split | Images | Labels | Annotations | Status |",
            "|---|:---:|:---:|:---:|:---:|",
        ]
        for split, counts in self.split_counts.items():
            status = "HEALTHY" if counts["images"] > 0 else "EMPTY"
            lines.append(f"| {split.upper()} | {counts['images']} | {counts['labels']} | {counts['annotations']} | {status} |")

        lines.extend([
            "",
            "---",
            "",
            "## 2. Class Distribution Across Splits",
            "",
        ])
        if self.class_distribution:
            all_classes = sorted(list(set(c for sp in self.class_distribution.values() for c in sp.keys())))
            header = "| Class ID / Name | " + " | ".join(sp.upper() for sp in self.class_distribution.keys()) + " | Total |"
            sep = "|---|" + "|".join([":---:"] * (len(self.class_distribution) + 1)) + "|"
            lines.append(header)
            lines.append(sep)
            for cls_name in all_classes:
                row = [cls_name]
                tot = 0
                for sp in self.class_distribution.keys():
                    c_val = self.class_distribution[sp].get(cls_name, 0)
                    tot += c_val
                    row.append(str(c_val))
                row.append(str(tot))
                lines.append("| " + " | ".join(row) + " |")
        else:
            lines.append("*No annotations present in dataset.*")

        lines.extend([
            "",
            "---",
            "",
            "## 3. Image Resolution Profile",
            "",
        ])
        if self.resolution_distribution:
            lines.extend([
                f"- **Average Width:** {self.resolution_distribution.get('avg_width', 0.0):.1f} px",
                f"- **Average Height:** {self.resolution_distribution.get('avg_height', 0.0):.1f} px",
                f"- **Min Resolution:** {int(self.resolution_distribution.get('min_width', 0))}x{int(self.resolution_distribution.get('min_height', 0))}",
                f"- **Max Resolution:** {int(self.resolution_distribution.get('max_width', 0))}x{int(self.resolution_distribution.get('max_height', 0))}",
            ])
        else:
            lines.append("*No images available to profile.*")

        lines.extend([
            "",
            "---",
            "",
            "## 4. Issues & Anomalies Log",
            "",
        ])
        if not self.issues:
            lines.append("No errors or warnings discovered during dataset validation.")
        else:
            lines.append("| Severity | Split | File | Issue Type | Details |")
            lines.append("|:---:|:---:|---|---|---|")
            for issue in self.issues[:50]:  # Cap display at 50 in markdown
                lines.append(f"| {issue.severity} | {issue.split} | `{issue.filename}` | {issue.issue_type} | {issue.message} |")
            if len(self.issues) > 50:
                lines.append(f"| ... | ... | ... | ... | *({len(self.issues) - 50} more issues omitted for brevity)* |")

        lines.append("")
        return "\n".join(lines)


class DatasetValidator:
    """
    Validates dataset integrity for YOLO training and evaluation.
    """

    def __init__(
        self,
        dataset_root: str,
        classes_config_path: Optional[str] = None,
        splits: Optional[List[str]] = None,
    ):
        self.dataset_root = os.path.abspath(dataset_root)
        self.splits = splits or ["train", "val", "test"]
        self.classes: Dict[int, str] = self._load_classes(classes_config_path)

    def _load_classes(self, classes_config_path: Optional[str]) -> Dict[int, str]:
        if classes_config_path and os.path.isfile(classes_config_path):
            with open(classes_config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict) and "classes" in data:
                    return {int(k): str(v) for k, v in data["classes"].items()}
        # Fallback default classes
        return {
            0: "person",
            1: "car",
            2: "motorcycle",
            3: "truck",
            4: "bus",
        }

    def validate(self) -> ValidationReport:
        issues: List[ValidationIssue] = []
        split_counts: Dict[str, Dict[str, int]] = {}
        class_distribution: Dict[str, Dict[str, int]] = {}
        total_annotations = 0

        # For checking duplicates & leakage
        hash_to_split_files: Dict[str, List[Tuple[str, str]]] = {}
        widths: List[int] = []
        heights: List[int] = []

        total_images = 0
        total_labels = 0

        for split in self.splits:
            img_dir = os.path.join(self.dataset_root, "images", split)
            lbl_dir = os.path.join(self.dataset_root, "labels", split)

            split_counts[split] = {"images": 0, "labels": 0, "annotations": 0}
            class_distribution[split] = {f"{cid}:{cname}": 0 for cid, cname in self.classes.items()}

            if not os.path.isdir(img_dir) or not os.path.isdir(lbl_dir):
                issues.append(
                    ValidationIssue(
                        split=split,
                        filename="",
                        issue_type="MISSING_DIRECTORY",
                        message=f"Split directories missing: images/{split} or labels/{split}",
                        severity="ERROR",
                    )
                )
                continue

            # List valid files
            image_files = {
                f: os.path.join(img_dir, f)
                for f in os.listdir(img_dir)
                if os.path.splitext(f)[1].lower() in VALID_IMAGE_EXTS
            }
            label_files = {
                f: os.path.join(lbl_dir, f)
                for f in os.listdir(lbl_dir)
                if f.endswith(".txt") and not f.startswith(".")
            }

            split_counts[split]["images"] = len(image_files)
            split_counts[split]["labels"] = len(label_files)
            total_images += len(image_files)
            total_labels += len(label_files)

            # Check 1: Check for label files without corresponding image
            image_basenames = {os.path.splitext(f)[0]: f for f in image_files.keys()}
            label_basenames = {os.path.splitext(f)[0]: f for f in label_files.keys()}

            for l_stem, l_fname in label_files.items():
                stem = os.path.splitext(l_stem)[0]
                if stem not in image_basenames:
                    issues.append(
                        ValidationIssue(
                            split=split,
                            filename=l_fname,
                            issue_type="ORPHAN_LABEL",
                            message=f"Label file {l_fname} exists without a corresponding image.",
                            severity="ERROR",
                        )
                    )

            # Check 2: Check for image files without corresponding label
            for i_stem, i_fname in image_files.items():
                stem = os.path.splitext(i_stem)[0]
                if stem not in label_basenames:
                    issues.append(
                        ValidationIssue(
                            split=split,
                            filename=i_fname,
                            issue_type="MISSING_LABEL",
                            message=f"Image {i_fname} has no corresponding .txt label file.",
                            severity="WARNING",
                        )
                    )

            # Check 3: Check Image integrity & resolution & compute SHA-256
            for img_name, img_path in image_files.items():
                try:
                    with open(img_path, "rb") as f:
                        content = f.read()
                        sha = hashlib.sha256(content).hexdigest()
                    hash_to_split_files.setdefault(sha, []).append((split, img_name))

                    # Test OpenCV read
                    img = cv2.imread(img_path)
                    if img is None or img.size == 0:
                        issues.append(
                            ValidationIssue(
                                split=split,
                                filename=img_name,
                                issue_type="CORRUPT_IMAGE",
                                message=f"Image {img_name} could not be decoded by OpenCV.",
                                severity="ERROR",
                            )
                        )
                    else:
                        h, w = img.shape[:2]
                        widths.append(w)
                        heights.append(h)
                except Exception as ex:
                    issues.append(
                        ValidationIssue(
                            split=split,
                            filename=img_name,
                            issue_type="IMAGE_READ_ERROR",
                            message=f"Failed to read image {img_name}: {str(ex)}",
                            severity="ERROR",
                        )
                    )

            # Check 4: Validate YOLO labels syntax, class IDs, bounding box range
            for lbl_name, lbl_path in label_files.items():
                try:
                    with open(lbl_path, "r", encoding="utf-8") as f:
                        lines = [line.strip() for line in f.readlines() if line.strip()]

                    file_annotations = 0
                    for line_idx, line in enumerate(lines, 1):
                        parts = line.split()
                        if len(parts) != 5:
                            issues.append(
                                ValidationIssue(
                                    split=split,
                                    filename=lbl_name,
                                    issue_type="MALFORMED_LABEL",
                                    message=f"Line {line_idx}: Expected 5 space-separated values, got {len(parts)} ('{line}')",
                                    severity="ERROR",
                                )
                            )
                            continue

                        # Check Class ID
                        try:
                            cls_id = int(parts[0])
                        except ValueError:
                            issues.append(
                                ValidationIssue(
                                    split=split,
                                    filename=lbl_name,
                                    issue_type="INVALID_CLASS_ID",
                                    message=f"Line {line_idx}: Class ID '{parts[0]}' is not an integer.",
                                    severity="ERROR",
                                )
                            )
                            continue

                        if cls_id not in self.classes:
                            issues.append(
                                ValidationIssue(
                                    split=split,
                                    filename=lbl_name,
                                    issue_type="UNKNOWN_CLASS_ID",
                                    message=f"Line {line_idx}: Class ID {cls_id} not defined in classes metadata (defined: {list(self.classes.keys())}).",
                                    severity="ERROR",
                                )
                            )
                            continue

                        # Check coordinates
                        try:
                            x, y, w, h = (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
                        except ValueError:
                            issues.append(
                                ValidationIssue(
                                    split=split,
                                    filename=lbl_name,
                                    issue_type="MALFORMED_BBOX",
                                    message=f"Line {line_idx}: Non-float bbox coordinates in '{line}'",
                                    severity="ERROR",
                                )
                            )
                            continue

                        # Bounding box bounds check
                        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                            issues.append(
                                ValidationIssue(
                                    split=split,
                                    filename=lbl_name,
                                    issue_type="BBOX_OUT_OF_BOUNDS",
                                    message=f"Line {line_idx}: Center coords (x={x}, y={y}) outside [0, 1].",
                                    severity="ERROR",
                                )
                            )
                        if w <= 0.0 or h <= 0.0 or w > 1.0 or h > 1.0:
                            issues.append(
                                ValidationIssue(
                                    split=split,
                                    filename=lbl_name,
                                    issue_type="INVALID_BBOX_DIMENSIONS",
                                    message=f"Line {line_idx}: Box width={w} or height={h} not in (0, 1].",
                                    severity="ERROR",
                                )
                            )
                        # Check box overflow
                        if (x - w / 2.0 < -0.05) or (x + w / 2.0 > 1.05) or (y - h / 2.0 < -0.05) or (y + h / 2.0 > 1.05):
                            issues.append(
                                ValidationIssue(
                                    split=split,
                                    filename=lbl_name,
                                    issue_type="BBOX_EXCEEDS_CANVAS",
                                    message=f"Line {line_idx}: Box exceeds image boundaries significantly.",
                                    severity="WARNING",
                                )
                            )

                        file_annotations += 1
                        cls_key = f"{cls_id}:{self.classes[cls_id]}"
                        class_distribution[split][cls_key] = class_distribution[split].get(cls_key, 0) + 1

                    split_counts[split]["annotations"] = file_annotations
                    total_annotations += file_annotations
                except Exception as ex:
                    issues.append(
                        ValidationIssue(
                            split=split,
                            filename=lbl_name,
                            issue_type="LABEL_READ_ERROR",
                            message=f"Failed to read label file: {str(ex)}",
                            severity="ERROR",
                        )
                    )

        # Check 5: Train / Val / Test Leakage and Duplicates
        duplicate_count = 0
        leakage_count = 0
        for sha, occurrences in hash_to_split_files.items():
            if len(occurrences) > 1:
                splits_involved = set(sp for sp, _ in occurrences)
                if len(splits_involved) > 1:
                    leakage_count += 1
                    issues.append(
                        ValidationIssue(
                            split=",".join(sorted(splits_involved)),
                            filename=occurrences[0][1],
                            issue_type="DATA_LEAKAGE",
                            message=f"Identical image (SHA: {sha[:10]}...) exists across multiple splits: {occurrences}",
                            severity="ERROR",
                        )
                    )
                else:
                    duplicate_count += 1
                    issues.append(
                        ValidationIssue(
                            split=list(splits_involved)[0],
                            filename=occurrences[0][1],
                            issue_type="DUPLICATE_IMAGE",
                            message=f"Duplicate image within split {list(splits_involved)[0]}: {[f for _, f in occurrences]}",
                            severity="WARNING",
                        )
                    )

        # Resolution distribution stats
        resolution_distribution = {}
        if widths and heights:
            resolution_distribution = {
                "avg_width": float(sum(widths) / len(widths)),
                "avg_height": float(sum(heights) / len(heights)),
                "min_width": float(min(widths)),
                "max_width": float(max(widths)),
                "min_height": float(min(heights)),
                "max_height": float(max(heights)),
            }

        error_count = sum(1 for i in issues if i.severity == "ERROR")
        is_valid = (error_count == 0)

        return ValidationReport(
            is_valid=is_valid,
            total_images=total_images,
            total_labels=total_labels,
            total_annotations=total_annotations,
            split_counts=split_counts,
            class_distribution=class_distribution,
            resolution_distribution=resolution_distribution,
            issues=issues,
            leakage_count=leakage_count,
            duplicate_count=duplicate_count,
        )
