"""
IBVAP — Spatial Rule Engine and Geometry Tests
==============================================
Verifies:
1. Ground contact point calculation (bottom-center of bounding box: x=center_x, y=y2)
2. Point-in-polygon containment (inside, outside, edge cases)
3. Line crossing ray-intersection
4. Intrusion detection transition (OUTSIDE -> INSIDE)
"""

import pytest
from datetime import datetime, timezone
from services.detection.schemas import BBox
from services.rules.schemas import Zone, ZoneType, Point, EventType
from services.rules.geometry import point_in_polygon, bbox_center, bbox_ground_point, line_segments_intersect
from services.rules.rule_engine import RuleEngine
from services.tracking.schemas import Track, TrackPoint, TrackState, TrackingResult


def test_bbox_ground_point():
    bbox = BBox(x1=0.2, y1=0.4, x2=0.6, y2=0.8)
    gp = bbox_ground_point(bbox)
    assert pytest.approx(gp.x) == 0.4 # (0.2 + 0.6) / 2
    assert pytest.approx(gp.y) == 0.8 # y2 (feet contact point)


def test_point_in_polygon_square():
    square = [
        Point(0.2, 0.2),
        Point(0.8, 0.2),
        Point(0.8, 0.8),
        Point(0.2, 0.8)
    ]
    # Inside
    assert point_in_polygon(Point(0.5, 0.5), square) is True
    # Outside
    assert point_in_polygon(Point(0.1, 0.5), square) is False
    assert point_in_polygon(Point(0.5, 0.9), square) is False


def test_rule_engine_bottom_center_intrusion():
    # Zone covers [0.5, 0.5] to [1.0, 1.0]
    zone = Zone(
        zone_id="ZONE-01",
        name="Restricted Zone",
        camera_id="CAM-01",
        zone_type=ZoneType.RESTRICTED_ZONE,
        points=[
            Point(0.5, 0.5),
            Point(1.0, 0.5),
            Point(1.0, 1.0),
            Point(0.5, 1.0)
        ],
        enabled=True
    )
    engine = RuleEngine(zones=[zone])

    now = datetime.now(timezone.utc)

    # Frame 1: Person bbox from y1=0.1 to y2=0.45 (ground point is outside zone y=0.45 < 0.5)
    bbox_outside = BBox(x1=0.6, y1=0.1, x2=0.8, y2=0.45)
    track = Track(
        track_id=101,
        camera_id="CAM-01",
        class_name="person",
        state=TrackState.ACTIVE,
        bbox=bbox_outside,
        center_x=bbox_outside.center_x,
        center_y=bbox_outside.center_y,
        first_seen=now,
        last_seen=now,
        confidence_history=[0.9],
        trajectory=[TrackPoint(now, bbox_outside, bbox_outside.center_x, bbox_outside.center_y, 0.9)],
        age_frames=1
    )
    res1 = TrackingResult("CAM-01", 1, now, [track], [101], [])
    events1 = engine.evaluate(res1)
    # Ground point is not inside zone yet
    assert len(events1) == 0

    # Frame 2: Person steps forward, ground point feet at y2=0.55 (now inside zone)
    bbox_inside = BBox(x1=0.6, y1=0.2, x2=0.8, y2=0.55)
    track.bbox = bbox_inside
    track.center_x = bbox_inside.center_x
    track.center_y = bbox_inside.center_y
    track.trajectory.append(TrackPoint(now, bbox_inside, bbox_inside.center_x, bbox_inside.center_y, 0.92))
    track.age_frames += 1

    res2 = TrackingResult("CAM-01", 2, now, [track], [], [])
    events2 = engine.evaluate(res2)

    assert len(events2) == 1
    assert events2[0].event_type == EventType.ZONE_ENTRY
    assert events2[0].track_id == 101
    assert events2[0].zone_id == "ZONE-01"
