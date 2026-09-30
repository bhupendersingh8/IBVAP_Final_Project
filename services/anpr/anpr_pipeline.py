import time
import uuid
from typing import Dict, List, Optional, Tuple, Any
import cv2
import numpy as np
import structlog

from ..tracking.schemas import Track
from ..detection.schemas import BBox
from .schemas import (
    ANPRConfig,
    ANPRObservation,
    OCRResult,
    PlateDetection,
    PlateStatus,
    VehicleObservation
)
from .plate_detector import PlateDetector, ContourPlateDetector
from .ocr_adapter import OCREngine, EasyOCREngine

logger = structlog.get_logger()

class TrackANPRState:
    """Maintains multi-frame ANPR history and consensus for a single tracked vehicle."""
    def __init__(self, track_id: int, camera_id: str, vehicle_class: str):
        self.track_id = track_id
        self.camera_id = camera_id
        self.vehicle_class = vehicle_class
        self.readings: List[OCRResult] = []
        self.best_reading: Optional[OCRResult] = None
        self.best_plate_bbox: Optional[BBox] = None
        self.best_vehicle_crop: Optional[np.ndarray] = None
        self.best_plate_crop: Optional[np.ndarray] = None
        self.status: PlateStatus = PlateStatus.CANDIDATE
        self.last_attempt_time: float = 0.0
        self.last_persisted_time: float = 0.0
        self.persisted_count: int = 0
        self.persisted_id: Optional[str] = None

