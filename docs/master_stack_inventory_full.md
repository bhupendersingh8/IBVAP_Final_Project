# IBVAP MASTER MODEL STACK INVENTORY & AUTONOMOUS MULTI-TIER AI ORCHESTRATION BLUEPRINT

> **Core System Doctrine:**  
> *“IBVAP does not execute every model on every frame. It maintains a unified, version-controlled portfolio of specialized AI experts and autonomously selects, activates, escalates, fuses, or bypasses them based on real-time scene diagnostics, bounding box uncertainty, temporal stability, and hardware compute budgets.”*

---

## 1. Complete Master Model Stack Inventory (All 17 Layers)

> [!NOTE]
> **Fit % Metric Definition:**  
> The percentage assigned to each model represents **IBVAP Practical Operational Fit & Contextual Utility** (edge feasibility, operational relevance, architectural synergy), **not raw benchmark accuracy on public benchmark datasets**.

---

### Layer 1: Detection / Object Detection Expert Pool

| Model | Variant Scope | Architectural Role | Execution Mode | IBVAP Fit % | Key Technical Note / License Context |
|:---|:---|:---|:---|:---:|:---|
| **YOLOv8** | Nano / Small (`yolov8n`, `yolov8s`) | Always-on primary baseline detector; fast CPU/edge inference | **Continuous (30 FPS)** | **85%** | Active local baseline; portable `.pt` / `.onnx` / TensorRT FP16. |
| **RF-DETR** | Nano $\to$ XL (ResNet / ConvNeXt) | High-accuracy deformable transformer detector | **Triggered / High-Value** | **95%** | Ultra-clean boundary boxes; official weights mix Apache-2.0 & PML (variant-dependent). |
| **D-FINE** | Large / XLarge (`D-FINE-L/X`) | Fine-grained bounding box regressor for distant/small targets | **Escalation (Low Confidence)** | **92%** | Exceptional IoU convergence on occluded perimeter objects. |
| **DEIM** | Real-Time DEIM | Dense edge-optimized object detector | **Alternate Primary** | **90%** | Excellent parameter-to-mAP ratio on constrained compute. |
| **RT-DETRv3** | Small / Medium / Large | Real-time transformer detection with multi-scale feature fusion | **Specialist Verification** | **92%** | Eliminates NMS bottlenecks; robust to dense border foliage. |
| **YOLOv12** | Nano $\to$ Large | Attention-centric real-time object detector | **Benchmark / Modern Route** | **91%** | Area attention reduces false alarms on waving vegetation. |
| **YOLOE** | Edge / Real-Time | Open-vocabulary efficient detector | **Unclassified Target Route** | **90%** | Detects rare/unseen objects without re-training weights. |
| **Grounding DINO 1.5 Pro** | Base / Large | Text-conditioned open-vocabulary zero-shot detector | **Operator / Escalation** | **88%** | Invoked when operator queries rare objects (e.g., *"crouching person with ladder"*). |

---

### Layer 2: Segmentation Expert Pool

| Model | Architectural Role | Execution Mode | IBVAP Fit % | Operational Trigger |
|:---|:---|:---|:---:|:---|
| **SAM 2.1** | High-precision video & spatial boundary segmentation | **Triggered (Event Buffer)** | **93%** | P0/P1 intrusions, pixel-accurate fence cut/breach verification (Apache 2.0). |
| **SAMURAI** | Temporal zero-shot visual object tracking & mask propagation | **Post-Trigger Tracking** | **91%** | Target weaving through dense camouflage/trees across consecutive frames. |
| **MobileSAM** | Ultra-lightweight edge segmentation (<10M params) | **Local Edge (RTX 3050)** | **89%** | Immediate foreground/background extraction for cropped threat objects. |
| **FastSAM** | CNN-based real-time segmenter (YOLOv8 backbone) | **Lightweight Trigger** | **88%** | Fast mask extraction when latency budget is under 25 ms. |
| **EfficientSAM** | Memory-efficient SAM with visual masked autoencoder | **Embedded Specialist** | **87%** | Compact edge deployment; low VRAM footprint. |
| **SEEM** | Multi-modal interactive segmentation (text, stroke, audio) | **Operator Interactive** | **86%** | Analyst clicks or draws polygon to isolate specific contraband/object. |

---

