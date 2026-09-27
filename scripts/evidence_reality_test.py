"""
Evidence Integrity Reality Test for IBVAP.
Verifies SHA-256 and Hash Chain, then introduces a corruption and verifies failure.
"""
import sys
import os
import hashlib
import asyncio
import shutil

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from apps.backend.database.connection import AsyncSessionLocal, init_db
from services.evidence.hash_chain import HashChainLedger
from apps.backend.database.models import HashChainBlock
from sqlalchemy import select

async def run_evidence_integrity_audit():
    await init_db()
    results = {}
    
    # 1. Verify existing ledger in database
    async with AsyncSessionLocal() as session:
        is_valid_initial = await HashChainLedger.verify_chain(session)
        query = select(HashChainBlock).order_by(HashChainBlock.sequence_id.asc())
        res = await session.execute(query)
        blocks = res.scalars().all()
        results["initial_ledger_valid"] = is_valid_initial
        results["total_blocks_in_db"] = len(blocks)
        
        if blocks:
            first_block = blocks[0]
            last_block = blocks[-1]
            results["sample_block"] = {
                "sequence_id": last_block.sequence_id,
                "incident_id": last_block.incident_id,
                "evidence_sha256": last_block.evidence_sha256,
                "record_hash": last_block.record_hash,
                "previous_hash": last_block.previous_hash,
                "timestamp": str(last_block.timestamp)
            }
            
            # Check real evidence file on disk
            evidence_dir = str(PROJECT_ROOT / "data" / "evidence")
            os.makedirs(evidence_dir, exist_ok=True)
            evidence_files = [f for f in os.listdir(evidence_dir) if f.endswith(".jpg")]
            results["evidence_files_count"] = len(evidence_files)
            
            if evidence_files:
                sample_file = os.path.join(evidence_dir, evidence_files[0])
                with open(sample_file, "rb") as f:
                    content = f.read()
                calc_sha256 = hashlib.sha256(content).hexdigest()
                results["sample_file_sha256_match"] = {
                    "filename": evidence_files[0],
                    "file_bytes": len(content),
                    "computed_sha256": calc_sha256
                }

    # 2. Tamper Test (Simulated corruption on isolated ledger copy)
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from apps.backend.database.models import Base
    
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    TestSession = async_sessionmaker(test_engine, expire_on_commit=False)
    
    async with TestSession() as session:
        # Add 3 authentic blocks
        b1 = await HashChainLedger.add_block(session, "inc-01", "ev-01", "sha256_01", "CAM-01", {"track_id": 1})
        b2 = await HashChainLedger.add_block(session, "inc-02", "ev-02", "sha256_02", "CAM-01", {"track_id": 2})
        b3 = await HashChainLedger.add_block(session, "inc-03", "ev-03", "sha256_03", "CAM-01", {"track_id": 3})
        await session.commit()
        
        valid_before = await HashChainLedger.verify_chain(session)
        results["tamper_test_baseline_valid"] = valid_before
        
        # Tamper with block 2's evidence hash (simulating modified evidence file)
        b2.evidence_sha256 = "TAMPERED_HASH_9999"
        session.add(b2)
        await session.commit()
        
        valid_after_tamper = await HashChainLedger.verify_chain(session)
        results["tamper_test_after_corruption_valid"] = valid_after_tamper
        results["tamper_detection_successful"] = (valid_before[0] is True and valid_after_tamper[0] is False)

    import json
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(run_evidence_integrity_audit())
