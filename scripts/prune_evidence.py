#!/usr/bin/env python3
"""
scripts/prune_evidence.py
=========================
Command Line Utility to enforce FIFO circular retention limits on evidence photos.
Maintains max 100 photos threshold (or custom value) and preserves live stream preview frames.

Usage:
  python scripts/prune_evidence.py --status
  python scripts/prune_evidence.py --dry-run
  python scripts/prune_evidence.py --max-photos 100
  python scripts/prune_evidence.py --max-photos 100 --curate-first
"""
from __future__ import annotations

import os
import sys
import argparse
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.evidence.retention_manager import EvidenceRetentionManager


def main():
    parser = argparse.ArgumentParser(
        description="IBVAP Evidence Retention & Pruning Utility (FIFO Policy)"
    )
    parser.add_argument(
        "--max-photos",
        type=int,
        default=100,
        help="Maximum number of evidence photos to retain (default: 100)",
    )
    parser.add_argument(
        "--evidence-dir",
        type=str,
        default="data/evidence",
        help="Path to evidence directory relative to project root",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Inspect current evidence count, limits, and age without modifying files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate pruning and list candidate files without deleting",
    )
    parser.add_argument(
        "--curate-first",
        action="store_true",
        help="Run auto-curator before pruning to index training annotations in data/labeled/",
    )

    args = parser.parse_args()

    retention = EvidenceRetentionManager(
        evidence_dir=args.evidence_dir,
        max_photos=args.max_photos,
        project_root=PROJECT_ROOT,
    )

    print("=" * 64)
    print("      IBVAP EVIDENCE FIFO RETENTION MANAGER")
    print("=" * 64)

    stats = retention.get_stats()
    print(f"Directory:           {stats['evidence_dir']}")
    print(f"Total Photos:        {stats['total_evidence_photos']}")
    print(f"Configured Limit:    {stats['max_photos_limit']}")
    print(f"Preserved Previews:  {stats['preserved_preview_files']}")
    print(f"Excess to Prune:     {stats['excess_photos']}")
    if stats.get("oldest_evidence"):
        print(f"Oldest Snapshot:     {stats['oldest_evidence']['filename']} ({stats['oldest_evidence']['timestamp']})")
    if stats.get("newest_evidence"):
        print(f"Newest Snapshot:     {stats['newest_evidence']['filename']} ({stats['newest_evidence']['timestamp']})")
    print("-" * 64)

    if args.status:
        return 0

    if args.dry_run:
        files = retention.get_evidence_files()
        excess = len(files) - args.max_photos
        if excess <= 0:
            print(f"[OK] Directory is within limit ({len(files)} <= {args.max_photos}). No deletion needed.")
            return 0
        print(f"[DRY-RUN] Found {len(files)} photos. Would delete {excess} oldest photos:")
        for fpath, mtime in files[:excess]:
            dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  [WOULD DELETE] {os.path.basename(fpath)} (Modified: {dt})")
        print(f"[DRY-RUN] Result would be exactly {args.max_photos} photos remaining.")
        return 0

    if args.curate_first:
        print("[AUTO-CURATE] Indexing any uncurated frames into data/labeled/ before pruning...")
        try:
            from ml.continuous_learning.auto_curator import AutoCurator
            curator = AutoCurator(project_root=PROJECT_ROOT)
            cur_res = curator.curate_all_evidence()
            print(f"[AUTO-CURATE] Indexed {cur_res.get('curated', 0)} frames into training pool.")
        except Exception as err:
            print(f"[WARN] Auto-curator encountered error: {err}")

    print(f"[PRUNE] Pruning oldest evidence to enforce max {args.max_photos} photos...")
    deleted = retention.enforce_retention(max_photos=args.max_photos)
    final_stats = retention.get_stats()
    print(f"[SUCCESS] Deleted {deleted} expired evidence photos.")
    print(f"[SUCCESS] Current photo count: {final_stats['total_evidence_photos']} (Limit: {final_stats['max_photos_limit']}).")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
