"""
Merkle Dataset Commitment Tree & Anti-Poisoning Verification (SIH26228)
======================================================================
Generates cryptographic commitments over multi-contributor training datasets:
Leaf Hash: H_leaf = SHA256(SampleID || CanonicalLabel || ImageBytes)
Builds balanced Merkle Tree Root to detect data poisoning or annotation manipulation.
"""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


def compute_sample_commitment(sample_id: str, label_data: Any, image_bytes: bytes) -> str:
    """
    Computes deterministic SHA-256 cryptographic commitment for a single dataset sample:
    H = SHA256(SampleID || Label || ImageBytes)
    """
    h = hashlib.sha256()
    h.update(str(sample_id).strip().encode("utf-8"))

    if isinstance(label_data, (dict, list)):
        label_str = json.dumps(label_data, sort_keys=True, separators=(",", ":"))
    else:
        label_str = str(label_data).strip()

    h.update(label_str.encode("utf-8"))
    h.update(image_bytes)
    return h.hexdigest()


class MerkleDatasetTree:
    """
    Cryptographic Merkle Tree over training dataset samples.
    Guarantees tamper-evident commitment before training and inference runs.
    """

    def __init__(self, samples: Optional[List[Dict[str, Any]]] = None):
        self.leaves: List[str] = []
        self.sample_ids: List[str] = []
        self.levels: List[List[str]] = []
        self.root: str = "0" * 64

        if samples:
            for s in samples:
                self.add_sample(
                    sample_id=s["sample_id"],
                    label_data=s.get("label", s.get("annotations", "")),
                    image_bytes=s.get("image_bytes", b"")
                )
            self.build_tree()

    def add_sample(self, sample_id: str, label_data: Any, image_bytes: bytes) -> str:
        leaf_hash = compute_sample_commitment(sample_id, label_data, image_bytes)
        self.leaves.append(leaf_hash)
        self.sample_ids.append(sample_id)
        return leaf_hash

    def build_tree(self) -> str:
        if not self.leaves:
            self.root = "0" * 64
            self.levels = []
            return self.root

        # Sort leaves deterministically
        paired = sorted(zip(self.sample_ids, self.leaves), key=lambda x: x[0])
        self.sample_ids = [p[0] for p in paired]
        current_level = [p[1] for p in paired]
        self.levels = [current_level]

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = hashlib.sha256((left + right).encode("utf-8")).hexdigest()
                next_level.append(combined)
            current_level = next_level
            self.levels.append(current_level)

        self.root = self.levels[-1][0] if self.levels else ("0" * 64)
        return self.root

    def get_root(self) -> str:
        if not self.levels:
            self.build_tree()
        return self.root

    def verify_sample(self, sample_id: str, label_data: Any, image_bytes: bytes) -> bool:
        """Verifies if a sample matches its expected leaf commitment in the dataset."""
        leaf_hash = compute_sample_commitment(sample_id, label_data, image_bytes)
        return leaf_hash in self.leaves
