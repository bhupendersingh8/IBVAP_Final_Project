import uuid
from typing import List, Dict

from ..rules.schemas import SpatialEvent, EventType
from ..rules.activity_engine import ActivityAssessment, ActivityState
from ..ingestion.camera_source import CameraHealth
from .schemas import CorrelatedEvent, Severity

class EventCorrelator:
    """
    Core logic hub. Combines raw spatial events (zone entry) and behavioral activity (loitering),
    filters them based on camera health, and assigns a final Severity score.
    Produces CorrelatedEvents which are then saved as Incidents.
    """
    
    def __init__(self):
        # Prevent spam: keep track of last critical alert per track
        self.last_alert_time: Dict[int, float] = {}
        
    def correlate(
        self, 
        spatial_events: List[SpatialEvent], 
        activity_assessments: List[ActivityAssessment],
        camera_health: Dict[str, CameraHealth],
        model_name: str = "unknown",
        model_version: str = "unknown"
    ) -> List[CorrelatedEvent]:
        
        correlated = []
        activity_map = {a.track_id: a for a in activity_assessments}
        
        for event in spatial_events:
            # If camera is broken/reconnecting, suppress alerts to avoid false positives
            health = camera_health.get(event.camera_id, CameraHealth.UNKNOWN)
            if health in (CameraHealth.DISCONNECTED, CameraHealth.ERROR):
                continue
                
            activity = activity_map.get(event.track_id)
            severity = Severity.INFO
            explanation = event.explanation
            signals = [f"Spatial:{event.event_type.value}"]
            
            # Severity logic
            if event.event_type == EventType.ZONE_ENTRY:
                severity = Severity.HIGH
            elif event.event_type == EventType.LINE_CROSSING:
                severity = Severity.MEDIUM
            elif event.event_type == EventType.ZONE_PRESENCE:
                if activity and activity.activity == ActivityState.LOITERING_CANDIDATE:
                    severity = Severity.CRITICAL
                    explanation += f" AND {activity.explanation}"
                    signals.append("Behavior:LOITERING")
                else:
                    severity = Severity.LOW

            correlated.append(CorrelatedEvent(
                event_id=str(uuid.uuid4()),
                camera_id=event.camera_id,
                timestamp=event.timestamp,
                severity=severity,
                event_type=event.event_type.value,
                track_id=event.track_id,
                zone_id=event.zone_id,
                activity=activity.activity.value if activity else None,
                confidence=event.confidence,
                explanation=explanation,
                contributing_signals=signals,
                model_name=model_name,
                model_version=model_version
            ))
            
        return correlated
