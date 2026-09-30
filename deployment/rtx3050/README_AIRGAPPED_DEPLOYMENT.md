# IBVAP — Air-Gapped Deployment Guide for NVIDIA RTX 3050 (Windows 11)

**Platform**: Intelligent Border Video Analytics Platform (IBVAP)  
**SIH Problem Statement**: 26187 | Ministry of Home Affairs (MHA)  
**Target Hardware**: Field Patrol Laptop with NVIDIA GeForce RTX 3050 (4GB / 6GB VRAM)  
**Operating System**: Windows 11 Home / Pro (64-bit)  
**Security Posture**: 100% Air-Gapped, Zero-Cloud, Sovereign Field Deployment  

---

## 1. System Requirements & Hardware Specifications

| Component | Minimum Specification | Recommended Specification |
|---|---|---|
| **Host Machine** | Dell G15 / Lenovo Legion / ASUS TUF | Tactical Ruggedized Mobile Workstation |
| **Processor** | Intel Core i5 (11th Gen) / AMD Ryzen 5 | Intel Core i7 (12th/13th Gen) / AMD Ryzen 7 |
| **GPU** | NVIDIA GeForce RTX 3050 Laptop (4GB) | NVIDIA GeForce RTX 3050 / 4060 (6GB / 8GB) |
| **NVIDIA Driver** | >= 528.33 (CUDA 12.0+) | >= 550.54 (CUDA 12.4 compatible) |
| **System RAM** | 16 GB DDR4 / DDR5 | 32 GB DDR5 |
| **Storage** | 20 GB free SSD space | 50 GB free NVMe M.2 SSD |
| **Network** | Air-gapped (Local Ethernet for IP-CCTV) | Gigabit Isolated Tactical LAN |

---

## 2. Stage A: Preparation on Internet-Connected Workstation

Perform these steps once on an internet-connected workstation to build the transfer media (USB drive):

1. **Clone or Copy IBVAP Repository**:
   Ensure the latest checkpoint (`d75abfb` or newer) is present.

2. **Download All Offline Wheels**:
   Open PowerShell and execute:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\deployment\rtx3050\download_rtx3050_wheels.ps1 -OutputDir "D:\IBVAP_USB\offline_wheels_rtx3050"
   ```
   This downloads:
   - PyTorch 2.4.1+cu124 with CUDA 12.4 runtime
   - Torchvision with NVDEC/NVENC support
   - ONNX Runtime GPU with CUDA 12.x provider
   - PaddleOCR, OpenCV, FastAPI, and scientific libraries

3. **Verify Model Weights**:
   Ensure pre-trained model weights are present in `models/`:
   - `models/detection/yolo26n.pt`
   - `yolov8n.pt`
   - `yolov8s.pt`

4. **Prepare Frontend Bundle**:
   Build the production frontend to avoid requiring Node.js on the field laptop:
   ```powershell
   cd apps\frontend
   npm run build
   cd ..\..
   ```
   *(The compiled bundle resides in `apps/frontend/dist/`)*.

---

## 3. Stage B: Installation on Air-Gapped Field Laptop

On the air-gapped patrol laptop:

1. **Insert USB Drive and Copy Files**:
   Copy the `IBVAP_Final_Project` directory to `C:\IBVAP`.

2. **Execute Automated Environment Setup**:
   Open PowerShell as Administrator:
   ```powershell
   Set-Location C:\IBVAP
   powershell -ExecutionPolicy Bypass -File .\deployment\rtx3050\setup_rtx3050_env.ps1 -Offline -WheelDir ".\offline_wheels_rtx3050"
   ```
   *The script will:*
   - Audit the NVIDIA driver version via `nvidia-smi`
   - Initialize Python virtual environment `venv_rtx`
   - Install all packages from the offline wheel cache with zero internet access
   - Run an inline PyTorch CUDA tensor verification check
   - Write optimized configuration to `configs/hardware/.env.rtx3050`

---

## 4. Stage C: Validation & Stress Testing

Before connecting live border surveillance cameras, execute the automated compatibility auditor:

```powershell
.\venv_rtx\Scripts\python.exe .\deployment\rtx3050\test_rtx3050_compatibility.py
```

Expected output:
```
==========================================================
 IBVAP NVIDIA RTX 3050 Compatibility & Stress Audit       
==========================================================
 [PASS] Hardware Profile Auto-Discovery: {'assigned_profile': 'RTX3050_4GB', ...}
 [PASS] CUDA & FP16 Environment Audit: {'cuda_available': True, 'device_name': 'NVIDIA GeForce RTX 3050 Laptop GPU', ...}
 [PASS] 4-Stream Pipeline Simulation: {'streams_tested': 4, 'average_latency_ms': 12.4, ...}
 [PASS] OOM & Graceful Fallback Resilience: {'fallback_functional': True, 'zero_crash_contract': 'VERIFIED'}
==========================================================
 Audit Complete: 4/4 Checks PASSED
==========================================================
```

---

## 5. Stage D: Optional TensorRT Engine Optimization

To maximize FPS and achieve sub-8ms latency per 1080p stream:

```powershell
.\venv_rtx\Scripts\python.exe .\deployment\rtx3050\export_tensorrt_engines.py --model yolov8s.pt --output-dir models/optimized
```

This builds an optimized `.engine` plan file with:
- FP16 half precision enabled
- Maximum workspace capped at 1024 MB (protecting the 4GB VRAM budget)
- Fixed batching tailored to RTX 3050 SM86 architecture

---

## 6. Stage E: 1-Click Operational Startup

Start the platform using either:

1. **Double-click** `start_ibvap_rtx3050.bat` from File Explorer.
2. **Or run via PowerShell**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\start_ibvap_rtx3050.ps1 -Profile RTX3050_4GB -Streams 4
   ```

The launcher automatically:
- Starts MediaMTX RTSP stream ingestion
- Starts the FastAPI accelerated inference backend on port 8000
- Opens the Tactical Operations Dashboard in the browser at `http://localhost:5173`

---

## 7. Zero-Crash Fallback Contracts

1. **NVIDIA Driver Missing / Corrupt**:
   If the GPU driver is unavailable, IBVAP automatically detects the missing driver and defaults to `DELL_CPU` / `cpu_fp32` mode without throwing an unhandled exception.
2. **VRAM Exhaustion (OOM)**:
   If 4 simultaneous 4K streams saturate the 4GB VRAM, the pipeline catches `torch.cuda.OutOfMemoryError`, purges CUDA cache, and directs pending frames through the CPU fallback worker pool.
3. **Evidence Integrity**:
   All alert snapshots and video clips generated under GPU mode maintain identical Section 65B Indian Evidence Act SHA-256 hash chains verified via `POST /api/v1/evidence/verify`.