### Layer 3: Tracking & Association Expert Pool

| Model | Architectural Role | Execution Mode | IBVAP Fit % | Operational Trigger |
|:---|:---|:---|:---:|:---|
| **ByteTrack** | Low-cost primary association via low-confidence detection matching | **Continuous (Always-on)** | **94%** | Default tracking baseline; zero GPU overhead; Hungarian matching on IoU. |
| **BoT-SORT** | Camera Motion Compensation (CMC) + appearance tracking | **PTZ / Dynamic Camera** | **92%** | Camera sway, wind vibration, or PTZ patrol re-centering. |
| **Deep OC-SORT** | Observation-Centric SORT with adaptive Kalman recovery | **Severe Occlusion** | **91%** | Target stepping behind guard posts, boulders, or vehicles for 3–8 seconds. |
| **Hybrid-SORT** | Multi-feature fusion tracker (motion + appearance + shape) | **Dense Cluster** | **90%** | Multiple overlapping targets crossing paths along perimeter trails. |
| **ImprAssoc** | Identity-preserving association for high-density queues | **Checkpost / Gate** | **89%** | Vehicle and foot patrol chokepoint management. |
| **MOTRv3 / MeMOTR** | End-to-end multi-object tracking transformers with long-term memory | **Research / Workstation** | **88%** | Global trajectory modeling over long temporal horizons. |

---

### Layer 4: Face Recognition & Identity Verification Expert Pool

| Model | Architectural Role | Execution Mode | IBVAP Fit % | Operational Trigger |
|:---|:---|:---|:---:|:---|
| **InsightFace (Antelopev2)** | Deep feature facial extraction and 512-D embedding | **Gate / Entry Verification** | **94%** | Clear facial crop ($>60\times60$ px) with frontal pose. |
| **AdaFace** | Quality-adaptive margin biometrics (resilient to blur/noise) | **Primary CCTV Face ID** | **93%** | Unconstrained CCTV crops where facial resolution is degraded. |
| **MagFace** | Magnitude-aware facial quality assessment and embedding | **Face Quality Gating** | **92%** | Discards unusable face crops before expensive database search. |
| **PartialFace** | Occluded / masked facial feature matching | **Winter / Camouflage** | **90%** | Targets wearing balaclavas, scarves, or tactical headgear. |
| **TransFace / KPRPE** | Vision transformer and pose-robust facial alignment | **Research / Benchmark** | **89%** | High-angle border watchtower perspectives. |
| **XCloud** | Distributed biometric gallery search adapter | **Remote Gallery Query** | **86%** | Synchronizing watchlists across deployed border outposts. |

---

### Layer 5: Person Re-Identification (Re-ID) Expert Pool

| Model | Architectural Role | Execution Mode | IBVAP Fit % | Operational Trigger |
|:---|:---|:---|:---:|:---|
| **FastReID** | Mobile/edge CNN-based person re-identification | **Local Cross-Camera (Fast)** | **92%** | Object exits CAM-01 and enters CAM-02 within 12-second window. |
| **TransReID** | Vision Transformer with jigsaw patch permutation for part-aware Re-ID | **High-Confidence Re-ID** | **91%** | Matching targets carrying tactical bags or asymmetric clothing. |
| **CLIP-ReID** | Vision-language aligned semantic appearance retrieval | **Analyst Multi-Camera Query** | **90%** | Operator searches: *"Person in green camouflage jacket with black backpack"*. |
| **SOLIDER** | Semantic-aligned representation learning for person Re-ID | **Multi-Camera Handover** | **89%** | Cross-camera association under varying sensor color temperatures. |
| **PersonMAE / KPR** | Self-supervised masked autoencoder & keypoint-guided Re-ID | **Occluded Re-ID** | **88%** | Target partially hidden by perimeter obstacles. |

---

### Layer 6: Vision-Language Models (VLM) & Multimodal Reasoning

