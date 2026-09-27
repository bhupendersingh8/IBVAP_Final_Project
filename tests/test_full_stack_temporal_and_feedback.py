"""
IBVAP — Full Stack Temporal Event Engine, Operator Feedback & Health Tests
========================================================================
Verifies:
1. Health endpoints (/health, /health/live, /api/v1/health) return HTTP 200 OK.
2. Operator Feedback Loop (POST /api/v1/events/feedback and /api/v1/feedback)
   supports TRUE_INTRUSION, FALSE_ALARM, and UNSURE labeling.
3. MainInferenceWorker evaluates TemporalEventEngine:
   - LOITERING (dwell_time >= 15s)
   - DIRECTION_VIOLATION (prohibited headings toward border)
   - NIGHT_MOVEMENT (curfew 22:00-05:00 IST)
   - REPEATED_ENTRY (>= 3 entries)
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from starlette.testclient import TestClient
from apps.backend.main import app
from apps.backend.database.connection import AsyncSessionLocal, init_db
from apps.backend.database.models import Incident, Event, Camera
from services.inference.main_inference_worker import MainInferenceWorker
from services.tracking.schemas import Track, TrackPoint, TrackState, TrackingResult
from services.detection.schemas import BBox
from services.rules.temporal_event_engine import TemporalEventType


def test_backend_health_endpoints():
    """Verify that backend health endpoints respond with 200 OK."""
    client = TestClient(app)

    # 1. Root /health
    resp1 = client.get("/health")
    assert resp1.status_code == 200
    assert resp1.json().get("status") == "ok"

    # 2. Kubernetes-style /health/live
    resp2 = client.get("/health/live")
    assert resp2.status_code == 200
    assert resp2.json().get("status") == "ok"

    # 3. API versioned /api/v1/health
    resp3 = client.get("/api/v1/health")
    assert resp3.status_code == 200
    assert resp3.json().get("status") == "ok"


def test_operator_feedback_loop():
    """Verify POST /api/v1/events/feedback and POST /api/v1/feedback with all labels."""
    async def _setup_and_test():
        await init_db()
        now = datetime.now(timezone.utc)
        incident_id = str(uuid.uuid4())
        event_id = str(uuid.uuid4())

        # Seed test camera and incident
        async with AsyncSessionLocal() as session:
            cam = await session.get(Camera, "CAM-TEST")
            if not cam:
                cam = Camera(id="CAM-TEST", name="Test Camera", scenario="border", enabled=True)
                session.add(cam)

            db_event = Event(
                id=event_id,
                camera_id="CAM-TEST",
                track_id=1,
                event_type="LOITERING",
                severity="MEDIUM",
                confidence=0.88,
                explanation="Person loitering near fence",
                timestamp=now
            )
            session.add(db_event)

            db_inc = Incident(
                id=incident_id,
                camera_id="CAM-TEST",
                event_id=event_id,
                timestamp=now,
                event_type="LOITERING",
                severity="MEDIUM",
                model_version="yolov8n-v1",
                confidence=0.88,
                status="NEW",
                acknowledged=False
            )
            session.add(db_inc)
            await session.commit()

        client = TestClient(app)

        # 1. Test POST /api/v1/events/feedback with TRUE_INTRUSION
        resp_true = client.post("/api/v1/events/feedback", json={
            "incident_id": incident_id,
            "label": "TRUE_INTRUSION",
            "notes": "Verified intrusion by human operator"
        })
        assert resp_true.status_code == 200
        assert resp_true.json().get("success") is True

        # Verify status became INVESTIGATING and acknowledged
        async with AsyncSessionLocal() as session:
            inc = await session.get(Incident, incident_id)
            assert inc.status == "INVESTIGATING"
            assert inc.acknowledged is True

        # 2. Test POST /api/v1/events/feedback with FALSE_ALARM
        resp_false = client.post("/api/v1/events/feedback", json={
            "incident_id": incident_id,
            "label": "FALSE_ALARM",
            "notes": "Benign maintenance personnel"
        })
        assert resp_false.status_code == 200
        assert resp_false.json().get("success") is True

        # Verify status became RESOLVED
        async with AsyncSessionLocal() as session:
            inc = await session.get(Incident, incident_id)
            assert inc.status == "RESOLVED"

        # 3. Test POST /api/v1/feedback (backward compatibility route) with UNSURE
        resp_unsure = client.post("/api/v1/feedback", json={
            "incident_id": incident_id,
            "label": "UNSURE",
            "notes": "Camera obstructed by fog"
        })
        assert resp_unsure.status_code == 200
        assert resp_unsure.json().get("success") is True

    asyncio.run(_setup_and_test())


def test_worker_temporal_event_engine_wiring():
    """Verify that MainInferenceWorker's TemporalEventEngine detects behavioral events."""
    worker = MainInferenceWorker(camera_id="CAM-01")
    now_day = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)
    now_night = datetime(2026, 9, 6, 17, 30, 0, tzinfo=timezone.utc) # 23:00 IST (curfew)

    # 1. Loitering test (dwell >= 15s)
    worker.temporal_engine.process_dwell(
        camera_id="CAM-01",
        track_id=101,
        class_name="person",
        zone_id="RESTRICTED_ZONE_01",
        dwell_seconds=16.0,
        confidence=0.91,
        timestamp=now_day
    )
    assert not worker.temporal_event_queue.empty()
    ev1 = worker.temporal_event_queue.get_nowait()
    assert ev1.event_type == TemporalEventType.LOITERING
    assert ev1.track_id == 101
    assert ev1.dwell_seconds == 16.0

    # 2. Direction Violation test (heading North toward boundary)
    worker.temporal_engine.process_direction_violation(
        camera_id="CAM-01",
        track_id=102,
        class_name="vehicle",
        direction="N",
        disallowed_directions={"N", "NORTH", "NW", "NORTH_WEST"},
        confidence=0.87,
        timestamp=now_day,
        boundary_name="international boundary"
    )
    assert not worker.temporal_event_queue.empty()
    ev2 = worker.temporal_event_queue.get_nowait()
    assert ev2.event_type == TemporalEventType.DIRECTION_VIOLATION
    assert ev2.track_id == 102
    assert "moving N toward international boundary" in ev2.reason

    # 3. Night Movement test (during curfew 22:00-05:00 IST)
    worker.temporal_engine.process_night_movement(
        camera_id="CAM-01",
        track_id=103,
        class_name="person",
        confidence=0.89,
        timestamp=now_night
    )
    assert not worker.temporal_event_queue.empty()
    ev3 = worker.temporal_event_queue.get_nowait()
    assert ev3.event_type == TemporalEventType.NIGHT_MOVEMENT
    assert ev3.track_id == 103
    assert "night hours" in ev3.reason

    # 4. Repeated Entry test (>= 3 times)
    worker.temporal_engine.config.cooldown_seconds = 0.01
    worker.temporal_engine.config.dedup_window_seconds = 0.01

    worker.temporal_engine.process_intrusion("CAM-01", 104, "truck", "GATE_ALPHA", 0.9, now_day)
    worker.temporal_engine.process_intrusion("CAM-01", 104, "truck", "GATE_ALPHA", 0.9, now_day + timedelta(seconds=1))
    worker.temporal_engine.process_intrusion("CAM-01", 104, "truck", "GATE_ALPHA", 0.9, now_day + timedelta(seconds=2))

    emitted_types = []
    while not worker.temporal_event_queue.empty():
        ev = worker.temporal_event_queue.get_nowait()
        emitted_types.append(ev.event_type)

    assert TemporalEventType.REPEATED_ENTRY in emitted_types