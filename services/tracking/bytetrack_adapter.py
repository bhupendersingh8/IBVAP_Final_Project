import numpy as np
from typing import List, Optional, Dict, Any
import structlog
from datetime import datetime, timezone

from ..detection.schemas import DetectionBatch, Detection, BBox
from .schemas import Track, TrackingResult, TrackState, TrackPoint
from .tracker import MultiObjectTracker

logger = structlog.get_logger()

def compute_iou(boxA, boxB):
    # box format: [x1, y1, x2, y2]
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0:
        return 0.0

    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

_ULTRALYTICS_AVAILABLE = False

class FallbackIoUTracker(MultiObjectTracker):
    """
    A lightweight, pure-Python IoU-based tracker used as a fallback if ByteTrack is unavailable,
    or for low-overhead CPU operations.
    """
    def __init__(
        self, 
        max_age: int = 30, 
        iou_threshold: float = 0.3, 
        max_trajectory: int = 50,
        min_hits: int = 1,
        max_trajectory_length: Optional[int] = None,
        **kwargs
    ):
        self.max_age = max_age
        self.iou_threshold = iou_threshold
        self.max_trajectory = max_trajectory_length if max_trajectory_length is not None else max_trajectory
        self.min_hits = min_hits
        
        self.tracks: Dict[int, Track] = {}
        self.unmatched_age: Dict[int, int] = {}
        self._next_id = 1
        
        # Telemetry
        self._total_created = 0
        self._frames_processed = 0

    def update(self, batch: DetectionBatch) -> TrackingResult:
        self._frames_processed += 1
        now = batch.timestamp
        camera_id = batch.camera_id
        
        new_tracks = []
        lost_tracks = []
        
        # Consider both ACTIVE and LOST tracks for matching (recovery)
        candidate_track_ids = [tid for tid, t in self.tracks.items() if t.camera_id == camera_id and t.state in (TrackState.ACTIVE, TrackState.LOST)]
        
        # Build cost matrix based on 1 - IoU
        detections = batch.detections
        matched_dets = set()
        matched_tracks = set()
        
        # Simple greedy matching
        for det_idx, det in enumerate(detections):
            best_iou = self.iou_threshold
            best_tid = -1
            det_box = [det.bbox.x1, det.bbox.y1, det.bbox.x2, det.bbox.y2]
            
            for tid in candidate_track_ids:
                if tid in matched_tracks:
                    continue
                track = self.tracks[tid]
                t_box = [track.bbox.x1, track.bbox.y1, track.bbox.x2, track.bbox.y2]
                iou = compute_iou(det_box, t_box)
                
                # Prevent cross-subclass confusion (e.g., truck != car != motorcycle)
                det_sub = getattr(det, 'subclass', None)
                if track.subclass and det_sub and track.subclass != det_sub:
                    continue
                    
                if iou > best_iou and track.class_name == det.class_name:
                    best_iou = iou
                    best_tid = tid
            
            if best_tid != -1:
                # Match found
                matched_tracks.add(best_tid)
                matched_dets.add(det_idx)
                
                track = self.tracks[best_tid]
                track.state = TrackState.ACTIVE

                # Exponential Moving Average (EMA) coordinate smoothing to eliminate jitter
                alpha = 0.75
                s_x1 = round(alpha * det.bbox.x1 + (1.0 - alpha) * track.bbox.x1, 4)
                s_y1 = round(alpha * det.bbox.y1 + (1.0 - alpha) * track.bbox.y1, 4)
                s_x2 = round(alpha * det.bbox.x2 + (1.0 - alpha) * track.bbox.x2, 4)
                s_y2 = round(alpha * det.bbox.y2 + (1.0 - alpha) * track.bbox.y2, 4)
                smoothed_bbox = BBox(x1=s_x1, y1=s_y1, x2=s_x2, y2=s_y2)

                track.bbox = smoothed_bbox
                track.center_x = smoothed_bbox.center_x
                track.center_y = smoothed_bbox.center_y
                track.last_seen = now
                track.age_frames += 1
                if getattr(det, 'subclass', None):
                    track.subclass = det.subclass
                self.unmatched_age[best_tid] = 0
                
                track.confidence = det.confidence
                track.confidence_history.append(det.confidence)
                if len(track.confidence_history) > self.max_trajectory:
                    track.confidence_history.pop(0)
                    
                tp = TrackPoint(now, smoothed_bbox, track.center_x, track.center_y, det.confidence)
                track.trajectory.append(tp)
                if len(track.trajectory) > self.max_trajectory:
                    track.trajectory.pop(0)

                # Compute velocity estimate (normalized distance / dt)
                if len(track.trajectory) >= 2:
                    p1 = track.trajectory[-2]
                    p2 = track.trajectory[-1]
                    dt = max(0.01, (p2.timestamp - p1.timestamp).total_seconds())
                    dist = ((p2.center_x - p1.center_x)**2 + (p2.center_y - p1.center_y)**2)**0.5
                    track.velocity_estimate = round(dist / dt, 3)

                # Advance lifecycle state
                if track.age_frames == 1:
                    track.lifecycle_state = "DETECTED"
                elif track.age_frames <= 5:
                    track.lifecycle_state = "TENTATIVE"
                elif track.age_frames <= 15:
                    track.lifecycle_state = "STABLE"
                else:
                    track.lifecycle_state = "VERIFIED"
                    
        # Process unmatched detections (create new tracks)
        for det_idx, det in enumerate(detections):
            if det_idx not in matched_dets:
                tid = self._next_id
                self._next_id += 1
                self._total_created += 1
                
                tp = TrackPoint(now, det.bbox, det.bbox.center_x, det.bbox.center_y, det.confidence)
                new_track = Track(
                    track_id=tid,
                    camera_id=camera_id,
                    class_name=det.class_name,
                    state=TrackState.ACTIVE,
                    bbox=det.bbox,
                    center_x=det.bbox.center_x,
                    center_y=det.bbox.center_y,
                    first_seen=now,
                    last_seen=now,
                    subclass=getattr(det, 'subclass', None),
                    confidence_history=[det.confidence],
                    trajectory=[tp],
                    age_frames=1
                )
                self.tracks[tid] = new_track
                self.unmatched_age[tid] = 0
                new_tracks.append(tid)
                
        # Process unmatched tracks (age them, mark lost or removed)
        for tid in list(candidate_track_ids):
            if tid not in matched_tracks:
                self.unmatched_age[tid] += 1
                track = self.tracks[tid]
                track.age_frames += 1
                
                if self.unmatched_age[tid] >= self.max_age:
                    track.state = TrackState.REMOVED
                    del self.tracks[tid]
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

    def get_track(self, track_id: int) -> Optional[Track]:
        return self.tracks.get(track_id)

    def get_active_tracks(self, camera_id: str) -> List[Track]:
        return [t for t in self.tracks.values() if t.camera_id == camera_id and t.state == TrackState.ACTIVE]

    def reset(self) -> None:
        self.tracks.clear()
        self.unmatched_age.clear()
        self._frames_processed = 0
        self._total_created = 0
        self._next_id = 1

    def get_stats(self) -> Dict[str, Any]:
        active_count = len([t for t in self.tracks.values() if t.state == TrackState.ACTIVE])
        lost_count = len([t for t in self.tracks.values() if t.state == TrackState.LOST])
        return {
            "backend": "fallback_iou",
            "frames_processed": self._frames_processed,
            "total_tracks_created": self._total_created,
            "active_tracks": active_count,
            "lost_tracks": lost_count,
            "current_active": active_count
        }

# Alias for backward compatibility
ByteTrackAdapter = FallbackIoUTracker