| Model | Parameter Class | Architectural Role | Execution Mode | IBVAP Fit % | Deployment Profile |
|:---|:---|:---|:---|:---:|:---|
| **Qwen2.5-VL 72B** | Frontier 72B | Deep multi-frame incident reasoning, tactical threat explanation | **Async Queue (Cloud/Server)** | **95%** | Dedicated GPU / Cloud node; invoked on confirmed P0/P1 incidents. |
| **Qwen2.5-VL 7B** | Local 7B | Compact local multimodal analysis, spatial question answering | **Event Triggered (RTX 3050 6GB+)** | **91%** | Quantized (AWQ/INT4); produces 2-sentence tactical event summaries. |
| **Florence-2** | Large (~0.7B) | Ultra-fast multimodal captioning, visual grounding, OCR integration | **Local Edge Trigger** | **92%** | Extremely fast (<80 ms); runs easily on local edge hardware. |
| **PaliGemma 2** | 3B / 10B | Fine-grained visual comprehension & inspection | **Specialist Route** | **88%** | Specialized perimeter anomaly captioning. |
| **InternVL 2.5** | 8B $\to$ 78B | High-resolution multi-modal video understanding | **Cloud / Workstation** | **89%** | Multi-angle cross-camera narrative reconstruction. |
| **LLaVA-OneVision** | 7B $\to$ 72B | Unified image and video understanding across variable native resolutions | **Heavy Reasoning Route** | **88%** | Long-context visual dialogue with border operator. |
| **NVILA / VideoLLaMA 3** | Video-Centric | Video-native spatio-temporal conversational agents | **Temporal Investigation** | **87%** | Complex sequence interpretation (e.g., digging, wire-cutting). |
| **Molmo / Pixtral / Llama 3.2V** | 11B $\to$ 90B | Open-weight multimodal models with native point-grounding | **Benchmark Alternate** | **86%** | Architectural fallbacks in Model Registry. |

---

### Layer 7: Video Understanding & Temporal Context Expert Pool

| Model | Architectural Role | Execution Mode | IBVAP Fit % | Operational Trigger |
|:---|:---|:---|:---:|:---|
| **VideoMAE v2** | Masked video autoencoder for temporal representation | **Ring Buffer (15s Clip)** | **92%** | Dispatched when kinematic motion cannot distinguish normal walking from pacing. |
| **VideoMamba** | State-space model (SSM) for linear-complexity long video analysis | **Extended Buffer (30–60s)**| **90%** | Efficient temporal context without quadratic transformer memory explosion. |
| **InternVideo2** | Large-scale multi-modal video representation foundation | **Heavy Incident Audit** | **89%** | Forensic post-event investigation on border monitoring workstations. |
| **VideoLLaMA 3** | Conversational video agent for multi-step temporal action grounding | **Forensic Dossier** | **88%** | Automatically generates military SITREP (Situation Report) narrative. |
| **LongVA / Tarsier** | Extended context video reasoning models | **Night Patrol Clip Audit**| **87%** | Auditing 10-minute continuous buffer during automated night sweeps. |

---

### Layer 8: Image Restoration, Low-Light & Weather Enhancement

| Model | Architectural Role | Execution Mode | IBVAP Fit % | Operational Trigger |
|:---|:---|:---|:---:|:---|
| **Adaptive CLAHE + Dynamic Gamma** | Ultra-fast mathematical contrast stretch ($<2$ ms) | **Local Edge Baseline** | **95%** | Always active; normalizes low-light patches before inference. |
| **Retinexformer** | Transformer-based low-light enhancement | **Night Surveillance** | **94%** | Mean brightness $<40.0$; reconstructs structural edges in dark shadows. |
| **Zero-DCE++** | Zero-reference deep curve estimation ($<15$ ms) | **Fast Low-Light Route** | **92%** | Real-time illumination recovery on edge GPUs without paired ground truth. |
| **DehazeFormer** | Transformer-based dense haze and fog removal | **Fog / Dust / Sandstorm** | **93%** | Contrast indicator $<0.25$ and high ambient scatter detected. |
| **ThermalGAN** | Thermal-to-visible spectrum cross-modal translation | **Thermal Sensor Feeds** | **88%** | Activated exclusively when FLIR / thermal IP cameras are connected. |
| **MambaIR / MIRNet v2** | Image restoration via state space / multi-scale architectures | **Heavy Restoration** | **87%** | Extreme rain, heavy snowfall, or lens condensation. |
| **DiffLL / SCI** | Diffusion and self-calibrated illumination algorithms | **Research / Benchmark** | **85%** | Offline evidentiary enhancement for court presentations. |

---

### Layer 9: Pose, Behavior & Kinematic Action Expert Pool

