"""
IBVAP — Cloud / Remote NVIDIA GPU Self-Contained Validation Script
SIH Problem Statement: 26187 | Tactical Border Surveillance

Designed to run inside Lightning AI Studio, RunPod, Google Colab, or any Linux/Windows remote NVIDIA GPU.
Executes genuine verification:
1. Driver & CUDA environment inspection (nvidia-smi, torch.cuda, compute capability)
2. Hardware profile detection (HardwareDetector)
3. FP16 tensor mathematical throughput benchmark
4. Real video pipeline execution on data/raw/test_video.mp4 (FPS, p50, p95 latency, VRAM)
5. Generates deployment/cloud_gpu_telemetry.json
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime, timezone

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def run_cmd(cmd_list):
    try:
        res = subprocess.run(cmd_list, capture_output=True, text=True, timeout=10)
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def main():
    print("=" * 65)
    print("  IBVAP — REMOTE / CLOUD NVIDIA GPU VERIFICATION SUITE")
    print("  SIH PS ID: 26187 | Tactical Border Surveillance")
    print("=" * 65)

    telemetry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": os.uname().nodename if hasattr(os, "uname") else os.environ.get("COMPUTERNAME", "unknown"),
        "platform": sys.platform,
        "python_version": sys.version.split()[0],
        "gpu_detected": False,
        "cuda_available": False,
        "gpu_details": {},
        "pipeline_benchmarks": {},
        "status": "INCOMPLETE"
    }

    # 1. Inspect nvidia-smi
    smi_out = run_cmd(["nvidia-smi", "--query-gpu=name,memory.total,driver_version,cuda_version", "--format=csv,noheader"])
    print(f"\n[1/5] Checking nvidia-smi...")
    if "Error" in smi_out or not smi_out:
        print("  [-] nvidia-smi not found or failed.")
        print(f"      Output: {smi_out}")
    else:
        print(f"  [+] nvidia-smi detected: {smi_out}")
        parts = [p.strip() for p in smi_out.split(",")]
        if len(parts) >= 4:
            telemetry["gpu_details"]["smi_name"] = parts[0]
            telemetry["gpu_details"]["total_vram"] = parts[1]
            telemetry["gpu_details"]["driver_version"] = parts[2]
            telemetry["gpu_details"]["cuda_version"] = parts[3]

    # 2. Inspect PyTorch & CUDA
    print(f"\n[2/5] Inspecting PyTorch & CUDA environment...")
    try:
        import torch
        telemetry["gpu_details"]["torch_version"] = torch.__version__
        cuda_avail = torch.cuda.is_available()
        telemetry["cuda_available"] = cuda_avail
        print(f"  PyTorch Version: {torch.__version__}")
        print(f"  torch.cuda.is_available(): {cuda_avail}")

        if cuda_avail:
            telemetry["gpu_detected"] = True
            dev_name = torch.cuda.get_device_name(0)
            dev_cap = torch.cuda.get_device_capability(0)
            vram_mb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 2)
            telemetry["gpu_details"]["device_name"] = dev_name
            telemetry["gpu_details"]["compute_capability"] = f"{dev_cap[0]}.{dev_cap[1]}"
            telemetry["gpu_details"]["total_vram_mb"] = round(vram_mb, 1)
            print(f"  Device Name: {dev_name}")
            print(f"  Compute Capability: {dev_cap[0]}.{dev_cap[1]}")
            print(f"  Total VRAM: {vram_mb:.1f} MB")

            # Mathematical FP16 verification
            print("  Verifying FP16 Tensor Throughput...")
            t0 = time.perf_counter()
            x = torch.randn(2048, 2048, dtype=torch.float16, device="cuda")
            y = torch.randn(2048, 2048, dtype=torch.float16, device="cuda")
            for _ in range(20):
                z = torch.matmul(x, y)
            torch.cuda.synchronize()
            fp16_time = (time.perf_counter() - t0) / 20.0 * 1000.0
            telemetry["gpu_details"]["fp16_matmul_latency_ms"] = round(fp16_time, 2)
            print(f"  [+] FP16 Matmul Latency: {fp16_time:.2f} ms")
        else:
            print("  [-] WARNING: CUDA is NOT available in PyTorch. Running in CPU fallback.")
    except ImportError:
        print("  [-] PyTorch is not installed in the current environment.")
        telemetry["gpu_details"]["torch_error"] = "PyTorch not installed"

    # 3. Inspect Optional Inference Engines (TensorRT / ONNX Runtime)
    print(f"\n[3/5] Inspecting Acceleration Backends...")
    try:
        import tensorrt as trt
        telemetry["gpu_details"]["tensorrt_version"] = trt.__version__
        print(f"  [+] TensorRT Version: {trt.__version__}")
    except (ImportError, Exception):
        telemetry["gpu_details"]["tensorrt_version"] = "NOT_INSTALLED"
        print("  [-] TensorRT: Not installed (optional acceleration provider)")

    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        telemetry["gpu_details"]["ort_providers"] = providers
        print(f"  [+] ONNX Runtime Providers: {providers}")
    except (ImportError, Exception):
        telemetry["gpu_details"]["ort_providers"] = []
        print("  [-] ONNX Runtime: Not installed")

    # 4. Hardware Profile Auto-Discovery
    print(f"\n[4/5] Testing IBVAP HardwareProfile Engine...")
    try:
        from services.hardware.hardware_detector import HardwareDetector
        detector = HardwareDetector()
        profile = detector.resolve_profile()
        telemetry["hardware_profile"] = profile.to_dict()
        print(f"  [+] Resolved Profile: {profile.profile_name.value}")
        print(f"  [+] Max Streams Recommended: {profile.max_streams_recommended}")
        print(f"  [+] FP16 Supported: {profile.runtime.fp16_supported}")
    except Exception as e:
        print(f"  [-] HardwareDetector failed: {e}")
        telemetry["hardware_profile_error"] = str(e)

    # 5. Real Video Pipeline Execution
    print(f"\n[5/5] Executing Real Video Pipeline on recorded CCTV footage...")
    video_path = os.path.join(PROJECT_ROOT, "data", "raw", "test_video.mp4")
    if os.path.exists(video_path):
        try:
            from benchmark.run_real_video_pipeline import run_pipeline
            print(f"  Running on: {video_path}")
            if telemetry["cuda_available"]:
                import torch
                torch.cuda.reset_peak_memory_stats()
            t_start = time.perf_counter()
            pipe_results = run_pipeline(video_path, max_frames=60)
            elapsed = time.perf_counter() - t_start
            if telemetry["cuda_available"]:
                import torch
                peak_vram = torch.cuda.max_memory_allocated() / (1024 ** 2)
                pipe_results["peak_vram_allocated_mb"] = round(peak_vram, 2)
                print(f"  [+] Peak VRAM Allocated: {peak_vram:.2f} MB")
            telemetry["pipeline_benchmarks"] = pipe_results
            telemetry["pipeline_duration_sec"] = round(elapsed, 2)
            telemetry["status"] = "SUCCESS_GPU" if telemetry["cuda_available"] else "SUCCESS_CPU_FALLBACK"
            print(f"  [+] Pipeline Execution Complete in {elapsed:.2f}s")
        except Exception as e:
            print(f"  [-] Real video pipeline execution encountered an error: {e}")
            telemetry["pipeline_error"] = str(e)
            telemetry["status"] = "PIPELINE_ERROR"
    else:
        print(f"  [-] Video test file not found at {video_path}")
        telemetry["status"] = "VIDEO_NOT_FOUND"

    # Save output telemetry
    output_path = os.path.join(PROJECT_ROOT, "deployment", "cloud_gpu_telemetry.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(telemetry, f, indent=2)
    print(f"\nTelemetry saved to: {output_path}")

    print("\n" + "=" * 65)
    print(f"  RESULT STATUS: {telemetry['status']}")
    print(f"  CUDA ACCELERATION: {'ACTIVE' if telemetry['cuda_available'] else 'OFFLINE (CPU)'}")
    print("=" * 65)
    return 0 if telemetry["cuda_available"] else 1

if __name__ == "__main__":
    sys.exit(main())
