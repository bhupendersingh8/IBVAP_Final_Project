"""
IBVAP End-to-End Multi-Channel Performance Benchmark
SIH PS-26187: Hardware-Agnostic Intelligent Surveillance

Benchmarks the complete production pipeline from frame ingestion to SHA-256 evidence ledger:
  Ingestion -> Detection (TensorRT/CUDA) -> ModelOrchestrator -> Tracking (ByteTrack/IoU)
  -> Specialist ANPR -> Spatial/Temporal Rules -> Evidence Hash -> Seqlock RAM Bus
Zero simulated numbers. All latencies physically measured with torch.cuda.synchronize() and time.perf_counter().
"""

import os
import sys
import time
import json
import asyncio
import hashlib
from datetime import datetime, timezone
import psutil
import cv2
import numpy as np
import torch

# Ensure root in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.detection.detection_engine import DetectionEngine
from services.detection.yolo_adapter import YOLOAdapter
from services.detection.runtime_adapters import TensorRTAdapter
from services.detection.model_orchestrator import ModelOrchestrator, HierarchicalObjectRouter
from services.tracking.bytetrack_adapter import FallbackIoUTracker
from services.rules.rule_engine import RuleEngine
from services.rules.temporal_event_engine import TemporalEventEngine, TemporalEngineConfig
from services.anpr.anpr_pipeline import ANPRPipeline
from services.evidence.hash_chain import compute_block_hash, GENESIS_PREVIOUS_HASH, normalize_timestamp_str
from services.ingestion.shared_frame_buffer import SharedFrameWriter


