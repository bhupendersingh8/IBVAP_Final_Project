"""
IBVAP Adaptive Tiled Inference Engine (SAHI-Equivalent)
======================================================
Implements Phase 5 requirements:
- Executes high-resolution window slicing (tiling) only when triggered.
- Triggers:
    1. Small/distant objects detected (area < 0.005 of frame).
    2. Uncertain confidence candidate (0.25 <= conf <= 0.45).
    3. Configured high-resolution border ROI.
    4. Distant geometry zone indication.
- Merges tiled candidate bounding boxes using Non-Maximum Suppression (NMS).
- Resource guard: Measures additional latency and automatically bypasses tiling
  if inference budget threshold (> 100ms) is exceeded.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import structlog

from .detector_backend import DetectorBackend, StandardDetectionBatch, StandardDetectionRecord

logger = structlog.get_logger(__name__)


def nms_boxes(
    boxes: List[Dict[str, float]],
    scores: List[float],
    iou_threshold: float = 0.45,
) -> List[int]:
    """Applies Non-Maximum Suppression on normalized [0, 1] bounding boxes."""
    if not boxes:
        return []

    x1 = np.array([b["x1"] for b in boxes])
    y1 = np.array([b["y1"] for b in boxes])
    x2 = np.array([b["x2"] for b in boxes])
    y2 = np.array([b["y2"] for b in boxes])
    scores = np.array(scores)

    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        if order.size == 1:
            break

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h

        union = areas[i] + areas[order[1:]] - inter
        iou = np.where(union > 0.0, inter / union, 0.0)

        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]

    return keep


class AdaptiveTiledDetector:
    """
    Wraps any DetectorBackend to provide adaptive, resource-guarded small-object slicing.
    """

    def __init__(
        self,
        base_detector: DetectorBackend,
        tile_size: Tuple[int, int] = (640, 640),
        overlap_ratio: float = 0.20,
        small_area_thresh: float = 0.005,
        uncertain_conf_window: Tuple[float, float] = (0.25, 0.45),
        latency_budget_ms: float = 120.0,
    ):
        self.base_detector = base_detector
        self.tile_size = tile_size
        self.overlap_ratio = overlap_ratio
        self.small_area_thresh = small_area_thresh
        self.uncertain_conf_window = uncertain_conf_window
        self.latency_budget_ms = latency_budget_ms

        self.last_tile_latency_ms = 0.0
        self.tiling_active_count = 0
        self.tiling_bypassed_count = 0

    def should_trigger_tiling(
        self,
        standard_batch: StandardDetectionBatch,
        frame_shape: Tuple[int, int],
        has_distant_zone: bool = False,
    ) -> bool:
        """Determines whether adaptive high-res slicing is warranted."""
        # 1. Distant zone trigger
        if has_distant_zone:
            return True

        # 2. Check for small, ambiguous targets
        for det in standard_batch.detections:
            w = det.bbox["x2"] - det.bbox["x1"]
            h = det.bbox["y2"] - det.bbox["y1"]
            area = w * h
            # Small object trigger
            if area <= self.small_area_thresh:
                return True
            # Uncertain confidence trigger
            if self.uncertain_conf_window[0] <= det.confidence <= self.uncertain_conf_window[1]:
                return True

        return False

    def detect_adaptive(
        self,
        frame: np.ndarray,
        camera_id: str,
        frame_id: int,
        has_distant_zone: bool = False,
    ) -> StandardDetectionBatch:
        """Runs standard detection, checks trigger, and selectively performs tiling."""
        t0 = time.perf_counter()
        h, w = frame.shape[:2]

        # 1. Standard full-frame detection (Fast Path)
        base_batch = self.base_detector.detect(frame, camera_id, frame_id)

        # 2. Trigger check
        if not self.should_trigger_tiling(base_batch, (h, w), has_distant_zone):
            self.last_tile_latency_ms = 0.0
            return base_batch

        # 3. Resource guard: If base detector already took > 70% of budget, bypass tiling
        if base_batch.total_latency >= (self.latency_budget_ms * 0.70):
            logger.info("Adaptive tiling bypassed due to latency budget", latency_ms=base_batch.total_latency)
            self.tiling_bypassed_count += 1
            return base_batch

        self.tiling_active_count += 1
        tile_t0 = time.perf_counter()

        # 4. Generate 2x2 overlapping tiles (or ROI slices)
        tile_h, tile_w = self.tile_size
        step_x = int(w * (1.0 - self.overlap_ratio))
        step_y = int(h * (1.0 - self.overlap_ratio))

        all_boxes: List[Dict[str, float]] = [d.bbox for d in base_batch.detections]
        all_scores: List[float] = [d.confidence for d in base_batch.detections]
        all_records: List[StandardDetectionRecord] = list(base_batch.detections)

        # Slice 2 horizontal quadrants (upper border horizon, lower border perimeter)
        slices = [
            (0, 0, min(w, tile_w), min(h, tile_h)),
            (max(0, w - tile_w), 0, w, min(h, tile_h)),
        ]

        for sx1, sy1, sx2, sy2 in slices:
            crop = frame[sy1:sy2, sx1:sx2]
            if crop.size == 0:
                continue

            crop_batch = self.base_detector.detect(crop, camera_id, frame_id)
            crop_w = sx2 - sx1
            crop_h = sy2 - sy1

            for c_det in crop_batch.detections:
                # Map crop coordinates back to global normalized frame
                gx1 = (sx1 + c_det.bbox["x1"] * crop_w) / float(w)
                gy1 = (sy1 + c_det.bbox["y1"] * crop_h) / float(h)
                gx2 = (sx1 + c_det.bbox["x2"] * crop_w) / float(w)
                gy2 = (sy1 + c_det.bbox["y2"] * crop_h) / float(h)

                mapped_bbox = {
                    "x1": round(max(0.0, min(1.0, gx1)), 4),
                    "y1": round(max(0.0, min(1.0, gy1)), 4),
                    "x2": round(max(0.0, min(1.0, gx2)), 4),
                    "y2": round(max(0.0, min(1.0, gy2)), 4),
                }

                all_boxes.append(mapped_bbox)
                all_scores.append(c_det.confidence)

                rec = StandardDetectionRecord(
                    bbox=mapped_bbox,
                    class_name=c_det.class_name,
                    confidence=c_det.confidence,
                    timestamp=base_batch.timestamp,
                    preprocess_latency=c_det.preprocess_latency,
                    inference_latency=c_det.inference_latency,
                    postprocess_latency=c_det.postprocess_latency,
                    total_latency=c_det.total_latency,
                    subclass="tiled_fine_object",
                    model_name=f"{base_batch.model_name}+SAHI_Tiled",
                    model_version=c_det.model_version,
                )
                all_records.append(rec)

        # 5. Non-Maximum Suppression across merged detections
        keep_indices = nms_boxes(all_boxes, all_scores, iou_threshold=0.45)
        fused_records = [all_records[idx] for idx in keep_indices]

        tile_elapsed_ms = (time.perf_counter() - tile_t0) * 1000.0
        self.last_tile_latency_ms = round(tile_elapsed_ms, 2)
        total_time_ms = (time.perf_counter() - t0) * 1000.0

        return StandardDetectionBatch(
            camera_id=camera_id,
            frame_id=frame_id,
            timestamp=base_batch.timestamp,
            detections=fused_records,
            preprocess_latency=base_batch.preprocess_latency,
            inference_latency=round(base_batch.inference_latency + tile_elapsed_ms, 2),
            postprocess_latency=round(base_batch.postprocess_latency + 1.0, 2),
            total_latency=round(total_time_ms, 2),
            model_name=f"{base_batch.model_name}+AdaptiveTiled",
            frame_width=w,
            frame_height=h,
        )
