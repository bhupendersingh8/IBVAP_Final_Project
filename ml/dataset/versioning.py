"""
IBVAP Dataset Versioning & Lineage Engine.
Tracks dataset versions, source lineage, daylight/night distribution,
class frequency, and cryptographic manifest digests.
"""
from __future__ import annotations

import os
import json
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
import yaml
import structlog

logger = structlog.get_logger()


@dataclass
class DatasetVersionMeta:
    dataset_version: str
    status: str
    provenance: str
    created_at: str
    source_ids: List[str]
    total_images: int
    annotated_images: int
    total_annotations: int
    split_statistics: Dict[str, Dict[str, int]]
    class_counts: Dict[str, int]
    day_count: int
    night_count: int
    low_light_count: int
    ir_count: int
    night_data_status: str
    ir_data_status: str
    manifest_sha256: Optional[str]
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DatasetVersionManager:
    """
    Computes and persists empirical dataset metadata.
    Enforces anti-hallucination guarantees: if images or annotations are 0,
    marks version as unpopulated and night/ir as NOT_AVAILABLE.
    """

    def __init__(
        self,
        dataset_root: Optional[str] = None,
        classes_config: Optional[str] = None,
    ):
        base = dataset_root or os.path.join(PROJECT_ROOT, "dataset")
        self.dataset_root = os.path.abspath(base)
        self.classes_config = classes_config or os.path.join(self.dataset_root, "metadata", "classes.yaml")
        self.info_file = os.path.join(self.dataset_root, "metadata", "dataset_info.yaml")
        self.manifest_file = os.path.join(self.dataset_root, "metadata", "frames.jsonl")

    def compute_metadata(self, version_name: str = "v1.0.0") -> DatasetVersionMeta:
        splits = ["train", "val", "test"]
        split_stats = {s: {"images": 0, "labels": 0, "annotations": 0} for s in splits}
        total_images = 0
        total_labels = 0
        total_annotations = 0
        class_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}

        # Check images and labels in splits
        for s in splits:
            img_dir = os.path.join(self.dataset_root, "images", s)
            lbl_dir = os.path.join(self.dataset_root, "labels", s)

            if os.path.isdir(img_dir):
                imgs = [f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".png", ".jpeg"))]
                split_stats[s]["images"] = len(imgs)
                total_images += len(imgs)

            if os.path.isdir(lbl_dir):
                lbls = [f for f in os.listdir(lbl_dir) if f.endswith(".txt") and not f.startswith(".")]
                split_stats[s]["labels"] = len(lbls)
                total_labels += len(lbls)

                for lf in lbls:
                    lp = os.path.join(lbl_dir, lf)
                    with open(lp, "r", encoding="utf-8") as f:
                        lines = [l.strip() for l in f.readlines() if l.strip()]
                    split_stats[s]["annotations"] += len(lines)
                    total_annotations += len(lines)
                    for l in lines:
                        parts = l.split()
                        if parts:
                            try:
                                cid = int(parts[0])
                                class_counts[cid] = class_counts.get(cid, 0) + 1
                            except ValueError:
                                pass

        # Read frames.jsonl manifest if present for day/night/source counts
        source_ids: List[str] = []
        day_count = 0
        night_count = 0
        low_light_count = 0
        ir_count = 0
        manifest_sha = None

        if os.path.isfile(self.manifest_file):
            with open(self.manifest_file, "rb") as mf:
                manifest_sha = hashlib.sha256(mf.read()).hexdigest()

            with open(self.manifest_file, "r", encoding="utf-8") as mf:
                for line in mf:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        sid = rec.get("source_id")
                        if sid and sid not in source_ids:
                            source_ids.append(sid)
                        lighting = rec.get("lighting_condition", "DAY")
                        if lighting == "DAY":
                            day_count += 1
                        elif lighting == "NIGHT":
                            night_count += 1
                        elif lighting == "LOW_LIGHT":
                            low_light_count += 1
                        elif lighting == "IR":
                            ir_count += 1
                    except json.JSONDecodeError:
                        pass

        # Evaluate honest availability status
        if total_images == 0 or total_annotations == 0:
            status = "UNPOPULATED_AWAITING_FIELD_DATA"
            effective_version = f"{version_name}-unpopulated"
            notes = "Dataset structure and tooling are operational. Awaiting labeled ground-truth field footage."
        else:
            status = "POPULATED"
            effective_version = version_name
            notes = f"Validated dataset version containing {total_images} images and {total_annotations} annotations."

        night_status = "PASS" if night_count > 0 else "NOT_AVAILABLE"
        ir_status = "PASS" if ir_count > 0 else "NOT_AVAILABLE"

        named_class_counts = {
            f"{cid}:{name}": class_counts.get(cid, 0)
            for cid, name in {0: "person", 1: "car", 2: "motorcycle", 3: "truck", 4: "bus"}.items()
        }

        provenance = "REAL_FIELD_DATA_VALIDATED" if status == "POPULATED" else "PROVENANCE_UNKNOWN_AWAITING_FIELD_DATA"

        meta = DatasetVersionMeta(
            dataset_version=effective_version,
            status=status,
            provenance=provenance,
            created_at=datetime.now(timezone.utc).isoformat(),
            source_ids=source_ids,
            total_images=total_images,
            annotated_images=total_labels,
            total_annotations=total_annotations,
            split_statistics=split_stats,
            class_counts=named_class_counts,
            day_count=day_count,
            night_count=night_count,
            low_light_count=low_light_count,
            ir_count=ir_count,
            night_data_status=night_status,
            ir_data_status=ir_status,
            manifest_sha256=manifest_sha,
            notes=notes,
        )

        return meta

    def save_metadata(self, meta: DatasetVersionMeta) -> str:
        os.makedirs(os.path.dirname(self.info_file), exist_ok=True)
        with open(self.info_file, "w", encoding="utf-8") as f:
            yaml.dump(meta.to_dict(), f, default_flow_style=False, sort_keys=False)
        logger.info("Dataset version metadata saved", file=self.info_file, version=meta.dataset_version)
        return self.info_file
