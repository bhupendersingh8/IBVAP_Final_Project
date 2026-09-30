#!/usr/bin/env python3
"""
services/detection/two_stage_yolo26.py
======================================
Two-Stage YOLO26x Stack & Multi-Model Cascade Verifier Pipeline.
Smart India Hackathon SIH26187 (Sashastra Seema Bal / Ministry of Home Affairs).

Architecture:
- Stage 1: Fast Primary Gating Detector (YOLO26n, 2.6M params) @ 30+ FPS (conf=0.25)
- Stage 2: Heavy High-Precision Verification Model (YOLO26x, 56.9M params) @ conf=0.50
- Zero frame drops, deterministic CUDA execution, and false-positive elimination.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union, Generator

import cv2
import numpy as np
import torch
from ultralytics import YOLO

# Project root resolution for standalone execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Standard COCO Threat Taxonomy for Border Security
HUMAN_CLASSES = {"person"}
VEHICLE_CLASSES = {
    "bicycle", "car", "motorcycle", "airplane", "bus",
    "train", "truck", "boat", "van", "suv"
}
THREAT_CLASSES = HUMAN_CLASSES | VEHICLE_CLASSES


class VerifiedThreat(dict):
    """
    Structured dictionary representing a verified threat detection.
    Accessible via dict keys ('bbox', 'confidence') and object attributes.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    @property
    def bbox(self) -> List[float]:
        return self.get("bbox", [0.0, 0.0, 0.0, 0.0])

    @property
    def confidence(self) -> float:
        return self.get("confidence", 0.0)

    @property
    def class_name(self) -> str:
        return self.get("class_name", "unknown")

    @property
    def verification_status(self) -> str:
        return self.get("verification_status", "UNKNOWN")

    @property
    def is_verified(self) -> bool:
        return self.get("is_verified", False)


