"""
tests/test_heavy_reasoner_queue.py
==================================
Tests for Asynchronous Heavy AI Priority Queue & Zero-Cost Tactical Reasoning.
"""
from __future__ import annotations

import asyncio
import numpy as np
import pytest

from services.agents.heavy_reasoner_queue import HeavyReasonerQueue, HeavyTaskItem


def test_priority_ordering():
    """Verify that P0 Critical tasks are dequeued before P2 Medium tasks."""
    async def _run():
        queue = HeavyReasonerQueue(maxsize=10)

        # Enqueue P2 first, then P0
        queue.enqueue_event(
            incident_id="INC-P2-001",
            camera_id="CAM-01",
            event_data={"event_type": "LOITERING", "severity": "MEDIUM"},
            context_slice=[{"relative_sec": -2.0}, {"relative_sec": 0.0}],
            priority=2,  # P2
        )

        queue.enqueue_event(
            incident_id="INC-P0-001",
            camera_id="CAM-01",
            event_data={"event_type": "PERIMETER_BREACH", "severity": "CRITICAL"},
            context_slice=[{"relative_sec": -5.0}, {"relative_sec": 0.0}, {"relative_sec": 2.0}],
            priority=0,  # P0
        )

        # Dequeue first item -> should be P0!
        first_item = await queue.queue.get()
        assert first_item.priority == 0
        assert first_item.incident_id == "INC-P0-001"

        # Dequeue second item -> should be P2
        second_item = await queue.queue.get()
        assert second_item.priority == 2
        assert second_item.incident_id == "INC-P2-001"

    asyncio.run(_run())


def test_zero_cost_local_reasoning():
    """Verify that tactical analysis produces rich narrative at 0.0 cost."""
    async def _run():
        queue = HeavyReasonerQueue()
        task = HeavyTaskItem(
            priority=0,
            created_at=0.0,
            incident_id="INC-TEST-99",
            camera_id="CAM-01",
            event_data={"event_type": "PERIMETER_BREACH", "severity": "CRITICAL", "zone_name": "SECTOR_DELTA"},
            context_slice=[{"relative_sec": -5.0}, {"relative_sec": 0.0}, {"relative_sec": 3.0}],
        )

        analysis = await queue._analyze_incident(task)
        assert "SECTOR_DELTA" in analysis["tactical_assessment"]
        assert "BSF SOP" in analysis["sop_action_directive"]
        assert analysis["cost_cents"] == 0.0
        assert analysis["model_engine"] == "TacticalOfflineBrain_17Layers"

    asyncio.run(_run())