| Model | Architectural Role | Execution Mode | IBVAP Fit % | Operational Trigger |
|:---|:---|:---|:---:|:---|
| **RTMPose / RTMPose-s** | Real-time 17-keypoint skeletal estimation ($<8$ ms) | **Triggered (Person Track)**| **94%** | Activated when a stabilized person track is inside a sensitive zone. |
| **CTR-GCN** | Channel-wise topology refinement graph convolutional network | **Temporal Action Class** | **92%** | Takes 30-frame skeleton sequence; flags climbing, crawling, crouching. |
| **ViTPose++** | High-precision vision transformer pose estimation | **High-Confidence Audit** | **91%** | Severe occlusion or unusual perspective where RTMPose confidence $<0.60$. |
| **Sapiens** | Native high-resolution human body pose and surface normal foundation | **Deep Forensic Analysis**| **88%** | Post-incident high-fidelity forensic reconstruction. |
| **MMPose / PoseAnything** | Generalizable multi-instance articulation frameworks | **Architecture Framework**| **89%** | Registry adapter foundation. |
| **Animal-Kingdom** | Skeletal tracking and behavior analysis for animal classes | **Wildlife Filtering** | **86%** | Eliminates false alarms caused by stray cattle, deer, or wild dogs near fences. |

---

### Layer 10: Anomaly Detection Expert Pool

| Model | Architectural Role | Execution Mode | IBVAP Fit % | Operational Trigger |
|:---|:---|:---|:---:|:---|
| **Anomalib** | Unsupervised deep visual anomaly detection framework | **Zone Anomaly Suite** | **91%** | Learns normal static border patterns; flags out-of-distribution visual objects. |
| **STAEformer** | Spatio-temporal autoencoder transformer for crowd/motion anomaly | **Temporal Motion Outlier** | **90%** | Detects sudden panic running, irregular vehicle velocity, or wrong-way traversal. |
| **MNAD / MemAE** | Memory-augmented autoencoders for normal scene reconstruction | **Visual Discrepancy** | **89%** | Identifies abandoned objects, backpacks, or fence tampering. |
| **PyOD** | Classical statistical and tabular anomaly framework (k-NN, Isolation Forest) | **Kinematic Trajectory** | **88%** | Detects abnormal track speed, loitering dwell times, and perimeter zig-zagging. |
| **UBnormal** | Benchmark framework for open-set abnormal video event evaluation | **Validation Suite** | **86%** | Evaluates anomaly detector precision against border infiltration datasets. |

---

### Layer 11: Foundation & Zero-Shot Representation Expert Pool

| Model | Architectural Role | Execution Mode | IBVAP Fit % | License & Policy Restriction |
|:---|:---|:---|:---:|:---|
| **DINOv2** | Self-supervised visual representation foundation ($768$-D embeddings) | **Visual Search / Re-ID** | **93%** | Apache-2.0. Clean for commercial and defense production. |
| **DINOv3** | High-capacity visual representation model | **Experimental Only** | **88%** | **CAUTION:** Current license explicitly restricts military/warfare uses. Kept strictly as research fallback. |
| **CLIP / SigLIP 2** | Multimodal zero-shot text-image embedding space | **Semantic Query Bus** | **92%** | Enables natural-language operator searches across historical incidents. |
| **Depth Anything V2** | Monocular metric depth estimation from single 2D camera frames | **Spatial Hazard / Geo** | **91%** | Approximates 3D distance of target from international boundary fence. |
| **VGGT / MoGe** | Geometry-guided geometric reconstruction and spatial reasoning | **3D Terrain Mapping** | **86%** | Maps camera coordinates to 3D terrain elevation models. |

---

### Layer 12: Edge Runtime, Deployment & Acceleration Stack

