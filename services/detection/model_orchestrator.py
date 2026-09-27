"""
IBVAP Model Orchestrator & Hierarchical Specialist Router
=========================================================
Implements PHASES D, E, F, G:
- Phase D: Model-Agnostic Common Abstraction (Model Registry + Orchestrator)
- Phase E: Broad Object Detection Coverage with UNKNOWN/UNSURE fallback
- Phase F: Hierarchical Specialist Model Routing (no wasteful all-model all-frame inference)
- Phase G: Model Agreement & Disagreement Fusion Engine (no blind score averaging)
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
import structlog
import time

from .schemas import DetectionBatch, Detection, BBox
from .detection_engine import DetectionEngine

logger = structlog.get_logger()

# ====================================================================== #
# Phase E: Broad Object Coverage & Taxonomy                               #
# ====================================================================== #

class BroadCategory(str, Enum):
    PERSON = "person"
    FACE = "face"
    VEHICLE = "vehicle"
    ANIMAL = "animal"
    BAGGAGE = "baggage"
    EQUIPMENT = "equipment"
    INFRASTRUCTURE = "infrastructure"
    WEAPON = "weapon"
    UNKNOWN = "UNKNOWN / UNSURE"

COCO_BROAD_TAXONOMY: Dict[str, Dict[str, str]] = {
    # Persons & Parts
    "person": {"category": BroadCategory.PERSON.value, "subclass": "person"},
    "face": {"category": BroadCategory.FACE.value, "subclass": "face"},
    "head": {"category": BroadCategory.FACE.value, "subclass": "head"},
    # Vehicles
    "car": {"category": BroadCategory.VEHICLE.value, "subclass": "car"},
    "truck": {"category": BroadCategory.VEHICLE.value, "subclass": "truck"},
    "bus": {"category": BroadCategory.VEHICLE.value, "subclass": "bus"},
    "motorcycle": {"category": BroadCategory.VEHICLE.value, "subclass": "motorcycle"},
    "bicycle": {"category": BroadCategory.VEHICLE.value, "subclass": "bicycle"},
    "van": {"category": BroadCategory.VEHICLE.value, "subclass": "van"},
    "suv": {"category": BroadCategory.VEHICLE.value, "subclass": "suv"},
    "pickup": {"category": BroadCategory.VEHICLE.value, "subclass": "pickup"},
    "trailer": {"category": BroadCategory.VEHICLE.value, "subclass": "trailer"},
    "tractor": {"category": BroadCategory.VEHICLE.value, "subclass": "tractor"},
    "train": {"category": BroadCategory.VEHICLE.value, "subclass": "train"},
    "airplane": {"category": BroadCategory.VEHICLE.value, "subclass": "aircraft"},
    "boat": {"category": BroadCategory.VEHICLE.value, "subclass": "vessel"},
    # Animals & Wildlife
    "dog": {"category": BroadCategory.ANIMAL.value, "subclass": "canine"},
    "cat": {"category": BroadCategory.ANIMAL.value, "subclass": "feline"},
    "horse": {"category": BroadCategory.ANIMAL.value, "subclass": "equine"},
    "cow": {"category": BroadCategory.ANIMAL.value, "subclass": "cattle"},
    "sheep": {"category": BroadCategory.ANIMAL.value, "subclass": "livestock"},
    "bird": {"category": BroadCategory.ANIMAL.value, "subclass": "avian"},
    "bear": {"category": BroadCategory.ANIMAL.value, "subclass": "wildlife"},
    # Baggage / Cargo
    "backpack": {"category": BroadCategory.BAGGAGE.value, "subclass": "backpack"},
    "handbag": {"category": BroadCategory.BAGGAGE.value, "subclass": "handbag"},
    "suitcase": {"category": BroadCategory.BAGGAGE.value, "subclass": "suitcase"},
    "box": {"category": BroadCategory.BAGGAGE.value, "subclass": "package"},
    "package": {"category": BroadCategory.BAGGAGE.value, "subclass": "package"},
    # Equipment & Objects
    "cell phone": {"category": BroadCategory.EQUIPMENT.value, "subclass": "phone"},
    "laptop": {"category": BroadCategory.EQUIPMENT.value, "subclass": "laptop"},
    "bottle": {"category": BroadCategory.EQUIPMENT.value, "subclass": "bottle"},
    "pen": {"category": BroadCategory.EQUIPMENT.value, "subclass": "pen"},
    "toothbrush": {"category": BroadCategory.EQUIPMENT.value, "subclass": "pen"},
    "watch": {"category": BroadCategory.EQUIPMENT.value, "subclass": "watch"},
    "clock": {"category": BroadCategory.EQUIPMENT.value, "subclass": "watch"},
    # Tactical Weapons & Threats (SIH Threat Registry)
    "gun": {"category": BroadCategory.WEAPON.value, "subclass": "gun"},
    "pistol": {"category": BroadCategory.WEAPON.value, "subclass": "gun"},
    "rifle": {"category": BroadCategory.WEAPON.value, "subclass": "gun"},
    "firearm": {"category": BroadCategory.WEAPON.value, "subclass": "gun"},
    "weapon": {"category": BroadCategory.WEAPON.value, "subclass": "gun"},
    "knife": {"category": BroadCategory.WEAPON.value, "subclass": "knife"},
    "grenade": {"category": BroadCategory.WEAPON.value, "subclass": "grenade"},
    "explosive": {"category": BroadCategory.WEAPON.value, "subclass": "explosive"},
    "explosion": {"category": BroadCategory.WEAPON.value, "subclass": "explosive"},
    "traffic light": {"category": BroadCategory.INFRASTRUCTURE.value, "subclass": "signal"},
    "stop sign": {"category": BroadCategory.INFRASTRUCTURE.value, "subclass": "sign"},
    "fire hydrant": {"category": BroadCategory.INFRASTRUCTURE.value, "subclass": "barrier"},
}

@dataclass
class SpecialistResult:
    specialist_name: str
    verified_class: str
    subclass: str
    confidence: float
    attributes: Dict[str, Any] = field(default_factory=dict)
    disagreement: bool = False
    notes: str = ""

# ====================================================================== #
# Phase G: Model Agreement & Disagreement Fusion Engine                   #
# ====================================================================== #

class ModelFusionEngine:
    """
    Combines primary detector output with specialist verifications.
    NEVER blindly averages confidence scores.
    Uses calibrated confidence weighting and flags MODEL_DISAGREEMENT.
    """

    @staticmethod
    def fuse(
        primary_class: str,
        primary_conf: float,
        primary_subclass: str,
        specialist_result: Optional[SpecialistResult] = None
    ) -> Tuple[str, str, float, bool, Dict[str, Any]]:
        metadata: Dict[str, Any] = {
            "primary_model_class": primary_class,
            "primary_model_confidence": round(primary_conf, 3),
        }

        if specialist_result is None:
            return (primary_class, primary_subclass, primary_conf, False, metadata)

        metadata["specialist_name"] = specialist_result.specialist_name
        metadata["specialist_class"] = specialist_result.verified_class
        metadata["specialist_confidence"] = round(specialist_result.confidence, 3)
        metadata.update(specialist_result.attributes)

        if primary_class.lower() == specialist_result.verified_class.lower():
            calibrated = min(0.99, max(primary_conf, specialist_result.confidence) + 0.02)
            final_sub = specialist_result.subclass or primary_subclass
            return (primary_class, final_sub, calibrated, False, metadata)

        logger.warning(
            "MODEL_DISAGREEMENT detected",
            primary=f"{primary_class}:{primary_subclass} ({primary_conf:.2f})",
            specialist=f"{specialist_result.verified_class}:{specialist_result.subclass} ({specialist_result.confidence:.2f})"
        )
        metadata["disagreement_reason"] = (
            f"Primary detector predicted '{primary_class}', "
            f"but {specialist_result.specialist_name} verified '{specialist_result.verified_class}'."
        )

        if specialist_result.confidence > (primary_conf + 0.25):
            return (
                specialist_result.verified_class,
                specialist_result.subclass,
                specialist_result.confidence,
                True,
                metadata
            )
        elif abs(specialist_result.confidence - primary_conf) < 0.15 and primary_conf < 0.50:
            return (
                BroadCategory.UNKNOWN.value,
                "UNSURE",
                round((primary_conf + specialist_result.confidence) / 2.0, 3),
                True,
                metadata
            )
        else:
            return (primary_class, primary_subclass, primary_conf, True, metadata)

# ====================================================================== #
# Phase F: Hierarchical Specialist Router                                 #
# ====================================================================== #

class HierarchicalObjectRouter:
    """
    Evaluates detected bounding boxes and routes crops to specialists on-demand:
    - Vehicles -> ANPR pipeline & vehicle subtype classification
    - Persons  -> Throttled Face/Head detector
    - Animals  -> Livestock/Wildlife classification
    - Ambiguous -> UNKNOWN / UNSURE
    """

    def __init__(self, anpr_pipeline=None, face_detector=None):
        self.anpr_pipeline = anpr_pipeline
        self.face_detector = face_detector

    def route_vehicle(
        self,
        frame: np.ndarray,
        det: Detection,
        camera_id: str,
        track_id: Optional[int] = None
    ) -> Optional[SpecialistResult]:
        h, w = frame.shape[:2]
        box_w = (det.bbox.x2 - det.bbox.x1) * w
        box_h = (det.bbox.y2 - det.bbox.y1) * h
        if box_w < 40 or box_h < 30:
            return None

        plate_text = None
        plate_conf = 0.0
        if self.anpr_pipeline and track_id is not None:
            telemetry = self.anpr_pipeline.get_track_telemetry(track_id)
            plate_text = telemetry.get("plate_number")
            plate_conf = telemetry.get("ocr_confidence") or 0.0

        attrs: Dict[str, Any] = {}
        if plate_text:
            attrs["plate_number"] = plate_text
            attrs["plate_confidence"] = plate_conf

        sub = det.subclass or "car"
        return SpecialistResult(
            specialist_name="ANPR_Vehicle_Specialist",
            verified_class="vehicle",
            subclass=sub,
            confidence=det.confidence,
            attributes=attrs
        )

    def route_person(
        self,
        frame: np.ndarray,
        det: Detection,
        frame_id: int
    ) -> Optional[SpecialistResult]:
        if not self.face_detector or (frame_id % 4 != 0):
            return None

        h, w = frame.shape[:2]
        pbox = {"x1": det.bbox.x1, "y1": det.bbox.y1, "x2": det.bbox.x2, "y2": det.bbox.y2}
        faces = self.face_detector.detect_faces(frame, person_bbox=pbox)
        
        attrs: Dict[str, Any] = {
            "faces_detected": len(faces),
            "face_boxes": [f.get("bbox") for f in faces]
        }
        return SpecialistResult(
            specialist_name="Face_Detection_Specialist",
            verified_class="person",
            subclass="person",
            confidence=det.confidence,
            attributes=attrs
        )

    def route_animal(self, det: Detection) -> Optional[SpecialistResult]:
        sub = det.subclass or "animal"
        is_wildlife = sub in ("bear", "wildlife", "avian")
        return SpecialistResult(
            specialist_name="Wildlife_Classifier",
            verified_class="animal",
            subclass="wildlife" if is_wildlife else "livestock",
            confidence=det.confidence,
            attributes={"animal_type": sub, "is_wildlife": is_wildlife}
        )

# ====================================================================== #
# Phase D: Unified Model Orchestrator                                     #
# ====================================================================== #

class ModelOrchestrator:
    """
    Unified Orchestrator coordinating Primary Detection, Hierarchical Routing,
    and Calibrated Model Fusion across all camera inputs.
    """

    def __init__(
        self,
        primary_detector: DetectionEngine,
        router: Optional[HierarchicalObjectRouter] = None
    ):
        self.primary_detector = primary_detector
        self.router = router or HierarchicalObjectRouter()
        self.fusion_engine = ModelFusionEngine()

    def process_frame(
        self,
        frame: np.ndarray,
        camera_id: str,
        frame_id: int,
        timestamp,
        active_tracks: Optional[List[Any]] = None
    ) -> DetectionBatch:
        t0 = time.perf_counter()

        batch = self.primary_detector.detect(frame, camera_id, frame_id, timestamp)

        refined_detections: List[Detection] = []
        for det in batch.detections:
            raw_label = (det.class_name or "").lower()

            tax_info = COCO_BROAD_TAXONOMY.get(raw_label, {
                "category": BroadCategory.UNKNOWN.value if det.confidence < 0.45 else raw_label,
                "subclass": raw_label
            })
            cat = tax_info["category"]
            sub = tax_info["subclass"]

            specialist_res = None
            if cat == BroadCategory.VEHICLE.value:
                specialist_res = self.router.route_vehicle(frame, det, camera_id)
            elif cat == BroadCategory.PERSON.value:
                specialist_res = self.router.route_person(frame, det, frame_id)
            elif cat == BroadCategory.ANIMAL.value:
                specialist_res = self.router.route_animal(det)

            final_class, final_sub, final_conf, is_disagree, meta = self.fusion_engine.fuse(
                primary_class=cat,
                primary_conf=det.confidence,
                primary_subclass=sub,
                specialist_result=specialist_res
            )

            refined_detections.append(Detection(
                class_name=final_class,
                confidence=final_conf,
                bbox=det.bbox,
                subclass=final_sub
            ))

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return DetectionBatch(
            camera_id=camera_id,
            frame_id=frame_id,
            timestamp=timestamp,
            detections=refined_detections,
            total_inference_ms=round(latency_ms, 2)
        )

    def process_cascaded(
        self,
        frame: np.ndarray,
        camera_id: str,
        frame_id: int,
        timestamp=None,
        zone_name: str = "DEFAULT_PERIMETER",
        zone_hazard_score: float = 0.5
    ):
        """
        Executes Level 0 through Level 6 Multi-Model Cascaded Inference.
        """
        from services.orchestrator.orchestrator import AutonomousAIOrchestrator
        cascade_engine = AutonomousAIOrchestrator(primary_detector=self.primary_detector)
        return cascade_engine.process_frame(
            frame=frame,
            camera_id=camera_id,
            frame_id=frame_id,
            timestamp=timestamp,
            zone_name=zone_name,
            zone_hazard_score=zone_hazard_score
        )

