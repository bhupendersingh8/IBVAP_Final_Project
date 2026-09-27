# IBVAP — GPU Runtime Environment Specification
**Intelligent Border Video Analytics Platform**  
*Document Version: 1.0.0 — Phase 2 Hardware Enablement*

---

## 1. Hardware Specification

Extracted directly via `nvidia-smi` and PyTorch hardware discovery:

| Hardware Component | Specification | Diagnostic / Capability |
| :--- | :--- | :--- |
| **GPU Name** | **NVIDIA GeForce RTX 3050 Laptop GPU** | Active Mobile Discrete GPU |
| **GPU Architecture** | NVIDIA Ampere (GA107) | 2nd Gen RT Cores, 3rd Gen Tensor Cores |
| **Compute Capability** | **8.6** | Supports FP32, TF32, FP16, INT8 |
| **Total VRAM** | **4096.0 MB (4.0 GB GDDR6)** | Bus width: 128-bit |
| **NVIDIA Driver Version** | **591.91** | Driver level supports up to CUDA 13.1 |
| **Power State & TGP** | **P0 State**, 14W idle to 43W load / 75W Max TGP | Active power management |
| **GPU Temperature** | 49°C idle, 58°C–67°C sustained benchmark load | Thermal headroom maintained |
| **Host CPU** | AMD64 / 6 Physical Cores, 12 Logical Processors | Host pipeline decode |
| **Host Memory** | 15.27 GB System RAM | Operational |

---

## 2. Software & Package Matrix

To maintain isolation and guarantee zero regressions on the existing system, a dedicated clean virtual environment was instantiated at `.venv_gpu/`:

| Component / Layer | Environment Version | Verified Source / Wheel |
| :--- | :--- | :--- |
| **Host OS** | Windows 11 (10.0.26200-SP0) | Native Windows Environment |
| **Python Runtime** | **Python 3.11.9 (64-bit)** | Isolated at `.venv_gpu\Scripts\python.exe` |
| **PyTorch Framework** | **`torch 2.5.1+cu121`** | PyTorch official CUDA 12.1 distribution wheel |
| **TorchVision** | **`torchvision 0.20.1+cu121`** | PyTorch official CUDA 12.1 distribution wheel |
| **CUDA Runtime** | **CUDA 12.1** (`torch.version.cuda: 12.1`) | Driver 591.91 forward-compatible |
| **NVIDIA TensorRT** | **`tensorrt 11.2.1.2`** | NVIDIA TensorRT 11.x Windows wheel |
| **TensorRT CUDA Libs** | **`tensorrt-cu12-libs 11.2.1.2`** | Native dynamic CUDA 12 execution runtime |
| **TensorRT Bindings** | **`tensorrt-cu12-bindings 11.2.1.2`** | Python 3.11 C++ PyBind layer |
| **Ultralytics YOLO** | **`ultralytics 8.4.142`** | Detection, tracking, and engine runner |
| **ONNX Runtime** | **`onnx 1.22.0` / `onnxruntime-gpu 1.29.0`** | Opset 18 Intermediate Representation |
| **OpenCV** | **`opencv-python 5.0.0.93`** | Low-latency stream ingestion |

---

## 3. Environment Verification Commands & Outputs

### A. Python CUDA Verification
Command:
```powershell
.\.venv_gpu\Scripts\python.exe -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0)); print('Compute:', torch.cuda.get_device_capability(0)); print('CUDA Version:', torch.version.cuda)"
```
Output:
```
CUDA Available: True
Device: NVIDIA GeForce RTX 3050 Laptop GPU
Compute: (8, 6)
CUDA Version: 12.1
```

### B. TensorRT Module Verification
Command:
```powershell
.\.venv_gpu\Scripts\python.exe -c "import tensorrt as trt; print('TensorRT Version:', trt.__version__)"
```
Output:
```
TensorRT Version: 11.2.1.2
```

### C. Live GPU Telemetry Check (`nvidia-smi`)
```
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 591.91                 Driver Version: 591.91         CUDA Version: 13.1     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                  Driver-Model | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 3050 ...  WDDM  |   00000000:01:00.0 Off |                  N/A |
| N/A   58C    P0             26W /   75W |     355MiB /   4096MiB |     27%      Default |
+-----------------------------------------+------------------------+----------------------+
```