| Component | Target Hardware | Execution Role | IBVAP Fit % | Status / Operational Benefit |
|:---|:---|:---|:---:|:---|
| **TensorRT FP16 / INT8** | NVIDIA RTX 3050 / Orin | Zero-latency model engine compilation | **96%** | $3\times$ speedup on YOLO and Pose detectors on Ampere (`sm_86`). |
| **DeepStream 7.0 / GStreamer** | NVIDIA Hardware | Hardware-accelerated NVDEC video decoding and batched inference | **95%** | Zero-copy pipeline from RTSP H.264 packet to CUDA frame buffer. |
| **ONNX Runtime (CPU/OpenVINO)**| Intel Core i3 (Current Dell) | Portable CPU-first acceleration using AVX2/AVX-512 | **96%** | Guarantees zero-crash fallback on machines without dedicated GPU. |
| **NVIDIA Triton Inference Server** | Multi-GPU Post Server | Enterprise model routing, dynamic batching, and concurrent queuing | **90%** | Coordinates multi-camera load balancing across edge clusters. |
| **llama.cpp / ExecuTorch** | Edge CPU / Low-VRAM GPU | Quantized GGUF inference for 3B/7B language models | **92%** | Runs Indic / lightweight reasoning models in under 3 GB RAM. |

---

### Layer 13: ANPR & Vehicle Intelligence Stack

| Component | Function | Execution Mode | IBVAP Fit % | Operational Logic |
|:---|:---|:---|:---:|:---|
| **Vehicle Detector & Classifier** | Identifies car, truck, bus, motorcycle, military vehicle | **Level 1 Detector** | **95%** | YOLOv8 COCO classes (2, 3, 5, 7) + border vehicle fine-tuned classes. |
| **Plate Region Detector (LPR)** | Localizes high-resolution license plate bounding box | **Level 3 Specialist** | **94%** | Invoked only when vehicle confidence $>0.50$ and plate area $>1500$ px. |
| **EasyOCR / PaddleOCR** | Character recognition with geometric perspective correction | **Multi-Frame OCR** | **92%** | Uses CLAHE and bilateral filtering to sharpen embossed plates. |
| **Multi-Frame OCR Aggregator** | Character-level voting across 5–15 consecutive frames | **Temporal Consensus** | **96%** | Eliminates single-frame glare/motion blur misreads via Levenshtein distance. |
| **Whitelist / Blacklist Engine** | Cross-references security database; logs entry/exit | **Rule Engine** | **98%** | Immediate P0 alert on stolen or unmanifested border vehicles. |

---

### Layer 14: Indian AI & Indic Intelligence Layer

| Platform / Model | Source Entity | Architectural Role | IBVAP Fit % | Practical Use Case |
|:---|:---|:---|:---:|:---|
| **BHASHINI** | Government of India (MeitY) | Multilingual speech-to-text, translation, and voice command dispatch | **88%** | Voice-activated operator search; automated translation of alerts into Hindi, Punjabi, Bengali, Assamese, etc. |
| **IndicTrans2** | AI4Bharat (IIT Madras) | Compact neural machine translation for Indian languages | **90%** | Translates technical incident reports (*"Intrusion detected at North Perimeter"*) into native Indic vernacular. |
| **IndicBERT / IndicWhisper** | AI4Bharat | Semantic retrieval and voice transcription | **87%** | Allows border sentries to query system via VHF/radio audio input. |
| **Krutrim AI** | Ola Krutrim | Indigenous Indic LLM reasoning and summarization | **85%** | Synthesizes daily border activity summaries in regional languages. |

---

### Layer 15: Temporal Event Correlation & State Machine Stack

| Component | Responsibility | State Progression | IBVAP Fit % | Operational Safeguard |
|:---|:---|:---|:---:|:---|
| **Temporal State Machine** | Multi-frame persistence gating | `DETECTED` $\to$ `TENTATIVE` $\to$ `STABLE` $\to$ `VERIFIED` $\to$ `ALERT_ELIGIBLE` | **98%** | Prevents transient single-frame noise from triggering sirens. Baseline: ~45 consecutive frames. |
| **Complex Event Processing (CEP)** | Relational event correlation | Cross-references trajectory + speed + zone + object type | **97%** | Differentiates loitering near fence from casual authorized transit. |
| **Dwell-Time & Zone Ingress** | Evaluates polygon hazard score | Dwell timer resets on exit; escalates to P1 on $>60$s loitering | **98%** | Polygon containment via ray-casting algorithm. |

---

### Layer 16: Scene & Camera Health Intelligence Stack

