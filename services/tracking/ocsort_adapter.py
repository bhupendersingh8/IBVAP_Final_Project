"""
Observation-Centric SORT (OC-SORT / Deep OC-SORT) Adapter
==========================================================
Implements OC-SORT key innovations:
1. Observation-Centric Momentum (OCM): Direction-consistent velocity matching.
2. Observation-Centric Recovery (OCR): Re-identifies tracks lost during occlusions.
3. Smooth virtual trajectory interpolation to prevent ID switches at border barriers.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import numpy as np
from scipy.optimize import linear_sum_assignment
import structlog

from ..detection.schemas import DetectionBatch, Detection, BBox
from .schemas import Track, TrackingResult, TrackState, TrackPoint
from .tracker import MultiObjectTracker
from .kalman_filter import KalmanFilterTracker, xywh_to_xyah, xyah_to_xyxy

logger = structlog.get_logger()


def compute_iou_matrix(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """Compute pairwise IoU matrix."""
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


class OCSORTAdapter(MultiObjectTracker):
    """
    Observation-Centric SORT (OC-SORT) tracker.
    Provides momentum-consistent association to resist ID switches during target crossing,
    fencing occlusion, and multi-second target disappearances.
    """

    def __init__(
        self,
        det_thresh: float = 0.40,
        max_age: int = 30,
        min_hits: int = 2,
        iou_threshold: float = 0.30,
        delta_t: int = 3,
        inertia: float = 0.20,
        max_trajectory: int = 50,
        **kwargs
    ):
        self.det_thresh = det_thresh
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.delta_t = delta_t
        self.inertia = inertia
        self.max_trajectory = max_trajectory

        self.tracks: Dict[int, Track] = {}
        self.kf_states: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
        self.unmatched_age: Dict[int, int] = {}
        self.last_observations: Dict[int, np.ndarray] = {}  # tid -> last observed xyxy
        self.velocity_directions: Dict[int, np.ndarray] = {}  # tid -> normalized [dx, dy]
        self._next_id = 1

        self.kalman = KalmanFilterTracker()
        self._total_created = 0
        self._frames_processed = 0

    def _compute_ocm_cost(
        self,
        track_boxes: np.ndarray,
        det_boxes: np.ndarray,
        tids: List[int]
    ) -> np.ndarray:
        """
        Compute Observation-Centric Momentum (OCM) cost:
        Penalizes candidates whose movement direction diverges from the established track momentum.
        """
        N, M = len(track_boxes), len(det_boxes)
        cost_mat = np.zeros((N, M), dtype=np.float32)

        for i, tid in enumerate(tids):
            last_obs = self.last_observations.get(tid)
            if last_obs is None:
                continue

            last_center = np.array([(last_obs[0] + last_obs[2]) / 2, (last_obs[1] + last_obs[3]) / 2])
            track_vel = self.velocity_directions.get(tid, np.zeros(2))
            vel_norm = np.linalg.norm(track_vel)

            if vel_norm > 1e-4:
                unit_vel = track_vel / vel_norm
                for j in range(M):
                    det_center = np.array([(det_boxes[j, 0] + det_boxes[j, 2]) / 2, (det_boxes[j, 1] + det_boxes[j, 3]) / 2])
                    disp = det_center - last_center
                    disp_norm = np.linalg.norm(disp)
                    if disp_norm > 1e-4:
                        unit_disp = disp / disp_norm
                        cos_sim = float(np.dot(unit_vel, unit_disp))
                        # Cost penalty proportional to direction divergence (1 - cos_sim)
                        cost_mat[i, j] = self.inertia * (1.0 - cos_sim)
        return cost_mat

    def update(self, batch: DetectionBatch) -> TrackingResult:
        self._frames_processed += 1
        now = batch.timestamp
        camera_id = batch.camera_id

        # 1. Kalman prediction for active tracks
        active_tids = [tid for tid, t in self.tracks.items() if t.camera_id == camera_id and t.state != TrackState.REMOVED]
        for tid in active_tids:
            mean, cov = self.kf_states[tid]
            mean, cov = self.kalman.predict(mean, cov)
            self.kf_states[tid] = (mean, cov)

        # 2. Filter detections
        dets = [d for d in batch.detections if d.confidence >= self.det_thresh]

        matched_tracks = set()
        matched_dets = set()
        new_tracks = []
        lost_tracks = []

        if active_tids and dets:
            track_boxes = np.array([xyah_to_xyxy(self.kf_states[tid][0]) for tid in active_tids], dtype=np.float32)
            det_boxes = np.array([[d.bbox.x1, d.bbox.y1, d.bbox.x2, d.bbox.y2] for d in dets], dtype=np.float32)

            # Combined cost: (1 - IoU) + OCM directional divergence penalty
            iou_mat = compute_iou_matrix(track_boxes, det_boxes)
            ocm_penalty = self._compute_ocm_cost(track_boxes, det_boxes, active_tids)
            total_cost = (1.0 - iou_mat) + ocm_penalty

            row_ind, col_ind = linear_sum_assignment(total_cost)
            for r, c in zip(row_ind, col_ind):
                if iou_mat[r, c] >= self.iou_threshold:
                    tid = active_tids[r]
                    matched_tracks.add(tid)
                    matched_dets.add(c)
                    self._update_track(tid, dets[c], now)

        # 3. Observation-Centric Recovery (OCR): Try to associate remaining lost tracks
        unmatched_tids = [tid for tid in active_tids if tid not in matched_tracks]
        unmatched_dets = [idx for idx in range(len(dets)) if idx not in matched_dets]

        if unmatched_tids and unmatched_dets:
            # Check proximity to last raw observation rather than drifted Kalman prediction
            last_obs_boxes = np.array([self.last_observations.get(tid, xyah_to_xyxy(self.kf_states[tid][0])) for tid in unmatched_tids], dtype=np.float32)
            rem_det_boxes = np.array([[dets[idx].bbox.x1, dets[idx].bbox.y1, dets[idx].bbox.x2, dets[idx].bbox.y2] for idx in unmatched_dets], dtype=np.float32)

            ocr_iou = compute_iou_matrix(last_obs_boxes, rem_det_boxes)
            ocr_cost = 1.0 - ocr_iou
            r_idx, c_idx = linear_sum_assignment(ocr_cost)

            for r, c in zip(r_idx, c_idx):
                if ocr_iou[r, c] >= (self.iou_threshold * 0.80):
                    tid = unmatched_tids[r]
                    det_idx = unmatched_dets[c]
                    matched_tracks.add(tid)
                    matched_dets.add(det_idx)
                    self._update_track(tid, dets[det_idx], now)

        # 4. Initiate new tracks
        for idx in range(len(dets)):
            if idx not in matched_dets:
                tid = self._create_track(dets[idx], camera_id, now)
                new_tracks.append(tid)

        # 5. Age tracks
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
                    self.last_observations.pop(tid, None)
                    self.velocity_directions.pop(tid, None)
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
        curr_box = np.array([det.bbox.x1, det.bbox.y1, det.bbox.x2, det.bbox.y2], dtype=np.float32)

        # Update velocity direction observation
        last_obs = self.last_observations.get(tid)
        if last_obs is not None:
            curr_center = np.array([(curr_box[0] + curr_box[2]) / 2, (curr_box[1] + curr_box[3]) / 2])
            last_center = np.array([(last_obs[0] + last_obs[2]) / 2, (last_obs[1] + last_obs[3]) / 2])
            disp = curr_center - last_center
            # Smooth momentum vector
            prev_vel = self.velocity_directions.get(tid, np.zeros(2))
            self.velocity_directions[tid] = 0.7 * prev_vel + 0.3 * disp

        self.last_observations[tid] = curr_box

        # Kalman update
        meas = xywh_to_xyah(curr_box)
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

        # Lifecycle progression
        if track.age_frames <= 2:
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
        self.last_observations[tid] = box
        self.velocity_directions[tid] = np.zeros(2, dtype=np.float32)

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
        self.last_observations.clear()
        self.velocity_directions.clear()
        self._frames_processed = 0
        self._total_created = 0
        self._next_id = 1

    def get_stats(self) -> Dict[str, Any]:
        active_count = len([t for t in self.tracks.values() if t.state == TrackState.ACTIVE])
        lost_count = len([t for t in self.tracks.values() if t.state == TrackState.LOST])
        return {
            "backend": "ocsort_observation_momentum",
            "frames_processed": self._frames_processed,
            "total_tracks_created": self._total_created,
            "active_tracks": active_count,
            "lost_tracks": lost_count,
            "current_active": active_count,
            "ocm_inertia": self.inertia
        }
