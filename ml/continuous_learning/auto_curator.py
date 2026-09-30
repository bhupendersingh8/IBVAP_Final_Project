"""
Auto-Curator Engine for Continuous Learning in IBVAP.
Scans evidence captures, filters duplicates, auto-generates normalized YOLO annotations,
and prepares high-quality curated samples in data/labeled/.
"""
from __future__ import annotations

import os
import sys
import time
import uuid
import json
import hashlib
from typing import Dict, List, Optional, Set, Tuple
import cv2
import numpy as np
import structlog

logger = structlog.get_logger()

# Default COCO to IBVAP unified dataset class mapping
DEFAULT_CLASS_MAPPING = {
    0: 0,  # person -> person (0)
    2: 1,  # car -> car (1)
    3: 2,  # motorcycle -> motorcycle (2)
    7: 3,  # truck -> truck (3)
    5: 4,  # bus -> bus (4)
}


class AutoCurator:
    """
    Automates the ingestion, filtering, deduplication, and YOLO labeling
    of real-world camera snapshots into the training pool.
    """

    def __init__(
        self,
        project_root: Optional[str] = None,
        evidence_dir: str = "data/evidence",
        labeled_dir: str = "data/labeled",
        manifest_path: str = "data/dataset_manifest.json",
        min_confidence: float = 0.30,
        model_weights: str = "yolov8n.pt",
        class_mapping: Optional[Dict[int, int]] = None,
    ):
        self.project_root = project_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self.evidence_dir = os.path.join(self.project_root, evidence_dir)
        self.labeled_dir = os.path.join(self.project_root, labeled_dir)
        self.manifest_path = os.path.join(self.project_root, manifest_path)
        self.min_confidence = min_confidence
        self.model_weights = model_weights
        self.class_mapping = class_mapping or DEFAULT_CLASS_MAPPING

        # Ensure directory structure
        self.images_dir = os.path.join(self.labeled_dir, "images")
        self.labels_dir = os.path.join(self.labeled_dir, "labels")
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.labels_dir, exist_ok=True)

        self._processed_hashes: Set[str] = set()
        self._load_manifest()

        self._detector = None

    def _load_manifest(self) -> None:
        """Loads known processed image hashes from manifest to prevent duplicates."""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        h = item.get("sha256")
                        if h:
                            self._processed_hashes.add(h)
            except Exception as e:
                logger.warning("Could not read dataset manifest, initializing fresh", error=str(e))

    def _save_manifest(self, entries: List[Dict]) -> None:
        """Appends new curation records to dataset manifest."""
        data = []
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []

        data.extend(entries)
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to write dataset manifest", error=str(e))

    def _get_detector(self):
        """Lazy-loads pre-trained YOLO detector."""
        if self._detector is None:
            try:
                from ultralytics import YOLO
                self._detector = YOLO(self.model_weights)
            except Exception as e:
                logger.error("Failed to load YOLO model for auto-curation", error=str(e))
                self._detector = None
        return self._detector

    def _compute_sha256(self, filepath: str) -> str:
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def curate_image(
        self,
        image_path: str,
        camera_id: str = "CAM-01",
        notes: str = "",
        allow_empty_background: bool = True
    ) -> Optional[Dict]:
        """
        Processes a single image: verifies quality, deduplicates, runs pseudo-labeling,
        and saves formatted YOLO training sample into data/labeled/.
        """
        if not os.path.exists(image_path):
            return None

        # 1. Deduplication check
        file_hash = self._compute_sha256(image_path)
        if file_hash in self._processed_hashes:
            logger.debug("Skipping duplicate image", hash=file_hash[:8], path=image_path)
            return None

        frame = cv2.imread(image_path)
        if frame is None or frame.size == 0:
            return None

        h, w = frame.shape[:2]
        if h < 100 or w < 100:
            return None

        # 2. Quality check: skip completely dark or blank frames
        if np.mean(frame) < 8.0:
            return None

        sample_id = f"curated_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        detector = self._get_detector()
        boxes_written = 0
        detected_classes = []

        label_dest = os.path.join(self.labels_dir, f"{sample_id}.txt")
        image_dest = os.path.join(self.images_dir, f"{sample_id}.jpg")

        if detector is not None:
            try:
                results = detector.predict(frame, conf=self.min_confidence, verbose=False)[0]
                lines = []
                for box in results.boxes:
                    coco_cls = int(box.cls[0])
                    if coco_cls in self.class_mapping:
                        target_cls = self.class_mapping[coco_cls]
                        xywhn = box.xywhn[0].tolist()
                        lines.append(f"{target_cls} {xywhn[0]:.6f} {xywhn[1]:.6f} {xywhn[2]:.6f} {xywhn[3]:.6f}\n")
                        detected_classes.append(target_cls)
                        boxes_written += 1

                if boxes_written > 0 or allow_empty_background:
                    with open(label_dest, "w", encoding="utf-8") as lf:
                        lf.writelines(lines)
                else:
                    return None
            except Exception as e:
                logger.warning("Inference auto-labeling failed", error=str(e))
                if allow_empty_background:
                    with open(label_dest, "w", encoding="utf-8") as lf:
                        pass
                else:
                    return None
        else:
            if allow_empty_background:
                with open(label_dest, "w", encoding="utf-8") as lf:
                    pass
            else:
                return None

        # 3. Save curated image
        cv2.imwrite(image_dest, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        self._processed_hashes.add(file_hash)

        entry = {
            "sample_id": sample_id,
            "sha256": file_hash,
            "timestamp": datetime_iso(),
            "camera_id": camera_id,
            "image_file": f"{sample_id}.jpg",
            "label_file": f"{sample_id}.txt",
            "objects_count": boxes_written,
            "classes": list(set(detected_classes)),
            "source": image_path,
            "notes": notes
        }
        return entry

    def curate_all_evidence(self, limit: Optional[int] = None) -> Dict:
        """
        Scans all images in data/evidence/, curates new unindexed frames,
        and saves them to data/labeled/.
        """
        if not os.path.exists(self.evidence_dir):
            return {"curated": 0, "skipped": 0, "total_scanned": 0}

        valid_exts = {".jpg", ".jpeg", ".png"}
        all_files = [
            os.path.join(self.evidence_dir, f)
            for f in os.listdir(self.evidence_dir)
            if os.path.splitext(f)[1].lower() in valid_exts
            and not f.startswith("live_")  # Skip live preview rolling buffers
        ]

        if limit:
            all_files = all_files[:limit]

        new_entries = []
        skipped = 0

        for fpath in all_files:
            entry = self.curate_image(fpath, camera_id="CAM-01", notes="auto-curated from evidence")
            if entry:
                new_entries.append(entry)
            else:
                skipped += 1

        if new_entries:
            self._save_manifest(new_entries)

        logger.info(
            "Auto-curation complete",
            curated=len(new_entries),
            skipped=skipped,
            total_scanned=len(all_files)
        )

        return {
            "curated": len(new_entries),
            "skipped": skipped,
            "total_scanned": len(all_files),
            "total_labeled_available": len([
                f for f in os.listdir(self.images_dir) if f.endswith((".jpg", ".png"))
            ]) if os.path.exists(self.images_dir) else 0
        }

    def curate_and_prune(self, max_evidence_photos: int = 100) -> Dict[str, Any]:
        """
        Two-step retention & continuous learning cycle:
        1. Auto-curates any new frames from evidence/ into labeled/ with YOLO annotations.
        2. Prunes raw evidence/ down to max_evidence_photos (FIFO) to prevent disk overflow.
        """
        curation_result = self.curate_all_evidence()

        from services.evidence.retention_manager import EvidenceRetentionManager
        retention = EvidenceRetentionManager(
            evidence_dir=self.evidence_dir,
            max_photos=max_evidence_photos,
            project_root=self.project_root,
        )
        pruned_count = retention.enforce_retention()
        stats = retention.get_stats()

        return {
            "curation": curation_result,
            "pruned_evidence_count": pruned_count,
            "remaining_evidence_photos": stats["total_evidence_photos"],
            "max_photos_limit": max_evidence_photos,
        }


def datetime_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
