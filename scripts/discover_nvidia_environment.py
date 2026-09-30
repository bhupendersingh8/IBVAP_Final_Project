#!/usr/bin/env python3
"""
IBVAP — Comprehensive NVIDIA Hardware & Environment Discovery
=============================================================
Probes physical hardware, driver, CUDA toolkit, runtime packages,
and video analytics infrastructure.
"""

import sys
import os
import shutil
import subprocess
import json

def run_cmd(args):
    try:
        res = subprocess.run(args, capture_output=True, text=True, timeout=5)
        return res.stdout.strip() if res.returncode == 0 else None
    except Exception:
        return None

def main():
    discovery = {}

    # 1. nvidia-smi
    smi_raw = run_cmd(["nvidia-smi"])
    discovery["nvidia_smi_available"] = smi_raw is not None
    if smi_raw:
        query_out = run_cmd([
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.used,driver_version,utilization.gpu,utilization.memory,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits"
        ])
        if query_out:
            parts = [p.strip() for p in query_out.split(",")]
            discovery["gpu_name"] = parts[0] if len(parts) > 0 else "Unknown"
            discovery["vram_total_mb"] = float(parts[1]) if len(parts) > 1 else 0.0
            discovery["vram_used_mb"] = float(parts[2]) if len(parts) > 2 else 0.0
            discovery["driver_version"] = parts[3] if len(parts) > 3 else "Unknown"
            discovery["gpu_util_percent"] = float(parts[4]) if len(parts) > 4 else 0.0
            discovery["memory_util_percent"] = float(parts[5]) if len(parts) > 5 else 0.0
            discovery["temp_c"] = int(float(parts[6])) if len(parts) > 6 else 0
            discovery["power_w"] = float(parts[7]) if len(parts) > 7 else 0.0

    # 2. PyTorch & CUDA
    try:
        import torch
        discovery["torch_version"] = torch.__version__
        discovery["torch_cuda_version"] = torch.version.cuda
        discovery["torch_cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            discovery["torch_device_name"] = torch.cuda.get_device_name(0)
            discovery["torch_compute_capability"] = torch.cuda.get_device_capability(0)
            discovery["cudnn_version"] = torch.backends.cudnn.version() if hasattr(torch.backends, "cudnn") else None
            discovery["cudnn_available"] = torch.backends.cudnn.is_available() if hasattr(torch.backends, "cudnn") else False
    except ImportError:
        discovery["torch_available"] = False

    # 3. TensorRT
    try:
        import tensorrt as trt
        discovery["tensorrt_version"] = trt.__version__
        discovery["tensorrt_available"] = True
    except ImportError:
        discovery["tensorrt_available"] = False
        discovery["tensorrt_version"] = None

    # 4. ONNX Runtime & ONNX Runtime GPU
    try:
        import onnxruntime as ort
        discovery["onnxruntime_version"] = ort.__version__
        discovery["onnxruntime_providers"] = ort.get_available_providers()
        discovery["onnxruntime_gpu_available"] = "CUDAExecutionProvider" in ort.get_available_providers()
    except ImportError:
        discovery["onnxruntime_available"] = False

    # 5. External Tools & Compilers
    discovery["nvcc_path"] = shutil.which("nvcc")
    discovery["ffmpeg_path"] = shutil.which("ffmpeg")
    discovery["docker_path"] = shutil.which("docker")
    discovery["gstreamer_path"] = shutil.which("gst-launch-1.0")
    discovery["mediamtx_path"] = shutil.which("mediamtx") or os.path.exists("infrastructure/mediamtx/mediamtx.exe")
    discovery["nvidia_container_toolkit"] = shutil.which("nvidia-ctk") or shutil.which("nvidia-container-cli")

    print("\n" + "=" * 60)
    print("  IBVAP — NVIDIA Hardware & Environment Discovery Report")
    print("=" * 60)
    for k, v in discovery.items():
        print(f"  {k:30s}: {v}")
    print("=" * 60 + "\n")

    os.makedirs("docs", exist_ok=True)
    with open("docs/nvidia_environment_discovery.json", "w") as f:
        json.dump(discovery, f, indent=2)

if __name__ == "__main__":
    main()
