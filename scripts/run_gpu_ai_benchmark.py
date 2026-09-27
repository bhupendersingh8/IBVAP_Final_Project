"""
IBVAP Real GPU + AI Performance Baseline Benchmark
===================================================
Benchmarks YOLOv8n across CPU, PyTorch CUDA, and TensorRT FP16 using
the exact same video frames under identical conditions.

Separates:
- Model load time
- Warmup time
- Real inference latency (with torch.cuda.synchronize)
- CPU / GPU utilization & VRAM
- Detection consistency & bounding-box similarity
"""

import os
import sys
import time
import json
import psutil
import subprocess
import numpy as np
import cv2
from typing import Dict, Any, List

def query_nvidia_smi() -> Dict[str, Any]:
    """Query real-time NVIDIA GPU stats."""
    res = {"gpu_util_percent": 0.0, "vram_used_mb": 0.0, "vram_total_mb": 0.0, "temp_c": 0, "power_w": 0.0}
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
            encoding="utf-8"
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        if len(parts) >= 3:
            res["gpu_util_percent"] = float(parts[0])
            res["vram_used_mb"] = float(parts[1])
            res["vram_total_mb"] = float(parts[2])
        if len(parts) >= 4:
            res["temp_c"] = int(float(parts[3]))
        if len(parts) >= 5:
            res["power_w"] = float(parts[4])
    except Exception:
        pass
    return res

