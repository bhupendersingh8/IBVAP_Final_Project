# IBVAP UNIFIED MODEL REGISTRY
**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Specification:** Grand Finale Autonomous Multi-Model AI Orchestration Architecture  
**Authoritative Source:** `ml/registry/model_registry.yaml` & `ml/registry/model_registry.py`  
**Host Target:** Dell Core i3-1115G4 (CPU-First Baseline) + Target RTX 3050 & Sovereign Cloud  

---

## 1. Executive Summary & Governance Model

The IBVAP Model Registry provides a unified catalog and governance lifecycle across **13 Expert AI Pools** and the **Edge / NVIDIA Runtime Stack**. Every model registered in the system adheres to strict deployment and safety standards:

1. **Zero-Crash Fallback Contract:** If an advanced model has status `REGISTERED_NOT_INSTALLED` on edge hardware (such as this Dell Core i3), the system dynamically routes execution to its pre-validated CPU fallback without throwing unhandled exceptions or interrupting real-time video surveillance.
2. **Explicit Verification States:**
   - `PRODUCTION / ACTIVE_BASELINE`: Model weights are locally present, benchmarked, and actively serving inference.
   - `REGISTERED / NOT INSTALLED`: Model architecture, signature, parameters, and fallback route are registered in YAML; model is staged for GPU cluster or edge deployment upon artifact staging.
   - `VALIDATED / CANARY`: Model has passed evaluation gates and is serving partial canary traffic.
   - `ROLLED_BACK`: Model superseded by newer production checkpoint.

---

## 2. Comprehensive Catalog across 13 Expert Pools

### Pool 1: Detection Expert Pool
Primary 2D object localization, bounding box regression, and edge spatial filtering.

| Model ID | Task Description | Params (M) | Latency CPU (ms) | Latency GPU (ms) | VRAM (MB) | Local Status | Fallback Target |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| `yolov8n_pretrained_baseline` | Real-time COCO-80 detection | 3.2 | 52.4 | 4.8 | 600 | **PRODUCTION** | *Self (Root)* |
| `yolov8s_detector` | High-precision small detector | 11.2 | 145.0 | 7.2 | 1800 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `yolov8x_detector` | Heavy enterprise detector | 68.2 | 720.0 | 18.5 | 6200 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `rf_detr_edge` | Real-time Focus DETR | 29.4 | 280.0 | 12.4 | 3200 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `d_fine_detector` | Fine-grained localization DETR | 22.0 | 210.0 | 9.8 | 2800 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `deim_edge_detector` | Edge-informed detection | 18.5 | 180.0 | 8.6 | 2400 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `rt_detrv3_detector` | Real-Time Transformer v3 | 32.1 | 310.0 | 11.2 | 3500 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `yolov12_attention_detector`| Attention-centric YOLOv12 | 26.0 | 260.0 | 10.4 | 3100 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `yoloe_oriented_detector` | Oriented bounding boxes (UAV) | 14.8 | 165.0 | 7.9 | 2100 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `grounding_dino_1_5_pro` | Open-vocabulary text grounding | 210.0 | 2400.0 | 45.0 | 8500 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |

---

### Pool 2: Segmentation Expert Pool
Pixel-level perimeter intrusion masks, natural obstacle segmentation, and boundary extraction.

| Model ID | Task Description | Params (M) | Latency CPU (ms) | Latency GPU (ms) | VRAM (MB) | Local Status | Fallback Target |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| `fast_sam_baseline` | Real-time CNN segmentation | 68.0 | 390.0 | 15.0 | 3800 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `mobile_sam_edge` | Ultralight edge SAM | 9.6 | 180.0 | 8.5 | 1100 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `efficient_sam` | Leveraged cross-attention SAM | 25.0 | 240.0 | 11.0 | 2600 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `sam_2_1_foundation` | Video streaming memory SAM 2.1 | 224.0 | 2800.0 | 38.0 | 9500 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `samurai_visual_tracker` | Zero-shot visual mask tracking | 224.0 | 2950.0 | 42.0 | 9800 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `seem_multimodal_segmentor` | Interactive multimodal segment | 180.0 | 2200.0 | 32.0 | 7200 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |

