"""
Track analytics — PHASE 5.
Computes velocity, direction, dwell time, and trajectory for active tracks.
These are additive properties layered on top of the existing Track schema.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .schemas import Track


# 8-way compass from angle in degrees (0° = East, CCW positive)
_COMPASS = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]


def compute_velocity(track: Track) -> Tuple[float, float]:
    """
    Returns (speed_px_per_sec, angle_deg) using the last two trajectory points.
    speed is in normalized coordinate units/second.
    Returns (0.0, 0.0) if insufficient trajectory.
    """
    if len(track.trajectory) < 2:
        return 0.0, 0.0
    p1 = track.trajectory[-2]
    p2 = track.trajectory[-1]
    dt = (p2.timestamp - p1.timestamp).total_seconds()
    if dt <= 0:
        return 0.0, 0.0
    dx = p2.center_x - p1.center_x
    dy = p2.center_y - p1.center_y
    speed = math.sqrt(dx**2 + dy**2) / dt
    angle = math.degrees(math.atan2(-dy, dx))  # -dy because y increases downward
    return round(speed, 5), round(angle, 2)


def compute_direction(angle_deg: float) -> str:
    """
    Maps an angle (degrees, 0=East, CCW) to 8-way compass direction.
    Returns 'STATIONARY' if called with 0 speed context.
    """
    # Normalize to 0-360
    angle_norm = angle_deg % 360
    # Each sector is 45°, offset by 22.5° so N is centered at 90°
    sector = int((angle_norm + 22.5) / 45) % 8
    return _COMPASS[sector]


def compute_dwell_seconds(track: Track) -> float:
    """Seconds since the track was first seen."""
    return track.duration_seconds


def ground_contact_trajectory(track: Track, max_points: int = 10) -> List[Tuple[float, float]]:
    """
    Returns the last N ground-contact points (bottom-center of bbox) from trajectory.
    Coordinates are normalized [0, 1].
    """
    points = []
    for tp in track.trajectory[-max_points:]:
        bx = (tp.bbox.x1 + tp.bbox.x2) / 2.0
        by = tp.bbox.y2  # bottom of bbox = ground contact
        points.append((round(bx, 4), round(by, 4)))
    return points


@dataclass
class TrackAnalytics:
    """Computed analytics for a single track. Created fresh each frame."""
    track_id: int
    speed: float               # normalized coords / second
    angle_deg: float           # direction angle
    direction: str             # compass direction
    dwell_seconds: float       # time in scene
    avg_confidence: float
    ground_trajectory: List[Tuple[float, float]]  # last 10 ground-contact points

    def to_dict(self) -> Dict:
        return {
            "track_id": self.track_id,
            "speed": self.speed,
            "angle_deg": self.angle_deg,
            "direction": self.direction,
            "dwell_seconds": round(self.dwell_seconds, 2),
            "avg_confidence": round(self.avg_confidence, 3),
            "ground_trajectory": self.ground_trajectory,
        }


def analyze_track(track: Track) -> TrackAnalytics:
    """Compute all analytics for a track in one call."""
    speed, angle = compute_velocity(track)
    direction = compute_direction(angle) if speed > 0.001 else "STATIONARY"
    return TrackAnalytics(
        track_id=track.track_id,
        speed=speed,
        angle_deg=angle,
        direction=direction,
        dwell_seconds=compute_dwell_seconds(track),
        avg_confidence=track.avg_confidence,
        ground_trajectory=ground_contact_trajectory(track),
    )
