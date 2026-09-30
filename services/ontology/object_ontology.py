"""
IBVAP Canonical Object Ontology
SIH 2026 Problem Statement 187 — Border Surveillance Platform

Enforces strict, standardized object classification across the entire platform.
No downstream component may invent arbitrary class strings.
All detector class IDs (COCO / custom) map deterministically to CanonicalObjectType.
"""

from enum import Enum
from typing import Dict, Optional, Set


class CanonicalObjectType(str, Enum):
    PERSON = "PERSON"
    CAR = "CAR"
    TRUCK = "TRUCK"
    BUS = "BUS"
    MOTORCYCLE = "MOTORCYCLE"
    BICYCLE = "BICYCLE"
    UNKNOWN_VEHICLE = "UNKNOWN_VEHICLE"
    UNKNOWN = "UNKNOWN"

    @property
    def is_person(self) -> bool:
        return self == CanonicalObjectType.PERSON

    @property
    def is_vehicle(self) -> bool:
        return self in {
            CanonicalObjectType.CAR,
            CanonicalObjectType.TRUCK,
            CanonicalObjectType.BUS,
            CanonicalObjectType.MOTORCYCLE,
            CanonicalObjectType.BICYCLE,
            CanonicalObjectType.UNKNOWN_VEHICLE,
        }

    @property
    def requires_anpr(self) -> bool:
        # Motorized vehicles that legally bear license plates
        return self in {
            CanonicalObjectType.CAR,
            CanonicalObjectType.TRUCK,
            CanonicalObjectType.BUS,
            CanonicalObjectType.MOTORCYCLE,
            CanonicalObjectType.UNKNOWN_VEHICLE,
        }


# Standard COCO 80-Class Index Mapping
COCO_CLASS_ID_TO_CANONICAL: Dict[int, CanonicalObjectType] = {
    0: CanonicalObjectType.PERSON,
    1: CanonicalObjectType.BICYCLE,
    2: CanonicalObjectType.CAR,
    3: CanonicalObjectType.MOTORCYCLE,
    5: CanonicalObjectType.BUS,
    7: CanonicalObjectType.TRUCK,
}

# String label normalization mapping
NAME_TO_CANONICAL: Dict[str, CanonicalObjectType] = {
    "person": CanonicalObjectType.PERSON,
    "human": CanonicalObjectType.PERSON,
    "pedestrian": CanonicalObjectType.PERSON,
    "man": CanonicalObjectType.PERSON,
    "woman": CanonicalObjectType.PERSON,
    "car": CanonicalObjectType.CAR,
    "automobile": CanonicalObjectType.CAR,
    "sedan": CanonicalObjectType.CAR,
    "suv": CanonicalObjectType.CAR,
    "truck": CanonicalObjectType.TRUCK,
    "lorry": CanonicalObjectType.TRUCK,
    "pickup": CanonicalObjectType.TRUCK,
    "bus": CanonicalObjectType.BUS,
    "van": CanonicalObjectType.BUS,
    "motorcycle": CanonicalObjectType.MOTORCYCLE,
    "motorbike": CanonicalObjectType.MOTORCYCLE,
    "bike": CanonicalObjectType.MOTORCYCLE,
    "scooter": CanonicalObjectType.MOTORCYCLE,
    "bicycle": CanonicalObjectType.BICYCLE,
    "cycle": CanonicalObjectType.BICYCLE,
    "vehicle": CanonicalObjectType.UNKNOWN_VEHICLE,
}


class ObjectOntologyManager:
    """Translates raw model detector outputs to canonical ontology types."""

    @staticmethod
    def from_coco_id(class_id: int) -> CanonicalObjectType:
        return COCO_CLASS_ID_TO_CANONICAL.get(class_id, CanonicalObjectType.UNKNOWN)

    @staticmethod
    def from_name(name: str) -> CanonicalObjectType:
        clean = (name or "").strip().lower()
        return NAME_TO_CANONICAL.get(clean, CanonicalObjectType.UNKNOWN)

    @staticmethod
    def normalize(class_id: Optional[int] = None, name: Optional[str] = None) -> CanonicalObjectType:
        if class_id is not None and class_id in COCO_CLASS_ID_TO_CANONICAL:
            return COCO_CLASS_ID_TO_CANONICAL[class_id]
        if name:
            return ObjectOntologyManager.from_name(name)
        return CanonicalObjectType.UNKNOWN


# Module singleton
ontology_manager = ObjectOntologyManager()
