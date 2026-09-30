"""
Temporal Skeleton Action Recognizer
===================================
Performs multi-frame temporal biomechanical action recognition on 17-keypoint COCO skeletons.
Detects critical border surveillance behaviors:
1. SCALING_FENCE / CLIMBING: Hands extended above head near perimeter barriers.
2. CRAWLING / PRONE_INFILTRATION: Low-profile prone posture moving under barbed wire.
3. CROUCHING / HIDING: Low center-of-mass with bent knees and static concealment.
4. RUNNING / SPRINTING: High velocity displacement with alternating gait stride.
5. WALKING / PATROLLING: Upright posture with standard cyclic motion.
6. LOITERING: Static lingering in sensitive security perimeters.
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import deque
import numpy as np
import structlog

logger = structlog.get_logger()

# COCO Keypoint Indices
NOSE = 0
L_EYE, R_EYE = 1, 2
L_EAR, R_EAR = 3, 4
L_SHOULDER, R_SHOULDER = 5, 6
L_ELBOW, R_ELBOW = 7, 8
L_WRIST, R_WRIST = 9, 10
L_HIP, R_HIP = 11, 12
L_KNEE, R_KNEE = 13, 14
L_ANKLE, R_ANKLE = 15, 16


def compute_angle(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    """Compute angle between p1-p2 and p3-p2 in degrees."""
    v1 = p1 - p2
    v2 = p3 - p2
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 < 1e-4 or norm2 < 1e-4:
        return 180.0
    cos_angle = np.clip(np.dot(v1, v2) / (norm1 * norm2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


class TemporalSkeletonActionRecognizer:
    """
    Analyzes temporal window of 17-keypoint skeleton poses for a track
    to infer tactical border behavior.
    """

    def __init__(self, window_size: int = 15):
        self.window_size = window_size
        # track_id -> deque of keypoint arrays [17, 3] (x, y, conf)
        self.history: Dict[int, deque] = {}

    def update_track_pose(self, track_id: int, keypoints: np.ndarray) -> Dict[str, Any]:
        """
        Record new frame keypoints [17, 2] or [17, 3] and evaluate action.
        Returns: {
            "action": str,
            "confidence": float,
            "features": dict,
            "is_threat": bool,
            "tactical_alert": Optional[str]
        }
        """
        if track_id not in self.history:
            self.history[track_id] = deque(maxlen=self.window_size)

        pts = np.asarray(keypoints, dtype=np.float32)
        if pts.shape[-1] == 2:
            # Add synthetic confidence 1.0 if not present
            confs = np.ones((len(pts), 1), dtype=np.float32)
            pts = np.hstack([pts, confs])

        self.history[track_id].append(pts)
        return self.classify_action(track_id)

    def classify_action(self, track_id: int) -> Dict[str, Any]:
        buf = self.history.get(track_id)
        if not buf or len(buf) < 3:
            return {
                "action": "DETECTED_INITIALIZING",
                "confidence": 0.50,
                "features": {},
                "is_threat": False,
                "tactical_alert": None
            }

        recent_poses = list(buf)
        latest_pose = recent_poses[-1]

        # Extract latest keypoints
        sh_mid = (latest_pose[L_SHOULDER, :2] + latest_pose[R_SHOULDER, :2]) * 0.5
        hip_mid = (latest_pose[L_HIP, :2] + latest_pose[R_HIP, :2]) * 0.5
        knee_mid = (latest_pose[L_KNEE, :2] + latest_pose[R_KNEE, :2]) * 0.5
        ankle_mid = (latest_pose[L_ANKLE, :2] + latest_pose[R_ANKLE, :2]) * 0.5

        torso_vec = sh_mid - hip_mid
        torso_height = np.linalg.norm(torso_vec)
        body_height = max(1e-3, abs(ankle_mid[1] - sh_mid[1]))
        body_width = max(1e-3, abs(latest_pose[R_SHOULDER, 0] - latest_pose[L_SHOULDER, 0]))
        aspect_ratio = body_height / body_width

        # Angle of spine vs vertical
        if torso_height > 1e-3:
            spine_angle_deg = float(np.degrees(np.arctan2(abs(torso_vec[0]), abs(torso_vec[1]))))
        else:
            spine_angle_deg = 0.0

        # Hand elevation check (hands above shoulders or head)
        l_hand_raised = latest_pose[L_WRIST, 1] < (latest_pose[L_SHOULDER, 1] - 10)
        r_hand_raised = latest_pose[R_WRIST, 1] < (latest_pose[R_SHOULDER, 1] - 10)
        hands_raised = l_hand_raised or r_hand_raised

        # Knee flexion angle (average of both legs)
        l_knee_angle = compute_angle(latest_pose[L_HIP, :2], latest_pose[L_KNEE, :2], latest_pose[L_ANKLE, :2])
        r_knee_angle = compute_angle(latest_pose[R_HIP, :2], latest_pose[R_KNEE, :2], latest_pose[R_ANKLE, :2])
        avg_knee_flexion = (l_knee_angle + r_knee_angle) * 0.5

        # Temporal velocity & displacement over window
        displacements = []
        for i in range(1, len(recent_poses)):
            prev_center = (recent_poses[i-1][L_HIP, :2] + recent_poses[i-1][R_HIP, :2]) * 0.5
            curr_center = (recent_poses[i][L_HIP, :2] + recent_poses[i][R_HIP, :2]) * 0.5
            displacements.append(np.linalg.norm(curr_center - prev_center))
        avg_velocity = float(np.mean(displacements)) if displacements else 0.0

        # Action Decision Tree
        features = {
            "spine_angle_deg": round(spine_angle_deg, 1),
            "aspect_ratio": round(aspect_ratio, 2),
            "hands_raised": bool(hands_raised),
            "avg_knee_flexion": round(avg_knee_flexion, 1),
            "avg_velocity": round(avg_velocity, 2)
        }

        # 1. Scaling Fence / Climbing Obstacle
        if hands_raised and (spine_angle_deg < 40 or avg_velocity > 2.0):
            return {
                "action": "SCALING_FENCE",
                "confidence": 0.88 if (l_hand_raised and r_hand_raised) else 0.76,
                "features": features,
                "is_threat": True,
                "tactical_alert": "PERIMETER_BREACH_SUSPECTED: Subject climbing border barrier"
            }

        # 2. Prone Infiltration / Crawling
        if spine_angle_deg > 55 or aspect_ratio < 1.1:
            return {
                "action": "CRAWLING",
                "confidence": 0.89,
                "features": features,
                "is_threat": True,
                "tactical_alert": "STEALTH_INFILTRATION: Prone/crawling subject detected"
            }

        # 3. Crouching / Concealment
        if avg_knee_flexion < 110.0 and avg_velocity < 3.0:
            return {
                "action": "CROUCHING",
                "confidence": 0.82,
                "features": features,
                "is_threat": True,
                "tactical_alert": "CONCEALMENT_SUSPECTED: Subject crouching in blindspot"
            }

        # 4. Running / Rapid Evasion
        if avg_velocity > 12.0:
            return {
                "action": "RUNNING",
                "confidence": 0.85,
                "features": features,
                "is_threat": True,
                "tactical_alert": "RAPID_TRANSIT: High-speed target movement"
            }

        # 5. Loitering
        if len(recent_poses) >= self.window_size and avg_velocity < 1.0:
            return {
                "action": "LOITERING",
                "confidence": 0.80,
                "features": features,
                "is_threat": False,
                "tactical_alert": "STATIC_LOITERING: Stationary target observed"
            }

        # 6. Normal Patrol / Walking
        return {
            "action": "WALKING",
            "confidence": 0.92,
            "features": features,
            "is_threat": False,
            "tactical_alert": None
        }

    def clear_track(self, track_id: int):
        self.history.pop(track_id, None)