---

### Pool 3: Tracking Expert Pool
Continuous target state estimation, track ID persistence across occlusions, and motion modeling.

| Model ID | Task Description | Params (M) | Latency CPU (ms) | Latency GPU (ms) | VRAM (MB) | Local Status | Fallback Target |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| `bytetrack_baseline` | Low-conf association tracking | 0.0 | 3.2 | 0.8 | 50 | **PRODUCTION** | *Self (Root)* |
| `bot_sort_tracker` | Camera motion compensation + ReID | 12.0 | 45.0 | 5.4 | 1200 | `REGISTERED_NOT_INSTALLED` | `bytetrack_baseline` |
| `deep_oc_sort_tracker` | Observation-centric momentum | 15.0 | 52.0 | 6.1 | 1400 | `REGISTERED_NOT_INSTALLED` | `bytetrack_baseline` |
| `hybrid_sort_tracker` | Multi-modal association | 18.0 | 65.0 | 7.2 | 1600 | `REGISTERED_NOT_INSTALLED` | `bytetrack_baseline` |
| `impr_assoc_tracker` | High-overlap data association | 8.5 | 28.0 | 4.2 | 900 | `REGISTERED_NOT_INSTALLED` | `bytetrack_baseline` |
| `motrv3_transformer_tracker`| End-to-end MOT transformer | 48.0 | 550.0 | 18.0 | 4800 | `REGISTERED_NOT_INSTALLED` | `bytetrack_baseline` |
| `memotr_long_term_tracker` | Multi-day memory MOT transformer | 64.0 | 680.0 | 22.0 | 5600 | `REGISTERED_NOT_INSTALLED` | `bytetrack_baseline` |

---

### Pool 4: Face & Identity Expert Pool
4-State Identity Verification (`UNKNOWN`, `UNVERIFIED`, `AUTHORIZED`, `UNAUTHORIZED`).

| Model ID | Task Description | Params (M) | Latency CPU (ms) | Latency GPU (ms) | VRAM (MB) | Local Status | Fallback Target |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| `haar_face_baseline` | Frontal Haar Cascade face detector | 0.1 | 18.5 | 2.1 | 20 | **PRODUCTION** | *Self (Root)* |
| `adaface_ir100` | Quality-adaptive margin ArcFace | 65.0 | 310.0 | 12.0 | 2400 | `REGISTERED_NOT_INSTALLED` | `haar_face_baseline` |
| `transface_transformer` | Transformer face representation | 85.0 | 450.0 | 14.5 | 3200 | `REGISTERED_NOT_INSTALLED` | `haar_face_baseline` |
| `magface_quality_recognizer`| Magnitude-aware quality face | 54.0 | 280.0 | 10.5 | 2200 | `REGISTERED_NOT_INSTALLED` | `haar_face_baseline` |
| `kprpe_face_verifier` | Keypoint relative pose embedding | 42.0 | 220.0 | 9.0 | 1800 | `REGISTERED_NOT_INSTALLED` | `haar_face_baseline` |
| `partial_face_recognizer` | Balaclava/mask face verifier | 48.0 | 250.0 | 9.5 | 2000 | `REGISTERED_NOT_INSTALLED` | `haar_face_baseline` |
| `xcloud_cross_pose_identity`| Multi-view PTZ cross-pose identity | 110.0 | 620.0 | 16.0 | 4500 | `REGISTERED_NOT_INSTALLED` | `haar_face_baseline` |
| `insightface_antelopev2` | SOTA 512D ArcFace pipeline | 75.0 | 340.0 | 11.8 | 2800 | `REGISTERED_NOT_INSTALLED` | `haar_face_baseline` |

---

### Pool 5: Person Re-ID Expert Pool
Cross-camera appearance matching across non-overlapping surveillance nodes.

