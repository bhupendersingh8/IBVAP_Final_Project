"""
IBVAP Long-Term Remembrance & Cross-Camera Re-Identification Store
SIH PS-26187: Hardware-Agnostic Intelligent Surveillance

Maintains persistent entity profiles for vehicles and persons across temporary occlusions,
camera angle changes, and intermittent tracks. Associates license plates, vehicle classes
(truck, car, motorcycle, bus), and temporal sightings.
"""

import os
import json
import time
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import structlog

logger = structlog.get_logger()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_STORE_PATH = os.path.join(PROJECT_ROOT, "data", "remembrance_store.json")

@dataclass
class EntityProfile:
    global_id: str
    entity_type: str
    subclass: str
    license_plate: Optional[str] = None
    plate_confidence: Optional[float] = None
    first_seen: str = ""
    last_seen: str = ""
    total_sightings: int = 1
    active_track_id: Optional[int] = None
    cameras_seen: List[str] = field(default_factory=list)
    confidence_avg: float = 0.85
    last_bbox: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class LongTermRemembranceStore:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, store_path: str = DEFAULT_STORE_PATH) -> "LongTermRemembranceStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(store_path=store_path)
            return cls._instance

    def __init__(self, store_path: str = DEFAULT_STORE_PATH):
        self.store_path = store_path
        self._profiles: Dict[str, EntityProfile] = {}
        self._plate_to_id: Dict[str, str] = {}
        self._track_to_id: Dict[int, str] = {}
        self._next_vehicle_seq = 1
        self._next_person_seq = 1
        self._next_other_seq = 1
        self._last_save_time = time.time()
        self._lock = threading.Lock()
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if not os.path.exists(self.store_path):
            return
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("profiles", []):
                profile = EntityProfile(**item)
                self._profiles[profile.global_id] = profile
                if profile.license_plate:
                    self._plate_to_id[profile.license_plate.upper()] = profile.global_id
                if profile.global_id.startswith("REID-V"):
                    try:
                        seq = int(profile.global_id.replace("REID-V", ""))
                        self._next_vehicle_seq = max(self._next_vehicle_seq, seq + 1)
                    except ValueError:
                        pass
                elif profile.global_id.startswith("REID-P"):
                    try:
                        seq = int(profile.global_id.replace("REID-P", ""))
                        self._next_person_seq = max(self._next_person_seq, seq + 1)
                    except ValueError:
                        pass
            logger.info("Loaded remembrance store", total_profiles=len(self._profiles))
        except Exception as e:
            logger.warning("Failed to load remembrance store", error=str(e))

    def _save_to_disk(self, force: bool = False) -> None:
        now = time.time()
        if not force and (now - self._last_save_time < 5.0):
            return
        self._last_save_time = now
        try:
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            payload = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "total_profiles": len(self._profiles),
                "profiles": [p.to_dict() for p in self._profiles.values()]
            }
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.error("Failed to save remembrance store", error=str(e))

    def record_sighting(
        self,
        camera_id: str,
        track_id: int,
        class_name: str,
        subclass: Optional[str] = None,
        bbox: Optional[Dict[str, float]] = None,
        confidence: float = 0.8,
        plate: Optional[str] = None,
        plate_conf: Optional[float] = None
    ) -> EntityProfile:
        with self._lock:
            now_iso = datetime.now(timezone.utc).isoformat()
            sub = (subclass or class_name).lower()
            norm_plate = plate.strip().upper().replace(" ", "") if plate else None
            matched_id: Optional[str] = None

            if norm_plate and norm_plate in self._plate_to_id:
                matched_id = self._plate_to_id[norm_plate]

            if not matched_id and track_id in self._track_to_id:
                matched_id = self._track_to_id[track_id]

            if not matched_id and bbox:
                for gid, prof in self._profiles.items():
                    if prof.subclass == sub and prof.last_bbox:
                        try:
                            last_seen_dt = datetime.fromisoformat(prof.last_seen)
                            age_sec = (datetime.now(timezone.utc) - last_seen_dt).total_seconds()
                            if age_sec < 15.0:
                                c1x = (bbox["x1"] + bbox["x2"]) / 2.0
                                c1y = (bbox["y1"] + bbox["y2"]) / 2.0
                                c2x = (prof.last_bbox["x1"] + prof.last_bbox["x2"]) / 2.0
                                c2y = (prof.last_bbox["y1"] + prof.last_bbox["y2"]) / 2.0
                                dist = ((c1x - c2x)**2 + (c1y - c2y)**2)**0.5
                                if dist < 0.15:
                                    matched_id = gid
                                    break
                        except Exception:
                            pass

            if matched_id and matched_id in self._profiles:
                prof = self._profiles[matched_id]
                prof.last_seen = now_iso
                prof.total_sightings += 1
                prof.active_track_id = track_id
                prof.last_bbox = bbox or prof.last_bbox
                if camera_id not in prof.cameras_seen:
                    prof.cameras_seen.append(camera_id)
                if norm_plate and (not prof.license_plate or (plate_conf and plate_conf > (prof.plate_confidence or 0.0))):
                    prof.license_plate = norm_plate
                    prof.plate_confidence = plate_conf
                    self._plate_to_id[norm_plate] = matched_id
                prof.confidence_avg = round((prof.confidence_avg * 0.8) + (confidence * 0.2), 2)
            else:
                if class_name.lower() == "vehicle" or sub in ("car", "truck", "motorcycle", "bus", "bicycle"):
                    gid = f"REID-V{self._next_vehicle_seq:03d}"
                    self._next_vehicle_seq += 1
                    etype = "vehicle"
                elif class_name.lower() == "person":
                    gid = f"REID-P{self._next_person_seq:03d}"
                    self._next_person_seq += 1
                    etype = "person"
                else:
                    gid = f"REID-O{self._next_other_seq:03d}"
                    self._next_other_seq += 1
                    etype = "object"

                prof = EntityProfile(
                    global_id=gid,
                    entity_type=etype,
                    subclass=sub,
                    license_plate=norm_plate,
                    plate_confidence=plate_conf,
                    first_seen=now_iso,
                    last_seen=now_iso,
                    total_sightings=1,
                    active_track_id=track_id,
                    cameras_seen=[camera_id],
                    confidence_avg=round(confidence, 2),
                    last_bbox=bbox
                )
                self._profiles[gid] = prof
                if norm_plate:
                    self._plate_to_id[norm_plate] = gid
                matched_id = gid

            self._track_to_id[track_id] = matched_id
            self._save_to_disk()
            return prof

    def get_profile_by_track(self, track_id: int) -> Optional[EntityProfile]:
        with self._lock:
            gid = self._track_to_id.get(track_id)
            return self._profiles.get(gid) if gid else None

    def get_profile_by_plate(self, plate: str) -> Optional[EntityProfile]:
        with self._lock:
            gid = self._plate_to_id.get(plate.strip().upper().replace(" ", ""))
            return self._profiles.get(gid) if gid else None

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        with self._lock:
            sorted_profs = sorted(self._profiles.values(), key=lambda p: p.last_seen, reverse=True)
            return [p.to_dict() for p in sorted_profs]

    def clear(self) -> None:
        with self._lock:
            self._profiles.clear()
            self._plate_to_id.clear()
            self._track_to_id.clear()
            self._next_vehicle_seq = 1
            self._next_person_seq = 1
            self._next_other_seq = 1
            self._save_to_disk(force=True)
            logger.info("Remembrance store cleared")
