"""
services/evidence/hash_chain.py
================================
Cryptographic SHA-256 Tamper-Evident Evidence Hash Chain Ledger.
Provides cryptographically verifiable technical evidence chain-of-custody.
"""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from apps.backend.database.models import HashChainBlock

GENESIS_PREVIOUS_HASH: str = "0" * 64


def normalize_timestamp_str(ts: Any) -> str:
    """Normalizes a datetime or timestamp string to a consistent ISO format."""
    if isinstance(ts, datetime):
        if ts.tzinfo is not None:
            ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
        return ts.isoformat()
    if isinstance(ts, str):
        return ts
    return str(ts or "")


def compute_block_hash(
    previous_hash: str,
    incident_id: str,
    evidence_sha256: str,
    timestamp: Any = None,
    payload: Any = None,
    *,
    timestamp_iso: Any = None,
    payload_str: Any = None,
    **kwargs,
) -> str:
    """
    Computes a deterministic SHA-256 record hash for a block in the evidence ledger.
    Supports both positional and keyword arguments for timestamps and payloads.
    """
    ts_val = timestamp_iso if timestamp_iso is not None else timestamp
    p_val = payload_str if payload_str is not None else payload

    ts_str = normalize_timestamp_str(ts_val)
    if isinstance(p_val, (dict, list)):
        payload_text = json.dumps(p_val, sort_keys=True)
    else:
        payload_text = str(p_val if p_val is not None else "")

    block_data = f"{previous_hash}|{incident_id}|{evidence_sha256}|{ts_str}|{payload_text}"
    return hashlib.sha256(block_data.encode("utf-8")).hexdigest()


class HashChainLedger:
    """
    Immutable append-only ledger that cryptographically links evidence records
    via SHA-256 chaining.
    """

    @classmethod
    async def add_block(
        cls,
        session: AsyncSession,
        incident_id: str,
        event_id: str,
        evidence_sha256: str,
        camera_id: str,
        payload_data: Any = None,
        timestamp: Optional[datetime] = None,
    ) -> HashChainBlock:
        """
        Appends a new verified block to the hash chain ledger.
        Fetches the previous block hash or defaults to GENESIS_PREVIOUS_HASH.
        """
        stmt = (
            select(HashChainBlock)
            .order_by(HashChainBlock.sequence_id.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        latest_block = result.scalar_one_or_none()

        if latest_block is not None:
            previous_hash = latest_block.record_hash
        else:
            previous_hash = GENESIS_PREVIOUS_HASH

        block_time = timestamp or datetime.now(timezone.utc)
        if isinstance(block_time, datetime) and block_time.tzinfo is not None:
            block_time = block_time.astimezone(timezone.utc).replace(tzinfo=None)

        if isinstance(payload_data, (dict, list)):
            payload_json = json.dumps(payload_data, sort_keys=True)
        else:
            payload_json = str(payload_data if payload_data is not None else "")

        record_hash = compute_block_hash(
            previous_hash=previous_hash,
            incident_id=incident_id,
            evidence_sha256=evidence_sha256,
            timestamp=block_time,
            payload=payload_json,
        )

        block = HashChainBlock(
            record_hash=record_hash,
            previous_hash=previous_hash,
            event_id=event_id,
            incident_id=incident_id,
            evidence_sha256=evidence_sha256,
            camera_id=camera_id,
            timestamp=block_time,
            payload_json=payload_json,
        )

        session.add(block)
        await session.flush()
        return block

    @classmethod
    async def verify_chain(
        cls, session: AsyncSession
    ) -> Tuple[bool, Optional[int], str]:
        """
        Audits the entire hash chain from genesis to the latest record.
        Returns:
            (is_valid: bool, corrupted_sequence_id: Optional[int], message: str)
        """
        stmt = select(HashChainBlock).order_by(HashChainBlock.sequence_id.asc())
        result = await session.execute(stmt)
        blocks = result.scalars().all()

        if not blocks:
            return True, None, "Hash chain is empty"

        expected_prev = GENESIS_PREVIOUS_HASH

        for block in blocks:
            # 1. Verify sequential linkage
            if block.previous_hash != expected_prev:
                return (
                    False,
                    block.sequence_id,
                    f"Block {block.sequence_id} broken chain: previous_hash mismatch",
                )

            # 2. Verify payload and metadata integrity
            computed_hash = compute_block_hash(
                previous_hash=block.previous_hash,
                incident_id=block.incident_id,
                evidence_sha256=block.evidence_sha256,
                timestamp=block.timestamp,
                payload=block.payload_json,
            )

            if computed_hash != block.record_hash:
                return (
                    False,
                    block.sequence_id,
                    f"Block {block.sequence_id} is tampered: record hash mismatch",
                )

            expected_prev = block.record_hash

        return True, None, f"Hash chain verified successfully ({len(blocks)} blocks)"
