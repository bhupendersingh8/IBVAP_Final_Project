# IBVAP — REMOTE GPU MODEL EXECUTION RUNBOOK
============================================
*Reproducible guide for executing high-VRAM models on Target B (RTX 3050) and Target C (Remote Google Colab / Vast.ai).*

## 1. Hardware Execution Architecture
IBVAP decouples inference across three tier targets:

- **TARGET A (Dell Laptop Core i3):** Executes real-time baseline models (YOLOv8n, ByteTrack, SFace, YuNet, CLAHE, FSM, Hash Chain) at zero external cost.
- **TARGET B (RTX 3050 4GB/6GB Edge Node):** Executes escalation models (YOLOv8x, RT-DETR-L, FastSAM-s, DINOv2, OSNet, OpenVINO) with TensorRT FP16 acceleration.
- **TARGET C (Remote GPU Worker - Colab T4 / Vast.ai RTX 4090):** Executes heavy vision-language and foundation models (Qwen2.5-VL-7B, SAM 2.1, FastReID, Depth Anything V2).

## 2. Remote Worker Deployment Instructions

### Step 1: Launch Free Google Colab Worker
1. Open [Google Colab](https://colab.research.google.com).
2. Select Runtime $\to$ Change Runtime Type $\to$ **T4 GPU** (15 GB VRAM free).
3. Upload or paste [`scripts/colab_free_gpu_worker.py`](../scripts/colab_free_gpu_worker.py).
4. Run the worker cell:

```bash
!pip install fastapi uvicorn pyngrok torch torchvision transformers timm einops
!python colab_free_gpu_worker.py --port 8080 --tunnel ngrok
```

5. The worker will output an HTTPS endpoint URL (e.g. `https://xyz.ngrok-free.app`).

### Step 2: Configure Local IBVAP Bridge
Set the remote endpoint in your local environment or configuration:

```powershell
$env:IBVAP_REMOTE_GPU_URL = "https://xyz.ngrok-free.app"
```

The local `CloudGPUBridge` in `services/orchestrator/cloud_gpu_bridge.py` will automatically forward VLM and segmentation requests to the remote worker while keeping the local CPU pipeline running without interruption.

## 3. Remote Models Dispatch Directory

| Model ID | Remote Task | Required VRAM | Colab Script Flag | Fallback if Offline |
|:---|:---|:---:|:---|:---|
| `qwen2_5_vl_7b` | Visual Incident Explanation | 16 GB | `--model qwen2_5_vl_7b` | Deterministic Tactical Copilot |
| `sam_2_1_foundation` | Perimeter Fence Cut Segmentation | 12 GB | `--model sam_2_1` | YOLOv8n-Seg (Local) |
| `fast_reid_baseline` | High-Precision Appearance Re-ID | 4 GB | `--model fast_reid` | OSNet-x0.25 (Local) |
| `depth_anything_v2_vit_s` | Metric Depth & Intruder Proximity | 4 GB | `--model depth_anything` | Camera Calibration Heuristic |
| `florence_2_base` | Dense Captioning & Bounding | 4 GB | `--model florence_2` | YOLOv8 Detection Classes |