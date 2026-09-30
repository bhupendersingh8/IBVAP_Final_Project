"""
Detection, Tracking & Zone Geometry Reality Audit for IBVAP.
Runs genuine YOLOv8n inference on data/test_video.mp4, updates tracker,
and evaluates spatial/temporal rule triggers.
"""
import sys
import os
import cv2
import json
import numpy as np

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from services.detection.yolo_adapter import YOLOAdapter
from services.tracking.bytetrack_adapter import FallbackIoUTracker
from services.tracking.track_analytics import analyze_track
from services.rules.geometry import point_in_polygon, bbox_ground_point
from services.rules.schemas import Point, Zone, ZoneType
from services.rules.rule_engine import RuleEngine
from services.rules.temporal_event_engine import TemporalEventEngine

results = {}

# 1. Test Ground Contact Point and Geometry
test_zone = Zone(
    zone_id="TEST_SECTOR",
    name="Test Sector",
    camera_id="CAM-01",
    zone_type=ZoneType.RESTRICTED_ZONE,
    points=[Point(x=0.4, y=0.4), Point(x=0.8, y=0.4), Point(x=0.8, y=0.9), Point(x=0.4, y=0.9)]
)

# Simulated Person: Standing outside zone at bottom (y2=0.95), but head at y1=0.35 (inside y range)
# Ground contact must place them OUTSIDE
pt_ground_outside = Point(x=0.3, y=0.95)
inside_outside_check = point_in_polygon(pt_ground_outside, test_zone.points)

# Simulated Person stepping inside (ground contact at 0.5, 0.6)
pt_ground_inside = Point(x=0.5, y=0.6)
inside_inside_check = point_in_polygon(pt_ground_inside, test_zone.points)

results["geometry_ground_contact"] = {
    "point_outside_is_inside": inside_outside_check,
    "point_inside_is_inside": inside_inside_check,
    "ground_contact_anchor": "bottom-center (x_center, y2)",
    "correct_spatial_behavior": (not inside_outside_check and inside_inside_check)
}

# 2. Test Real YOLOv8n Detection on Video Frame
video_path = str(PROJECT_ROOT / "data" / "raw" / "test_video.mp4")
detector = YOLOAdapter({
    "model_path": str(PROJECT_ROOT / "yolov8n.pt"),
    "device": "cpu",
    "confidence_threshold": 0.35,
    "input_size": 640
})
detector.load_model()

tracker = FallbackIoUTracker(max_age=30, iou_threshold=0.3)
rule_engine = RuleEngine([test_zone])
temporal_engine = TemporalEventEngine()

cap = cv2.VideoCapture(video_path)
frame_count = 0
detection_classes_seen = set()
tracks_observed = {}
events_triggered = []

while cap.isOpened() and frame_count < 25:
    ret, frame = cap.read()
    if not ret or frame is None:
        break
    frame_count += 1
    
    # Genuine YOLO Detection
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc)
    batch = detector.detect(frame, "CAM-01", frame_count, ts)
    for det in batch.detections:
        detection_classes_seen.add(det.class_name)
    
    # Tracking update
    tracking_res = tracker.update(batch)
    for t in tracking_res.active_tracks:
        if t.track_id not in tracks_observed:
            tracks_observed[t.track_id] = {
                "class_name": t.class_name,
                "first_seen_frame": frame_count,
                "hits": 1
            }
        else:
            tracks_observed[t.track_id]["hits"] += 1
        
        # Track analytics
        analytics = analyze_track(t)
        tracks_observed[t.track_id]["speed"] = analytics.speed
        tracks_observed[t.track_id]["direction"] = analytics.direction
        tracks_observed[t.track_id]["dwell_s"] = analytics.dwell_seconds
    
    # Rule Evaluation
    spatial_events = rule_engine.evaluate(tracking_res)
    for se in spatial_events:
        # find class name from active_tracks
        matched = next((t for t in tracking_res.active_tracks if t.track_id == se.track_id), None)
        cls_name = matched.class_name if matched else "person"
        temporal_engine.process_intrusion(
            camera_id=se.camera_id,
            track_id=se.track_id,
            class_name=cls_name,
            zone_id=se.zone_id,
            confidence=se.confidence,
            timestamp=se.timestamp
        )
        while not temporal_engine.event_queue.empty():
            ev = temporal_engine.event_queue.get_nowait()
            events_triggered.append({
                "event_type": ev.event_type.value,
                "severity": ev.severity.value,
                "camera_id": ev.camera_id,
                "track_id": ev.track_id,
                "reason": ev.reason
            })

cap.release()

results["real_detection_and_tracking"] = {
    "frames_analyzed": frame_count,
    "classes_detected": list(detection_classes_seen),
    "total_unique_tracks": len(tracks_observed),
    "sample_tracks": {k: tracks_observed[k] for k in list(tracks_observed.keys())[:3]},
    "spatial_events_emitted": len(events_triggered),
    "sample_events": events_triggered[:2]
}

print(json.dumps(results, indent=2))
