"""
Event Gate & Selective Specialist Scheduler (IBVAP / SIH26187 & SIH26228)
========================================================================
Implements the core cooperative vision architecture:
CHEAP CORE (Detection + ByteTrack)
    -> EVENT GATE
        -> SELECTIVE SPECIALISTS (OCR/ANPR, Pose, MobileSAM, Face, Threat)
            -> SPATIAL & TEMPORAL REASONING
                -> EVIDENCE FUSION
                    -> VERIFIED EVENT
                        -> 228 CRYPTOGRAPHIC ASSURANCE

The Event Gate prevents running expensive neural models on every frame by scheduling
specialists only when specific track, zone, or uncertainty criteria are met.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class SpecialistType(str, Enum):
    ANPR_OCR = "ANPR_OCR"
    POSE_ESTIMATION = "POSE_ESTIMATION"
    MOBILE_SAM = "MOBILE_SAM"
    FACE_AUTHORIZATION = "FACE_AUTHORIZATION"
    THREAT_DETECTOR = "THREAT_DETECTOR"
    DEPTH_ESTIMATOR = "DEPTH_ESTIMATOR"
    REID_ASSOCIATION = "REID_ASSOCIATION"
    SCENE_VLM = "SCENE_VLM"


class GatePriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class SpecialistTask:
    """Actionable specialist execution directive produced by EventGate."""
    specialist_type: SpecialistType
    track_id: int
    priority: GatePriority
    reason: str
    roi_bbox: List[float]  # [x1, y1, x2, y2]
    sampling_cadence: int = 1  # 1 = this frame, 4 = every 4th frame, 30 = every 30th frame
    timeout_ms: float = 150.0
    fallback_action: str = "SKIP_AND_PRESERVE_EVENT"


@dataclass
class GateEvaluationResult:
    """Aggregated schedule from EventGate for the current frame."""
    frame_id: int
    active_tracks_count: int
    scheduled_tasks: List[SpecialistTask] = field(default_factory=list)
    suppressed_specialists: List[str] = field(default_factory=list)


class EventGate:
    """
    Cooperative Event-Driven Vision Gatekeeper.
    Evaluates tracking state, persistence, zone proximity, and confidence to selectively trigger AI specialists.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.pose_min_dwell_sec = self.config.get("pose_min_dwell_sec", 1.5)
        self.camou_aspect_ratio_thresh = self.config.get("camou_aspect_ratio_thresh", 0.65)
        self.camou_conf_thresh = self.config.get("camou_conf_thresh", 0.50)

    def evaluate(
        self,
        frame_id: int,
        tracks: List[Any],
        in_restricted_zone: bool = False,
        is_night: bool = False,
        is_gpu: bool = False
    ) -> GateEvaluationResult:
        """
        Determines which secondary specialists should be scheduled for the current frame.
        """
        result = GateEvaluationResult(
            frame_id=frame_id,
            active_tracks_count=len(tracks)
        )

        for tr in tracks:
            cname = str(getattr(tr, 'class_name', '')).lower()
            sub = str(getattr(tr, 'subclass', None) or cname).lower()
            conf = float(getattr(tr, 'avg_confidence', getattr(tr, 'confidence', 0.85)))
            bbox = [
                getattr(tr.bbox, 'x1', 0.0),
                getattr(tr.bbox, 'y1', 0.0),
                getattr(tr.bbox, 'x2', 1.0),
                getattr(tr.bbox, 'y2', 1.0)
            ]
            track_id = int(getattr(tr, 'track_id', -1))
            age_frames = int(getattr(tr, 'age_frames', 1))

            # 1. VEHICLE SPECIALIST: ANPR / License Plate OCR
            if cname == "vehicle" or sub in ("car", "truck", "bus", "van", "suv"):
                # Only execute when vehicle is established (tracked for >= 3 frames)
                if age_frames >= 3:
                    result.scheduled_tasks.append(SpecialistTask(
                        specialist_type=SpecialistType.ANPR_OCR,
                        track_id=track_id,
                        priority=GatePriority.NORMAL,
                        reason="Vehicle detected and tracked; license plate extraction scheduled",
                        roi_bbox=bbox,
                        sampling_cadence=1,
                        timeout_ms=120.0
                    ))

            # 2. PERSON SPECIALISTS: Pose, Silhouette Segmentation, Face Liveness
            elif cname == "person":
                # Check for Camouflage / Crawling Silhouette -> MobileSAM
                bw = max(0.01, abs(bbox[2] - bbox[0]))
                bh = max(0.01, abs(bbox[3] - bbox[1]))
                aspect_ratio = bh / bw

                if (aspect_ratio < self.camou_aspect_ratio_thresh or conf < self.camou_conf_thresh) and (frame_id % 4 == 0):
                    result.scheduled_tasks.append(SpecialistTask(
                        specialist_type=SpecialistType.MOBILE_SAM,
                        track_id=track_id,
                        priority=GatePriority.HIGH,
                        reason=f"Silhouette anomaly (aspect_ratio={aspect_ratio:.2f}, conf={conf:.2f}); MobileSAM mask scheduled",
                        roi_bbox=bbox,
                        sampling_cadence=4,
                        timeout_ms=100.0
                    ))

                # Face Authorization & Liveness
                face_cadence = 1 if is_gpu else 30
                if frame_id % face_cadence == 0:
                    result.scheduled_tasks.append(SpecialistTask(
                        specialist_type=SpecialistType.FACE_AUTHORIZATION,
                        track_id=track_id,
                        priority=GatePriority.HIGH if in_restricted_zone else GatePriority.NORMAL,
                        reason="Person tracked; biometric facial authorization scheduled",
                        roi_bbox=bbox,
                        sampling_cadence=face_cadence,
                        timeout_ms=80.0
                    ))

                # Pose Estimation (triggered if entering restricted zone or persistent dwell)
                if in_restricted_zone or age_frames >= 15:
                    pose_cadence = 1 if is_gpu else 15
                    if frame_id % pose_cadence == 0:
                        result.scheduled_tasks.append(SpecialistTask(
                            specialist_type=SpecialistType.POSE_ESTIMATION,
                            track_id=track_id,
                            priority=GatePriority.HIGH if in_restricted_zone else GatePriority.NORMAL,
                            reason="Person in perimeter corridor; posture and keypoint dynamics scheduled",
                            roi_bbox=bbox,
                            sampling_cadence=pose_cadence,
                            timeout_ms=90.0
                        ))

            # 3. THREAT / WEAPON CLASSIFIER
            # Triggered on high-risk subclasses or periodic perimeter scan
            threat_cadence = 5 if is_gpu else 30
            if frame_id % threat_cadence == 0 or sub in ("gun", "knife", "weapon", "explosive"):
                result.scheduled_tasks.append(SpecialistTask(
                    specialist_type=SpecialistType.THREAT_DETECTOR,
                    track_id=track_id,
                    priority=GatePriority.CRITICAL if sub in ("gun", "knife") else GatePriority.NORMAL,
                    reason="Tactical threat scan scheduled",
                    roi_bbox=bbox,
                    sampling_cadence=threat_cadence,
                    timeout_ms=75.0
                ))

        return result
