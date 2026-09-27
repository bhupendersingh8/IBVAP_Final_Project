"""
IBVAP Multi-Camera & Agent Event Bus
====================================
Coordinates cross-camera tracking handovers, distributed alerts,
and tactical agent message dispatching.
"""
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
import re
import math
import structlog

logger = structlog.get_logger()


@dataclass
class BusMessage:
    topic: str
    camera_id: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GlobalTracklet:
    global_id: str
    primary_camera_id: str
    local_track_ids: Dict[str, int] = field(default_factory=dict)
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    appearance_embedding: Optional[List[float]] = None
    last_position: Dict[str, float] = field(default_factory=dict)  # normalized x, y
    trajectory: List[Dict[str, Any]] = field(default_factory=list)
    identity_state: str = "UNKNOWN"
    notes: str = ""


class MultiCameraEventBus:
    """
    Thread-safe synchronous and asynchronous event broker for multi-camera surveillance.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[Callable[[BusMessage], None]]] = {}
        self._global_tracks: Dict[str, GlobalTracklet] = {}
        self._event_history: List[BusMessage] = []
        self._max_history: int = 500

    def subscribe(self, topic: str, callback: Callable[[BusMessage], None]) -> None:
        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(callback)

    def publish(self, topic: str, camera_id: str, payload: Dict[str, Any]) -> BusMessage:
        msg = BusMessage(topic=topic, camera_id=camera_id, payload=payload)
        with self._lock:
            self._event_history.append(msg)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)

            handlers = list(self._subscribers.get(topic, []))
            handlers.extend(self._subscribers.get("*", []))

        for handler in handlers:
            try:
                handler(msg)
            except Exception as e:
                logger.error("Error in bus subscriber", topic=topic, error=str(e))

        return msg

    def register_camera_track(
        self,
        camera_id: str,
        local_track_id: int,
        norm_x: float,
        norm_y: float,
        identity_state: str = "UNKNOWN"
    ) -> str:
        """
        Associates or creates a global tracklet for cross-camera handover.
        """
        now = datetime.now(timezone.utc)
        with self._lock:
            # Check for existing global tracklet with this camera and local id
            for gid, gt in self._global_tracks.items():
                if gt.local_track_ids.get(camera_id) == local_track_id:
                    gt.last_seen = now
                    gt.last_position = {"x": norm_x, "y": norm_y}
                    gt.identity_state = identity_state
                    gt.trajectory.append({"cam": camera_id, "x": norm_x, "y": norm_y, "t": now.isoformat()})
                    return gid

            # Check for cross-camera handover proximity
            # Only match if target was near camera boundary and matches adjacent entry geometry
            for gid, gt in self._global_tracks.items():
                last_cam = gt.trajectory[-1]["cam"] if gt.trajectory else gt.primary_camera_id
                if last_cam != camera_id:
                    delta_sec = (now - gt.last_seen).total_seconds()
                    if abs(delta_sec) < 12.0:
                        last_x = gt.last_position.get("x", 0.5)
                        last_y = gt.last_position.get("y", 0.5)

                        # Boundary adjacency logic:
                        from_cam = last_cam
                        to_cam = camera_id

                        # Euclidean distance between normalized positions
                        dist = math.sqrt((last_x - norm_x) ** 2 + (last_y - norm_y) ** 2)

                        # Check camera directional ordering (e.g. CAM-01 -> CAM-02)
                        m_from = re.search(r'\d+', from_cam)
                        m_to = re.search(r'\d+', to_cam)

                        is_boundary_match = False
                        if m_from and m_to:
                            idx_from = int(m_from.group())
                            idx_to = int(m_to.group())
                            # Adjacent linear camera topology handover:
                            # Only immediately adjacent cameras can hand over directly along boundary
                            if abs(idx_from - idx_to) == 1:
                                if idx_from < idx_to:
                                    # Moving Left-to-Right: Leaving CAM-01 on right edge (last_x >= 0.70)
                                    # enters CAM-02 on left edge (norm_x <= 0.30)
                                    horizontal_match = (last_x >= 0.70 and norm_x <= 0.30)
                                else:
                                    # Moving Right-to-Left: Leaving CAM-02 on left edge (last_x <= 0.30)
                                    # enters CAM-01 on right edge (norm_x >= 0.70)
                                    horizontal_match = (last_x <= 0.30 and norm_x >= 0.70)

                                vertical_continuity = (abs(last_y - norm_y) <= 0.45)
                                is_boundary_match = horizontal_match and vertical_continuity
                            else:
                                # Non-adjacent cameras along linear topology cannot hand over directly
                                is_boundary_match = False
                        else:
                            # Generic fallback with camera ID ordering check when no digits are present
                            is_ltr = (from_cam < to_cam)
                            if is_ltr:
                                h_match = (last_x >= 0.70 and norm_x <= 0.30) and abs(last_y - norm_y) <= 0.45
                                v_match = (last_y >= 0.70 and norm_y <= 0.30) and abs(last_x - norm_x) <= 0.45
                            else:
                                h_match = (last_x <= 0.30 and norm_x >= 0.70) and abs(last_y - norm_y) <= 0.45
                                v_match = (last_y <= 0.30 and norm_y >= 0.70) and abs(last_x - norm_x) <= 0.45

                            # Overlapping FOV fallback: close euclidean distance (dist <= 0.45)
                            # Rejects far-apart points (e.g. 0.10 to 0.90 where dist=0.80 > 0.45)
                            is_boundary_match = h_match or v_match or (dist <= 0.45)

                        if is_boundary_match:
                            gt.local_track_ids[camera_id] = local_track_id
                            gt.last_seen = now
                            gt.last_position = {"x": norm_x, "y": norm_y}
                            gt.trajectory.append({"cam": camera_id, "x": norm_x, "y": norm_y, "t": now.isoformat()})
                            logger.info(
                                "Multi-Camera Track Handover successful",
                                global_id=gid,
                                from_cam=from_cam,
                                to_cam=camera_id,
                                local_track_id=local_track_id
                            )
                            self.publish("track.handover", camera_id, {
                                "global_id": gid,
                                "from_camera": from_cam,
                                "to_camera": camera_id,
                                "local_id": local_track_id,
                            })
                            return gid

            # Create new global track
            new_gid = f"GLOBAL-{camera_id}-{local_track_id}-{int(now.timestamp()) % 10000}"
            new_gt = GlobalTracklet(
                global_id=new_gid,
                primary_camera_id=camera_id,
                local_track_ids={camera_id: local_track_id},
                first_seen=now,
                last_seen=now,
                last_position={"x": norm_x, "y": norm_y},
                trajectory=[{"cam": camera_id, "x": norm_x, "y": norm_y, "t": now.isoformat()}],
                identity_state=identity_state
            )
            self._global_tracks[new_gid] = new_gt
            return new_gid

    def get_global_tracks(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "global_id": gt.global_id,
                    "primary_camera": gt.primary_camera_id,
                    "associated_cameras": list(gt.local_track_ids.keys()),
                    "first_seen": gt.first_seen.isoformat(),
                    "last_seen": gt.last_seen.isoformat(),
                    "last_position": gt.last_position,
                    "identity_state": gt.identity_state,
                    "trajectory_length": len(gt.trajectory),
                }
                for gt in self._global_tracks.values()
            ]

    def clear(self) -> None:
        with self._lock:
            self._global_tracks.clear()
            self._event_history.clear()
