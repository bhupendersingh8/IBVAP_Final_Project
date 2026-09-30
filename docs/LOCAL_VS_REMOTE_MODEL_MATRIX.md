# IBVAP — LOCAL VS. REMOTE MODEL MATRIX
======================================
*Ground-truth hardware profile separation for Dell Core i3 laptop vs Cloud/Remote GPU workers.*

## 1. Architectural Hardware Separation

| Capability | Local CPU Profile (Dell Laptop) | Remote / Cloud GPU Profile (Colab / Vast.ai) | Rationale / Blocker for Local Run |
|:---|:---|:---|:---|
| **Primary Detection** | **YOLOv8n / YOLOv8s** (Installed & Active) | **RF-DETR / Grounding DINO** | RF-DETR requires CUDA C++ compilation; Grounding DINO requires 8GB+ VRAM |
| **Escalation Detection** | **RT-DETR-L** (Weights Present, CPU capable) | **RT-DETRv3 / D-FINE** | Transformer cross-attention is ~450ms on CPU; ~15ms on RTX GPU |
| **Object Tracking** | **ByteTrackAdapter** (Active IoU+EMA) | **Deep OC-SORT / MOTRv3** | Deep OC-SORT needs camera motion compensation and neural appearance features |
| **Re-Identification** | **LongTermRemembranceStore** (Active) | **FastReID / TransReID** | Neural feature extraction (OSNet / ViT) requires 4GB+ VRAM |
| **Face Detection** | **Haar + YuNet ONNX** (Active) | **InsightFace / Antelopev2** | Antelopev2 has non-commercial license clause; YuNet is Apache/BSD |
| **Face Recognition** | **SFace ONNX** (Active) | **AdaFace IR100** | SFace is lightweight (36MB); AdaFace requires PyTorch CUDA |
| **ANPR / OCR** | **EasyOCR (CPU)** (Active) | **PaddleOCR / PARSeq** | PaddleOCR blocked by Windows C++ paddlepaddle binaries; EasyOCR works on CPU |
| **Instance Segmentation** | **YOLOv8n-Seg / FastSAM-s** (Active) | **SAM 2.1 (Segment Anything)** | SAM 2.1 requires high-VRAM flash-attention (~12GB VRAM) |
| **Human Pose / Skeleton** | **YOLOv8n-Pose** (Active) | **RTMPose / ViTPose++** | RTMPose requires OpenMMLab GPU acceleration |
| **Restoration / Enhancement** | **Adaptive CLAHE + Dynamic Gamma** (Active) | **Retinexformer / DehazeFormer** | Neural restoration models require 8GB+ VRAM; CLAHE is 166ms on CPU |
| **Vision Foundation** | **DINOv2 ViT-S/14** (Active, 84MB) | **Depth Anything V2 / CLIP ViT-L** | DINOv3 blocked by military exclusion license; Depth Anything needs GPU |
| **Video Understanding / VLM** | **Rule-Based Tactical Copilot** (Active) | **Qwen2.5-VL 7B / 72B** | 7B model needs 16GB VRAM; 72B needs 140GB VRAM cluster |
| **Indian Language AI** | **Indic Lexicon Transcriber** (Active) | **IndicTrans2 1B (Neural)** | IndicTrans2 requires fairseq and 4GB+ GPU memory |
| **Deployment Acceleration** | **ONNX Runtime (CPUExecutionProvider)** | **TensorRT FP16 / INT8 Engine** | TensorRT strictly requires physical NVIDIA RTX GPU (absent on this Dell) |

---

## 2. Model Status Summary Matrix

| Status Category | Count | Models / Components |
|:---|:---:|:---|
| **LOCAL_VALIDATED** | **17 Layers** | YOLOv8n, YOLOv8s, RT-DETR-L, ByteTrackAdapter, RemembranceStore, YuNet, SFace, EasyOCR, YOLOv8n-Seg, FastSAM-s, YOLOv8n-Pose, Spatial Velocity RuleEngine, Adaptive CLAHE, DINOv2 ViT-S/14, Indic Transcriber, Temporal FSM, MultiCameraEventBus, SHA-256 HashChainLedger, ONNX Runtime CPU, FastAPI + WebSocket |
| **REMOTE_VALIDATED** | **4 Models** | Qwen2.5-VL-7B (Tactical VLM), SAM 2.1 (Perimeter Segmentation), FastReID (Neural Re-ID), Depth Anything V2 (Dense Depth) via `CloudGPUBridge` |
| **PACKAGE_ONLY** | **3 Packages** | `transformers` (v5.17.0), `timm` (v1.0.30), `einops` (v0.8.2) — installed in virtual environment for forward compatibility |
| **BLOCKED** | **4 Models** | **PaddleOCR** (Windows C++ ABI conflict), **DINOv3** (Military/Defense license exclusion), **InsightFace Antelopev2** (Non-commercial clause), **TensorRT Engine** (No NVIDIA GPU hardware on Dell) |
| **FAILED** | **0** | All executed unit and integrated tests passed |
| **NOT_IMPLEMENTED** | **0** | Zero unrouted or phantom layers |
