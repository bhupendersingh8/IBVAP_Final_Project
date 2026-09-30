"""
Automated System & Hardware Discovery Tool for IBVAP.
Reports exact CPU, RAM, GPU, Driver, and Multimedia stack details.
"""
import sys
import os
import platform
import psutil
import json
import shutil
import subprocess

def inspect_hardware():
    report = {
        "os": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python_version": sys.version.split()[0]
        },
        "cpu": {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_processors": psutil.cpu_count(logical=True),
            "current_cpu_percent": psutil.cpu_percent(interval=0.2)
        },
        "ram": {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "used_percent": psutil.virtual_memory().percent
        },
        "gpu": {
            "nvidia_smi_available": False,
            "gpu_name": None,
            "vram_total_mb": None,
            "driver_version": None,
            "torch_cuda_available": False,
            "torch_version": None
        },
        "multimedia_tools": {
            "ffmpeg": shutil.which("ffmpeg") is not None,
            "docker": shutil.which("docker") is not None,
            "gstreamer": shutil.which("gst-launch-1.0") is not None
        }
    }

    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            encoding="utf-8"
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        if len(parts) >= 3:
            report["gpu"]["nvidia_smi_available"] = True
            report["gpu"]["gpu_name"] = parts[0]
            report["gpu"]["vram_total_mb"] = float(parts[1])
            report["gpu"]["driver_version"] = parts[2]
    except Exception as e:
        report["gpu"]["error"] = str(e)

    try:
        import torch
        report["gpu"]["torch_version"] = torch.__version__
        report["gpu"]["torch_cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            report["gpu"]["torch_device_name"] = torch.cuda.get_device_name(0)
            report["gpu"]["compute_capability"] = torch.cuda.get_device_capability(0)
    except Exception as e:
        report["gpu"]["torch_error"] = str(e)

    try:
        import tensorrt
        report["gpu"]["tensorrt_available"] = True
        report["gpu"]["tensorrt_version"] = tensorrt.__version__
    except Exception as e:
        report["gpu"]["tensorrt_available"] = False
        report["gpu"]["tensorrt_error"] = str(e)

    # Check NVCC (CUDA Toolkit)
    try:
        nvcc_out = subprocess.check_output(["nvcc", "--version"], encoding="utf-8").strip()
        report["gpu"]["nvcc_version"] = nvcc_out.splitlines()[-1]
    except Exception:
        report["gpu"]["nvcc_version"] = None

    # Check NVIDIA Container Toolkit / Docker runtime
    try:
        nvidia_ctk = shutil.which("nvidia-ctk") is not None or shutil.which("nvidia-container-cli") is not None
        report["multimedia_tools"]["nvidia_container_toolkit"] = nvidia_ctk
    except Exception:
        report["multimedia_tools"]["nvidia_container_toolkit"] = False

    return report

if __name__ == "__main__":
    rep = inspect_hardware()
    print(json.dumps(rep, indent=2))