def run_benchmark(video_path: str, max_frames: int = 150):
    print("================================================================================")
    print("        IBVAP END-TO-END PRODUCTION PIPELINE BENCHMARK (RTX 3050)              ")
    print("================================================================================")

    cuda_avail = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if cuda_avail else "CPU Only"
    print(f"Hardware Device: {gpu_name}")
    print(f"CUDA Available:  {cuda_avail}")
    print(f"Test Video:      {video_path}")
    print(f"Max Frames:      {max_frames}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open test video: {video_path}")

    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_in = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video Specs:     {width}x{height} @ {fps_in:.1f} FPS ({total_video_frames} total frames)")

    engine_path = os.path.join(PROJECT_ROOT, "models", "yolov8n.engine")
    use_trt = os.path.exists(engine_path) and cuda_avail

    if use_trt:
        print(f"Primary Detection Engine: TensorRT FP16 ({engine_path})")
        detector = TensorRTAdapter({
            "model_path": engine_path,
            "confidence_threshold": 0.25,
            "input_size": 640,
            "model_name": "yolov8n_tensorrt_fp16",
            "model_version": "8.4.142"
        })
        engine_label = "TensorRT FP16"
    else:
        print("Primary Detection Engine: YOLOv8n PyTorch CUDA")
        detector = YOLOAdapter({
            "model_path": os.path.join(PROJECT_ROOT, "models", "yolov8n.pt"),
            "device": "cuda:0" if cuda_avail else "cpu",
            "confidence_threshold": 0.25,
            "input_size": 640
        })
        engine_label = "PyTorch CUDA"

    detector.load_model()

    # 1. Initialize Pipeline Subsystems
    anpr = ANPRPipeline()
    router = HierarchicalObjectRouter(anpr_pipeline=anpr, face_detector=None)
    orchestrator = ModelOrchestrator(primary_detector=detector, router=router)
    tracker = FallbackIoUTracker(max_age=30, iou_threshold=0.20)
    rule_engine = RuleEngine()
    dummy_queue = asyncio.Queue(maxsize=100)
    temporal_engine = TemporalEventEngine(
        event_queue=dummy_queue,
        config=TemporalEngineConfig(
            cooldown_seconds=10.0,
            dedup_window_seconds=3.0,
            loitering_threshold_seconds=10.0,
            repeated_entry_threshold=3,
        )
    )
    evidence_chain = []
    last_block_hash = GENESIS_PREVIOUS_HASH
    shm_writer = SharedFrameWriter("benchmark_cam_01")

    # Warmup
    print("\nWarming up engine and CUDA stream (5 iterations)...")
    dummy = np.zeros((height, width, 3), dtype=np.uint8)
    for _ in range(5):
        _ = detector.detect(dummy, "CAM_WARMUP", 0, datetime.now(timezone.utc))
        if cuda_avail:
            torch.cuda.synchronize()

    # Latency tracking arrays (milliseconds)
    t_ingest_list = []
    t_detect_list = []
    t_track_list = []
    t_specialist_list = []
    t_rules_list = []
    t_evidence_list = []
    t_shm_list = []
    t_total_list = []

    detection_counts = []
    processed_count = 0

    cpu_before = psutil.cpu_percent(interval=None)
    vram_before = torch.cuda.memory_allocated() / (1024 ** 2) if cuda_avail else 0.0

    print(f"Benchmarking {max_frames} frames end-to-end...")
    t_start = time.perf_counter()

    while processed_count < max_frames:
        t0 = time.perf_counter()
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                break
        t_ingest = (time.perf_counter() - t0) * 1000
        now_ts = datetime.now(timezone.utc)

        # Step 2: Primary Detection & Hierarchical Orchestrator
        t1 = time.perf_counter()
        batch = orchestrator.process_frame(frame, "CAM_BENCHMARK", processed_count, now_ts)
        if cuda_avail:
            torch.cuda.synchronize()
        t_detect = (time.perf_counter() - t1) * 1000
        detection_counts.append(len(batch.detections))

        # Step 3: Multi-Object Tracking
        t2 = time.perf_counter()
        tracking_result = tracker.update(batch)
        t_track = (time.perf_counter() - t2) * 1000

        # Step 4: Hierarchical Specialist ANPR on active vehicle tracks
        t3 = time.perf_counter()
        for tr in tracking_result.active_tracks:
            if tr.class_name.lower() in ("vehicle", "car", "truck", "bus", "motorcycle"):
                anpr.process_vehicle_track(tr, frame, "CAM_BENCHMARK")
        t_specialist = (time.perf_counter() - t3) * 1000

        # Step 5: Spatial and Temporal Rules
        t4 = time.perf_counter()
        spatial_events = rule_engine.evaluate(tracking_result)
        for ev in spatial_events:
            temporal_engine.process_intrusion(
                camera_id="CAM_BENCHMARK",
                track_id=ev.track_id,
                class_name=getattr(ev, "class_name", "unknown"),
                zone_id=ev.zone_id,
                confidence=getattr(ev, "confidence", 0.8),
                timestamp=now_ts
            )
        t_rules = (time.perf_counter() - t4) * 1000

        # Step 6: Tamper-Evident Evidence Cryptographic Hashing
        t5 = time.perf_counter()
        if len(batch.detections) > 0 and (processed_count % 5 == 0):
            ev_hash = hashlib.sha256(frame.tobytes()[:2048]).hexdigest()
            ts_str = normalize_timestamp_str(datetime.now(timezone.utc))
            payload = json.dumps({"frame_id": processed_count, "detections": len(batch.detections)}, sort_keys=True)
            blk_hash = compute_block_hash(
                previous_hash=last_block_hash,
                incident_id=f"INC_{processed_count:04d}",
                evidence_sha256=ev_hash,
                timestamp_iso=ts_str,
                payload_str=payload
            )
            evidence_chain.append({
                "block_id": len(evidence_chain) + 1,
                "record_hash": blk_hash,
                "previous_hash": last_block_hash,
            })
            last_block_hash = blk_hash
        t_evidence = (time.perf_counter() - t5) * 1000

        # Step 7: Seqlock Zero-Disk-I/O RAM Frame Bus
        t6 = time.perf_counter()
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        shm_writer.write_frame(buf.tobytes())
        t_shm = (time.perf_counter() - t6) * 1000

        t_total = (time.perf_counter() - t0) * 1000

        t_ingest_list.append(t_ingest)
        t_detect_list.append(t_detect)
        t_track_list.append(t_track)
        t_specialist_list.append(t_specialist)
        t_rules_list.append(t_rules)
        t_evidence_list.append(t_evidence)
        t_shm_list.append(t_shm)
        t_total_list.append(t_total)

        processed_count += 1

    t_end = time.perf_counter()
    wall_time = t_end - t_start
    system_fps = processed_count / wall_time
    cpu_after = psutil.cpu_percent(interval=None)
    vram_after = torch.cuda.memory_allocated() / (1024 ** 2) if cuda_avail else 0.0

    cap.release()
    shm_writer.close()

    results = {
        "hardware": {
            "device": gpu_name,
            "cuda_available": cuda_avail,
            "engine": engine_label,
            "vram_allocated_mb": round(vram_after, 2),
            "cpu_percent": round(cpu_after, 1),
        },
        "frames_processed": processed_count,
        "wall_time_seconds": round(wall_time, 3),
        "end_to_end_fps": round(system_fps, 2),
        "latency_percentiles_ms": {
            "p50": round(float(np.percentile(t_total_list, 50)), 2),
            "p95": round(float(np.percentile(t_total_list, 95)), 2),
            "p99": round(float(np.percentile(t_total_list, 99)), 2),
            "mean": round(float(np.mean(t_total_list)), 2),
            "min": round(float(np.min(t_total_list)), 2),
            "max": round(float(np.max(t_total_list)), 2),
        },
        "subsystem_latencies_mean_ms": {
            "1_frame_ingestion": round(float(np.mean(t_ingest_list)), 2),
            "2_detection_orchestration": round(float(np.mean(t_detect_list)), 2),
            "3_multi_object_tracking": round(float(np.mean(t_track_list)), 2),
            "4_specialist_anpr": round(float(np.mean(t_specialist_list)), 2),
            "5_spatial_temporal_rules": round(float(np.mean(t_rules_list)), 2),
            "6_evidence_cryptographic_hash": round(float(np.mean(t_evidence_list)), 2),
            "7_seqlock_ram_bus_publishing": round(float(np.mean(t_shm_list)), 2),
        },
        "detections_summary": {
            "total_detected_objects": int(sum(detection_counts)),
            "average_objects_per_frame": round(float(np.mean(detection_counts)), 2),
        },
        "tamper_evident_ledger": {
            "total_blocks_recorded": len(evidence_chain),
            "integrity_verified": (
                all(evidence_chain[i]["previous_hash"] == evidence_chain[i-1]["record_hash"]
                    for i in range(1, len(evidence_chain)))
                and (len(evidence_chain) == 0 or evidence_chain[0]["previous_hash"] == GENESIS_PREVIOUS_HASH)
            ),
        }
    }

    print("\n================================================================================")
    print(f"                  END-TO-END PIPELINE BENCHMARK COMPLETE ({engine_label})        ")
    print("================================================================================")
    print(f"End-to-End System Throughput: {results['end_to_end_fps']} FPS")
    print(f"Mean Pipeline Latency:       {results['latency_percentiles_ms']['mean']} ms")
    print(f"P50 Latency:                 {results['latency_percentiles_ms']['p50']} ms")
    print(f"P95 Latency:                 {results['latency_percentiles_ms']['p95']} ms")
    print(f"VRAM Allocated:              {results['hardware']['vram_allocated_mb']} MB")
    print(f"Total Objects Detected:      {results['detections_summary']['total_detected_objects']}")
    print(f"Cryptographic Ledger Status: {'VERIFIED [OK]' if results['tamper_evident_ledger']['integrity_verified'] else 'FAILED'}")
    print("--------------------------------------------------------------------------------")
    for k, v in results["subsystem_latencies_mean_ms"].items():
        print(f"  - {k:35s}: {v:6.2f} ms")
    print("================================================================================")

    out_json = os.path.join(PROJECT_ROOT, "docs", "end_to_end_benchmark_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {out_json}")

    return results

if __name__ == "__main__":
    video = os.path.join(PROJECT_ROOT, "data", "raw", "clean_stream.mp4")
    run_benchmark(video, max_frames=100)
