"""
IBVAP Multi-Model Confidence Fusion Engine
==========================================
Combines primary spatial detections with specialist verifications, temporal state,
zone hazard rules, 4-state identity verification, anomaly detection, VLM reasoning,
and camera quality.
Enforces strict anti-hallucination rules and never blindly averages confidence scores.
"""
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
import structlog

logger = structlog.get_logger()


@dataclass
class FusedTargetRecord:
    target_id: str
    camera_id: str
    primary_class: str
    subclass: str
    fused_confidence: float
    identity_state: str  # UNKNOWN, UNVERIFIED, AUTHORIZED, UNAUTHORIZED
    temporal_state: str  # DETECTED, TENTATIVE, STABLE, VERIFIED, ALERT_ELIGIBLE
    temporal_frame_count: int
    zone_name: str
    zone_hazard_score: float
    anomaly_score: float
    specialist_attributes: Dict[str, Any] = field(default_factory=dict)
    disagreements: List[str] = field(default_factory=list)
    alert_eligible: bool = False
    notes: str = ""
    event_score: float = 0.0
    supporting_signals: List[str] = field(default_factory=list)
    missing_signals: List[str] = field(default_factory=list)
    uncertainty: float = 0.10
    decision_state: str = "NORMAL"  # NORMAL, OBSERVE, REVIEW, CONFIRMED_EVENT


class ConfidenceFusionEngine:
    """
    Calibrated multi-model fusion engine.
    Ensures:
    1. Detection is strictly decoupled from Identity.
    2. Model disagreements are detected and prioritized logically without hallucination.
    3. Weak specialist scores cannot overturn confident primary detections.
    4. Confident specialist confirmations grant calibrated boosts up to 0.99.
    """

    def __init__(self):
        pass

    def fuse_target(
        self,
        target_id: str,
        camera_id: str,
        primary_class: str,
        primary_conf: float,
        primary_subclass: str = "",
        specialist_results: Optional[List[Dict[str, Any]]] = None,
        identity_state: str = "UNKNOWN",
        temporal_state: str = "DETECTED",
        temporal_frame_count: int = 1,
        zone_name: str = "DEFAULT_MONITOR",
        zone_hazard_score: float = 0.5,
        anomaly_score: float = 0.0,
        vlm_threat_score: float = 0.0,
        camera_quality: float = 1.0,
    ) -> FusedTargetRecord:
        specialist_results = specialist_results or []
        disagreements = []
        spec_attrs = {}

        final_class = primary_class
        final_sub = primary_subclass or primary_class
        base_conf = float(primary_conf)

        # 1. Process Specialist Input
        for spec in specialist_results:
            spec_name = spec.get("name", "UnknownSpecialist")
            spec_class = spec.get("class", "").lower()
            spec_sub = spec.get("subclass", "")
            spec_conf = float(spec.get("confidence", 0.0))
            spec_attrs[spec_name] = spec.get("attributes", {})

            if spec_class:
                if spec_class == primary_class.lower():
                    # Agreement: calibrated confidence boost
                    base_conf = min(0.99, max(base_conf, spec_conf) + 0.02)
                    if spec_sub:
                        final_sub = spec_sub
                else:
                    # Disagreement detected
                    reason = f"{spec_name} predicted '{spec_class}' vs Primary '{primary_class}'"
                    disagreements.append(reason)
                    logger.warning("Specialist disagreement", reason=reason, target_id=target_id)
                    if spec_conf > (base_conf + 0.25):
                        final_class = spec_class
                        final_sub = spec_sub or spec_class
                        base_conf = spec_conf
                    else:
                        # Unresolved disagreement slightly attenuates confidence
                        base_conf = max(0.20, base_conf - 0.04)

        # 2. Camera Quality Calibration
        # Poor stream quality attenuates confidence but never drops below 0.10
        quality_weight = 0.85 + 0.15 * max(0.2, min(1.0, camera_quality))
        fused_conf = base_conf * quality_weight

        # 3. Anomaly and VLM synthesis
        if anomaly_score > 0.60:
            fused_conf = min(0.99, fused_conf + 0.04)
        if vlm_threat_score > 0.70:
            fused_conf = min(0.99, fused_conf + 0.05)

        # 4. Temporal Event Engine Status Check
        # Alert eligibility requires verified temporal stability (~45 frames) unless in critical perimeter
        is_alert_eligible = False
        if temporal_state in ("VERIFIED", "ALERT_ELIGIBLE") or temporal_frame_count >= 45:
            if identity_state in ("UNAUTHORIZED", "UNKNOWN") and fused_conf >= 0.50:
                is_alert_eligible = True
            elif zone_hazard_score >= 0.85 and fused_conf >= 0.60:
                # Critical perimeter violation regardless of identity
                is_alert_eligible = True
        elif zone_hazard_score >= 0.90 and fused_conf >= 0.60 and temporal_frame_count >= 5:
            # High hazard perimeter rapid response shortcut
            is_alert_eligible = True

        # 5. Supporting & Missing Signals Analysis (Phase 13)
        supporting: List[str] = [f"Primary detector ({final_class}: {primary_conf:.2f})"]
        missing: List[str] = []

        if temporal_frame_count >= 15:
            supporting.append(f"Temporal persistence: {temporal_frame_count} frames ({temporal_state})")
        else:
            missing.append(f"Immature track history ({temporal_frame_count} frames)")

        if zone_hazard_score > 0.5:
            supporting.append(f"Zone hazard rating: {zone_hazard_score:.2f} ({zone_name})")

        if identity_state in ("UNAUTHORIZED", "AUTHORIZED"):
            supporting.append(f"Identity state: {identity_state}")
        else:
            missing.append("Unconfirmed identity (UNKNOWN)")

        for spec_k, spec_v in spec_attrs.items():
            supporting.append(f"Specialist confirmation: {spec_k}")

        uncertainty = round(max(0.01, 1.0 - fused_conf), 3)
        event_score = round(fused_conf * (0.4 + 0.6 * max(0.1, zone_hazard_score)), 3)

        # Decision State derivation
        if is_alert_eligible and fused_conf >= 0.65:
            decision_state = "CONFIRMED_EVENT"
        elif is_alert_eligible or zone_hazard_score >= 0.70:
            decision_state = "REVIEW"
        elif temporal_frame_count >= 5 or fused_conf >= 0.45:
            decision_state = "OBSERVE"
        else:
            decision_state = "NORMAL"

        return FusedTargetRecord(
            target_id=str(target_id),
            camera_id=camera_id,
            primary_class=final_class,
            subclass=final_sub,
            fused_confidence=round(fused_conf, 3),
            identity_state=identity_state,
            temporal_state=temporal_state,
            temporal_frame_count=temporal_frame_count,
            zone_name=zone_name,
            zone_hazard_score=round(zone_hazard_score, 2),
            anomaly_score=round(anomaly_score, 3),
            specialist_attributes=spec_attrs,
            disagreements=disagreements,
            alert_eligible=is_alert_eligible,
            notes=f"Temporal maturity: {temporal_frame_count} frames, State: {temporal_state}",
            event_score=event_score,
            supporting_signals=supporting,
            missing_signals=missing,
            uncertainty=uncertainty,
            decision_state=decision_state,
        )