def compute_box_iou(box1, box2):
    # box format: [x1, y1, x2, y2]
    xA = max(box1[0], box2[0])
    yA = max(box1[1], box2[1])
    xB = min(box1[2], box2[2])
    yB = min(box1[3], box2[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0:
        return 0.0
    boxAArea = (box1[2] - box1[0]) * (box1[3] - box1[1])
    boxBArea = (box2[2] - box2[0]) * (box2[3] - box2[1])
    return interArea / float(boxAArea + boxBArea - interArea)

def run_benchmark_for_config(
    name: str,
    device_target: str,
    video_path: str,
    max_frames: int = 100,
    conf_thresh: float = 0.25,
    imgsz: int = 640
) -> Dict[str, Any]:
    print(f"\n=======================================================")
    print(f"[*] Starting Benchmark: {name}")
    print(f"=======================================================")

    result: Dict[str, Any] = {
        "pipeline_name": name,
        "target_device": device_target,
        "success": False,
        "error": None,
        "model_load_time_ms": 0.0,
        "warmup_time_ms": 0.0,
        "total_frames_evaluated": 0,
        "dropped_frames": 0,
        "total_detections": 0,
        "avg_fps": 0.0,
        "avg_latency_ms": 0.0,
        "p50_latency_ms": 0.0,
        "p95_latency_ms": 0.0,
        "min_latency_ms": 0.0,
        "max_latency_ms": 0.0,
        "cpu_util_percent": 0.0,
        "gpu_util_percent": 0.0,
        "vram_used_mb": 0.0,
        "vram_total_mb": 0.0,
        "gpu_temp_c": 0,
        "detections_per_frame_sample": [],
        "sample_detections": []
    }

    cpu_measurements = []
    gpu_measurements = []
    vram_measurements = []

    # 1. Load Model
    t_load_start = time.perf_counter()
    model = None
    try:
        import torch
        from ultralytics import YOLO

        model_weights = "models/yolov8n.pt"
        if not os.path.exists(model_weights):
            model_weights = "yolov8n.pt"

        is_cuda = "CUDA" in name or "TensorRT" in name

        if is_cuda and not torch.cuda.is_available():
            raise RuntimeError(
                f"PyTorch CUDA is unavailable (torch version: {torch.__version__}). "
                "Current Python runtime does not contain CUDA-compiled PyTorch binaries."
            )

        if name == "YOLOv8n TensorRT FP16":
            engine_path = "models/yolov8n.engine"
            if not os.path.exists(engine_path):
                raise FileNotFoundError(f"TensorRT engine file not found: {engine_path}")
            model = YOLO(engine_path, task="detect")
            dev = "cuda:0"
        elif name == "YOLOv8n PyTorch CUDA":
            model = YOLO(model_weights)
            dev = "cuda:0"
        else: # CPU
            model = YOLO(model_weights)
            dev = "cpu"

        result["model_load_time_ms"] = round((time.perf_counter() - t_load_start) * 1000.0, 2)
        print(f"[+] Model loaded in {result['model_load_time_ms']} ms")

        # 2. Warmup
        t_warm_start = time.perf_counter()
        dummy = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
        for _ in range(5):
            if is_cuda:
                torch.cuda.synchronize()
            _ = model(dummy, device=dev, conf=conf_thresh, imgsz=imgsz, verbose=False)
            if is_cuda:
                torch.cuda.synchronize()
        result["warmup_time_ms"] = round((time.perf_counter() - t_warm_start) * 1000.0, 2)
        print(f"[+] Warmup completed (5 iterations) in {result['warmup_time_ms']} ms")

    except Exception as e:
        result["error"] = str(e)
        result["model_load_time_ms"] = round((time.perf_counter() - t_load_start) * 1000.0, 2)
        print(f"[-] Pipeline initialization failed: {e}")
        return result

    # 3. Open Video and run inference
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        result["error"] = f"Failed to open video file: {video_path}"
        return result

    latencies_ms: List[float] = []
    frame_count = 0
    total_detections = 0
    dropped = 0

    psutil.cpu_percent(interval=None)
    t_bench_start = time.perf_counter()

    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret or frame is None:
            dropped += 1
            break

        if is_cuda:
            torch.cuda.synchronize()
        t0 = time.perf_counter()

        try:
            preds = model(frame, device=dev, conf=conf_thresh, imgsz=imgsz, verbose=False)
            if is_cuda:
                torch.cuda.synchronize()
            t_inf = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(t_inf)

            num_dets = len(preds[0].boxes) if preds and len(preds) > 0 else 0
            total_detections += num_dets
            if frame_count < 10:
                result["detections_per_frame_sample"].append(num_dets)
                # Store sample detection bboxes for consistency comparison
                if preds and len(preds) > 0 and len(preds[0].boxes) > 0:
                    sample_boxes = []
                    for b in preds[0].boxes[:3]:
                        sample_boxes.append({
                            "cls": int(b.cls[0].cpu().numpy()),
                            "conf": round(float(b.conf[0].cpu().numpy()), 3),
                            "xyxy": [round(float(coord), 1) for coord in b.xyxy[0].cpu().numpy()]
                        })
                    result["sample_detections"].append({"frame": frame_count, "boxes": sample_boxes})

        except Exception as e:
            result["error"] = f"Inference execution error: {e}"
            break

        frame_count += 1

        if frame_count % 10 == 0:
            cpu_measurements.append(psutil.cpu_percent(interval=None))
            smi = query_nvidia_smi()
            gpu_measurements.append(smi["gpu_util_percent"])
            vram_measurements.append(smi["vram_used_mb"])
            result["vram_total_mb"] = smi["vram_total_mb"]
            result["gpu_temp_c"] = smi.get("temp_c", 0)

    cap.release()
    total_time_elapsed = time.perf_counter() - t_bench_start

    if latencies_ms:
        result["success"] = True
        result["total_frames_evaluated"] = frame_count
        result["dropped_frames"] = dropped
        result["total_detections"] = total_detections
        result["avg_latency_ms"] = round(float(np.mean(latencies_ms)), 2)
        result["p50_latency_ms"] = round(float(np.percentile(latencies_ms, 50)), 2)
        result["p95_latency_ms"] = round(float(np.percentile(latencies_ms, 95)), 2)
        result["min_latency_ms"] = round(float(np.min(latencies_ms)), 2)
        result["max_latency_ms"] = round(float(np.max(latencies_ms)), 2)
        result["avg_fps"] = round(1000.0 / result["avg_latency_ms"], 2) if result["avg_latency_ms"] > 0 else 0.0
        result["cpu_util_percent"] = round(float(np.mean(cpu_measurements)), 1) if cpu_measurements else psutil.cpu_percent()
        result["gpu_util_percent"] = round(float(np.mean(gpu_measurements)), 1) if gpu_measurements else 0.0
        result["vram_used_mb"] = round(float(np.mean(vram_measurements)), 1) if vram_measurements else 0.0

    print(f"[+] Result for {name}:")
    print(f"    - Frames Processed: {result['total_frames_evaluated']}")
    print(f"    - Pure Inference FPS: {result['avg_fps']}")
    print(f"    - Avg Latency:      {result['avg_latency_ms']} ms")
    print(f"    - p50 Latency:      {result['p50_latency_ms']} ms")
    print(f"    - p95 Latency:      {result['p95_latency_ms']} ms")
    print(f"    - Total Detections: {result['total_detections']}")
    print(f"    - CPU Utilization:  {result['cpu_util_percent']}%")
    print(f"    - GPU Utilization:  {result['gpu_util_percent']}%")
    print(f"    - VRAM Usage:       {result['vram_used_mb']} / {result['vram_total_mb']} MB")
    print(f"    - GPU Temp:         {result['gpu_temp_c']} C")

    return result

def evaluate_consistency(cpu_res: Dict, cuda_res: Dict, trt_res: Dict) -> Dict[str, Any]:
    """Evaluates detection consistency across models."""
    consistency = {
        "cpu_vs_cuda_detection_diff": abs(cpu_res["total_detections"] - cuda_res["total_detections"]) if cpu_res["success"] and cuda_res["success"] else "N/A",
        "cuda_vs_trt_detection_diff": abs(cuda_res["total_detections"] - trt_res["total_detections"]) if cuda_res["success"] and trt_res["success"] else "N/A",
        "cpu_total_detections": cpu_res["total_detections"],
        "cuda_total_detections": cuda_res["total_detections"],
        "trt_total_detections": trt_res["total_detections"],
        "sample_bbox_iou_cuda_trt": []
    }

    if cuda_res.get("sample_detections") and trt_res.get("sample_detections"):
        for f_c, f_t in zip(cuda_res["sample_detections"], trt_res["sample_detections"]):
            c_boxes = f_c.get("boxes", [])
            t_boxes = f_t.get("boxes", [])
            if c_boxes and t_boxes:
                iou = compute_box_iou(c_boxes[0]["xyxy"], t_boxes[0]["xyxy"])
                consistency["sample_bbox_iou_cuda_trt"].append({
                    "frame": f_c["frame"],
                    "iou": round(iou, 4),
                    "cuda_conf": c_boxes[0]["conf"],
                    "trt_conf": t_boxes[0]["conf"]
                })
    return consistency

def main():
    video_path = os.path.abspath("data/raw/clean_stream.mp4")
    if not os.path.exists(video_path):
        video_path = os.path.abspath("data/raw/test_video.mp4")

    print(f"Using Benchmark Video: {video_path}")

    configs = [
        ("YOLOv8n PyTorch CPU", "cpu"),
        ("YOLOv8n PyTorch CUDA", "cuda:0"),
        ("YOLOv8n TensorRT FP16", "tensorrt_fp16")
    ]

    all_results = {}
    for name, target in configs:
        res = run_benchmark_for_config(name, target, video_path, max_frames=100)
        all_results[name] = res

    # Consistency analysis
    consistency = evaluate_consistency(
        all_results.get("YOLOv8n PyTorch CPU", {}),
        all_results.get("YOLOv8n PyTorch CUDA", {}),
        all_results.get("YOLOv8n TensorRT FP16", {})
    )
    all_results["detection_consistency_audit"] = consistency

    # Speedups
    cpu_fps = all_results.get("YOLOv8n PyTorch CPU", {}).get("avg_fps", 1.0)
    cuda_fps = all_results.get("YOLOv8n PyTorch CUDA", {}).get("avg_fps", 0.0)
    trt_fps = all_results.get("YOLOv8n TensorRT FP16", {}).get("avg_fps", 0.0)

    all_results["performance_summary"] = {
        "cpu_fps": cpu_fps,
        "cuda_fps": cuda_fps,
        "trt_fps": trt_fps,
        "cuda_speedup_vs_cpu": round(cuda_fps / max(cpu_fps, 0.001), 2) if cuda_fps > 0 else 0.0,
        "trt_speedup_vs_cpu": round(trt_fps / max(cpu_fps, 0.001), 2) if trt_fps > 0 else 0.0,
        "trt_speedup_vs_cuda": round(trt_fps / max(cuda_fps, 0.001), 2) if trt_fps > 0 and cuda_fps > 0 else 0.0,
    }

    out_file = os.path.abspath("docs/gpu_benchmark_results.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n[+] Benchmark complete. Saved raw data to: {out_file}")
    print(f"    - CPU FPS:  {cpu_fps}")
    print(f"    - CUDA FPS: {cuda_fps} ({all_results['performance_summary']['cuda_speedup_vs_cpu']}x vs CPU)")
    print(f"    - TRT FPS:  {trt_fps} ({all_results['performance_summary']['trt_speedup_vs_cpu']}x vs CPU)")

if __name__ == "__main__":
    main()
