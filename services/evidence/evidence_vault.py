"""
services/evidence/evidence_vault.py
===================================
Forensic Evidence Vault maintaining local verification and storage commitments.
"""
from __future__ import annotations

import os
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from services.evidence.hash_chain import compute_block_hash, GENESIS_PREVIOUS_HASH


class EvidenceVault:
    """In-memory and local repository for forensic evidence commitment."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or os.path.join("data", "evidence")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.last_hash = GENESIS_PREVIOUS_HASH
        self.blocks = []

    def commit_evidence(
        self,
        camera_id: str,
        frame_bytes: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Cryptographically registers an evidence artifact into the local vault."""
        sha256_hash = hashlib.sha256(frame_bytes).hexdigest()
        now_iso = datetime.now(timezone.utc).isoformat()
        incident_id = f"INC-{camera_id}-{len(self.blocks) + 1:04d}"

        record_hash = compute_block_hash(
            previous_hash=self.last_hash,
            incident_id=incident_id,
            evidence_sha256=sha256_hash,
            timestamp=now_iso,
            payload=metadata or {},
        )

        block = {
            "sequence_id": len(self.blocks) + 1,
            "incident_id": incident_id,
            "camera_id": camera_id,
            "evidence_sha256": sha256_hash,
            "previous_hash": self.last_hash,
            "record_hash": record_hash,
            "timestamp": now_iso,
            "metadata": metadata or {},
        }

        self.last_hash = record_hash
        self.blocks.append(block)
        return block
