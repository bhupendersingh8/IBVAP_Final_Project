"""
IBVAP — Cryptographic Hash Chain Ledger Tests
=============================================
Verifies genesis initialization, sequential SHA-256 block linking,
tamper-evident detection, and invalid link rejection.
Uses an isolated in-memory database to prevent test pollution.
"""

import os
import sys
import pytest
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apps.backend.database.models import Base, HashChainBlock
from services.evidence.hash_chain import HashChainLedger, GENESIS_PREVIOUS_HASH, compute_block_hash


async def create_isolated_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, session_maker


def test_empty_chain_is_valid():
    async def _run():
        engine, session_maker = await create_isolated_db()
        async with session_maker() as session:
            is_valid, corrupted_id, msg = await HashChainLedger.verify_chain(session)
            assert is_valid is True
            assert corrupted_id is None
            assert "empty" in msg.lower()
        await engine.dispose()
    asyncio.run(_run())


def test_single_block_addition_and_verification():
    async def _run():
        engine, session_maker = await create_isolated_db()
        now = datetime.now(timezone.utc)
        async with session_maker() as session:
            block1 = await HashChainLedger.add_block(
                session=session,
                incident_id="INC-CHAIN-001",
                event_id="EVT-CHAIN-001",
                evidence_sha256="a" * 64,
                camera_id="CAM-01",
                payload_data={"test": 123},
                timestamp=now
            )
            await session.commit()

            assert block1.previous_hash == GENESIS_PREVIOUS_HASH
            assert len(block1.record_hash) == 64

            is_valid, corrupted_id, msg = await HashChainLedger.verify_chain(session)
            assert is_valid is True
            assert corrupted_id is None
        await engine.dispose()
    asyncio.run(_run())


def test_multi_block_sequential_linking():
    async def _run():
        engine, session_maker = await create_isolated_db()
        now = datetime.now(timezone.utc)
        async with session_maker() as session:
            b1 = await HashChainLedger.add_block(
                session=session,
                incident_id="INC-CHAIN-002",
                event_id="EVT-CHAIN-002",
                evidence_sha256="b" * 64,
                camera_id="CAM-01",
                payload_data={"severity": "HIGH"},
                timestamp=now
            )
            b2 = await HashChainLedger.add_block(
                session=session,
                incident_id="INC-CHAIN-003",
                event_id="EVT-CHAIN-003",
                evidence_sha256="c" * 64,
                camera_id="CAM-01",
                payload_data={"severity": "CRITICAL"},
                timestamp=now
            )
            await session.commit()

            assert b2.previous_hash == b1.record_hash

            is_valid, corrupted_id, msg = await HashChainLedger.verify_chain(session)
            assert is_valid is True
            assert corrupted_id is None
        await engine.dispose()
    asyncio.run(_run())


def test_tamper_detection():
    async def _run():
        engine, session_maker = await create_isolated_db()
        now = datetime.now(timezone.utc)
        async with session_maker() as session:
            b1 = await HashChainLedger.add_block(
                session=session,
                incident_id="INC-CHAIN-004",
                event_id="EVT-CHAIN-004",
                evidence_sha256="d" * 64,
                camera_id="CAM-01",
                payload_data={"status": "ORIGINAL"},
                timestamp=now
            )
            await session.commit()

            # Tamper with payload directly
            b1.payload_json = '{"status": "FORGED_TAMPERED"}'
            await session.commit()

            is_valid, corrupted_id, msg = await HashChainLedger.verify_chain(session)
            assert is_valid is False
            assert corrupted_id == b1.sequence_id
            assert "tampered" in msg.lower()
        await engine.dispose()
    asyncio.run(_run())