| Model ID | Task Description | Params (M) | Latency CPU (ms) | Latency GPU (ms) | VRAM (MB) | Local Status | Fallback Target |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| `spatial_temporal_reid_baseline`| Spatial topology & clothing heuristics| 0.0 | 1.5 | 0.3 | 30 | **PRODUCTION** | *Self (Root)* |
| `trans_reid_vit` | Vision Transformer Re-ID | 86.0 | 480.0 | 14.0 | 3400 | `REGISTERED_NOT_INSTALLED` | `spatial_temporal_reid_baseline` |
| `clip_reid_multimodal` | Language-guided text Re-ID | 150.0 | 720.0 | 19.0 | 4200 | `REGISTERED_NOT_INSTALLED` | `spatial_temporal_reid_baseline` |
| `kpr_part_reid` | Keypoint-guided part Re-ID | 52.0 | 290.0 | 10.2 | 2300 | `REGISTERED_NOT_INSTALLED` | `spatial_temporal_reid_baseline` |
| `person_mae_reid` | Masked autoencoder Re-ID | 105.0 | 650.0 | 17.5 | 4600 | `REGISTERED_NOT_INSTALLED` | `spatial_temporal_reid_baseline` |
| `fast_reid_baseline` | Real-time ResNet50-IBN Re-ID | 25.0 | 160.0 | 6.8 | 1800 | `REGISTERED_NOT_INSTALLED` | `spatial_temporal_reid_baseline` |
| `solider_semantic_reid` | Semantic attribute-oriented Re-ID | 88.0 | 510.0 | 14.8 | 3600 | `REGISTERED_NOT_INSTALLED` | `spatial_temporal_reid_baseline` |

---

### Pool 6: Vision-Language Models (VLM) Expert Pool
Tactical multi-modal scene reasoning, natural language threat synthesis, and incident reporting.

| Model ID | Task Description | Params (M) | Latency CPU (ms) | Latency GPU (ms) | VRAM (MB) | Local Status | Fallback Target |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| `rule_based_copilot_baseline` | Deterministic tactical copilot | 0.0 | 8.0 | 1.0 | 100 | **PRODUCTION** | *Self (Root)* |
| `florence_2_base` | Microsoft multi-task vision VLM | 230.0 | 1400.0 | 35.0 | 3800 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `paligemma_2_3b` | Google DeepMind lightweight VLM | 3000.0 | 4800.0 | 85.0 | 7500 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `qwen2_5_vl_7b` | Frontier edge multimodal VLM | 7000.0 | 12000.0 | 140.0 | 14000 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `qwen2_5_vl_72b` | Sovereign HQ flagship VLM | 72000.0 | 120000.0 | 950.0 | 85000 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `intern_vl_2_5` | High-res dynamic patch VLM | 8000.0 | 15000.0 | 165.0 | 16000 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `llava_onevision_7b` | Unified image/video understanding | 7000.0 | 13500.0 | 150.0 | 14500 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `videollama_3` | Multi-minute conversational video | 7000.0 | 14000.0 | 175.0 | 15000 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `nvila_nvidia_agent` | NVIDIA embodied spatial agent | 8000.0 | 16000.0 | 180.0 | 17000 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `molmo_7b` | AllenAI 2D pointing & grounding | 7200.0 | 13800.0 | 155.0 | 15000 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `pixtral_12b` | Mistral arbitrary-aspect VLM | 12000.0 | 22000.0 | 210.0 | 24000 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `llama_3_2_vision_11b` | Meta multimodal reasoning model | 11000.0 | 19500.0 | 190.0 | 22000 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |

---

### Pool 7: Video Understanding Expert Pool
Temporal activity comprehension, continuous CCTV video representation, and motion dynamics.

| Model ID | Task Description | Params (M) | Latency CPU (ms) | Latency GPU (ms) | VRAM (MB) | Local Status | Fallback Target |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| `videomae_v2_vit_b` | Self-supervised masked video | 86.0 | 850.0 | 28.0 | 4200 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `intern_video_2` | Frontier video foundation model | 1000.0 | 5200.0 | 88.0 | 12000 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `video_mamba_ssm` | Linear-time State Space Model | 45.0 | 320.0 | 12.0 | 2800 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `long_va_video` | Long-context multi-hour video | 7000.0 | 14000.0 | 160.0 | 15000 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |
| `tarsier_surveillance` | Night patrol surveillance reasoner | 7000.0 | 13000.0 | 145.0 | 14000 | `REGISTERED_NOT_INSTALLED` | `rule_based_copilot_baseline` |

