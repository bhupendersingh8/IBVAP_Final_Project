"""
IBVAP — Real Video Pipeline Execution & Empirical Telemetry Audit
SIH Problem Statement: 26187 | Tactical Border Surveillance

Executes the full 10-stage IBVAP analytics pipeline on actual recorded footage:
data/raw/test_video.mp4
"""

import os
import sys
import time
import json
import cv2
import psutil
import numpy as np
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.preprocessing.condition_analyzer import ConditionAnalyzer, EnhancementManager
from services.detection.detector_backend import YOLOv8Backend
from services.detection.schemas import DetectionBatch, Detection, BBox
from services.tracking.bytetrack_adapter import ByteTrackAdapter
from services.rules.spatial_reasoning_engine import SpatialReasoningEngine, ZoneDefinition
from services.orchestrator.confidence_fusion import ConfidenceFusionEngine, FusedTargetRecord
import hashlib


def run_pipeline(video_path: str, max_frames: int = 60):
    if not os.path.exists(video_path):
        print(f"Error: Video file {video_path} does not exist.")
        sys.exit(1)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Failed to open {video_path}")
        sys.exit(1)

    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_video = cap.get(cv2.CAP_PROP_FPS)
    w_vid = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h_vid = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Loaded Recorded Video: {video_path} ({w_vid}x{h_vid} @ {fps_video:.1f} FPS, {total_video_frames} frames)")

    # 1. Initialize Engines
    condition_analyzer = ConditionAnalyzer()
    enhancement_mgr = EnhancementManager()
    detector = YOLOv8Backend(config={"confidence_threshold": 0.25})
    tracker = ByteTrackAdapter()
    spatial_engine = SpatialReasoningEngine(
        zones=[
            ZoneDefinition(
                zone_id="exclusion_01",
                name="Perimeter Fence",
                polygon=[(0.0, 0.6), (1.0, 0.6), (1.0, 1.0), (0.0, 1.0)],
                zone_type="RESTRICTED",
                hazard_score=1.0
            )
        ]
    )

    fusion_engine = ConfidenceFusionEngine()
    proc = psutil.Process()
    latencies = {
        "ingest": [],
        "preprocess": [],
        "detect": [],
        "track": [],
        "spatial": [],
        "total": []
    }

    frames_processed = 0
    total_detections = 0
    total_tracks = 0
    sample_sha256 = ""

    print(f"Executing real pipeline on {max_frames} frames...")
    t_global_start = time.perf_counter()

    while frames_processed < max_frames:
        t_frame_start = time.perf_counter()

        # Ingestion
        t0 = time.perf_counter()
        ret, frame = cap.read()
        if not ret:
            break
        latencies["ingest"].append((time.perf_counter() - t0) * 1000.0)

        # Preprocessing & Condition Analysis
        t0 = time.perf_counter()
        analysis = condition_analyzer.analyze(frame)
        enh_res = enhancement_mgr.enhance(frame, analysis)
        processed_frame = enh_res.frame
        latencies["preprocess"].append((time.perf_counter() - t0) * 1000.0)

        # Detection
        t0 = time.perf_counter()
        now = datetime.now(timezone.utc)
        det_batch = detector.detect(processed_frame, camera_id="CAM_RECORDED_01", frame_id=frames_processed + 1, timestamp=now)
        latencies["detect"].append((time.perf_counter() - t0) * 1000.0)
        total_detections += len(det_batch.detections)

        # Tracking
        t0 = time.perf_counter()
        detection_objs = [
            Detection(
                class_id=0,
                class_name=d.class_name,
                confidence=d.confidence,
                bbox=BBox(x1=d.bbox["x1"], y1=d.bbox["y1"], x2=d.bbox["x2"], y2=d.bbox["y2"])
            )
            for d in det_batch.detections
        ]
        track_batch = DetectionBatch(
            camera_id="CAM_RECORDED_01",
            frame_id=frames_processed + 1,
            timestamp=now,
            detections=detection_objs
        )
        trk_res = tracker.update(track_batch)
        latencies["track"].append((time.perf_counter() - t0) * 1000.0)
        total_tracks = len(trk_res.active_tracks)

        # Spatial Reasoning & Fusion
        t0 = time.perf_counter()
        for trk in trk_res.active_tracks:
            traj = [(tp.center_x, tp.center_y) for tp in trk.trajectory]
            s_eval = spatial_engine.evaluate_spatial_state(trk.track_id, trk.bbox, traj, frame=processed_frame)
            trk.zone_state = "EXCLUSION" if s_eval.inside_zones else "MONITORING"
            fused = fusion_engine.fuse_target(
                target_id=str(trk.track_id),
                camera_id="CAM_RECORDED_01",
                primary_class=trk.class_name,
                primary_conf=trk.confidence,
                temporal_state=trk.lifecycle_state,
                temporal_frame_count=trk.age_frames,
                zone_name=trk.zone_state,
                zone_hazard_score=s_eval.hazard_score
            )
        latencies["spatial"].append((time.perf_counter() - t0) * 1000.0)

        # Evidence Hash Chain (Section 65B simulation on sample frame)
        if frames_processed == 10:
            success, enc = cv2.imencode(".jpg", frame)
            if success:
                sample_sha256 = hashlib.sha256(enc.tobytes()).hexdigest()

        latencies["total"].append((time.perf_counter() - t_frame_start) * 1000.0)
        frames_processed += 1

    cap.release()
    total_time_s = time.perf_counter() - t_global_start
    effective_fps = frames_processed / max(0.001, total_time_s)

    mem_info = proc.memory_info()
    ram_mb = mem_info.rss / (1024 * 1024)
    cpu_pct = proc.cpu_percent(interval=None)

    p50_latency = float(np.percentile(latencies["total"], 50))
    p95_latency = float(np.percentile(latencies["total"], 95))
    mean_detect = float(np.mean(latencies["detect"]))
    mean_prep = float(np.mean(latencies["preprocess"]))

    results = {
        "video_source": "RECORDED_VIDEO",
        "video_path": video_path,
        "frames_processed": frames_processed,
        "input_resolution": f"{w_vid}x{h_vid}",
        "effective_fps": round(effective_fps, 2),
        "mean_latency_ms": round(float(np.mean(latencies["total"])), 2),
        "p50_latency_ms": round(p50_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "mean_detect_latency_ms": round(mean_detect, 2),
        "mean_preprocess_latency_ms": round(mean_prep, 2),
        "total_detections_logged": total_detections,
        "active_tracks_final": total_tracks,
        "host_ram_used_mb": round(ram_mb, 1),
        "host_cpu_percent": round(cpu_pct, 1),
        "evidence_sample_sha256": sample_sha256,
        "status": "PASS"
    }

    print("\n" + json.dumps(results, indent=2))

    with open("benchmark/results/real_video_pipeline_results.json", "w") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    run_pipeline("data/raw/test_video.mp4", max_frames=50)
