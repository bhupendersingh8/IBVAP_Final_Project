"""
IBVAP Dynamic Route Scoring Engine
==================================
Implements the multi-factor route scoring formula for autonomous routing:
S_route = w_d * C_det + w_t * C_track + w_temp * C_temporal + w_z * C_zone
          + w_id * C_identity + w_a * C_anomaly + w_v * C_vlm + w_q * C_cam_quality
"""
from dataclasses import dataclass
from typing import Dict, Any, Tuple


@dataclass
class RouteWeights:
    w_det: float = 0.20          # Primary detector confidence
    w_track: float = 0.15        # Tracking stability & association IoU
    w_temporal: float = 0.15     # Temporal state maturity (45 frames baseline)
    w_zone: float = 0.15         # Zone tactical criticality (Buffer, Restricted, Perimeter)
    w_identity: float = 0.15     # Identity risk (Authorized=0.0, Unknown=0.5, Unauthorized=1.0)
    w_anomaly: float = 0.10      # Anomaly/outlier severity
    w_vlm: float = 0.05          # Vision-Language semantic threat assessment
    w_cam_quality: float = 0.05  # Camera stream quality (lighting, blur, resolution)

    def normalize(self) -> None:
        total = (self.w_det + self.w_track + self.w_temporal + self.w_zone +
                 self.w_identity + self.w_anomaly + self.w_vlm + self.w_cam_quality)
        if total > 0:
            self.w_det /= total
            self.w_track /= total
            self.w_temporal /= total
            self.w_zone /= total
            self.w_identity /= total
            self.w_anomaly /= total
            self.w_vlm /= total
            self.w_cam_quality /= total


class DynamicRouteScorer:
    """
    Evaluates threat vector significance and produces dynamic priority route scores.
    """

    def __init__(self, weights: RouteWeights = None):
        self.weights = weights or RouteWeights()
        self.weights.normalize()

    def calculate_score(
        self,
        c_det: float,
        c_track: float,
        c_temporal: float,
        c_zone: float,
        c_identity: float,
        c_anomaly: float = 0.0,
        c_vlm: float = 0.0,
        c_cam_quality: float = 1.0,
    ) -> Tuple[float, str, Dict[str, Any]]:
        """
        Calculates normalized S_route score and assigns tactical directive.
        """
        # Helper to sanitize float values against None, NaN, and Inf
        def _safe_float(val: Any, default: float = 0.0) -> float:
            if val is None:
                return default
            try:
                f = float(val)
                import math
                return default if math.isnan(f) or math.isinf(f) else f
            except (ValueError, TypeError):
                return default

        # Clamp inputs between 0.0 and 1.0 safely
        c_det = max(0.0, min(1.0, _safe_float(c_det, 0.0)))
        c_track = max(0.0, min(1.0, _safe_float(c_track, 0.0)))
        c_temporal = max(0.0, min(1.0, _safe_float(c_temporal, 0.0)))
        c_zone = max(0.0, min(1.0, _safe_float(c_zone, 0.0)))
        c_identity = max(0.0, min(1.0, _safe_float(c_identity, 0.0)))
        c_anomaly = max(0.0, min(1.0, _safe_float(c_anomaly, 0.0)))
        c_vlm = max(0.0, min(1.0, _safe_float(c_vlm, 0.0)))
        c_cam_quality = max(0.0, min(1.0, _safe_float(c_cam_quality, 1.0)))

        s_route = (
            self.weights.w_det * c_det +
            self.weights.w_track * c_track +
            self.weights.w_temporal * c_temporal +
            self.weights.w_zone * c_zone +
            self.weights.w_identity * c_identity +
            self.weights.w_anomaly * c_anomaly +
            self.weights.w_vlm * c_vlm +
            self.weights.w_cam_quality * c_cam_quality
        )
        s_route = round(max(0.0, min(1.0, s_route)), 4)

        # Tactical Directive Decision Matrix
        if s_route >= 0.85:
            directive = "CRITICAL_INTERCEPT_DISPATCH"
        elif s_route >= 0.65:
            directive = "ELEVATED_TACTICAL_ALERT"
        elif s_route >= 0.45:
            directive = "ACTIVE_MONITORING_TRACK"
        elif s_route >= 0.25:
            directive = "LOW_CONFIDENCE_OBSERVATION"
        else:
            directive = "DISREGARD_FILTERED_NOISE"

        breakdown = {
            "s_route": s_route,
            "directive": directive,
            "components": {
                "detection": round(self.weights.w_det * c_det, 4),
                "tracking": round(self.weights.w_track * c_track, 4),
                "temporal": round(self.weights.w_temporal * c_temporal, 4),
                "zone": round(self.weights.w_zone * c_zone, 4),
                "identity": round(self.weights.w_identity * c_identity, 4),
                "anomaly": round(self.weights.w_anomaly * c_anomaly, 4),
                "vlm": round(self.weights.w_vlm * c_vlm, 4),
                "cam_quality": round(self.weights.w_cam_quality * c_cam_quality, 4),
            },
            "raw_inputs": {
                "c_det": c_det,
                "c_track": c_track,
                "c_temporal": c_temporal,
                "c_zone": c_zone,
                "c_identity": c_identity,
                "c_anomaly": c_anomaly,
                "c_vlm": c_vlm,
                "c_cam_quality": c_cam_quality,
            }
        }

        return s_route, directive, breakdown
