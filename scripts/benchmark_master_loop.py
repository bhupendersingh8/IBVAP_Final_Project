"""
IBVAP Master Loop Empirical Performance Benchmark
SIH 2026 Problem Statement 187 — Border Surveillance Platform

Executes rigorous, multi-sample empirical latency and throughput benchmarks
across all active models, specialist tasks, and multi-stream scenarios.
Records:
- Warmup runs
- 10+ repeated measurements
- p50 and p95 latency
- Sustained FPS
- Process RSS memory
- Real hardware execution status
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import psutil
import numpy as np

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.hardware import hardware_detector
from services.preprocessing.motion_detector import AdaptiveFrameSkipper
from services.preprocessing.clahe_enhancer import CLAHEEnhancer
from services.ontology import CanonicalObjectType, ontology_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ibvap.benchmark")


def get_current_rss_mb() -> float:
    p = psutil.Process(os.getpid())
    return round(p.memory_info().rss / (1024 * 1024), 2)


def benchmark_function(name: str, fn, warmup_iters: int = 3, bench_iters: int = 15) -> Dict[str, Any]:
    logger.info(f"Benchmarking {name} ({warmup_iters} warmup, {bench_iters} runs)...")
    
    # Warmup
    for _ in range(warmup_iters):
        fn()

    latencies = []
    mem_before = get_current_rss_mb()

    for _ in range(bench_iters):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    mem_after = get_current_rss_mb()
    latencies_arr = np.array(latencies)

    mean_lat = float(np.mean(latencies_arr))
    p50_lat = float(np.percentile(latencies_arr, 50))
    p95_lat = float(np.percentile(latencies_arr, 95))
    fps = round(1000.0 / mean_lat, 2) if mean_lat > 0 else 0.0

    return {
        "component": name,
        "runs": bench_iters,
        "mean_ms": round(mean_lat, 2),
        "p50_ms": round(p50_lat, 2),
        "p95_ms": round(p95_lat, 2),
        "fps": fps,
        "rss_mb": mem_after,
        "memory_delta_mb": round(mem_after - mem_before, 2)
    }


def main():
    profile = hardware_detector.resolve_profile()
    logger.info(f"Starting Master Benchmark on profile: {profile.profile_name.value}")

    results = {
        "profile": profile.to_dict(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "benchmarks": {}
    }

    # Dummy test frames (640x480 & 640x640)
    frame_rgb = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    frame_sq = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

    # 1. Motion Gater (AdaptiveFrameSkipper)
    skipper = AdaptiveFrameSkipper(motion_threshold=0.005, pixel_diff_threshold=22)
    results["benchmarks"]["motion_gater"] = benchmark_function(
        "Motion Gater (AdaptiveFrameSkipper)",
        lambda: skipper.evaluate(frame_rgb)
    )

    # 2. Low-Light CLAHE Enhancer
    from services.preprocessing.quality_assessor import QualityAssessor
    qa = QualityAssessor()
    q_report = qa.assess(frame_rgb)
    clahe = CLAHEEnhancer(clip_limit=2.0, tile_grid_size=(8, 8))
    results["benchmarks"]["clahe_restoration"] = benchmark_function(
        "Low-Light CLAHE Enhancer",
        lambda: clahe.enhance(frame_rgb, q_report)
    )

    # 3. Primary Detection (YOLO26n)
    try:
        from ultralytics import YOLO
        yolo26 = YOLO(str(PROJECT_ROOT / "yolo26n.pt"))
        results["benchmarks"]["yolo26n_primary"] = benchmark_function(
            "Primary Detection (YOLO26n)",
            lambda: yolo26(frame_sq, verbose=False, imgsz=640)
        )
    except Exception as e:
        logger.error(f"YOLO26 benchmark failed: {e}")
        results["benchmarks"]["yolo26n_primary"] = {"error": str(e)}

    # 4. Fallback Detection (YOLOv8n)
    try:
        yolov8 = YOLO(str(PROJECT_ROOT / "yolov8n.pt"))
        results["benchmarks"]["yolov8n_fallback"] = benchmark_function(
            "Fallback Detection (YOLOv8n)",
            lambda: yolov8(frame_sq, verbose=False, imgsz=640)
        )
    except Exception as e:
        logger.error(f"YOLOv8 benchmark failed: {e}")
        results["benchmarks"]["yolov8n_fallback"] = {"error": str(e)}

    # 5. Pose Estimation (YOLO11n-Pose)
    try:
        yolo_pose = YOLO(str(PROJECT_ROOT / "yolo11n-pose.pt"))
        results["benchmarks"]["yolo11n_pose"] = benchmark_function(
            "Pose Keypoints (YOLO11n-Pose)",
            lambda: yolo_pose(frame_sq, verbose=False, imgsz=640)
        )
    except Exception as e:
        logger.error(f"YOLO11-Pose benchmark failed: {e}")
        results["benchmarks"]["yolo11n_pose"] = {"error": str(e)}

    # 6. Instance Segmentation (YOLO11n-Seg)
    try:
        yolo_seg = YOLO(str(PROJECT_ROOT / "yolo11n-seg.pt"))
        results["benchmarks"]["yolo11n_seg"] = benchmark_function(
            "Instance Segmentation (YOLO11n-Seg)",
            lambda: yolo_seg(frame_sq, verbose=False, imgsz=640)
        )
    except Exception as e:
        logger.error(f"YOLO11-Seg benchmark failed: {e}")
        results["benchmarks"]["yolo11n_seg"] = {"error": str(e)}

    # 7. Re-ID Feature Extraction (OSNet-x0.25)
    try:
        import torch
        from ml.models.reid_osnet import OSNet_x0_25
        osnet = OSNet_x0_25(embedding_dim=512)
        osnet.eval()
        crop_tensor = torch.randn(1, 3, 256, 128)
        results["benchmarks"]["osnet_reid"] = benchmark_function(
            "Person Re-ID (OSNet-x0.25)",
            lambda: osnet(crop_tensor)
        )
    except Exception as e:
        logger.error(f"OSNet Re-ID benchmark failed: {e}")
        results["benchmarks"]["osnet_reid"] = {"error": str(e)}

    # 8. Multi-Stream Simulated Workload
    stream_results = {}
    for num_streams in [1, 2, 4]:
        logger.info(f"Simulating {num_streams} concurrent camera stream processing...")
        t0 = time.perf_counter()
        for _ in range(5):
            for _ in range(num_streams):
                m_res = skipper.evaluate(frame_rgb)
                if not m_res.should_skip_inference:
                    yolo26(frame_sq, verbose=False, imgsz=640)
        t_tot = time.perf_counter() - t0
        stream_results[f"{num_streams}_streams"] = {
            "elapsed_sec": round(t_tot, 2),
            "effective_fps_per_stream": round((5 * num_streams) / t_tot, 2),
            "total_throughput_fps": round((5 * num_streams) / t_tot, 2),
            "rss_mb": get_current_rss_mb()
        }
    results["multi_camera_simulation"] = stream_results

    # Output to docs and JSON
    out_json = PROJECT_ROOT / "docs" / "master_loop_benchmark.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Master benchmark results written to {out_json}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
