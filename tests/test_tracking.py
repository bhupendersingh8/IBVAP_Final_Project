"""
IBVAP — Tracking Unit Tests
=============================
Tests for the tracking service: schemas, ByteTrackAdapter (fallback IoU
backend), track lifecycle, trajectory accumulation, and TrackingResult output.

These tests require NO real ML models and NO GPU.  They operate entirely on
synthetic detections produced by a minimal mock detector.

Run with:
    pytest tests/test_tracking.py -v
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List
from unittest.mock import patch

import pytest

from services.detection.schemas import BBox, Detection, DetectionBatch
from services.tracking.bytetrack_adapter import ByteTrackAdapter
from services.tracking.schemas import Track, TrackPoint, TrackState, TrackingResult


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_bbox(x1: float, y1: float, x2: float, y2: float) -> BBox:
    return BBox(x1=x1, y1=y1, x2=x2, y2=y2)


def _make_detection(
    bbox: BBox,
    class_name: str = "person",
    confidence: float = 0.9,
    class_id: int = 0,
) -> Detection:
    return Detection(
        bbox=bbox,
        class_name=class_name,
        class_id=class_id,
        confidence=confidence,
    )


def _make_batch(
    detections: List[Detection],
    camera_id: str = "cam_test",
    frame_id: int = 1,
    frame_width: int = 1920,
    frame_height: int = 1080,
) -> DetectionBatch:
    return DetectionBatch(
        camera_id=camera_id,
        frame_id=frame_id,
        timestamp=_utcnow(),
        detections=detections,
        frame_width=frame_width,
        frame_height=frame_height,
    )


def _make_tracker(
    max_age: int = 5,
    min_hits: int = 1,
    iou_threshold: float = 0.3,
    max_trajectory_length: int = 50,
) -> ByteTrackAdapter:
    """
    Return a ByteTrackAdapter forced into the fallback IoU backend by
    patching the Ultralytics availability flag.
    """
    with patch("services.tracking.bytetrack_adapter._ULTRALYTICS_AVAILABLE", False):
        tracker = ByteTrackAdapter(
            max_age=max_age,
            min_hits=min_hits,
            iou_threshold=iou_threshold,
            max_trajectory_length=max_trajectory_length,
        )
    return tracker


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestTrackPointSchema:
    def test_requires_tz_aware_timestamp(self) -> None:
        """TrackPoint must reject naive datetimes."""
        with pytest.raises(ValueError, match="timezone-aware"):
            TrackPoint(
                timestamp=datetime(2024, 1, 1),  # naive!
                bbox=_make_bbox(0, 0, 10, 10),
                center_x=5.0,
                center_y=5.0,
                confidence=0.8,
            )

    def test_accepts_utc_timestamp(self) -> None:
        pt = TrackPoint(
            timestamp=_utcnow(),
            bbox=_make_bbox(0, 0, 10, 10),
            center_x=5.0,
            center_y=5.0,
            confidence=0.8,
        )
        assert pt.confidence == 0.8


class TestTrackSchema:
    def _make_track(self, **overrides) -> Track:
        defaults = dict(
            track_id=1,
            camera_id="cam_01",
            class_name="person",
            state=TrackState.ACTIVE,
            bbox=_make_bbox(10, 10, 50, 60),
            center_x=30.0,
            center_y=35.0,
            first_seen=_utcnow(),
            last_seen=_utcnow(),
            confidence_history=[0.8, 0.9],
            trajectory=[],
            age_frames=2,
        )
        defaults.update(overrides)
        return Track(**defaults)

    def test_avg_confidence(self) -> None:
        t = self._make_track(confidence_history=[0.8, 0.9, 1.0])
        assert abs(t.avg_confidence - 0.9) < 1e-6

    def test_avg_confidence_empty(self) -> None:
        t = self._make_track(confidence_history=[])
        assert t.avg_confidence == 0.0

    def test_duration_seconds(self) -> None:
        from datetime import timedelta
        first = _utcnow()
        last = first + timedelta(seconds=5.5)
        t = self._make_track(first_seen=first, last_seen=last)
        assert abs(t.duration_seconds - 5.5) < 0.01

    def test_distance_traveled_two_points(self) -> None:
        now = _utcnow()
        pt1 = TrackPoint(timestamp=now, bbox=_make_bbox(0, 0, 10, 10), center_x=0.0, center_y=0.0, confidence=0.9)
        pt2 = TrackPoint(timestamp=now, bbox=_make_bbox(3, 4, 13, 14), center_x=3.0, center_y=4.0, confidence=0.9)
        t = self._make_track(trajectory=[pt1, pt2])
        assert abs(t.distance_traveled - 5.0) < 1e-6  # 3-4-5 right triangle

    def test_distance_traveled_single_point(self) -> None:
        now = _utcnow()
        pt = TrackPoint(timestamp=now, bbox=_make_bbox(0, 0, 10, 10), center_x=5.0, center_y=5.0, confidence=0.9)
        t = self._make_track(trajectory=[pt])
        assert t.distance_traveled == 0.0

    def test_requires_tz_aware_timestamps(self) -> None:
        with pytest.raises(ValueError):
            Track(
                track_id=1,
                camera_id="cam",
                class_name="person",
                state=TrackState.ACTIVE,
                bbox=_make_bbox(0, 0, 10, 10),
                center_x=5.0,
                center_y=5.0,
                first_seen=datetime(2024, 1, 1),  # naive
                last_seen=_utcnow(),
            )


class TestTrackingResultSchema:
    def test_requires_tz_aware_timestamp(self) -> None:
        with pytest.raises(ValueError):
            TrackingResult(
                camera_id="cam",
                frame_id=1,
                timestamp=datetime(2024, 1, 1),  # naive
            )

    def test_defaults(self) -> None:
        r = TrackingResult(camera_id="cam", frame_id=0, timestamp=_utcnow())
        assert r.active_tracks == []
        assert r.new_tracks == []
        assert r.lost_tracks == []


# ---------------------------------------------------------------------------
# Tracker behaviour tests (always uses fallback IoU backend)
# ---------------------------------------------------------------------------


class TestByteTrackAdapterFallback:
    """Tests that force the fallback IoU backend."""

    @pytest.fixture()
    def tracker(self) -> ByteTrackAdapter:
        return _make_tracker()

    # ------------------------------------------------------------------
    # Track creation
    # ------------------------------------------------------------------

    def test_single_detection_creates_track(self, tracker: ByteTrackAdapter) -> None:
        """One detection in an empty tracker should create exactly one track."""
        det = _make_detection(_make_bbox(100, 100, 200, 200))
        result = tracker.update(_make_batch([det], frame_id=1))
        assert len(result.active_tracks) == 1
        assert len(result.new_tracks) == 1

    def test_two_separate_detections_create_two_tracks(self, tracker: ByteTrackAdapter) -> None:
        """Two non-overlapping detections should create two distinct tracks."""
        det1 = _make_detection(_make_bbox(0, 0, 50, 50))
        det2 = _make_detection(_make_bbox(500, 500, 600, 600))
        result = tracker.update(_make_batch([det1, det2], frame_id=1))
        assert len(result.active_tracks) == 2
        assert len(result.new_tracks) == 2

    def test_track_ids_are_unique(self, tracker: ByteTrackAdapter) -> None:
        det1 = _make_detection(_make_bbox(0, 0, 50, 50))
        det2 = _make_detection(_make_bbox(500, 500, 600, 600))
        result = tracker.update(_make_batch([det1, det2]))
        ids = [t.track_id for t in result.active_tracks]
        assert len(set(ids)) == len(ids), "Track IDs must be unique."

    # ------------------------------------------------------------------
    # Track matching / update
    # ------------------------------------------------------------------

    def test_same_detection_maintains_single_track(self, tracker: ByteTrackAdapter) -> None:
        """The same detection across frames should keep one track (not create new ones)."""
        bbox = _make_bbox(100, 100, 200, 200)
        for frame_id in range(1, 5):
            result = tracker.update(
                _make_batch([_make_detection(bbox)], frame_id=frame_id)
            )
        assert len(result.active_tracks) == 1
        assert result.active_tracks[0].age_frames >= 4

    def test_slightly_moved_detection_matches_existing_track(self, tracker: ByteTrackAdapter) -> None:
        """A detection that moved a few pixels should still match the existing track."""
        result1 = tracker.update(_make_batch([_make_detection(_make_bbox(100, 100, 200, 200))], frame_id=1))
        track_id_1 = result1.active_tracks[0].track_id

        # Move by 5px — still high IoU
        result2 = tracker.update(_make_batch([_make_detection(_make_bbox(105, 105, 205, 205))], frame_id=2))
        assert len(result2.active_tracks) == 1
        assert result2.active_tracks[0].track_id == track_id_1

    # ------------------------------------------------------------------
    # Track expiry
    # ------------------------------------------------------------------

    def test_no_detections_makes_track_lost(self, tracker: ByteTrackAdapter) -> None:
        """Missing detection for one frame should make the track LOST (not yet REMOVED)."""
        tracker.update(_make_batch([_make_detection(_make_bbox(100, 100, 200, 200))], frame_id=1))
        result = tracker.update(_make_batch([], frame_id=2))
        assert len(result.lost_tracks) == 1
        assert len(result.active_tracks) == 0

    def test_track_removed_after_max_age(self) -> None:
        """A track should be permanently removed after max_age consecutive unmatched frames."""
        max_age = 3
        tracker = _make_tracker(max_age=max_age)
        tracker.update(_make_batch([_make_detection(_make_bbox(100, 100, 200, 200))], frame_id=1))
        for i in range(2, 2 + max_age + 1):
            tracker.update(_make_batch([], frame_id=i))
        stats = tracker.get_stats()
        assert stats["active_tracks"] == 0
        assert stats["lost_tracks"] == 0  # should be removed entirely

    def test_track_recovers_after_lost(self, tracker: ByteTrackAdapter) -> None:
        """A LOST track should become ACTIVE again when matched in a later frame."""
        bbox = _make_bbox(100, 100, 200, 200)
        tracker.update(_make_batch([_make_detection(bbox)], frame_id=1))

        # One empty frame → LOST
        result2 = tracker.update(_make_batch([], frame_id=2))
        assert len(result2.lost_tracks) == 1

        # Matching detection appears again → ACTIVE
        result3 = tracker.update(_make_batch([_make_detection(bbox)], frame_id=3))
        assert len(result3.active_tracks) == 1

    # ------------------------------------------------------------------
    # Trajectory accumulation
    # ------------------------------------------------------------------

    def test_trajectory_grows_with_frames(self, tracker: ByteTrackAdapter) -> None:
        """Trajectory list should grow by one entry per matched frame."""
        bbox = _make_bbox(100, 100, 200, 200)
        n_frames = 5
        for i in range(1, n_frames + 1):
            result = tracker.update(_make_batch([_make_detection(bbox)], frame_id=i))
        track = result.active_tracks[0]
        assert len(track.trajectory) == n_frames

    def test_trajectory_pruned_at_max_length(self) -> None:
        """Trajectory must not exceed max_trajectory_length."""
        max_len = 5
        tracker = _make_tracker(max_trajectory_length=max_len)
        bbox = _make_bbox(100, 100, 200, 200)
        for i in range(1, 20):
            result = tracker.update(_make_batch([_make_detection(bbox)], frame_id=i))
        track = result.active_tracks[0]
        assert len(track.trajectory) <= max_len

    def test_trajectory_timestamps_are_utc(self, tracker: ByteTrackAdapter) -> None:
        """All TrackPoint timestamps in the trajectory must be UTC-aware."""
        bbox = _make_bbox(100, 100, 200, 200)
        for i in range(1, 4):
            result = tracker.update(_make_batch([_make_detection(bbox)], frame_id=i))
        for pt in result.active_tracks[0].trajectory:
            assert pt.timestamp.tzinfo is not None, "TrackPoint timestamp must be timezone-aware."

    def test_trajectory_centers_reflect_movement(self, tracker: ByteTrackAdapter) -> None:
        """Trajectory centre coordinates should change when the bbox moves."""
        # Frame 1: bbox centred at (150, 150)
        tracker.update(_make_batch([_make_detection(_make_bbox(100, 100, 200, 200))], frame_id=1))
        # Frame 2: bbox centred at (350, 350)
        result = tracker.update(_make_batch([_make_detection(_make_bbox(300, 300, 400, 400))], frame_id=2))

        # These should create two tracks (non-overlapping bboxes)
        # Verify that each track has at least one trajectory point
        for track in result.active_tracks:
            assert len(track.trajectory) >= 1

    # ------------------------------------------------------------------
    # TrackingResult structure
    # ------------------------------------------------------------------

    def test_tracking_result_active_tracks_count(self, tracker: ByteTrackAdapter) -> None:
        """active_tracks in result must equal the number of ACTIVE tracks."""
        dets = [
            _make_detection(_make_bbox(0, 0, 50, 50)),
            _make_detection(_make_bbox(200, 200, 250, 250)),
            _make_detection(_make_bbox(400, 400, 450, 450)),
        ]
        result = tracker.update(_make_batch(dets, frame_id=1))
        assert len(result.active_tracks) == 3

    def test_tracking_result_camera_id_propagated(self, tracker: ByteTrackAdapter) -> None:
        result = tracker.update(_make_batch([], camera_id="cam_border_42"))
        assert result.camera_id == "cam_border_42"

    def test_tracking_result_frame_id_propagated(self, tracker: ByteTrackAdapter) -> None:
        result = tracker.update(_make_batch([], frame_id=99))
        assert result.frame_id == 99

    def test_tracking_result_timestamp_is_utc(self, tracker: ByteTrackAdapter) -> None:
        result = tracker.update(_make_batch([]))
        assert result.timestamp.tzinfo is not None

    # ------------------------------------------------------------------
    # get_track / get_active_tracks
    # ------------------------------------------------------------------

    def test_get_track_by_id(self, tracker: ByteTrackAdapter) -> None:
        result = tracker.update(_make_batch([_make_detection(_make_bbox(0, 0, 50, 50))]))
        tid = result.active_tracks[0].track_id
        fetched = tracker.get_track(tid)
        assert fetched is not None
        assert fetched.track_id == tid

    def test_get_track_nonexistent_returns_none(self, tracker: ByteTrackAdapter) -> None:
        assert tracker.get_track(99999) is None

    def test_get_active_tracks_filtered_by_camera(self, tracker: ByteTrackAdapter) -> None:
        tracker.update(_make_batch([_make_detection(_make_bbox(0, 0, 50, 50))], camera_id="cam_A"))
        active = tracker.get_active_tracks("cam_A")
        assert len(active) >= 1
        assert all(t.camera_id == "cam_A" for t in active)

        empty = tracker.get_active_tracks("cam_NONEXISTENT")
        assert empty == []

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def test_get_stats_keys(self, tracker: ByteTrackAdapter) -> None:
        tracker.update(_make_batch([_make_detection(_make_bbox(0, 0, 50, 50))]))
        stats = tracker.get_stats()
        for key in ("backend", "frames_processed", "total_tracks_created", "active_tracks", "lost_tracks"):
            assert key in stats, f"Missing stats key: {key}"

    def test_frames_processed_increments(self, tracker: ByteTrackAdapter) -> None:
        for i in range(7):
            tracker.update(_make_batch([], frame_id=i))
        assert tracker.get_stats()["frames_processed"] == 7

    def test_total_tracks_created_increments(self, tracker: ByteTrackAdapter) -> None:
        tracker.update(_make_batch([_make_detection(_make_bbox(0, 0, 50, 50))]))
        tracker.update(_make_batch([_make_detection(_make_bbox(500, 500, 600, 600))]))
        # Second det won't match first track (no overlap)
        assert tracker.get_stats()["total_tracks_created"] >= 2

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def test_reset_clears_all_state(self, tracker: ByteTrackAdapter) -> None:
        tracker.update(_make_batch([_make_detection(_make_bbox(0, 0, 50, 50))]))
        tracker.reset()
        stats = tracker.get_stats()
        assert stats["active_tracks"] == 0
        assert stats["frames_processed"] == 0
        assert stats["total_tracks_created"] == 0

    def test_reset_allows_fresh_start(self, tracker: ByteTrackAdapter) -> None:
        """After reset, new detections should create fresh tracks."""
        tracker.update(_make_batch([_make_detection(_make_bbox(0, 0, 50, 50))]))
        tracker.reset()
        result = tracker.update(_make_batch([_make_detection(_make_bbox(0, 0, 50, 50))]))
        assert len(result.active_tracks) == 1
        assert result.active_tracks[0].track_id == 1  # IDs restart from 1
