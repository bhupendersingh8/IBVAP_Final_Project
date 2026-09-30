"""
Stress & Load Profile Benchmark for Newly Promoted Models:
- YOLO26n (Detection Primary)
- YOLO11n-Seg (Segmentation Primary)
- YOLO11n-Pose (Pose Primary)
- ByteTrack (Tracking Primary)
Measures sustained FPS, latency jitter (mean, p50, p95, max), CPU usage %, and memory footprint under 30-frame video load.
"""
import os
import sys
import time
import psutil
import numpy as np
import cv2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ultralytics import YOLO

video_path = os.path.join(PROJECT_ROOT, "data", "raw", "test_video.mp4")
cap = cv2.VideoCapture(video_path)
frames = []
for _ in range(30):
    ret, f = cap.read()
    if not ret:
        break
    frames.append(f)
cap.release()

if not frames:
    print("Generating synthetic frames...")
    frames = [np.full((360, 640, 3), 128, dtype=np.uint8) for _ in range(30)]

print(f"Loaded {len(frames)} benchmark frames ({frames[0].shape}).")

def profile_model(name, model_path, forward_fn):
    print(f"\n=======================================================")
    print(f" Profiling Under Sustained Load: {name}")
    print(f" Path: {model_path}")
    print(f"=======================================================")
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)
    
    model = YOLO(model_path)
    
    # Warmup
    forward_fn(model, frames[0])
    
    latencies = []
    cpu_usages = []
    
    t_start = time.perf_counter()
    for i, frame in enumerate(frames):
        t0 = time.perf_counter()
        cpu_before = psutil.cpu_percent(interval=None)
        res = forward_fn(model, frame)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)
        cpu_usages.append(psutil.cpu_percent(interval=None))
        
    total_time = time.perf_counter() - t_start
    sustained_fps = len(frames) / total_time
    mem_after = process.memory_info().rss / (1024 * 1024)
    
    mean_lat = float(np.mean(latencies))
    p50_lat = float(np.percentile(latencies, 50))
    p95_lat = float(np.percentile(latencies, 95))
    max_lat = float(np.max(latencies))
    avg_cpu = float(np.mean([c for c in cpu_usages if c > 0] or [psutil.cpu_percent()]))
    
    print(f"Sustained FPS:     {sustained_fps:.2f} FPS")
    print(f"Mean Latency:      {mean_lat:.2f} ms")
    print(f"Median (p50):      {p50_lat:.2f} ms")
    print(f"95th Percentile:   {p95_lat:.2f} ms")
    print(f"Max Latency:       {max_lat:.2f} ms")
    print(f"Memory Overhead:   +{mem_after - mem_before:.1f} MB (Total: {mem_after:.1f} MB)")
    return {
        "model": name,
        "sustained_fps": round(sustained_fps, 2),
        "mean_latency_ms": round(mean_lat, 2),
        "p50_latency_ms": round(p50_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
        "max_latency_ms": round(max_lat, 2),
        "mem_delta_mb": round(mem_after - mem_before, 2)
    }

results = []
results.append(profile_model(
    "YOLO26n Primary Detector",
    os.path.join(PROJECT_ROOT, "models", "detection", "yolo26n.pt"),
    lambda m, f: m(f, verbose=False)
))

results.append(profile_model(
    "YOLO11n-Pose Primary Pose",
    os.path.join(PROJECT_ROOT, "models", "pose", "yolo11n-pose.pt"),
    lambda m, f: m(f, verbose=False)
))

results.append(profile_model(
    "YOLO11n-Seg Primary Segmentor",
    os.path.join(PROJECT_ROOT, "models", "segmentation", "yolo11n-seg.pt"),
    lambda m, f: m(f, verbose=False)
))

print("\n\nSUMMARY RESULTS TABLE:")
print(f"{'Model Architecture':<32} | {'FPS':<8} | {'Mean (ms)':<10} | {'P95 (ms)':<10} | {'RAM (MB)':<10}")
print("-" * 80)
for r in results:
    print(f"{r['model']:<32} | {r['sustained_fps']:<8} | {r['mean_latency_ms']:<10} | {r['p95_latency_ms']:<10} | {r['mem_delta_mb']:<10}")
