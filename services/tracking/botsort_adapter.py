"""
BoT-SORT (Bag of Tricks for Multi-Object Tracking) Adapter
===========================================================
Implements BoT-SORT key innovations:
1. Kalman Filter motion state estimation [x, y, a, h, vx, vy, va, vh].
2. Camera Motion Compensation (CMC) using affine feature transform.
3. High & low score two-stage association.
4. Smooth trajectory interpolation.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment
import structlog

from ..detection.schemas import DetectionBatch, Detection, BBox
from .schemas import Track, TrackingResult, TrackState, TrackPoint
from .tracker import MultiObjectTracker
from .kalman_filter import KalmanFilterTracker, xywh_to_xyah, xyah_to_xyxy

logger = structlog.get_logger()


def compute_iou_matrix(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """Compute pairwise IoU between two arrays of bounding boxes [N, 4] and [M, 4]."""
    if len(boxes_a) == 0 or len(boxes_b) == 0:
        return np.zeros((len(boxes_a), len(boxes_b)), dtype=np.float32)

    x1 = np.maximum(boxes_a[:, None, 0], boxes_b[None, :, 0])
    y1 = np.maximum(boxes_a[:, None, 1], boxes_b[None, :, 1])
    x2 = np.minimum(boxes_a[:, None, 2], boxes_b[None, :, 2])
    y2 = np.minimum(boxes_a[:, None, 3], boxes_b[None, :, 3])

    inter_w = np.maximum(0.0, x2 - x1)
    inter_h = np.maximum(0.0, y2 - y1)
    inter_area = inter_w * inter_h

    area_a = (boxes_a[:, 2] - boxes_a[:, 0]) * (boxes_a[:, 3] - boxes_a[:, 1])
    area_b = (boxes_b[:, 2] - boxes_b[:, 0]) * (boxes_b[:, 3] - boxes_b[:, 1])

    union_area = area_a[:, None] + area_b[None, :] - inter_area
    iou = inter_area / np.maximum(1e-6, union_area)
    return iou


class BoTSORTAdapter(MultiObjectTracker):
    """
    BoT-SORT Tracker featuring Camera Motion Compensation (CMC) and
    Kalman Filter state estimation for robust tracking under border pan-tilt-zoom motion.
    """

    def __init__(
        self,
        track_high_thresh: float = 0.50,
        track_low_thresh: float = 0.15,
        match_thresh: float = 0.70,
        max_age: int = 30,
        max_trajectory: int = 50,
        enable_cmc: bool = True,
        **kwargs
    ):
        self.track_high_thresh = track_high_thresh
        self.track_low_thresh = track_low_thresh
        self.match_thresh = match_thresh
        self.max_age = max_age
        self.max_trajectory = max_trajectory
        self.enable_cmc = enable_cmc

        self.tracks: Dict[int, Track] = {}
        self.kf_states: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}  # tid -> (mean, cov)
        self.unmatched_age: Dict[int, int] = {}
        self._next_id = 1

        self.kalman = KalmanFilterTracker()
        self.prev_frame_gray: Optional[np.ndarray] = None
        self.affine_transform: np.ndarray = np.eye(2, 3, dtype=np.float32)

        self._total_created = 0
        self._frames_processed = 0

    def _estimate_camera_motion(self, current_frame_gray: Optional[np.ndarray]) -> np.ndarray:
        """
        Estimate camera affine transform between previous and current frame.
        """
        if not self.enable_cmc or current_frame_gray is None or self.prev_frame_gray is None:
            return np.eye(2, 3, dtype=np.float32)

        try:
            prev_pts = cv2.goodFeaturesToTrack(self.prev_frame_gray, maxCorners=100, qualityLevel=0.01, minDistance=10)
            if prev_pts is not None and len(prev_pts) > 10:
                curr_pts, status, _ = cv2.calcOpticalFlowPyrLK(self.prev_frame_gray, current_frame_gray, prev_pts, None)
                good_prev = prev_pts[status == 1]
                good_curr = curr_pts[status == 1]
                if len(good_prev) > 8:
                    warp_matrix, _ = cv2.estimateAffinePartial2D(good_prev, good_curr)
                    if warp_matrix is not None:
                        return warp_matrix
        except Exception as e:
            logger.debug("CMC estimation skipped", reason=str(e))

        return np.eye(2, 3, dtype=np.float32)

    def update(self, batch: DetectionBatch, frame_image: Optional[np.ndarray] = None) -> TrackingResult:
        self._frames_processed += 1
        now = batch.timestamp
        camera_id = batch.camera_id

        curr_gray = None
        if frame_image is not None:
            curr_gray = cv2.cvtColor(frame_image, cv2.COLOR_BGR2GRAY) if len(frame_image.shape) == 3 else frame_image
            self.affine_transform = self._estimate_camera_motion(curr_gray)
            self.prev_frame_gray = curr_gray

        # 1. Predict new locations with Kalman Filter & apply CMC
        active_tids = [tid for tid, t in self.tracks.items() if t.camera_id == camera_id and t.state != TrackState.REMOVED]
        for tid in active_tids:
            mean, cov = self.kf_states[tid]
            # Apply CMC to position
            if self.enable_cmc:
                mean[0] += self.affine_transform[0, 2]
                mean[1] += self.affine_transform[1, 2]
            mean, cov = self.kalman.predict(mean, cov)
            self.kf_states[tid] = (mean, cov)

        # 2. Split detections into high and low confidence sets
        dets = batch.detections
        high_dets = [d for d in dets if d.confidence >= self.track_high_thresh]
        low_dets = [d for d in dets if self.track_low_thresh <= d.confidence < self.track_high_thresh]

        # 3. Stage 1: Associate high-confidence detections with active tracks
        matched_tracks = set()
        matched_high_dets = set()
        new_tracks = []
        lost_tracks = []

        if active_tids and high_dets:
            track_boxes = np.array([xyah_to_xyxy(self.kf_states[tid][0]) for tid in active_tids], dtype=np.float32)
            det_boxes = np.array([[d.bbox.x1, d.bbox.y1, d.bbox.x2, d.bbox.y2] for d in high_dets], dtype=np.float32)
            iou_mat = compute_iou_matrix(track_boxes, det_boxes)
            cost_mat = 1.0 - iou_mat

            row_ind, col_ind = linear_sum_assignment(cost_mat)
            for r, c in zip(row_ind, col_ind):
                if cost_mat[r, c] <= self.match_thresh:
                    tid = active_tids[r]
                    matched_tracks.add(tid)
                    matched_high_dets.add(c)
                    self._update_track(tid, high_dets[c], now)

        # 4. Stage 2: Associate remaining tracks with low-confidence detections
        unmatched_tids = [tid for tid in active_tids if tid not in matched_tracks]
        if unmatched_tids and low_dets:
            track_boxes = np.array([xyah_to_xyxy(self.kf_states[tid][0]) for tid in unmatched_tids], dtype=np.float32)
            det_boxes = np.array([[d.bbox.x1, d.bbox.y1, d.bbox.x2, d.bbox.y2] for d in low_dets], dtype=np.float32)
            iou_mat = compute_iou_matrix(track_boxes, det_boxes)
            cost_mat = 1.0 - iou_mat

            row_ind, col_ind = linear_sum_assignment(cost_mat)
            for r, c in zip(row_ind, col_ind):
                if cost_mat[r, c] <= (self.match_thresh * 0.85):
                    tid = unmatched_tids[r]
                    matched_tracks.add(tid)
                    self._update_track(tid, low_dets[c], now)

        # 5. Initialize new tracks from unmatched high-confidence detections
        for idx, det in enumerate(high_dets):
            if idx not in matched_high_dets:
                tid = self._create_track(det, camera_id, now)
                new_tracks.append(tid)

        # 6. Age unmatched tracks and handle loss/removal
        for tid in active_tids:
            if tid not in matched_tracks:
                self.unmatched_age[tid] += 1
                track = self.tracks[tid]
                track.age_frames += 1
                if self.unmatched_age[tid] >= self.max_age:
                    track.state = TrackState.REMOVED
                    del self.tracks[tid]
                    del self.kf_states[tid]
                    del self.unmatched_age[tid]
                else:
                    if track.state != TrackState.LOST:
                        track.state = TrackState.LOST
                        lost_tracks.append(tid)

        active_out = [t for t in self.tracks.values() if t.camera_id == camera_id and t.state == TrackState.ACTIVE]
        return TrackingResult(
            camera_id=camera_id,
            frame_id=batch.frame_id,
            timestamp=now,
            active_tracks=active_out,
            new_tracks=new_tracks,
            lost_tracks=lost_tracks
        )

    def _update_track(self, tid: int, det: Detection, timestamp: datetime):
        track = self.tracks[tid]
        meas = xywh_to_xyah(np.array([det.bbox.x1, det.bbox.y1, det.bbox.x2, det.bbox.y2], dtype=np.float32))
        mean, cov = self.kf_states[tid]
        new_mean, new_cov = self.kalman.update(mean, cov, meas)
        self.kf_states[tid] = (new_mean, new_cov)

        xyxy = xyah_to_xyxy(new_mean)
        smoothed_bbox = BBox(x1=float(xyxy[0]), y1=float(xyxy[1]), x2=float(xyxy[2]), y2=float(xyxy[3]))

        track.bbox = smoothed_bbox
        track.center_x = smoothed_bbox.center_x
        track.center_y = smoothed_bbox.center_y
        track.last_seen = timestamp
        track.state = TrackState.ACTIVE
        track.age_frames += 1
        track.confidence = det.confidence
        self.unmatched_age[tid] = 0

        tp = TrackPoint(timestamp, smoothed_bbox, track.center_x, track.center_y, det.confidence)
        track.trajectory.append(tp)
        if len(track.trajectory) > self.max_trajectory:
            track.trajectory.pop(0)

        # Lifecycle state progression
        if track.age_frames <= 3:
            track.lifecycle_state = "TENTATIVE"
        elif track.age_frames <= 15:
            track.lifecycle_state = "STABLE"
        else:
            track.lifecycle_state = "VERIFIED"

    def _create_track(self, det: Detection, camera_id: str, timestamp: datetime) -> int:
        tid = self._next_id
        self._next_id += 1
        self._total_created += 1

        box = np.array([det.bbox.x1, det.bbox.y1, det.bbox.x2, det.bbox.y2], dtype=np.float32)
        meas = xywh_to_xyah(box)
        mean, cov = self.kalman.initiate(meas)
        self.kf_states[tid] = (mean, cov)
        self.unmatched_age[tid] = 0

        tp = TrackPoint(timestamp, det.bbox, det.bbox.center_x, det.bbox.center_y, det.confidence)
        new_track = Track(
            track_id=tid,
            camera_id=camera_id,
            class_name=det.class_name,
            state=TrackState.ACTIVE,
            bbox=det.bbox,
            center_x=det.bbox.center_x,
            center_y=det.bbox.center_y,
            first_seen=timestamp,
            last_seen=timestamp,
            subclass=getattr(det, 'subclass', None),
            confidence_history=[det.confidence],
            trajectory=[tp],
            age_frames=1,
            lifecycle_state="DETECTED",
            confidence=det.confidence
        )
        self.tracks[tid] = new_track
        return tid

    def get_track(self, track_id: int) -> Optional[Track]:
        return self.tracks.get(track_id)

    def get_active_tracks(self, camera_id: str) -> List[Track]:
        return [t for t in self.tracks.values() if t.camera_id == camera_id and t.state == TrackState.ACTIVE]

    def reset(self) -> None:
        self.tracks.clear()
        self.kf_states.clear()
        self.unmatched_age.clear()
        self.prev_frame_gray = None
        self._frames_processed = 0
        self._total_created = 0
        self._next_id = 1

    def get_stats(self) -> Dict[str, Any]:
        active_count = len([t for t in self.tracks.values() if t.state == TrackState.ACTIVE])
        lost_count = len([t for t in self.tracks.values() if t.state == TrackState.LOST])
        return {
            "backend": "botsort_cmc_kalman",
            "frames_processed": self._frames_processed,
            "total_tracks_created": self._total_created,
            "active_tracks": active_count,
            "lost_tracks": lost_count,
            "current_active": active_count,
            "cmc_enabled": self.enable_cmc
        }