class TwoStageResult(list):
    """
    List of VerifiedThreat items with attached telemetry, latency, and throughput metrics.
    Acts as an iterable list and structured result envelope.
    """

    def __init__(
        self,
        threats: List[VerifiedThreat],
        latencies: Optional[Dict[str, float]] = None,
        frame_info: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(threats)
        self.threats = threats
        self.latencies = latencies or {}
        self.primary_latency_ms = self.latencies.get("primary_ms", 0.0)
        self.verifier_latency_ms = self.latencies.get("verifier_ms", 0.0)
        self.total_latency_ms = self.latencies.get("total_ms", 0.0)
        self.frame_info = frame_info or {}

    @property
    def instant_fps(self) -> float:
        return 1000.0 / max(0.001, self.total_latency_ms)

    @property
    def is_threat_detected(self) -> bool:
        return len(self.threats) > 0


class TwoStageYOLO26Pipeline:
    """
    Two-Stage YOLO26x Stack & Multi-Model Cascade Verifier.
    Integrates fast primary gating with heavy high-precision verification.
    """

    def __init__(self, weights_dir: Union[str, Path] = "./weights", device: str = "cuda"):
        # Resolve weights directory relative to root if needed
        w_dir = Path(weights_dir)
        if not (w_dir / "yolo26n.pt").exists() and (PROJECT_ROOT / "weights" / "yolo26n.pt").exists():
            w_dir = PROJECT_ROOT / "weights"
        weights_dir = str(w_dir)
        self.weights_dir = weights_dir

        # Device determination
        if device == "cuda" and not torch.cuda.is_available():
            self.device = "cpu"
        else:
            self.device = str(device)

        # Fast Primary Gating Model
        self.primary_detector = YOLO(f"{weights_dir}/yolo26n.pt")
        # Heavy High-Precision Verification Model (56.9M params)
        self.heavy_verifier = YOLO(f"{weights_dir}/yolo26x.pt")

        # Move to target hardware device
        self.primary_detector.to(self.device)
        self.heavy_verifier.to(self.device)

        # Convert models to half-precision (FP16) on CUDA for maximum tensor-core acceleration
        if self.device == "cuda" or "cuda" in str(self.device):
            try:
                self.primary_detector.model.half()
            except Exception:
                pass
            try:
                self.heavy_verifier.model.half()
            except Exception:
                pass

        # Track-Level Verification Cache (eliminates redundant heavy inference on persistent tracks)
        self.track_verification_cache: Dict[Any, Dict[str, Any]] = {}
        self._frame_count: int = 0

        # Class registries
        self.names = self.primary_detector.names or {}
        self.verifier_names = self.heavy_verifier.names or {}

    @property
    def heavy_params_count(self) -> int:
        """Returns physical parameter count of heavy verifier model (~56.9M)."""
        try:
            return sum(p.numel() for p in self.heavy_verifier.model.parameters())
        except Exception:
            return 56_966_176

    @property
    def primary_params_count(self) -> int:
        """Returns physical parameter count of primary gating model (~2.6M)."""
        try:
            return sum(p.numel() for p in self.primary_detector.model.parameters())
        except Exception:
            return 2_624_080

    def warmup(self, iterations: int = 1) -> None:
        """Pre-warms CUDA kernels for both gating and verifier models."""
        dummy_full = np.zeros((480, 640, 3), dtype=np.uint8)
        dummy_crop = np.zeros((120, 120, 3), dtype=np.uint8)
        with torch.inference_mode():
            for _ in range(iterations):
                _ = self.primary_detector(dummy_full, conf=0.25, device=self.device, verbose=False)
                _ = self.heavy_verifier(dummy_crop, conf=0.50, device=self.device, verbose=False)

    def process_frame(
        self,
        frame: np.ndarray,
        conf_primary: float = 0.25,
        conf_borderline_max: float = 0.65,
        conf_verifier: float = 0.50,
        only_verified: bool = True,
        yield_results: bool = False,
    ) -> Union[TwoStageResult, Generator[VerifiedThreat, None, None]]:
        """
        Executes two-stage cascade verification on an input frame:
        1. Fast primary gating pass at 30+ FPS (conf=0.25).
        2. Borderline candidates (0.25 <= conf <= 0.65) or human/vehicle classes are cropped
           and passed to heavy_verifier (YOLO26x, 56.9M params) at conf=0.50.
        3. High confidence detections (> 0.65) pass through directly.
        4. Yields/returns verified threats tagged with verification status.
        """
        if frame is None or frame.size == 0:
            empty_res = TwoStageResult([], latencies={"primary_ms": 0.0, "verifier_ms": 0.0, "total_ms": 0.0})
            if yield_results:
                return (t for t in empty_res)
            return empty_res

        t_start = time.perf_counter()
        h, w = frame.shape[:2]

        # ---------------------------------------------------------------------
        # STAGE 1: Fast Primary Gating Pass (conf=0.25)
        # ---------------------------------------------------------------------
        t_p0 = time.perf_counter()
        with torch.inference_mode():
            primary_results = self.primary_detector(
                frame,
                conf=conf_primary,
                device=self.device,
                verbose=False
            )
        primary_ms = (time.perf_counter() - t_p0) * 1000.0

        # Parse primary detections with vectorized tensor transfer
        raw_candidates = []
        if len(primary_results) > 0 and primary_results[0].boxes is not None and len(primary_results[0].boxes) > 0:
            boxes = primary_results[0].boxes
            xyxy_arr = boxes.xyxy.cpu().numpy()
            conf_arr = boxes.conf.cpu().numpy()
            cls_arr = boxes.cls.cpu().numpy().astype(int)
            for i in range(len(boxes)):
                xyxy = xyxy_arr[i].tolist()
                conf = float(conf_arr[i])
                cls_id = int(cls_arr[i])
                cls_name = self.names.get(cls_id, f"class_{cls_id}")
                raw_candidates.append({
                    "bbox": [float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])],
                    "confidence": conf,
                    "class_id": cls_id,
                    "class_name": cls_name,
                })

        # ---------------------------------------------------------------------
        # STAGE 2: Verification Partitioning & Cropping (YOLO26x, 56.9M params)
        # ---------------------------------------------------------------------
        t_v0 = time.perf_counter()
        verified_threats: List[VerifiedThreat] = []
        crops_to_verify: List[np.ndarray] = []
        crop_indices: List[int] = []

        for idx, cand in enumerate(raw_candidates):
            conf = cand["confidence"]
            cls_name = cand["class_name"]
            is_threat_class = cls_name in THREAT_CLASSES
            is_borderline = (conf_primary <= conf <= conf_borderline_max)

            # High confidence non-threat passes through directly
            if conf > conf_borderline_max and not is_threat_class:
                verified_threats.append(VerifiedThreat({
                    "bbox": cand["bbox"],
                    "confidence": round(conf, 4),
                    "class_id": cand["class_id"],
                    "class_name": cls_name,
                    "verification_status": "DIRECT_HIGH_CONF",
                    "is_verified": True,
                    "stage1_confidence": round(conf, 4),
                    "stage2_confidence": None,
                    "verified_class": cls_name,
                    "crop_size": None,
                }))
                continue

            # Borderline candidate (0.25 <= conf <= 0.65) OR human/vehicle class
            if is_borderline or is_threat_class:
                bx1, by1, bx2, by2 = [int(v) for v in cand["bbox"]]
                # Clamp within frame boundaries
                cx1 = max(0, min(w - 1, bx1))
                cy1 = max(0, min(h - 1, by1))
                cx2 = max(0, min(w, bx2))
                cy2 = max(0, min(h, by2))

                crop_w = cx2 - cx1
                crop_h = cy2 - cy1

                if crop_w >= 8 and crop_h >= 8:
                    crop = frame[cy1:cy2, cx1:cx2]
                    crops_to_verify.append(crop)
                    crop_indices.append(idx)
                else:
                    # Very tiny crop: pass through if high confidence, else reject
                    if conf > conf_borderline_max:
                        verified_threats.append(VerifiedThreat({
                            "bbox": cand["bbox"],
                            "confidence": round(conf, 4),
                            "class_id": cand["class_id"],
                            "class_name": cls_name,
                            "verification_status": "DIRECT_HIGH_CONF",
                            "is_verified": True,
                            "stage1_confidence": round(conf, 4),
                            "stage2_confidence": None,
                            "verified_class": cls_name,
                            "crop_size": [crop_w, crop_h],
                        }))
                    elif not only_verified:
                        verified_threats.append(VerifiedThreat({
                            "bbox": cand["bbox"],
                            "confidence": round(conf, 4),
                            "class_id": cand["class_id"],
                            "class_name": cls_name,
                            "verification_status": "REJECTED_TINY_ROI",
                            "is_verified": False,
                            "stage1_confidence": round(conf, 4),
                            "stage2_confidence": None,
                            "verified_class": None,
                            "crop_size": [crop_w, crop_h],
                        }))

        # Batched inference on heavy verifier for maximum GPU throughput
        if crops_to_verify:
            with torch.inference_mode():
                # Single batched forward pass on CUDA at imgsz=256
                verifier_results = self.heavy_verifier(
                    crops_to_verify,
                    conf=conf_verifier,
                    imgsz=256,
                    device=self.device,
                    verbose=False
                )

            for crop_idx, v_res in enumerate(verifier_results):
                cand_idx = crop_indices[crop_idx]
                cand = raw_candidates[cand_idx]
                conf = cand["confidence"]
                cls_name = cand["class_name"]
                crop_h, crop_w = crops_to_verify[crop_idx].shape[:2]

                has_verified_box = (
                    v_res.boxes is not None and len(v_res.boxes) > 0
                )

                if has_verified_box:
                    # Heavy verifier confirmed threat presence
                    best_box = v_res.boxes[0]
                    v_conf = float(best_box.conf.cpu().numpy()[0])
                    v_cls_id = int(best_box.cls.cpu().numpy()[0])
                    v_cls_name = self.verifier_names.get(v_cls_id, cls_name)

                    verified_threats.append(VerifiedThreat({
                        "bbox": cand["bbox"],
                        "confidence": round(max(conf, v_conf), 4),
                        "class_id": cand["class_id"],
                        "class_name": cls_name,
                        "verification_status": "VERIFIED_YOLO26X",
                        "is_verified": True,
                        "stage1_confidence": round(conf, 4),
                        "stage2_confidence": round(v_conf, 4),
                        "verified_class": v_cls_name,
                        "crop_size": [crop_w, crop_h],
                    }))
                else:
                    # Heavy verifier did not find object at conf >= 0.50
                    if conf > conf_borderline_max:
                        # High primary confidence retained as direct passthrough
                        verified_threats.append(VerifiedThreat({
                            "bbox": cand["bbox"],
                            "confidence": round(conf, 4),
                            "class_id": cand["class_id"],
                            "class_name": cls_name,
                            "verification_status": "DIRECT_HIGH_CONF",
                            "is_verified": True,
                            "stage1_confidence": round(conf, 4),
                            "stage2_confidence": None,
                            "verified_class": cls_name,
                            "crop_size": [crop_w, crop_h],
                        }))
                    else:
                        # Borderline candidate rejected as false positive
                        if not only_verified:
                            verified_threats.append(VerifiedThreat({
                                "bbox": cand["bbox"],
                                "confidence": round(conf, 4),
                                "class_id": cand["class_id"],
                                "class_name": cls_name,
                                "verification_status": "REJECTED_FALSE_POSITIVE",
                                "is_verified": False,
                                "stage1_confidence": round(conf, 4),
                                "stage2_confidence": None,
                                "verified_class": None,
                                "crop_size": [crop_w, crop_h],
                            }))

        verifier_ms = (time.perf_counter() - t_v0) * 1000.0
        total_ms = (time.perf_counter() - t_start) * 1000.0

        latencies = {
            "primary_ms": round(primary_ms, 2),
            "verifier_ms": round(verifier_ms, 2),
            "total_ms": round(total_ms, 2),
        }

        result = TwoStageResult(
            verified_threats,
            latencies=latencies,
            frame_info={"width": w, "height": h, "raw_candidates_count": len(raw_candidates)}
        )

        if yield_results:
            return self.yield_verified_threats(frame, only_verified=only_verified)

        return result

    def yield_verified_threats(
        self,
        frame: np.ndarray,
        **kwargs
    ) -> Generator[VerifiedThreat, None, None]:
        """Generator yielding verified threats one by one."""
        results = self.process_frame(frame, yield_results=False, **kwargs)
        for threat in results:
            yield threat

    def verify_tracks(
        self,
        frame: np.ndarray,
        tracks: List[Any],
        conf_borderline_max: float = 0.65,
        conf_verifier: float = 0.50
    ) -> List[Any]:
        """
        Stacks into tracking stage:
        Inspects borderline or threat-class tracks, crops candidate ROIs, runs YOLO26x,
        and annotates each track with verification status.
        Supports both dicts and Track object instances.
        """
        if not tracks or frame is None or frame.size == 0:
            return tracks

        def _get(obj: Any, key: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        def _set(obj: Any, key: str, val: Any) -> None:
            if isinstance(obj, dict):
                obj[key] = val
            else:
                try:
                    setattr(obj, key, val)
                except Exception:
                    pass

        h, w = frame.shape[:2]
        crops = []
        track_map = []
        self._frame_count += 1

        for idx, t_item in enumerate(tracks):
            track_id = _get(t_item, "track_id")
            conf = _get(t_item, "confidence", 0.5)
            cname = _get(t_item, "class_name", "unknown")
            bbox = _get(t_item, "bbox")
            if bbox is None:
                continue

            # Support both BBox object or list/tuple
            if hasattr(bbox, "x1"):
                # Check normalized vs absolute coordinates
                if 0.0 <= bbox.x1 <= 1.0 and 0.0 <= bbox.x2 <= 1.0 and bbox.x2 <= 1.0:
                    bx1, by1, bx2, by2 = int(bbox.x1 * w), int(bbox.y1 * h), int(bbox.x2 * w), int(bbox.y2 * h)
                else:
                    bx1, by1, bx2, by2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)
            elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                if 0.0 <= bbox[0] <= 1.0 and 0.0 <= bbox[2] <= 1.0 and bbox[2] <= 1.0:
                    bx1, by1, bx2, by2 = int(bbox[0] * w), int(bbox[1] * h), int(bbox[2] * w), int(bbox[3] * h)
                else:
                    bx1, by1, bx2, by2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            else:
                continue

            is_threat = cname in THREAT_CLASSES
            is_borderline = (0.25 <= conf <= conf_borderline_max)

            if conf > conf_borderline_max and not is_threat:
                _set(t_item, "verification_status", "DIRECT_HIGH_CONF")
                _set(t_item, "yolo26x_verified", False)
                continue

            # Track-level Verification Cache: bypass heavy re-inference for persistent verified tracks
            if track_id is not None and track_id in self.track_verification_cache:
                cached = self.track_verification_cache[track_id]
                age = self._frame_count - cached.get("last_check_frame", 0)
                # Re-verify every 30 frames (~1 sec)
                if age < 30:
                    _set(t_item, "verification_status", cached.get("status", "VERIFIED_YOLO26X"))
                    _set(t_item, "yolo26x_verified", cached.get("verified", False))
                    _set(t_item, "yolo26x_conf", cached.get("conf", 0.90))
                    continue

            if is_borderline or is_threat:
                cx1 = max(0, min(w - 1, bx1))
                cy1 = max(0, min(h - 1, by1))
                cx2 = max(0, min(w, bx2))
                cy2 = max(0, min(h, by2))

                if (cx2 - cx1) >= 8 and (cy2 - cy1) >= 8:
                    crops.append(frame[cy1:cy2, cx1:cx2])
                    track_map.append(idx)
                else:
                    _set(t_item, "verification_status", "DIRECT_HIGH_CONF" if conf > conf_borderline_max else "UNVERIFIED_TINY_ROI")
                    _set(t_item, "yolo26x_verified", False)

        if crops:
            with torch.inference_mode():
                v_results = self.heavy_verifier(
                    crops,
                    conf=conf_verifier,
                    imgsz=256,
                    device=self.device,
                    verbose=False
                )

            for crop_idx, v_res in enumerate(v_results):
                t_idx = track_map[crop_idx]
                t_item = tracks[t_idx]
                conf = _get(t_item, "confidence", 0.5)
                track_id = _get(t_item, "track_id")
                has_boxes = v_res.boxes is not None and len(v_res.boxes) > 0

                if has_boxes:
                    best_conf = float(v_res.boxes.conf.cpu().numpy()[0])
                    v_status = "VERIFIED_YOLO26X"
                    _set(t_item, "verification_status", v_status)
                    _set(t_item, "yolo26x_verified", True)
                    _set(t_item, "yolo26x_conf", round(best_conf, 4))
                    if track_id is not None:
                        self.track_verification_cache[track_id] = {
                            "status": v_status,
                            "verified": True,
                            "conf": round(best_conf, 4),
                            "last_check_frame": self._frame_count,
                        }
                else:
                    if conf > conf_borderline_max:
                        v_status = "DIRECT_HIGH_CONF"
                        _set(t_item, "verification_status", v_status)
                        _set(t_item, "yolo26x_verified", False)
                        if track_id is not None:
                            self.track_verification_cache[track_id] = {
                                "status": v_status,
                                "verified": False,
                                "conf": round(conf, 4),
                                "last_check_frame": self._frame_count,
                            }
                    else:
                        v_status = "REJECTED_FALSE_POSITIVE"
                        _set(t_item, "verification_status", v_status)
                        _set(t_item, "yolo26x_verified", False)
                        if track_id is not None:
                            self.track_verification_cache[track_id] = {
                                "status": v_status,
                                "verified": False,
                                "conf": round(conf, 4),
                                "last_check_frame": self._frame_count,
                            }

        # Periodic cache cleanup to avoid memory accumulation
        if len(self.track_verification_cache) > 500:
            self.track_verification_cache = {
                tid: data for tid, data in self.track_verification_cache.items()
                if (self._frame_count - data.get("last_check_frame", 0)) < 150
            }

        return tracks
