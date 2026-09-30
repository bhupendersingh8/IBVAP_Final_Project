import uuid
import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict

from ..tracking.schemas import TrackingResult, Track

class ActivityState(Enum):
    UNKNOWN = "UNKNOWN"
    STANDING = "STANDING"
    WALKING = "WALKING"
    CROUCHING = "CROUCHING"
    LOITERING_CANDIDATE = "LOITERING_CANDIDATE"

@dataclass
class ActivityAssessment:
    track_id: int
    activity: ActivityState
    confidence: float
    time_window_seconds: float
    observation_count: int
    explanation: str

class ActivityEngine:
    """Analyzes behavioral patterns of tracked objects over time (e.g. loitering)."""
    
    def __init__(self, loiter_seconds_thresh=30.0, stationary_dist_thresh=0.05):
        self.loiter_seconds_thresh = loiter_seconds_thresh
        self.stationary_dist_thresh = stationary_dist_thresh

    def update(self, tracking_result: TrackingResult) -> List[ActivityAssessment]:
        assessments = []
        
        for track in tracking_result.active_tracks:
            if track.class_name != "person":
                continue
                
            duration = track.duration_seconds
            if duration < 2.0:
                continue
                
            # Calculate total distance traveled
            if len(track.trajectory) > 1:
                start_p = track.trajectory[0]
                end_p = track.trajectory[-1]
                dist = math.hypot(end_p.center_x - start_p.center_x, end_p.center_y - start_p.center_y)
                
                if dist < self.stationary_dist_thresh:
                    # Not moving much
                    if duration > self.loiter_seconds_thresh:
                        assessments.append(ActivityAssessment(
                            track_id=track.track_id,
                            activity=ActivityState.LOITERING_CANDIDATE,
                            confidence=0.85,
                            time_window_seconds=duration,
                            observation_count=len(track.trajectory),
                            explanation=f"Person detected staying within {self.stationary_dist_thresh*100:.0f}% area for {duration:.1f}s"
                        ))
                    else:
                        assessments.append(ActivityAssessment(
                            track_id=track.track_id,
                            activity=ActivityState.STANDING,
                            confidence=0.9,
                            time_window_seconds=duration,
                            observation_count=len(track.trajectory),
                            explanation="Person is stationary"
                        ))
                else:
                    assessments.append(ActivityAssessment(
                        track_id=track.track_id,
                        activity=ActivityState.WALKING,
                        confidence=0.9,
                        time_window_seconds=duration,
                        observation_count=len(track.trajectory),
                        explanation="Person is moving steadily"
                    ))
                    
        return assessments
