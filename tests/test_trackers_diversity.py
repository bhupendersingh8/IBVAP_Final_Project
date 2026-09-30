"""
Unit Tests for Tracker Diversity & Factory
==========================================
Verifies ByteTrack, BoT-SORT (with CMC & Kalman), OC-SORT (with momentum),
and TrackerFactory dynamic instantiation.
"""

import pytest
import numpy as np
from datetime import datetime, timezone

from services.detection.schemas import DetectionBatch, Detection, BBox
from services.tracking.tracker_factory import TrackerFactory
from services.tracking.bytetrack_adapter import FallbackIoUTracker, ByteTrackAdapter
from services.tracking.botsort_adapter import BoTSORTAdapter
from services.tracking.ocsort_adapter import OCSORTAdapter
from services.tracking.kalman_filter import KalmanFilterTracker, xywh_to_xyah, xyah_to_xyxy


def test_kalman_filter_state_cycle():
    kf = KalmanFilterTracker()
    box = np.array([100.0, 100.0, 150.0, 200.0], dtype=np.float32)
    xyah = xywh_to_xyah(box)
    mean, cov = kf.initiate(xyah)
    assert mean.shape == (8,)
    assert cov.shape == (8, 8)

    # Predict
    pred_mean, pred_cov = kf.predict(mean, cov)
    assert pred_mean.shape == (8,)

    # Update with shifted measurement
    meas2 = xywh_to_xyah(np.array([105.0, 102.0, 155.0, 202.0], dtype=np.float32))
    new_mean, new_cov = kf.update(pred_mean, pred_cov, meas2)
    xyxy = xyah_to_xyxy(new_mean)
    assert len(xyxy) == 4
    assert xyxy[0] > 0


def test_tracker_factory_resolution():
    assert "bytetrack" in TrackerFactory.list_available_trackers()
    assert "botsort" in TrackerFactory.list_available_trackers()
    assert "ocsort" in TrackerFactory.list_available_trackers()

    t_byte = TrackerFactory.create_tracker("bytetrack")
    assert isinstance(t_byte, FallbackIoUTracker)

    t_bot = TrackerFactory.create_tracker("botsort")
    assert isinstance(t_bot, BoTSORTAdapter)

    t_oc = TrackerFactory.create_tracker("ocsort")
    assert isinstance(t_oc, OCSORTAdapter)


def test_botsort_update_and_cmc():
    tracker = BoTSORTAdapter(track_high_thresh=0.5, track_low_thresh=0.2)
    now = datetime.now(timezone.utc)
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)

    batch1 = DetectionBatch(
        camera_id="CAM-01",
        frame_id=1,
        timestamp=now,
        detections=[Detection(BBox(100, 100, 200, 300), "person", 0.92)]
    )
    res1 = tracker.update(batch1, frame_image=frame)
    assert len(res1.active_tracks) == 1
    tid = res1.active_tracks[0].track_id

    # Second frame with small movement
    batch2 = DetectionBatch(
        camera_id="CAM-01",
        frame_id=2,
        timestamp=now,
        detections=[Detection(BBox(105, 102, 205, 302), "person", 0.89)]
    )
    res2 = tracker.update(batch2, frame_image=frame)
    assert len(res2.active_tracks) == 1
    assert res2.active_tracks[0].track_id == tid


def test_ocsort_update_and_momentum():
    tracker = OCSORTAdapter(det_thresh=0.4)
    now = datetime.now(timezone.utc)

    batch1 = DetectionBatch(
        camera_id="CAM-02",
        frame_id=1,
        timestamp=now,
        detections=[Detection(BBox(300, 200, 450, 400), "car", 0.88)]
    )
    res1 = tracker.update(batch1)
    assert len(res1.active_tracks) == 1
    tid = res1.active_tracks[0].track_id

    batch2 = DetectionBatch(
        camera_id="CAM-02",
        frame_id=2,
        timestamp=now,
        detections=[Detection(BBox(310, 200, 460, 400), "car", 0.85)]
    )
    res2 = tracker.update(batch2)
    assert len(res2.active_tracks) == 1
    assert res2.active_tracks[0].track_id == tid
    assert tracker.velocity_directions[tid][0] > 0 # positive x direction