---

### Pool 8: Image / Low-Light / Weather Restoration Expert Pool
Enhancing degraded border feeds under zero-lux, dense fog, sandstorms, and monsoon rains.

| Model ID | Task Description | Params (M) | Latency CPU (ms) | Latency GPU (ms) | VRAM (MB) | Local Status | Fallback Target |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| `clahe_gamma_restoration_baseline` | Adaptive CLAHE + gamma booster | 0.0 | 4.5 | 0.6 | 10 | **PRODUCTION** | *Self (Root)* |
| `zero_dce_plus_plus` | Zero-reference deep curve restorer | 0.08 | 12.0 | 1.8 | 150 | `REGISTERED_NOT_INSTALLED` | `clahe_gamma_restoration_baseline` |
| `retinexformer_enhancer` | Transformer Retinex low-light | 1.6 | 140.0 | 8.2 | 950 | `REGISTERED_NOT_INSTALLED` | `clahe_gamma_restoration_baseline` |
| `sci_self_calibrated_enhancer` | Self-calibrated illumination | 0.12 | 15.0 | 2.2 | 180 | `REGISTERED_NOT_INSTALLED` | `clahe_gamma_restoration_baseline` |
| `mirnet_v2_restorer` | Denoising, deblurring & contrast | 5.9 | 280.0 | 11.5 | 1600 | `REGISTERED_NOT_INSTALLED` | `clahe_gamma_restoration_baseline` |
| `dehaze_former_fog` | Heavy fog and smoke dehazer | 2.8 | 190.0 | 9.4 | 1200 | `REGISTERED_NOT_INSTALLED` | `clahe_gamma_restoration_baseline` |
| `diff_ll_diffusion_restorer`| Conditional diffusion night enhancer | 28.0 | 3400.0 | 75.0 | 5200 | `REGISTERED_NOT_INSTALLED` | `clahe_gamma_restoration_baseline` |
| `thermal_gan_synthetic` | FLIR LWIR Thermal-to-RGB synthesis | 14.0 | 260.0 | 10.8 | 2200 | `REGISTERED_NOT_INSTALLED` | `clahe_gamma_restoration_baseline` |
| `mamba_ir_restorer` | Selective state space rain removal | 8.5 | 175.0 | 7.8 | 1800 | `REGISTERED_NOT_INSTALLED` | `clahe_gamma_restoration_baseline` |

---

### Pool 9: Pose / Behavior / Action Expert Pool
Skeletal body posture, perimeter climbing, crawling, weapon aiming, and animal behavior.

| Model ID | Task Description | Params (M) | Latency CPU (ms) | Latency GPU (ms) | VRAM (MB) | Local Status | Fallback Target |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| `yolov8n_pose_baseline` | 17-keypoint skeleton detector | 3.3 | 58.0 | 5.2 | 650 | **PRODUCTION** | *Self (Root)* |
| `rtmpose_m_realtime` | SOTA real-time multi-person pose | 13.5 | 110.0 | 4.8 | 1500 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pose_baseline` |
| `rtmpose_s_edge` | Ultralight edge pose estimator | 4.8 | 45.0 | 2.9 | 600 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pose_baseline` |
| `vitpose_plus_plus` | Vision Transformer multi-task pose | 307.0 | 2600.0 | 32.0 | 8500 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pose_baseline` |
| `sapiens_meta_foundation` | Meta 1B human foundation model | 1000.0 | 8500.0 | 78.0 | 18000 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pose_baseline` |
| `mmpose_behavior_suite` | Climbing, crawling & prone posture | 28.0 | 210.0 | 8.5 | 2600 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pose_baseline` |
| `pose_anything_zeroshot` | Zero-shot open-domain pose | 120.0 | 950.0 | 21.0 | 4800 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pose_baseline` |
| `animal_kingdom_behavior` | Wildlife vs livestock discrimination | 35.0 | 230.0 | 9.8 | 2400 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pose_baseline` |
| `ctr_gcn_action_recognizer` | Channel-topology graph action net | 1.4 | 65.0 | 3.5 | 850 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pose_baseline` |

---

### Pool 10: Anomaly Detection Expert Pool
Unsupervised novelty detection, out-of-distribution path departures, and fence tampering.

