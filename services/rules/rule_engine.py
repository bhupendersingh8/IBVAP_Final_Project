import uuid
from typing import List, Dict, Set
from .schemas import Zone, ZoneType, SpatialEvent, EventType, Point
from ..tracking.schemas import TrackingResult, Track
from .geometry import point_in_polygon, line_segments_intersect

class RuleEngine:
    def __init__(self, zones: List[Zone] = None):
        self.zones: Dict[str, Zone] = {z.zone_id: z for z in (zones or []) if z.enabled}
        # State tracking: track_id -> set(zone_id) where it was present last frame
        self.track_presence: Dict[int, Set[str]] = {}
        # Track previous centers: track_id -> Point
        self.track_previous_center: Dict[int, Point] = {}

    def add_zone(self, zone: Zone) -> None:
        if zone.enabled:
            self.zones[zone.zone_id] = zone

    def remove_zone(self, zone_id: str) -> None:
        self.zones.pop(zone_id, None)

    def get_zones(self, camera_id: str) -> List[Zone]:
        return [z for z in self.zones.values() if z.camera_id == camera_id]

    def evaluate(self, tracking_result: TrackingResult) -> List[SpatialEvent]:
        events = []
        camera_id = tracking_result.camera_id
        active_zones = self.get_zones(camera_id)
        
        if not active_zones:
            self._update_state(tracking_result)
            return events

        for track in tracking_result.active_tracks:
            tid = track.track_id
            curr_center = Point(track.center_x, track.center_y)
            # Bottom-center ground contact reference point prevents false intrusion alerts from upper body overlap
            ground_point = Point(track.center_x, track.bbox.y2) if hasattr(track, 'bbox') and track.bbox else curr_center
            prev_center = self.track_previous_center.get(tid)
            
            curr_zones = set()
            
            for zone in active_zones:
                if zone.zone_type == ZoneType.LINE and prev_center is not None:
                    # Check Line Crossing
                    if len(zone.points) >= 2:
                        p1, p2 = zone.points[0], zone.points[1]
                        if line_segments_intersect(prev_center, curr_center, p1, p2):
                            events.append(SpatialEvent(
                                event_id=str(uuid.uuid4()),
                                camera_id=camera_id,
                                track_id=tid,
                                zone_id=zone.zone_id,
                                event_type=EventType.LINE_CROSSING,
                                timestamp=tracking_result.timestamp,
                                confidence=track.avg_confidence,
                                explanation=f"{track.class_name.capitalize()} crossed line '{zone.name}'"
                            ))

                elif zone.zone_type in (ZoneType.POLYGON, ZoneType.RESTRICTED_ZONE, ZoneType.EXCLUSION_ZONE):
                    if len(zone.points) >= 3:
                        is_inside = point_in_polygon(ground_point, zone.points)
                        if is_inside:
                            curr_zones.add(zone.zone_id)
                            
                            # Was it inside last frame?
                            prev_zones = self.track_presence.get(tid, set())
                            if zone.zone_id not in prev_zones:
                                events.append(SpatialEvent(
                                    event_id=str(uuid.uuid4()),
                                    camera_id=camera_id,
                                    track_id=tid,
                                    zone_id=zone.zone_id,
                                    event_type=EventType.ZONE_ENTRY,
                                    timestamp=tracking_result.timestamp,
                                    confidence=track.avg_confidence,
                                    explanation=f"{track.class_name.capitalize()} entered zone '{zone.name}'"
                                ))
                            else:
                                events.append(SpatialEvent(
                                    event_id=str(uuid.uuid4()),
                                    camera_id=camera_id,
                                    track_id=tid,
                                    zone_id=zone.zone_id,
                                    event_type=EventType.ZONE_PRESENCE,
                                    timestamp=tracking_result.timestamp,
                                    confidence=track.avg_confidence,
                                    explanation=f"{track.class_name.capitalize()} is present in zone '{zone.name}'"
                                ))
                            
            # Check for Exits
            prev_zones = self.track_presence.get(tid, set())
            for z_id in prev_zones:
                if z_id not in curr_zones and z_id in self.zones:
                    events.append(SpatialEvent(
                        event_id=str(uuid.uuid4()),
                        camera_id=camera_id,
                        track_id=tid,
                        zone_id=z_id,
                        event_type=EventType.ZONE_EXIT,
                        timestamp=tracking_result.timestamp,
                        confidence=track.avg_confidence,
                        explanation=f"{track.class_name.capitalize()} exited zone '{self.zones[z_id].name}'"
                    ))
                    
            self.track_presence[tid] = curr_zones
            self.track_previous_center[tid] = curr_center
            
        self._cleanup_lost_tracks(tracking_result.lost_tracks)
        return events

    def _update_state(self, tracking_result: TrackingResult):
        for track in tracking_result.active_tracks:
            self.track_previous_center[track.track_id] = Point(track.center_x, track.center_y)
        self._cleanup_lost_tracks(tracking_result.lost_tracks)

    def _cleanup_lost_tracks(self, lost_tracks: List[int]):
        for tid in lost_tracks:
            self.track_presence.pop(tid, None)
            self.track_previous_center.pop(tid, None)
