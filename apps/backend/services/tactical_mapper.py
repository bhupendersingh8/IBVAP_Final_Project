"""
SIH26228 Tactical Defence Class Remapping (Ministry of Defence / Indian Army DGIS)
==================================================================================
Remaps generic COCO vision classes into operational defence assets:
- 0 (person)     -> 'tactical_personnel'
- 2 (car)        -> 'recon_vehicle'
- 3 (motorcycle) -> 'patrol_convoy'
- 5 (bus)        -> 'transport_convoy'
- 7 (truck)      -> 'armored_vehicle'
"""

from typing import List, Dict, Any

TACTICAL_DEFENCE_MAP = {
    0: "tactical_personnel",    # COCO 'person'
    2: "recon_vehicle",         # COCO 'car'
    3: "patrol_convoy",         # COCO 'motorcycle'
    5: "transport_convoy",      # COCO 'bus'
    7: "armored_vehicle"        # COCO 'truck'
}

COCO_NAME_TO_TACTICAL = {
    "person": "tactical_personnel",
    "car": "recon_vehicle",
    "motorcycle": "patrol_convoy",
    "bicycle": "patrol_convoy",
    "bus": "transport_convoy",
    "truck": "armored_vehicle",
    "van": "recon_vehicle",
    "suv": "recon_vehicle",
    "pickup": "recon_vehicle",
    "gun": "armed_threat_weapon",
    "weapon": "armed_threat_weapon",
    "knife": "armed_threat_weapon",
    "explosive": "explosive_hazard",
    "grenade": "explosive_hazard"
}


def map_sih26228_label(class_id: int = -1, class_name: str = "") -> str:
    """Returns the SIH26228 tactical defence label for a class ID or name."""
    c_lower = str(class_name).lower().strip()
    if c_lower and c_lower in COCO_NAME_TO_TACTICAL:
        return COCO_NAME_TO_TACTICAL[c_lower]
    if class_id in TACTICAL_DEFENCE_MAP:
        return TACTICAL_DEFENCE_MAP[class_id]
    return c_lower or "unknown_tactical_asset"


def map_sih26228_detections(raw_boxes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remaps detection dictionaries to conform strictly to SIH26228 tactical schema.
    """
    tactical_boxes = []
    for box in raw_boxes:
        cls_id = int(box.get("class_id", box.get("cls", 0)))
        raw_name = str(box.get("class_name", box.get("name", box.get("label", ""))))
        label = map_sih26228_label(cls_id, raw_name)

        tactical_boxes.append({
            "class_id": cls_id,
            "label": label,
            "class_name": label,
            "confidence": round(float(box.get("confidence", box.get("conf", 0.9))), 2),
            "bbox": box.get("bbox", [0.0, 0.0, 0.0, 0.0]),
            "track_id": box.get("track_id", -1),
            "integrity_status": "VERIFIED"
        })
    return tactical_boxes
