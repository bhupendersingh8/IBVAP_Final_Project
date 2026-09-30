"""
services/evidence
=================
Cryptographic evidence management, SHA-256 hash-chain ledger,
and FIFO circular retention manager for IBVAP.
"""
from services.evidence.hash_chain import HashChainLedger, compute_block_hash, GENESIS_PREVIOUS_HASH, normalize_timestamp_str
from services.evidence.retention_manager import EvidenceRetentionManager

__all__ = [
    "HashChainLedger",
    "compute_block_hash",
    "GENESIS_PREVIOUS_HASH",
    "normalize_timestamp_str",
    "EvidenceRetentionManager",
]