| Model ID | Task Description | Params (M) | Latency CPU (ms) | Latency GPU (ms) | VRAM (MB) | Local Status | Fallback Target |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| `heuristic_spatial_anomaly_baseline`| Loitering, wrong-way & zone rules | 0.0 | 2.1 | 0.4 | 20 | **PRODUCTION** | *Self (Root)* |
| `anomalib_patchcore` | Memory-bank neighborhood embedding | 24.0 | 240.0 | 8.8 | 2200 | `REGISTERED_NOT_INSTALLED` | `heuristic_spatial_anomaly_baseline` |
| `mnad_normality_model` | Video normality learning network | 16.0 | 180.0 | 7.2 | 1800 | `REGISTERED_NOT_INSTALLED` | `heuristic_spatial_anomaly_baseline` |
| `staeformer_anomaly_transformer` | Spatio-temporal crowd autoencoder | 48.0 | 450.0 | 14.5 | 3800 | `REGISTERED_NOT_INSTALLED` | `heuristic_spatial_anomaly_baseline` |
| `pyod_anomaly_ensemble` | Speed and trajectory outlier suite | 0.0 | 18.0 | 3.5 | 120 | `REGISTERED_NOT_INSTALLED` | `heuristic_spatial_anomaly_baseline` |
| `mem_ae_memory_autoencoder` | Memory-augmented deep autoencoder | 12.0 | 150.0 | 6.2 | 1500 | `REGISTERED_NOT_INSTALLED` | `heuristic_spatial_anomaly_baseline` |
| `ubnormal_atypical_border` | Synthetic border breach benchmark | 32.0 | 290.0 | 10.4 | 2600 | `REGISTERED_NOT_INSTALLED` | `heuristic_spatial_anomaly_baseline` |

---

### Pool 11: Foundation Models Expert Pool
Pretrained visual representations, open-vocabulary alignment, and monocular 3D geometry.

| Model ID | Task Description | Params (M) | Latency CPU (ms) | Latency GPU (ms) | VRAM (MB) | Local Status | Fallback Target |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| `dinov2_vit_b` | Self-supervised visual features | 86.0 | 460.0 | 13.5 | 3200 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `dinov3_nextgen_foundation`| Advanced linear-attention features | 300.0 | 2400.0 | 36.0 | 8800 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `clip_vit_b32` | Zero-shot multimodal text retrieval | 151.0 | 620.0 | 16.0 | 3600 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `siglip_2_so400m` | Multilingual sigmoid loss vision | 400.0 | 2900.0 | 44.0 | 9200 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `depth_anything_v2_vit_s` | Monocular metric depth estimation | 24.8 | 180.0 | 6.5 | 1800 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `vggt_visual_geometry_grounded`| Multi-view 3D scene geometry | 180.0 | 1800.0 | 28.0 | 6800 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |
| `moge_monocular_geometry` | Single-frame surface normal & depth | 65.0 | 410.0 | 12.8 | 2800 | `REGISTERED_NOT_INSTALLED` | `yolov8n_pretrained_baseline` |

---

### Pool 12: ANPR / Vehicle Intelligence Expert Pool
Automatic Number Plate Recognition, High Security Registration Plates (HSRP), and vehicle classification.

| Model ID | Task Description | Params (M) | Latency CPU (ms) | Latency GPU (ms) | VRAM (MB) | Local Status | Fallback Target |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| `fast_plate_anpr_baseline` | Real-time Indian HSRP plate reader | 1.2 | 28.0 | 3.5 | 150 | **PRODUCTION** | *Self (Root)* |
| `vehicle_attr_net` | Make, model, color & chassis classifier | 18.0 | 140.0 | 5.8 | 1600 | `REGISTERED_NOT_INSTALLED` | `fast_plate_anpr_baseline` |
| `corner_plate_detector` | Skewed 4-corner perspective plate | 4.5 | 48.0 | 2.8 | 600 | `REGISTERED_NOT_INSTALLED` | `fast_plate_anpr_baseline` |
| `night_plate_enhancer` | Headlamp glare suppressor OCR | 2.1 | 32.0 | 2.1 | 300 | `REGISTERED_NOT_INSTALLED` | `fast_plate_anpr_baseline` |

