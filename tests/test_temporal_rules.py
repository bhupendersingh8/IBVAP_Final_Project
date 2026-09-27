"""
IBVAP -- Temporal Event Engine and Behavioral Analytics Tests
============================================================
Verifies SIH 2026 PS-26187 requirements:
1. ZONE_INTRUSION: Detection of target crossing into restricted border perimeter.
2. LOITERING: Sustained presence in a zone exceeding configurable threshold (e.g. 20s).
3. DIRECTION_VIOLATION: Movement vector matching restricted headings toward international boundary.
4. NIGHT_MOVEMENT: Temporal detection during border curfew / night hours (22:00-05:00).
5. REPEATED_ENTRY: Track re-entering a zone >= threshold times within session (reconnaissance detection).
6. Anti-spam deduplication and cooldown suppression.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from services.rules.temporal_event_engine import (
    TemporalEventEngine,
    TemporalEngineConfig,
    TemporalEventType,
    TemporalState,
    EventSeverity,
    TemporalEvent,
    _is_night,
    _severity
)


def test_zone_intrusion_emitted():
    async def _run():
        q = asyncio.Queue()
        engine = TemporalEventEngine(event_queue=q, config=TemporalEngineConfig(cooldown_seconds=1.0))
        now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)

        engine.process_intrusion(
            camera_id="CAM-01",
            track_id=42,
            class_name="person",
            zone_id="BORDER_FENCE_01",
            confidence=0.92,
            timestamp=now
        )

        assert not q.empty()
        event = await q.get()
        assert event.event_type == TemporalEventType.ZONE_INTRUSION
        assert event.track_id == 42
        assert event.camera_id == "CAM-01"
        assert event.zone_id == "BORDER_FENCE_01"
        assert event.class_name == "person"
        assert event.severity == EventSeverity.MEDIUM
        assert "entered restricted zone" in event.reason

    asyncio.run(_run())


def test_loitering_dwell_threshold():
    async def _run():
        q = asyncio.Queue()
        config = TemporalEngineConfig(loitering_threshold_seconds=15.0, cooldown_seconds=2.0)
        engine = TemporalEventEngine(event_queue=q, config=config)
        now = datetime(2026, 9, 6, 14, 0, 0, tzinfo=timezone.utc)

        engine.process_dwell(
            camera_id="CAM-01",
            track_id=10,
            class_name="person",
            zone_id="OUTPOST_SECTOR_A",
            dwell_seconds=10.0,
            confidence=0.88,
            timestamp=now
        )
        assert q.empty()

        engine.process_dwell(
            camera_id="CAM-01",
            track_id=10,
            class_name="person",
            zone_id="OUTPOST_SECTOR_A",
            dwell_seconds=16.5,
            confidence=0.88,
            timestamp=now + timedelta(seconds=6.5)
        )
        assert not q.empty()
        event = await q.get()
        assert event.event_type == TemporalEventType.LOITERING
        assert event.dwell_seconds == 16.5
        assert "loitering in zone 'OUTPOST_SECTOR_A' for 16.5s" in event.reason

    asyncio.run(_run())


def test_direction_violation():
    async def _run():
        q = asyncio.Queue()
        engine = TemporalEventEngine(event_queue=q)
        now = datetime(2026, 9, 6, 15, 0, 0, tzinfo=timezone.utc)

        engine.process_direction_violation(
            camera_id="CAM-02",
            track_id=5,
            class_name="vehicle",
            direction="SOUTH",
            disallowed_directions={"NORTH", "NORTH_WEST"},
            confidence=0.85,
            timestamp=now,
            boundary_name="zero line"
        )
        assert q.empty()

        engine.process_direction_violation(
            camera_id="CAM-02",
            track_id=5,
            class_name="vehicle",
            direction="NORTH",
            disallowed_directions={"NORTH", "NORTH_WEST"},
            confidence=0.85,
            timestamp=now,
            boundary_name="zero line"
        )
        assert not q.empty()
        event = await q.get()
        assert event.event_type == TemporalEventType.DIRECTION_VIOLATION
        assert "moving NORTH toward zero line" in event.reason

    asyncio.run(_run())


def test_night_movement_detection():
    async def _run():
        q = asyncio.Queue()
        night_time_utc = datetime(2026, 9, 6, 17, 30, 0, tzinfo=timezone.utc)
        engine = TemporalEventEngine(event_queue=q)

        engine.process_night_movement(
            camera_id="CAM-03",
            track_id=77,
            class_name="person",
            confidence=0.91,
            timestamp=night_time_utc
        )

        assert not q.empty()
        event = await q.get()
        assert event.event_type == TemporalEventType.NIGHT_MOVEMENT
        assert event.severity == EventSeverity.HIGH
        assert "night hours" in event.reason

    asyncio.run(_run())


def test_repeated_entry_detection():
    async def _run():
        q = asyncio.Queue()
        config = TemporalEngineConfig(
            repeated_entry_threshold=3,
            cooldown_seconds=1.0,
            dedup_window_seconds=0.1
        )
        engine = TemporalEventEngine(event_queue=q, config=config)
        base_time = datetime(2026, 9, 6, 10, 0, 0, tzinfo=timezone.utc)

        engine.process_intrusion("CAM-01", 99, "person", "CHECKPOST_1", 0.9, base_time)
        e1 = await q.get()
        assert e1.event_type == TemporalEventType.ZONE_INTRUSION

        t2 = base_time + timedelta(seconds=2)
        engine.process_intrusion("CAM-01", 99, "person", "CHECKPOST_1", 0.9, t2)
        e2 = await q.get()
        assert e2.event_type == TemporalEventType.ZONE_INTRUSION

        t3 = base_time + timedelta(seconds=4)
        engine.process_intrusion("CAM-01", 99, "person", "CHECKPOST_1", 0.9, t3)
        
        emitted_types = []
        while not q.empty():
            ev = await q.get()
            emitted_types.append(ev.event_type)

        assert TemporalEventType.REPEATED_ENTRY in emitted_types
        assert TemporalEventType.ZONE_INTRUSION in emitted_types

    asyncio.run(_run())


def test_cooldown_anti_spam_suppression():
    async def _run():
        q = asyncio.Queue()
        config = TemporalEngineConfig(cooldown_seconds=30.0, dedup_window_seconds=5.0)
        engine = TemporalEventEngine(event_queue=q, config=config)
        now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)

        engine.process_intrusion("CAM-01", 12, "truck", "GATE_A", 0.95, now)
        assert q.qsize() == 1
        await q.get()

        engine.process_intrusion("CAM-01", 12, "truck", "GATE_A", 0.95, now + timedelta(seconds=10))
        assert q.empty()

        stats = engine.get_stats()
        assert stats["total_emitted"] == 1

    asyncio.run(_run())


def test_temporal_state_progression():
    """Verify Phase 11 DETECTED -> TENTATIVE -> STABLE -> VERIFIED -> ALERT_ELIGIBLE (~45 frames baseline)."""
    engine = TemporalEventEngine(
        config=TemporalEngineConfig(
            min_alert_frames=45,
            tentative_threshold_frames=10,
            stable_threshold_frames=25,
            verified_threshold_frames=35,
        )
    )
    base_time = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)

    # Frame 1: DETECTED
    state, eligible = engine.validate_candidate(
        track_id=101, event_type="ZONE_INTRUSION", zone_id="ZONE_A", frame_number=1, timestamp=base_time
    )
    assert state == TemporalState.DETECTED
    assert not eligible

    # Frames 2-9: Still DETECTED
    for f in range(2, 10):
        t = base_time + timedelta(milliseconds=33 * f)
        state, eligible = engine.validate_candidate(
            track_id=101, event_type="ZONE_INTRUSION", zone_id="ZONE_A", frame_number=f, timestamp=t
        )
        assert state == TemporalState.DETECTED
        assert not eligible

    # Frame 10: TENTATIVE
    t10 = base_time + timedelta(milliseconds=330)
    state, eligible = engine.validate_candidate(
        track_id=101, event_type="ZONE_INTRUSION", zone_id="ZONE_A", frame_number=10, timestamp=t10
    )
    assert state == TemporalState.TENTATIVE
    assert not eligible

    # Frame 25: STABLE
    for f in range(11, 26):
        t = base_time + timedelta(milliseconds=33 * f)
        state, eligible = engine.validate_candidate(
            track_id=101, event_type="ZONE_INTRUSION", zone_id="ZONE_A", frame_number=f, timestamp=t
        )
    assert state == TemporalState.STABLE
    assert not eligible

    # Frame 35: VERIFIED
    for f in range(26, 36):
        t = base_time + timedelta(milliseconds=33 * f)
        state, eligible = engine.validate_candidate(
            track_id=101, event_type="ZONE_INTRUSION", zone_id="ZONE_A", frame_number=f, timestamp=t
        )
    assert state == TemporalState.VERIFIED
    assert not eligible

    # Frame 45: ALERT_ELIGIBLE
    for f in range(36, 46):
        t = base_time + timedelta(milliseconds=33 * f)
        state, eligible = engine.validate_candidate(
            track_id=101, event_type="ZONE_INTRUSION", zone_id="ZONE_A", frame_number=f, timestamp=t
        )
    assert state == TemporalState.ALERT_ELIGIBLE
    assert eligible


def test_temporal_candidate_gap_expiry():
    """Verify that a candidate with observation gap exceeding candidate_expiry_seconds transitions to EXPIRED."""
    engine = TemporalEventEngine(
        config=TemporalEngineConfig(
            candidate_expiry_seconds=2.0,
            min_alert_frames=45,
        )
    )
    t0 = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)
    state, _ = engine.validate_candidate(track_id=202, event_type="LOITERING", frame_number=1, timestamp=t0)
    assert state == TemporalState.DETECTED

    # Advance by 3 seconds (> 2.0s expiry threshold)
    t_after = t0 + timedelta(seconds=3.0)
    state, eligible = engine.validate_candidate(track_id=202, event_type="LOITERING", frame_number=2, timestamp=t_after)
    assert state == TemporalState.EXPIRED
    assert not eligible


def test_temporal_candidate_clear():
    """Verify that clear_candidate explicitly sets candidate state to CLEARED."""
    engine = TemporalEventEngine()
    t0 = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)
    engine.validate_candidate(track_id=303, event_type="ZONE_INTRUSION", zone_id="ZONE_B", timestamp=t0)
    assert engine.get_candidate_state(303, "ZONE_INTRUSION", "ZONE_B") == TemporalState.DETECTED

    cleared_state = engine.clear_candidate(303, "ZONE_INTRUSION", "ZONE_B")
    assert cleared_state == TemporalState.CLEARED
    assert engine.get_candidate_state(303, "ZONE_INTRUSION", "ZONE_B") == TemporalState.CLEARED