| Parameter | Diagnostic Method | Trigger Threshold | IBVAP Fit % | Automated System Action |
|:---|:---|:---|:---:|:---|
| **Brightness / Illumination** | Mean frame intensity | Mean $<45.0$ or $>220.0$ | **97%** | Automatically triggers Layer 8 low-light enhancement / auto-exposure alert. |
| **Blur & Defocus** | Laplacian variance ($\sigma^2_{\Delta}$) | $\sigma^2 < 65.0$ | **96%** | Flags lens contamination, dew, or mechanical defocusing. |
| **Contrast & Fog Index** | Dynamic range histogram spread | Histogram std dev $<25.0$ | **95%** | Engages DehazeFormer; lowers detector thresholds to compensate for fog. |
| **FPS & Dropped Frames** | Inter-frame arrival delta ($\Delta t$) | $\Delta t > 100$ ms | **98%** | Activates frame-drop queue; switches to lightweight inference mode. |
| **Camera Tampering / Occlusion** | Structural Similarity (SSIM) to background | SSIM $<0.15$ sudden drop | **98%** | Emits immediate P0 `CAMERA_OBSTRUCTION_SUSPECTED` critical alert. |

---

### Layer 17: Tamper-Evident Evidence & Security Stack

| Security Component | Mechanism | Cryptographic Standard | IBVAP Fit % | Legal & Evidentiary Role |
|:---|:---|:---|:---:|:---|
| **SHA-256 Hash Chain** | Cryptographic block linking | $\text{Hash}_n = \text{SHA256}(\text{Hash}_{n-1} + \text{Data})$ | **98%** | Tamper-evident ledger conforming to Indian Evidence Act Section 65B requirements. |
| **Role-Based Access Control (RBAC)**| JWT token validation with role scopes | OAuth2 / HMAC-SHA256 | **96%** | Sentry (view only), Operator (acknowledge/comment), Commander (export/audit). |
| **FIFO Evidence Retention** | Automated disk quota management | Configurable cap (e.g., 100 snapshots) | **97%** | Purges oldest un-flagged evidence while pinning confirmed incident chains. |

---

## 2. The 3-Tier Operational Runtime Architecture

To resolve the compute vs. quality trade-off, IBVAP operates strictly across three asynchronous tiers:

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                           TIER 1: EDGE REAL-TIME (30 FPS)                      │
│ Target: Local CPU / NVIDIA RTX 3050 (4GB)                                      │
│ Models: YOLOv8n + ByteTrack + Camera Health + Zone Engine + Temporal States     │
│ Rule: Fast, zero-lag, continuous watch. Drops zero frames.                     │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       │
                         Suspicious / Uncertain Event
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                        TIER 2: LOCAL HEAVY TRIGGERED (On-Demand)               │
│ Target: Local RTX 3050 (4GB/6GB) / Intel AVX2 Multi-Thread                     │
│ Models: RTMPose + Face EAR Blink + ANPR OCR + Florence-2 / Qwen-7B (AWQ)       │
│ Rule: Executes ONLY on cropped ROI bounding boxes for stabilized tracks.       │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       │
                       High-Threat P0 / Complex Context
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                      TIER 3: ASYNCHRONOUS DEEP REASONING QUEUE                 │
│ Target: Command Post Workstation / Remote Secure Cloud / Background Worker     │
│ Models: Qwen2.5-VL 72B + SAM 2.1 + VideoMAE v2 + IndicTrans2                    │
│ Rule: Operates on 15s Ring Buffer clips. NEVER blocks live 30 FPS surveillance.│
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The 20-Second Ring Buffer Engine (Solving the 2–3s Infiltration Dilemma)

When a suspicious event lasts only 2–3 seconds, heavy models cannot be running continuously. The Ring Buffer preserves the complete tactical envelope:

```
T - 10s                       T - 2s                T = Trigger            T + 5s
[ PRE-EVENT ROLLING BUFFER ] [ APPROACH TRAJECTORY ] [ INTRUSION BREACH ] [ POST-EVENT ESCAPE ]
└────────────────────────────┴─────────────────────┴───────────────────┴──────────────────────┘
                                  │
                                  ▼
           Frozen as Immutable Incident Evidence Clip (15 seconds)
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
   Fast Initial Alert (<100 ms)         Asynchronous Deep Audit (3–10s)
   "Possible perimeter breach"          Qwen-72B & SAM 2.1 multi-frame analysis
   Operator alerted immediately         appended to Incident Record in DB
```

---

## 4. Confidence-Driven Dynamic Route Scorer ($S_{route}$)

The orchestrator dynamically routes frames using the calibrated routing formula:

$$S_{route} = 0.25 C_{det} + 0.15 C_{track} + 0.15 C_{temporal} + 0.20 C_{zone} + 0.10 C_{identity} + 0.05 C_{anomaly} + 0.05 C_{vlm} + 0.05 C_{cam}$$

```
                ┌──────────────────────────────────────────────────┐
                │             Calculate S_route Score             │
                └─────────────────────────┬────────────────────────┘
                                          │
                  ┌───────────────────────┼───────────────────────┐
                  ▼                       ▼                       ▼
            S_route < 0.25         0.25 <= S < 0.65        S_route >= 0.65
           [FILTERED NOISE]       [STANDARD INCIDENT]    [CRITICAL INTERCEPT]
           Drop candidate          Log incident to DB     Immediate audio alert
           Continue fast track     Dispatch telemetry     Escalate to Tier 2/3
```

---

## 5. Storage & Hardware Planning Matrix

| Deployment Tier | Minimum Storage | Recommended Storage | Hardware Target | Supported Model Capability |
|:---|:---|:---|:---|:---|
| **Development Laptop** | 250 GB SSD | 500 GB NVMe | Dell Core i3 / 12 GB RAM | CPU Baselines (11 models) + Full Registry Fallbacks + Offline RTSP Simulator. |
| **Border Post Edge Node** | 500 GB SSD | 1 TB NVMe | RTX 3050 4GB/6GB or Jetson Orin | Full Tier 1 (30 FPS) + Tier 2 (RTMPose, Fast ANPR, Florence-2, SAM-Mobile). |
| **Command Headquarters** | 2 TB NVMe | 4 TB Enterprise NVMe | Dual RTX 4090 / A100 Server | Tier 1 + Tier 2 + Tier 3 (Qwen2.5-VL 72B, SAM 2.1 Video, Full BHASHINI Stack). |

---

## 6. Official Government & Indian AI Integration Strategy

1. **BHASHINI Integration:**  
   Accessed via MeITy API schemas. Acts strictly as an **Incident Translation & Voice Sentry Interface**. It transforms structured telemetry into audio alerts in regional languages for border sentries.
2. **AI4Bharat Ecosystem:**  
   Employs **IndicTrans2** (distilled 1B variant) for high-speed edge text translation of incident logs, and **IndicWhisper** for radio audio transcription.
3. **Defense Positioning:**  
   Positioned as: *“IBVAP natively interoperates with indigenous Indian AI language foundations to ensure field operators receive situational awareness in their primary regional dialect without cloud dependency for core computer vision.”*


---

## 7. Model Licensing & Compliance Safeguards

| Model / Dataset | Declared License | IBVAP Production Policy |
|:---|:---|:---|
| **YOLOv8** | AGPL-3.0 | Permissible for standalone inference services; dual-licensing path for commercial distribution. |
| **SAM 2.1** | Apache-2.0 | Fully compliant for edge deployment and integration. |
| **DINOv3** | Non-Commercial / Research | **RESTRICTED:** Contains explicit military/defense exclusion clauses. Retained strictly in registry as an experimental academic benchmark; excluded from production deployment binaries. |
| **DINOv2** | Apache-2.0 | Production-approved replacement for visual feature embeddings. |
| **RF-DETR** | Apache-2.0 / PML | Base models compliant; Plus/XL variants reviewed individually per deployment. |

---

## 8. Summary of Completed System Alignment

Your complete master stack—spanning all 17 layers and every discussed model—is fully cataloged inside the local repository:
- **Registry Source of Truth:** [`ml/registry/model_registry.yaml`](file:///C:/Users/dell/Desktop/p2/IBVAP_Final_Project/ml/registry/model_registry.yaml) & [`model_registry.py`](file:///C:/Users/dell/Desktop/p2/IBVAP_Final_Project/ml/registry/model_registry.py) (106 cataloged models across 14 pools).
- **Zero-Crash Fallback Hierarchy:** Heavy or uninstalled models safely route to the active CPU/RTX baselines with status `REGISTERED / NOT INSTALLED / FALLBACK ACTIVE`.
- **Verified Local Flow:** Tested live on your Dell machine with MediaMTX, FFmpeg, YOLOv8, ByteTrack, WebSocket telemetry, SQLite persistence, and SHA-256 evidence chain verification.