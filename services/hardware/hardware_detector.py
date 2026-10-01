"""
IBVAP Central Hardware Capability Detector
SIH 2026 Problem Statement 187 — Border Surveillance Platform

Autonomously discovers CPU architecture, physical NVIDIA GPU presence,
CUDA runtimes, TensorRT, ONNX Runtime providers, and assigns one of 6
strict execution profiles:
- DELL_CPU
- RTX3050_4GB
- RTX3050_6GB
- HIGH_VRAM_NVIDIA
- REMOTE_GPU
- UNKNOWN
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
import os
import platform
import subprocess
import json
import logging
import psutil

logger = logging.getLogger("ibvap.hardware")


class HardwareProfileName(str, Enum):
    # Canonical Profiles (Grand Finale Section 1)
    LOW_VRAM_4GB = "LOW_VRAM_4GB"
    LOW_VRAM_6GB = "LOW_VRAM_6GB"
    STANDARD_8GB = "STANDARD_8GB"

    # Compatibility Aliases & Legacy Profiles
    DELL_CPU = "DELL_CPU"
    RTX3050_4GB = "RTX3050_4GB"
    RTX3050_6GB = "RTX3050_6GB"
    HIGH_VRAM_NVIDIA = "HIGH_VRAM_NVIDIA"
    REMOTE_GPU = "REMOTE_GPU"
    UNKNOWN = "UNKNOWN"


@dataclass
class CPUCapabilities:
    vendor: str
    model: str
    logical_cores: int
    physical_cores: int
    total_ram_gb: float
    available_ram_gb: float


@dataclass
class GPUCapabilities:
    nvidia_present: bool
    gpu_name: Optional[str]
    total_vram_mb: float
    free_vram_mb: float
    cuda_available: bool
    cuda_version: Optional[str]
    compute_capability: Optional[str]
    driver_version: Optional[str] = None


@dataclass
class RuntimeCapabilities:
    pytorch_cuda: bool
    tensorrt_available: bool
    onnx_cuda_provider: bool
    fp16_supported: bool
    int8_available: bool


@dataclass
class HardwareProfile:
    profile_name: HardwareProfileName
    cpu: CPUCapabilities
    gpu: GPUCapabilities
    runtime: RuntimeCapabilities
    vram_budget_mb: float
    ram_budget_mb: float
    max_streams_recommended: int
    primary_detection_model: str
    primary_runtime: str

    # Section 1 canonical properties
    @property
    def gpu_name(self) -> str:
        return self.gpu.gpu_name or "CPU_ONLY"

    @property
    def total_vram(self) -> float:
        """Total VRAM in MB."""
        return self.gpu.total_vram_mb

    @property
    def total_vram_gb(self) -> float:
        return round(self.gpu.total_vram_mb / 1024.0, 2)

    @property
    def compute_capability(self) -> str:
        return self.gpu.compute_capability or "N/A"

    @property
    def cuda_version(self) -> str:
        return self.gpu.cuda_version or "N/A"

    @property
    def driver_version(self) -> str:
        return self.gpu.driver_version or "N/A"

    @property
    def available_vram(self) -> float:
        """Available/free VRAM in MB."""
        return self.gpu.free_vram_mb

    @property
    def available_vram_gb(self) -> float:
        return round(self.gpu.free_vram_mb / 1024.0, 2)

    @property
    def cpu_threads(self) -> int:
        return self.cpu.logical_cores

    @property
    def system_ram(self) -> float:
        return self.cpu.total_ram_gb

    @property
    def max_streams(self) -> int:
        return self.max_streams_recommended

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_name": self.profile_name.value,
            "gpu_name": self.gpu_name,
            "total_vram": self.total_vram,
            "total_vram_gb": self.total_vram_gb,
            "compute_capability": self.compute_capability,
            "cuda_version": self.cuda_version,
            "driver_version": self.driver_version,
            "available_vram": self.available_vram,
            "available_vram_gb": self.available_vram_gb,
            "cpu_threads": self.cpu_threads,
            "system_ram": self.system_ram,
            "cpu": asdict(self.cpu),
            "gpu": asdict(self.gpu),
            "runtime": asdict(self.runtime),
            "vram_budget_mb": self.vram_budget_mb,
            "ram_budget_mb": self.ram_budget_mb,
            "max_streams_recommended": self.max_streams_recommended,
            "primary_detection_model": self.primary_detection_model,
            "primary_runtime": self.primary_runtime,
        }


class HardwareDetector:
    """Discovers host hardware specs and resolves authoritative IBVAP execution profiles."""

    def __init__(self, override_profile: Optional[str] = None):
        self.override_profile = override_profile

    def detect_cpu(self) -> CPUCapabilities:
        vm = psutil.virtual_memory()
        total_ram_gb = round(vm.total / (1024 ** 3), 2)
        avail_ram_gb = round(vm.available / (1024 ** 3), 2)
        
        # Processor info
        proc = platform.processor() or "Unknown CPU"
        logical_cores = os.cpu_count() or 4
        physical_cores = psutil.cpu_count(logical=False) or (logical_cores // 2)

        vendor = "Intel" if "Intel" in proc or "x86" in platform.machine() else "AMD"
        if "GenuineIntel" in proc:
            vendor = "Intel"
        elif "AuthenticAMD" in proc:
            vendor = "AMD"

        return CPUCapabilities(
            vendor=vendor,
            model=proc,
            logical_cores=logical_cores,
            physical_cores=physical_cores,
            total_ram_gb=total_ram_gb,
            available_ram_gb=avail_ram_gb
        )

    def detect_gpu(self) -> GPUCapabilities:
        nvidia_present = False
        gpu_name = None
        total_vram_mb = 0.0
        free_vram_mb = 0.0
        cuda_available = False
        cuda_version = None
        compute_capability = None

        # 1. PyTorch direct query
        try:
            import torch
            if torch.cuda.is_available():
                cuda_available = True
                nvidia_present = True
                gpu_name = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                total_vram_mb = round(props.total_memory / (1024 ** 2), 2)
                compute_capability = f"{props.major}.{props.minor}"
                cuda_version = torch.version.cuda
        except Exception as e:
            logger.debug(f"PyTorch CUDA check skipped: {e}")

        # 2. Subprocess nvidia-smi query (captures driver_version and fallback GPU detection)
        driver_version = None
        try:
            cmd = ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader,nounits"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if proc.returncode == 0 and proc.stdout.strip():
                parts = [p.strip() for p in proc.stdout.strip().split(",")]
                if len(parts) >= 3:
                    if not nvidia_present:
                        nvidia_present = True
                        gpu_name = parts[0]
                        total_vram_mb = float(parts[1])
                        free_vram_mb = float(parts[2])
                    if len(parts) >= 4:
                        driver_version = parts[3]
        except Exception:
            pass

        return GPUCapabilities(
            nvidia_present=nvidia_present,
            gpu_name=gpu_name,
            total_vram_mb=total_vram_mb,
            free_vram_mb=free_vram_mb,
            cuda_available=cuda_available,
            cuda_version=cuda_version,
            compute_capability=compute_capability,
            driver_version=driver_version,
        )

    def detect_runtime(self, gpu: GPUCapabilities) -> RuntimeCapabilities:
        pytorch_cuda = False
        try:
            import torch
            pytorch_cuda = torch.cuda.is_available()
        except ImportError:
            pass

        tensorrt_available = False
        try:
            import tensorrt
            tensorrt_available = True
        except ImportError:
            pass

        onnx_cuda_provider = False
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            onnx_cuda_provider = "CUDAExecutionProvider" in providers
        except ImportError:
            pass

        fp16_supported = gpu.cuda_available or (gpu.compute_capability is not None)
        int8_available = tensorrt_available or onnx_cuda_provider

        return RuntimeCapabilities(
            pytorch_cuda=pytorch_cuda,
            tensorrt_available=tensorrt_available,
            onnx_cuda_provider=onnx_cuda_provider,
            fp16_supported=fp16_supported,
            int8_available=int8_available
        )

    def detect(self) -> HardwareProfile:
        return self.resolve_profile()

    def resolve_profile(self) -> HardwareProfile:
        cpu = self.detect_cpu()
        gpu = self.detect_gpu()
        runtime = self.detect_runtime(gpu)

        # Helper to resolve existing primary model
        def _resolve_model(pref: str = "models/detection/yolov8n.pt") -> str:
            for c in [pref, "models/detection/yolov8n.pt", "models/yolov8n.pt", "yolov8n.pt"]:
                if os.path.exists(c):
                    return c
            return "models/detection/yolov8n.pt"

        # Handle explicit override
        if self.override_profile:
            override_raw = self.override_profile.upper()
            try:
                name = HardwareProfileName[override_raw]
            except KeyError:
                name = HardwareProfileName(override_raw)
        elif gpu.nvidia_present and gpu.gpu_name and gpu.cuda_available:
            if gpu.total_vram_mb <= 4600:
                name = HardwareProfileName.LOW_VRAM_4GB
            elif gpu.total_vram_mb <= 6600:
                name = HardwareProfileName.LOW_VRAM_6GB
            else:
                # 8GB+ tier (e.g. RTX 5050 8GB)
                name = HardwareProfileName.STANDARD_8GB
        else:
            # Fallback to Dell CPU
            name = HardwareProfileName.DELL_CPU

        # Memory and stream budgets per profile (Grand Finale Section 1)
        if name in (HardwareProfileName.LOW_VRAM_4GB, HardwareProfileName.RTX3050_4GB):
            vram_budget_mb = 3200.0  # Conservative for 4GB (leaving 800MB for OS/desktop)
            ram_budget_mb = 8192.0
            max_streams = 2
            primary_det = _resolve_model()
            primary_runtime = "tensorrt_fp16" if runtime.tensorrt_available else "cuda_fp16"
        elif name in (HardwareProfileName.LOW_VRAM_6GB, HardwareProfileName.RTX3050_6GB):
            vram_budget_mb = 5000.0  # Conservative for 6GB (leaving 1GB for OS)
            ram_budget_mb = 12288.0
            max_streams = 4
            primary_det = _resolve_model()
            primary_runtime = "tensorrt_fp16" if runtime.tensorrt_available else "cuda_fp16"
        elif name in (HardwareProfileName.STANDARD_8GB, HardwareProfileName.HIGH_VRAM_NVIDIA):
            vram_budget_mb = 6800.0  # 8GB tier (e.g. RTX 5050 with 1.2GB headroom)
            ram_budget_mb = 16384.0
            max_streams = 8
            primary_det = _resolve_model()
            primary_runtime = "cuda_fp16"
        elif name == HardwareProfileName.REMOTE_GPU:
            vram_budget_mb = 24000.0
            ram_budget_mb = 32768.0
            max_streams = 16
            primary_det = _resolve_model()
            primary_runtime = "remote_grpc"
        else:
            # DELL_CPU Default Baseline
            vram_budget_mb = 0.0
            ram_budget_mb = 6144.0
            max_streams = 1
            primary_det = _resolve_model()
            primary_runtime = "cpu_fp32"

        return HardwareProfile(
            profile_name=name,
            cpu=cpu,
            gpu=gpu,
            runtime=runtime,
            vram_budget_mb=vram_budget_mb,
            ram_budget_mb=ram_budget_mb,
            max_streams_recommended=max_streams,
            primary_detection_model=primary_det,
            primary_runtime=primary_runtime
        )


# Global singleton instance
hardware_detector = HardwareDetector()


if __name__ == "__main__":
    profile = hardware_detector.resolve_profile()
    print(json.dumps(profile.to_dict(), indent=2))
