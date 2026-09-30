"""
Eye Blink Liveness & Anti-Spoofing Verification Service (SIH PS-26187)
=======================================================================
Detects natural human eye blinks across camera frames using YOLOv8-pose 
keypoints and eye patch gradient/contrast analysis.

Defends against presentation attacks (printed photos, smartphone screens,
static images) by requiring verified eye-blink cycles before granting full
authorized personnel clearance.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import cv2
import numpy as np
import structlog

logger = structlog.get_logger()


@dataclass
class LivenessResult:
    is_live: bool
    blink_count: int
    liveness_status: str  # "VERIFIED_LIVE", "AWAITING_BLINK", "STATIC_SPOOF_SUSPECTED"
    eye_openness: float
    confidence: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class TrackBlinkState:
    """Maintains temporal eye openness and blink cycle state machine for a single tracked individual."""
    def __init__(self, track_id: int):
        self.track_id = track_id
        self.history: List[float] = []
        self.blink_count = 0
        self.state = "OPEN"  # "OPEN", "CLOSING", "PROLONGED_CLOSED"
        self.closed_frames = 0
        self.baseline_open: Optional[float] = None
        self.is_live = False
        self.frames_seen = 0
        self.last_blink_time = 0.0
        self.last_update_time = time.time()

    def update(self, openness: float) -> Tuple[Optional[str], int]:
        """
        Updates the blink tracker with the latest frame's eye openness score.
        Returns (event_name, current_blink_count).
        """
        self.frames_seen += 1
        self.last_update_time = time.time()
        self.history.append(openness)
        if len(self.history) > 45:
            self.history.pop(0)

        # Establish and dynamically calibrate baseline open eye score
        if self.baseline_open is None and len(self.history) >= 3:
            self.baseline_open = max(float(np.median(self.history)), 35.0)
        elif self.baseline_open is not None and openness > self.baseline_open * 0.75:
            # Smoothly adapt baseline to slight ambient lighting changes
            self.baseline_open = 0.95 * self.baseline_open + 0.05 * openness

        thresh_closed = (self.baseline_open or 80.0) * 0.50

        event = None
        if self.state == "OPEN":
            if openness < thresh_closed:
                self.state = "CLOSING"
                self.closed_frames = 1
        elif self.state == "CLOSING":
            if openness < thresh_closed:
                self.closed_frames += 1
                if self.closed_frames > 15:
                    # Eye closed for too long (squinting, looking down, sleeping)
                    self.state = "PROLONGED_CLOSED"
            else:
                # Natural human blink: closure lasts between 1 and 8 frames (~50ms - 250ms)
                if 1 <= self.closed_frames <= 8:
                    self.blink_count += 1
                    self.is_live = True
                    self.last_blink_time = time.time()
                    event = "BLINK_DETECTED"
                self.state = "OPEN"
                self.closed_frames = 0
        elif self.state == "PROLONGED_CLOSED":
            if openness >= thresh_closed:
                self.state = "OPEN"
                self.closed_frames = 0

        return event, self.blink_count


class EyeBlinkLivenessDetector:
    """
    High-precision software eye-blink liveness detector.
    Combines YOLOv8-pose facial keypoints (or facial proportion heuristics)
    with vertical edge energy and pupil-contrast profiling.
    """
    def __init__(self, min_blinks_required: int = 1, spoof_frame_threshold: int = 30):
        self.min_blinks_required = min_blinks_required
        self.spoof_frame_threshold = spoof_frame_threshold
        self.track_states: Dict[int, TrackBlinkState] = {}
        self.track_blinks: Dict[int, int] = {}
        self.track_liveness: Dict[int, bool] = {}
        # Pre-allocated adaptive CLAHE for night & low-light eye patch normalization
        self._eye_clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))

    def compute_eye_openness(self, eye_crop: np.ndarray) -> float:
        """
        Calculates normalized Eye Openness Score (EOS).
        - Open eye: Clear horizontal eyelid edges, dark central pupil, high Sobel-Y energy (>100).
        - Closed eye: Smooth skin over eyelid, low vertical gradient (<35).
        - Night Mode: Automatically applies adaptive CLAHE normalization on low-light patches.
        """
        if eye_crop is None or eye_crop.size == 0 or eye_crop.shape[0] < 6 or eye_crop.shape[1] < 6:
            return 0.0

        try:
            gray = cv2.cvtColor(eye_crop, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (32, 24))

            # Night & Low-Light Adaptive Equalization
            # If the patch is dark (CCTV night/IR conditions), normalize dynamic range
            if float(np.mean(gray)) < 75.0:
                gray = self._eye_clahe.apply(gray)

            # Sobel-Y vertical gradient magnitude across the eyelid slit
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            abs_y = np.abs(sobely)
            center_roi = abs_y[4:20, 6:26]
            grad_energy = float(np.mean(center_roi))

            # Contrast between pupil core and surrounding skin/sclera
            center_patch = gray[6:18, 10:22]
            outer_patch = np.concatenate([gray[0:4, :].flatten(), gray[20:24, :].flatten()])
            contrast = max(0.0, float(np.mean(outer_patch) - np.mean(center_patch)))

            openness = (grad_energy * 0.6) + (contrast * 0.4)
            return round(openness, 2)
        except Exception:
            return 0.0

    def extract_eye_patches(
        self,
        frame: np.ndarray,
        person_bbox: Optional[Dict[str, float]] = None,
        pose_model: Optional[Any] = None
    ) -> List[np.ndarray]:
        """
        Extracts left and right eye image patches using YOLOv8-Pose landmarks
        with facial geometry fallback.
        """
        if frame is None or frame.size == 0:
            return []

        h, w = frame.shape[:2]
        offset_x, offset_y = 0, 0
        if person_bbox:
            px1 = max(0, int(person_bbox["x1"] * w))
            py1 = max(0, int(person_bbox["y1"] * h))
            px2 = min(w, int(person_bbox["x2"] * w))
            py2 = min(h, int(person_bbox["y2"] * h))
            if px2 <= px1 + 15 or py2 <= py1 + 15:
                return []
            roi = frame[py1:py2, px1:px2]
            offset_x, offset_y = px1, py1
        else:
            roi = frame

        eye_crops = []

        # 1. Pose Keypoints Extraction (points 1=Left Eye, 2=Right Eye)
        if pose_model is not None:
            try:
                device = "cuda:0" if getattr(pose_model, "device", None) is not None and "cuda" in str(pose_model.device) else "cpu"
                res = pose_model(roi, verbose=False, device=device)
                for r in res:
                    if r.keypoints is not None and len(r.keypoints.xy) > 0:
                        kpts = r.keypoints.xy.cpu().numpy()[0]
                        confs = r.keypoints.conf.cpu().numpy()[0]
                        if confs[1] > 0.35 and confs[2] > 0.35:
                            l_eye = kpts[1] + [offset_x, offset_y]
                            r_eye = kpts[2] + [offset_x, offset_y]
                            dist = np.linalg.norm(l_eye - r_eye)
                            if dist >= 12:
                                ew = int(dist * 0.38)
                                eh = int(dist * 0.28)
                                for eye_pt in [l_eye, r_eye]:
                                    ex, ey = int(eye_pt[0]), int(eye_pt[1])
                                    y1 = max(0, ey - eh // 2)
                                    y2 = min(h, ey + eh // 2)
                                    x1 = max(0, ex - ew // 2)
                                    x2 = min(w, ex + ew // 2)
                                    if (y2 - y1) >= 6 and (x2 - x1) >= 6:
                                        eye_crops.append(frame[y1:y2, x1:x2])
                                if len(eye_crops) == 2:
                                    return eye_crops
            except Exception:
                pass

        # 2. Geometric Head Fallback
        if person_bbox:
            pw = px2 - px1
            ph = py2 - py1
            # Eye band across upper head (~12% to 24% from top of person box)
            ey1 = py1 + int(ph * 0.12)
            ey2 = py1 + int(ph * 0.24)
            ex1 = px1 + int(pw * 0.22)
            ex2 = px1 + int(pw * 0.48)  # Right eye region
            ex3 = px1 + int(pw * 0.52)
            ex4 = px1 + int(pw * 0.78)  # Left eye region

            for (x_start, x_end) in [(ex1, ex2), (ex3, ex4)]:
                sx1, sx2 = max(0, x_start), min(w, x_end)
                sy1, sy2 = max(0, ey1), min(h, ey2)
                if (sx2 - sx1) >= 6 and (sy2 - sy1) >= 6:
                    eye_crops.append(frame[sy1:sy2, sx1:sx2])

        return eye_crops

    def update_track(
        self,
        track_id: int,
        frame: np.ndarray,
        person_bbox: Optional[Dict[str, float]] = None,
        pose_model: Optional[Any] = None
    ) -> LivenessResult:
        """
        Processes a video frame for a given track, updates the temporal blink
        state machine, and evaluates liveness and spoof status.
        """
        if track_id not in self.track_states:
            self.track_states[track_id] = TrackBlinkState(track_id)

        state = self.track_states[track_id]

        # Extract eye patches
        patches = self.extract_eye_patches(frame, person_bbox, pose_model)
        if patches:
            scores = [self.compute_eye_openness(p) for p in patches]
            avg_openness = float(np.mean(scores))
        else:
            # Maintain previous baseline if occluded
            avg_openness = state.baseline_open or 80.0

        event, count = state.update(avg_openness)

        if track_id in self.track_blinks and count < self.track_blinks[track_id]:
            count = self.track_blinks[track_id]
            state.blink_count = count
        if track_id in self.track_liveness and self.track_liveness[track_id]:
            state.is_live = True

        self.track_blinks[track_id] = count
        self.track_liveness[track_id] = state.is_live

        # Evaluate anti-spoofing (Photo Presentation Attack Detection)
        # Static printed photos display near-zero eye variance across dozens of frames
        is_spoof = False
        if state.frames_seen >= self.spoof_frame_threshold and state.blink_count == 0:
            variance = float(np.var(state.history)) if len(state.history) >= 20 else 10.0
            if variance < 3.5:
                is_spoof = True

        # Determine status
        if state.is_live or count >= self.min_blinks_required:
            status = "VERIFIED_LIVE"
            is_live_flag = True
        elif is_spoof:
            status = "STATIC_SPOOF_SUSPECTED"
            is_live_flag = False
        else:
            status = "AWAITING_BLINK"
            is_live_flag = False

        return LivenessResult(
            is_live=is_live_flag,
            blink_count=count,
            liveness_status=status,
            eye_openness=round(avg_openness, 2),
            confidence=round(min(1.0, 0.50 + count * 0.25), 2) if is_live_flag else 0.0,
            details={
                "frames_seen": state.frames_seen,
                "baseline_open": round(state.baseline_open or 0.0, 1),
                "event": event,
                "variance": round(float(np.var(state.history)), 2) if state.history else 0.0
            }
        )

    def cleanup_track(self, track_id: int):
        """Cleans up expired track states to preserve memory."""
        self.track_states.pop(track_id, None)