---

### Pool 13: Indian AI / Indic Language Layer
Sovereign intelligence, vernacular language translation, and multi-lingual tactical broadcast.

| Model ID | Task Description | Params (M) | Latency CPU (ms) | Latency GPU (ms) | VRAM (MB) | Local Status | Fallback Target |
|:---|:---|:---:|:---:|:---:|:---:|:---|:---|
| `local_indic_regex_transcriber_baseline` | Multi-language tactical alert generator | 0.0 | 1.2 | 0.2 | 15 | **PRODUCTION** | *Self (Root)* |
| `krutrim_sovereign_llm` | Sovereign multimodal foundational AI | 22000.0 | 38000.0 | 420.0 | 48000 | `REGISTERED_NOT_INSTALLED` | `local_indic_regex_transcriber_baseline` |
| `bhashini_national_api` | MeitY 22-language translation service | 1000.0 | 1500.0 | 80.0 | 4000 | `REGISTERED_NOT_INSTALLED` | `local_indic_regex_transcriber_baseline` |
| `ai4bharat_indic_trans2` | Open-source Indic translation model | 1000.0 | 1800.0 | 65.0 | 4500 | `REGISTERED_NOT_INSTALLED` | `local_indic_regex_transcriber_baseline` |
| `ai4bharat_indic_bert` | Multilingual Indic intent parser | 110.0 | 120.0 | 6.2 | 850 | `REGISTERED_NOT_INSTALLED` | `local_indic_regex_transcriber_baseline` |
| `indic_language_embeddings`| Cross-lingual tactical vector space | 25.0 | 35.0 | 3.1 | 400 | `REGISTERED_NOT_INSTALLED` | `local_indic_regex_transcriber_baseline` |

---

### Edge & NVIDIA AI Runtime Stack

| Framework / Engine | Purpose | Dell Core i3 Status | Target RTX 3050 Status | Enterprise Cluster |
|:---|:---|:---:|:---:|:---:|
| `onnx_runtime` | Default cross-platform engine | **ACTIVE (CPU)** | ACTIVE (CUDA EP) | ACTIVE (TensorRT EP) |
| `openvino_2025` | Intel Tiger Lake UHD GPU acceleration | STANDBY | N/A | ACTIVE (Intel Xeon) |
| `executorch` | PyTorch on-device mobile runtime | STANDBY | STANDBY | N/A |
| `llama_cpp` | Quantized 4-bit CPU GGUF LLM runner | STANDBY | ACTIVE (cuBLAS) | N/A |
| `nvidia_cuda_12` | NVIDIA CUDA compute runtime | N/A (No GPU) | TARGET READY | ACTIVE |
| `nvidia_tensorrt_10` | TensorRT FP16/INT8 kernel optimizer | N/A (No GPU) | TARGET READY | ACTIVE |
| `nvidia_tensorrt_llm` | In-flight paged attention VLM engine | N/A (No GPU) | OPTIONAL (7B) | ACTIVE (72B) |
| `deepstream_7_0` | Multi-stream intelligent video pipeline | N/A | TARGET READY | ACTIVE (64+ Streams) |
| `triton_server` | Scalable dynamic batching server | STANDBY | TARGET READY | ACTIVE |

---

## 3. Verification & Governance Commands

### Querying Model Registry from Python
```python
from ml.registry.model_registry import ModelRegistry, ModelStatus

reg = ModelRegistry()
summary = reg.get_registry_summary()
print(f"Total models registered: {summary['total_models']}")
print(f"Active baseline: {summary['active_production_id']}")

# Query fallback route safely
model, is_fallback = reg.resolve_model("qwen2_5_vl_7b")
print(f"Requested: qwen2_5_vl_7b -> Resolved: {model.model_id} (Is Fallback: {is_fallback})")
```

### Promoting a Model to Production
```python
reg.promote_model(
    model_id="border_yolo_v2",
    target_status=ModelStatus.PRODUCTION,
    approved_by="COMMANDING_OFFICER",
    reason="Passes precision gate on low-light border evaluation set"
)
```
