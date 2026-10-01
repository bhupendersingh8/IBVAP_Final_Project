"""
services/evidence/retention_manager.py
======================================
FIFO Circular Evidence Retention Manager for IBVAP.
Maintains snapshot limits on disk to prevent storage exhaustion while
safeguarding live video preview frames and uncurated evidence.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
PRESERVED_PREFIX = "live_"


class EvidenceRetentionManager:
    """
    Manages local disk storage for evidence snapshots using a strict FIFO circular policy.
    Ensures that active live previews (live_CAM-01.jpg) are never pruned.
    """

    def __init__(
        self,
        evidence_dir: str = "data/evidence",
        max_photos: int = 500,
        project_root: Optional[str] = None,
    ):
        self.project_root = project_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        if os.path.isabs(evidence_dir):
            self.evidence_dir = evidence_dir
        else:
            self.evidence_dir = os.path.join(self.project_root, evidence_dir)

        self.max_photos = max_photos
        os.makedirs(self.evidence_dir, exist_ok=True)

    def is_preserved_file(self, filename: str) -> bool:
        """Returns True if the file is a protected live preview image."""
        return filename.startswith(PRESERVED_PREFIX)

    def get_evidence_files(self) -> List[Tuple[str, float]]:
        """
        Retrieves all non-preserved evidence image files sorted ascending by modification time.
        Oldest files are returned first.
        """
        if not os.path.exists(self.evidence_dir):
            return []

        evidence_items: List[Tuple[str, float]] = []
        try:
            for entry in os.scandir(self.evidence_dir):
                if not entry.is_file():
                    continue
                name_lower = entry.name.lower()
                if not name_lower.endswith(IMAGE_EXTENSIONS):
                    continue
                if self.is_preserved_file(entry.name):
                    continue

                try:
                    mtime = entry.stat().st_mtime
                    evidence_items.append((entry.path, mtime))
                except OSError:
                    continue
        except OSError:
            return []

        # Sort ascending by mtime (FIFO: oldest first)
        evidence_items.sort(key=lambda item: item[1])
        return evidence_items

    def get_stats(self) -> Dict[str, Any]:
        """Returns retention metrics for the evidence storage directory."""
        files = self.get_evidence_files()
        total_photos = len(files)
        excess = max(0, total_photos - self.max_photos)
        is_overflowing = total_photos > self.max_photos

        preserved_count = 0
        if os.path.exists(self.evidence_dir):
            try:
                for entry in os.scandir(self.evidence_dir):
                    if entry.is_file() and self.is_preserved_file(entry.name):
                        preserved_count += 1
            except OSError:
                pass

        oldest_info = None
        newest_info = None
        if files:
            oldest_path, oldest_mtime = files[0]
            newest_path, newest_mtime = files[-1]
            oldest_info = {
                "filename": os.path.basename(oldest_path),
                "timestamp": datetime.fromtimestamp(oldest_mtime).isoformat(),
            }
            newest_info = {
                "filename": os.path.basename(newest_path),
                "timestamp": datetime.fromtimestamp(newest_mtime).isoformat(),
            }

        return {
            "evidence_dir": self.evidence_dir,
            "total_evidence_photos": total_photos,
            "max_photos_limit": self.max_photos,
            "excess_photos": excess,
            "is_overflowing": is_overflowing,
            "preserved_preview_files": preserved_count,
            "oldest_evidence": oldest_info,
            "newest_evidence": newest_info,
        }

    def enforce_retention(self, max_photos: Optional[int] = None) -> int:
        """
        Enforces retention limit by pruning the oldest evidence files.
        Preserved preview files are immune to pruning.
        Returns the count of successfully deleted files.
        """
        limit = max_photos if max_photos is not None else self.max_photos
        files = self.get_evidence_files()
        excess = len(files) - limit

        if excess <= 0:
            return 0

        to_delete = files[:excess]
        deleted_count = 0

        for fpath, _ in to_delete:
            try:
                if os.path.exists(fpath):
                    os.remove(fpath)
                    deleted_count += 1
            except OSError:
                pass

        return deleted_count
