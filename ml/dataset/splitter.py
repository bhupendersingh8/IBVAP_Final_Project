"""
Deterministic & Sequence-Aware Dataset Splitting Utility for IBVAP.
Partitions unassigned image/label datasets into reproducible train, validation,
and test subsets (default 70/15/15) using a fixed deterministic random seed.
Supports sequence-aware grouping to prevent temporal frame leakage.
"""
from __future__ import annotations

import os
import shutil
import random
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Set
import structlog

logger = structlog.get_logger()
VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def extract_sequence_key(filename: str) -> str:
    """
    Extracts sequence identifier from filename to group temporally adjacent frames.
    Example: 'CAM-01-CCTV_f000030_20260906.jpg' -> 'CAM-01-CCTV'
             'seqA_frame012.jpg' -> 'seqA'
    """
    stem = os.path.splitext(filename)[0]
    # Try match before '_f' or '_frame' or take first two segments
    match = re.split(r"_f\d+|_frame\d+|_chunk\d+", stem, flags=re.IGNORECASE)
    if match and match[0]:
        return match[0]
    parts = stem.split("_")
    return parts[0] if len(parts) > 1 else stem


class DatasetSplitter:
    """
    Splits image/label pairs into train/val/test splits deterministically.
    Supports random stratified splitting or sequence-aware chunk splitting.
    """

    def __init__(
        self,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ):
        total = train_ratio + val_ratio + test_ratio
        if not (0.999 <= total <= 1.001):
            raise ValueError(f"Split ratios must sum to 1.0, got {total}")
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.seed = seed

    def split_dataset(
        self,
        source_images_dir: str,
        source_labels_dir: str,
        target_dataset_root: str,
        copy_files: bool = True,
        sequence_aware: bool = False,
    ) -> Dict[str, List[str]]:
        """
        Splits source images and labels into target dataset directories.
        """
        if not os.path.isdir(source_images_dir):
            raise FileNotFoundError(f"Source images directory not found: {source_images_dir}")

        image_files = sorted([
            f for f in os.listdir(source_images_dir)
            if os.path.splitext(f)[1].lower() in VALID_IMAGE_EXTS
        ])

        if not image_files:
            logger.warning("No images found in source directory to split", dir=source_images_dir)
            return {"train": [], "val": [], "test": []}

        rng = random.Random(self.seed)

        if sequence_aware:
            # Group by sequence key
            sequence_groups: Dict[str, List[str]] = {}
            for f in image_files:
                key = extract_sequence_key(f)
                sequence_groups.setdefault(key, []).append(f)

            # If there's only 1 sequence, chunk into contiguous temporal segments
            if len(sequence_groups) == 1:
                seq_name = list(sequence_groups.keys())[0]
                all_frames = sequence_groups[seq_name]
                # Chunk into small contiguous blocks of 5 frames
                chunk_size = max(1, len(all_frames) // 10)
                chunks = [all_frames[i:i + chunk_size] for i in range(0, len(all_frames), chunk_size)]
                rng.shuffle(chunks)
                
                n_c = len(chunks)
                n_train_c = max(1, int(n_c * self.train_ratio))
                n_val_c = max(1, int(n_c * self.val_ratio)) if n_c > 2 else 0

                train_files = [f for c in chunks[:n_train_c] for f in c]
                val_files = [f for c in chunks[n_train_c:n_train_c + n_val_c] for f in c]
                test_files = [f for c in chunks[n_train_c + n_val_c:] for f in c]
            else:
                # Distribute sequence groups across splits
                group_keys = list(sequence_groups.keys())
                rng.shuffle(group_keys)

                n_g = len(group_keys)
                n_train_g = max(1, int(n_g * self.train_ratio))
                n_val_g = max(1, int(n_g * self.val_ratio)) if n_g > 2 else 0

                train_keys = group_keys[:n_train_g]
                val_keys = group_keys[n_train_g:n_train_g + n_val_g]
                test_keys = group_keys[n_train_g + n_val_g:]

                train_files = [f for k in train_keys for f in sequence_groups[k]]
                val_files = [f for k in val_keys for f in sequence_groups[k]]
                test_files = [f for k in test_keys for f in sequence_groups[k]]
        else:
            # Deterministic item shuffle
            shuffled = list(image_files)
            rng.shuffle(shuffled)

            n = len(shuffled)
            n_train = int(n * self.train_ratio)
            n_val = int(n * self.val_ratio)
            train_files = shuffled[:n_train]
            val_files = shuffled[n_train:n_train + n_val]
            test_files = shuffled[n_train + n_val:]

        splits = {
            "train": train_files,
            "val": val_files,
            "test": test_files,
        }

        # Setup targets
        manifest_records = {}
        for split_name, files in splits.items():
            img_dest = os.path.join(target_dataset_root, "images", split_name)
            lbl_dest = os.path.join(target_dataset_root, "labels", split_name)
            os.makedirs(img_dest, exist_ok=True)
            os.makedirs(lbl_dest, exist_ok=True)

            split_manifest = []
            for fname in files:
                stem = os.path.splitext(fname)[0]
                src_img = os.path.join(source_images_dir, fname)
                dst_img = os.path.join(img_dest, fname)

                with open(src_img, "rb") as f:
                    sha = hashlib.sha256(f.read()).hexdigest()

                if copy_files:
                    shutil.copy2(src_img, dst_img)

                # Copy label if present
                lbl_fname = f"{stem}.txt"
                src_lbl = os.path.join(source_labels_dir, lbl_fname)
                dst_lbl = os.path.join(lbl_dest, lbl_fname)
                has_label = False
                if os.path.isfile(src_lbl):
                    has_label = True
                    if copy_files:
                        shutil.copy2(src_lbl, dst_lbl)

                split_manifest.append({
                    "image": fname,
                    "sha256": sha,
                    "has_label": has_label,
                })

            manifest_records[split_name] = split_manifest

            # Save manifest file
            manifest_dir = os.path.join(target_dataset_root, "manifests")
            os.makedirs(manifest_dir, exist_ok=True)
            manifest_path = os.path.join(manifest_dir, f"{split_name}_manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as mf:
                json.dump({
                    "split": split_name,
                    "count": len(files),
                    "sequence_aware": sequence_aware,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "seed": self.seed,
                    "files": split_manifest,
                }, mf, indent=2)

        logger.info(
            "Dataset split complete",
            total=len(image_files),
            train=len(train_files),
            val=len(val_files),
            test=len(test_files),
            sequence_aware=sequence_aware,
            seed=self.seed,
        )
        return splits