class ANPRPipeline:
    """
    Coordinates vehicle tracking with plate localization, OCR, multi-frame
    consensus verification, cooldown enforcement, and deduplication.
    """
    def __init__(
        self,
        config: Optional[ANPRConfig] = None,
        plate_detector: Optional[PlateDetector] = None,
        ocr_engine: Optional[OCREngine] = None
    ):
        self.config = config or ANPRConfig()
        self.plate_detector = plate_detector or ContourPlateDetector(
            min_plate_width=self.config.min_plate_width,
            min_plate_height=self.config.min_plate_height
        )
        self.ocr_engine = ocr_engine or EasyOCREngine(
            min_confidence=self.config.min_ocr_confidence
        )
        self.tracks_state: Dict[int, TrackANPRState] = {}

    def cleanup_lost_tracks(self, active_track_ids: List[int]):
        """Purge tracks that have been removed from tracking."""
        current_active = set(active_track_ids)
        for tid in list(self.tracks_state.keys()):
            if tid not in current_active:
                # Retain for brief period or purge
                pass

    def evaluate_track_consistency(self, state: TrackANPRState) -> Tuple[PlateStatus, Optional[str], float, int]:
        """
        Enforces multi-frame consensus rules:
        - Never verify based on a single frame alone.
        - Require at least min_consistent_frames matching readings for STABLE_VERIFIED.
        - If multiple conflicting valid readings exist on the same track, mark LOW_CONFIDENCE.
        """
        valid_readings = [r for r in state.readings if r.status == "SUCCESS" and len(r.normalized_text) >= 4]
        if not valid_readings:
            return PlateStatus.UNREADABLE, None, 0.0, 0

        # Frequency count of normalized text
        text_counts: Dict[str, List[float]] = {}
        for r in valid_readings:
            text_counts.setdefault(r.normalized_text, []).append(r.confidence)

        # Sort by occurrence count descending, then max confidence descending
        sorted_candidates = sorted(
            text_counts.items(),
            key=lambda item: (len(item[1]), max(item[1])),
            reverse=True
        )

        top_text, top_confs = sorted_candidates[0]
        consensus_count = len(top_confs)
        avg_conf = sum(top_confs) / float(consensus_count)

        # Check for conflict: if another candidate has significant occurrences (>=2) and differs
        if len(sorted_candidates) > 1 and len(sorted_candidates[1][1]) >= 2:
            second_text, second_confs = sorted_candidates[1]
            if second_text != top_text:
                logger.info(
                    "Conflicting plate OCR readings detected on track",
                    track_id=state.track_id,
                    primary=top_text,
                    conflicting=second_text
                )
                return PlateStatus.LOW_CONFIDENCE, top_text, avg_conf, consensus_count

        # Multi-frame consensus rule
        if consensus_count >= self.config.min_consistent_frames and avg_conf >= self.config.min_ocr_confidence:
            return PlateStatus.STABLE_VERIFIED, top_text, avg_conf, consensus_count
        elif consensus_count == 1 and avg_conf >= self.config.min_ocr_confidence:
            return PlateStatus.CANDIDATE, top_text, avg_conf, consensus_count
        else:
            return PlateStatus.LOW_CONFIDENCE, top_text, avg_conf, consensus_count

    def process_vehicle_track(
        self,
        track: Track,
        frame: np.ndarray,
        camera_id: str
    ) -> Optional[ANPRObservation]:
        """
        Processes a single vehicle track.
        Executes bounded sampling, plate localization, OCR, consensus assessment,
        and returns an ANPRObservation when eligible.
        """
        if not self.config.enabled or frame is None or frame.size == 0:
            return None

        now = time.time()
        tid = track.track_id
        v_class = getattr(track, 'subclass', None) or "vehicle"

        state = self.tracks_state.setdefault(tid, TrackANPRState(tid, camera_id, v_class))
        state.vehicle_class = v_class

        # Throttle OCR frequency per track
        if now - state.last_attempt_time < self.config.ocr_interval_seconds:
            return None

        state.last_attempt_time = now

        # 1. Crop vehicle from frame
        fh, fw = frame.shape[:2]
        vx1 = max(0, int(track.bbox.x1 * fw))
        vy1 = max(0, int(track.bbox.y1 * fh))
        vx2 = min(fw, int(track.bbox.x2 * fw))
        vy2 = min(fh, int(track.bbox.y2 * fh))

        if (vx2 - vx1) < (self.config.min_plate_width * 1.2) or (vy2 - vy1) < (self.config.min_plate_height * 1.5):
            # Vehicle too small / distant in frame for reliable plate localization
            return None

        vehicle_crop = frame[vy1:vy2, vx1:vx2]

        # 2. Localize plate candidate
        plate_det = self.plate_detector.detect_plate(vehicle_crop)
        if plate_det is None or plate_det.plate_crop is None or plate_det.plate_crop.size == 0:
            # Plate not localized on this frame
            return None

        # 3. Execute OCR on plate crop
        ocr_result = self.ocr_engine.read_plate(plate_det.plate_crop)
        if ocr_result.status == "UNREADABLE" or not ocr_result.normalized_text:
            return None

        state.readings.append(ocr_result)

        # Update best visual crops
        if state.best_reading is None or ocr_result.confidence > state.best_reading.confidence:
            state.best_reading = ocr_result
            state.best_plate_bbox = plate_det.bbox
            state.best_vehicle_crop = vehicle_crop.copy()
            state.best_plate_crop = plate_det.plate_crop.copy()

        # 4. Multi-frame consensus & stability evaluation
        status, verified_text, verified_conf, consensus_count = self.evaluate_track_consistency(state)
        state.status = status

        # 5. Determine if ready for persistence & emission
        # Rule: Persist on STABLE_VERIFIED (always when first achieved, or after cooldown)
        # or upon first high-quality CANDIDATE if no prior observation was emitted
        should_persist = False
        if status == PlateStatus.STABLE_VERIFIED:
            if not getattr(state, 'verified_persisted', False):
                should_persist = True
                state.verified_persisted = True
            elif now - state.last_persisted_time > self.config.anpr_cooldown_seconds:
                should_persist = True
        elif status == PlateStatus.CANDIDATE and state.persisted_count == 0:
            # First candidate observation can be recorded as CANDIDATE status for telemetry
            if verified_conf >= 0.70:
                should_persist = True

        if should_persist:
            state.last_persisted_time = now
            state.persisted_count += 1
            obs_id = str(uuid.uuid4())
            state.persisted_id = obs_id

            return ANPRObservation(
                observation_id=obs_id,
                camera_id=camera_id,
                track_id=tid,
                vehicle_class=state.vehicle_class,
                plate_text=verified_text,
                plate_confidence=verified_conf,
                status=status,
                plate_bbox=state.best_plate_bbox,
                ocr_engine=self.config.ocr_engine,
                consistent_readings=consensus_count
            )

        return None

    def get_track_telemetry(self, track_id: int) -> Dict[str, Any]:
        """Returns live plate text, confidence, and status for a track to stream to UI."""
        state = self.tracks_state.get(track_id)
        if not state:
            return {
                "plate_text": None,
                "plate_confidence": 0.0,
                "plate_status": PlateStatus.UNREADABLE.value,
                "vehicle_class": "vehicle"
            }

        text = state.best_reading.normalized_text if state.best_reading else None
        conf = state.best_reading.confidence if state.best_reading else 0.0

        return {
            "plate_text": text,
            "plate_confidence": round(conf, 2),
            "plate_status": state.status.value if isinstance(state.status, PlateStatus) else str(state.status),
            "vehicle_class": state.vehicle_class
        }
