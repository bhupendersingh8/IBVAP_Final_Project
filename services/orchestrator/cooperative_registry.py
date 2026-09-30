"""
services/orchestrator/cooperative_registry.py
=============================================
Central Authoritative Registry for the Multi-Model Cooperative AI Stack.
Smart India Hackathon SIH PS ID: 26187 (Sashastra Seema Bal / Ministry of Home Affairs).

Design Principle:
"Model Cooperation over Model Elimination"
Every license-compatible, useful model has a defined operational role:
- PRIMARY: Continuous first-pass inference (e.g. YOLO11n @ 70 FPS, ByteTrack)
- SECONDARY / VALIDATOR: Gated high-precision confirmation (e.g. YOLO26x 56.9M params, RT-DETR-L)
- SPECIALIST: Domain-specific event-triggered extraction (e.g. Zero-DCE++, MobileSAM, YOLOv8n-Pose, MiDaS)
- ASYNC: Background thread worker offload (e.g. ArcFace 512D FRS, EasyOCR ANPR, LocalTacticalVLM)
- FALLBACK: Resilient zero-crash execution path (e.g. Adaptive CLAHE, CPU baseline)
- ESCALATION: High-threat or uncertain multi-modal deep reasoning (e.g. LocalTacticalVLM)
- RESEARCH / BENCHMARK: Benchmarked in report, ready for deployment
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Union
import json
import structlog

logger = structlog.get_logger()
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class ModelRole(str, Enum):
    PRIMARY = "PRIMARY"                     # Fast continuous monitoring
    SECONDARY = "SECONDARY"                 # Gated confirmation
    VALIDATOR = "VALIDATOR"                 # Second-opinion cross-verification
    SPECIALIST = "SPECIALIST"               # Targeted domain extraction (Lux, Pose, SAM, Depth)
    FALLBACK = "FALLBACK"                   # Standby fail-safe if primary model unavailable
    ESCALATION = "ESCALATION"               # Deep tactical multi-modal reasoning
    ASYNC = "ASYNC"                         # Offloaded to background worker pool
    RESEARCH_BENCHMARK = "RESEARCH_BENCHMARK"  # Benchmarked baseline model


class ModelOperationalStatus(str, Enum):
    ACTIVE = "ACTIVE"                                   # Running continuously on live stream
    EVENT_TRIGGERED = "EVENT_TRIGGERED"                 # Invoked selectively on condition
    ASYNC = "ASYNC"                                     # Running non-blockingly in background thread
    FALLBACK = "FALLBACK"                               # Ready to take over on failure
    AVAILABLE = "AVAILABLE"                             # Physical weights installed, available on demand
    BENCHMARKED = "BENCHMARKED"                         # Validated and benchmarked on target GPU
    NOT_CURRENTLY_CONNECTED = "NOT_CURRENTLY_CONNECTED" # Registered but external device offline


@dataclass
class CooperativeModelEntry:
    """
    Unified metadata schema for models participating in the cooperative ecosystem.
    Prevents unverified, random model usage across the codebase.
    """
    name: str
    architecture: str
    task: str
    version: str = "1.0.0"
    license: str = "AGPL-3.0"
    weights_path: str = ""
    device: str = "cuda"
    backend: str = "torch"
    vram_mb: int = 500
    latency_ms: float = 15.0
    accuracy_metrics: Dict[str, Any] = field(default_factory=dict)
    role: ModelRole = ModelRole.PRIMARY
    trigger_condition: str = "continuous_every_frame"
    dependencies: List[str] = field(default_factory=list)
    fallback: Optional[str] = None
    status: ModelOperationalStatus = ModelOperationalStatus.AVAILABLE
    parameters_m: float = 0.0
    sha256: Optional[str] = None
    official_source_url: Optional[str] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["role"] = self.role.value if isinstance(self.role, ModelRole) else str(self.role)
        d["status"] = self.status.value if isinstance(self.status, ModelOperationalStatus) else str(self.status)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CooperativeModelEntry:
        role_val = data.get("role", ModelRole.PRIMARY)
        if isinstance(role_val, str):
            try:
                role_val = ModelRole(role_val)
            except ValueError:
                role_val = ModelRole.PRIMARY

        status_val = data.get("status", ModelOperationalStatus.AVAILABLE)
        if isinstance(status_val, str):
            try:
                status_val = ModelOperationalStatus(status_val)
            except ValueError:
                status_val = ModelOperationalStatus.AVAILABLE

        return cls(
            name=data.get("name", "unnamed_model"),
            architecture=data.get("architecture", "unknown"),
            task=data.get("task", "generic"),
            version=data.get("version", "1.0.0"),
            license=data.get("license", "AGPL-3.0"),
            weights_path=data.get("weights_path", ""),
            device=data.get("device", "cuda"),
            backend=data.get("backend", "torch"),
            vram_mb=data.get("vram_mb", 500),
            latency_ms=data.get("latency_ms", 15.0),
            accuracy_metrics=data.get("accuracy_metrics", {}),
            role=role_val,
            trigger_condition=data.get("trigger_condition", "continuous"),
            dependencies=data.get("dependencies", []),
            fallback=data.get("fallback"),
            status=status_val,
            parameters_m=data.get("parameters_m", 0.0),
            sha256=data.get("sha256"),
            official_source_url=data.get("official_source_url"),
            description=data.get("description", ""),
        )


class CooperativeModelRegistry:
    """
    Central repository for cooperative multi-model scheduling.
    Maintains all available models with their roles, triggers, and physical files.
    """

    def __init__(self, catalog_path: Optional[Union[str, Path]] = None):
        self.catalog_path = Path(catalog_path) if catalog_path else PROJECT_ROOT / "configs" / "cooperative_model_registry.json"
        self._models: Dict[str, CooperativeModelEntry] = {}
        self._initialize_default_ecosystem()
        self._load_or_save()

    def _initialize_default_ecosystem(self):
        """Initializes the authoritative cooperative ecosystem catalog."""
        default_entries = [
            # 1. Detection Stack
            CooperativeModelEntry(
                name="YOLO11n",
                architecture="YOLO11-nano (C3k2-SPPF-C2PSA)",
                task="2d_detection",
                version="1.0.0",
                license="AGPL-3.0",
                weights_path="weights/yolo11n.pt",
                device="cuda",
                backend="ultralytics",
                vram_mb=450,
                latency_ms=14.16,
                parameters_m=2.62,
                accuracy_metrics={"mAP50_coco": 0.395, "fps_rtx5050": 70.6},
                role=ModelRole.PRIMARY,
                trigger_condition="continuous_every_frame",
                fallback="YOLOv8n",
                status=ModelOperationalStatus.ACTIVE,
                official_source_url="https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt",
                description="Fast primary gating detector. Runs continuously at >70 FPS."
            ),
            CooperativeModelEntry(
                name="TwoStageYOLO26x",
                architecture="YOLO26x-Stack (56.9M params, FP16 imgsz=256 ROI crop)",
                task="cascade_verification",
                version="1.0.0",
                license="AGPL-3.0",
                weights_path="weights/yolo26x.pt",
                device="cuda",
                backend="ultralytics",
                vram_mb=890,
                latency_ms=35.82,
                parameters_m=56.97,
                accuracy_metrics={"mAP50_coco": 0.547, "crop_fps": 27.9},
                role=ModelRole.SECONDARY,
                trigger_condition="uncertain_or_threat_class (0.25 <= conf <= 0.65 or person/vehicle)",
                dependencies=["YOLO11n"],
                fallback="YOLO11n",
                status=ModelOperationalStatus.EVENT_TRIGGERED,
                official_source_url="https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11x.pt",
                description="Heavy verifier cascade model. Gated execution with 30-frame track caching."
            ),
            CooperativeModelEntry(
                name="RT-DETR-L",
                architecture="RT-DETR-L (ResNet50 Hybrid Encoder + Deformable Decoder)",
                task="2d_detection",
                version="1.0.0",
                license="Apache-2.0",
                weights_path="weights/rtdetr-l.pt",
                device="cuda",
                backend="ultralytics",
                vram_mb=1200,
                latency_ms=39.02,
                parameters_m=32.97,
                accuracy_metrics={"mAP50_coco": 0.531, "fps_rtx5050": 25.6},
                role=ModelRole.VALIDATOR,
                trigger_condition="escalation_disagreement_or_high_hazard_zone",
                dependencies=["YOLO11n"],
                fallback="YOLO11n",
                status=ModelOperationalStatus.AVAILABLE,
                official_source_url="https://github.com/ultralytics/assets/releases/download/v8.2.0/rtdetr-l.pt",
                description="High-accuracy real-time transformer detector for complex perimeter verification."
            ),
            CooperativeModelEntry(
                name="YOLOv8n",
                architecture="YOLOv8-nano",
                task="2d_detection",
                version="1.0.0",
                license="AGPL-3.0",
                weights_path="models/detection/yolov8n.pt",
                device="cuda",
                backend="ultralytics",
                vram_mb=350,
                latency_ms=12.5,
                parameters_m=3.16,
                accuracy_metrics={"mAP50_coco": 0.373},
                role=ModelRole.FALLBACK,
                trigger_condition="standby_if_primary_weights_corrupt",
                status=ModelOperationalStatus.FALLBACK,
                description="Zero-crash standalone fallback detector for low-VRAM and CPU environments."
            ),

            # 2. Tracking Stack
            CooperativeModelEntry(
                name="ByteTrack",
                architecture="ByteTrack (Kalman Filter + Low-Score Association)",
                task="multi_object_tracking",
                version="1.0.0",
                license="MIT",
                weights_path="internal_algorithm",
                device="cpu",
                backend="python",
                vram_mb=0,
                latency_ms=29.94,
                role=ModelRole.PRIMARY,
                trigger_condition="continuous_every_frame",
                fallback="FallbackIoUTracker",
                status=ModelOperationalStatus.ACTIVE,
                description="Primary multi-object tracker associating both high and low-confidence detections."
            ),
            CooperativeModelEntry(
                name="FallbackIoUTracker",
                architecture="IoU Association with Hungarian Matching",
                task="multi_object_tracking",
                version="1.0.0",
                license="MIT",
                weights_path="internal_algorithm",
                device="cpu",
                backend="python",
                vram_mb=0,
                latency_ms=1.5,
                role=ModelRole.FALLBACK,
                trigger_condition="standby_if_kalman_singular_matrix",
                status=ModelOperationalStatus.FALLBACK,
                description="Zero-dependency spatial IoU fallback tracker."
            ),

            # 3. Image Enhancement Stack
            CooperativeModelEntry(
                name="Zero-DCE++",
                architecture="Zero-DCE++ (Sub-10ms Deep Curve Estimation)",
                task="low_light_restoration",
                version="1.0.0",
                license="CC BY-NC-SA 4.0",
                weights_path="internal_weights",
                device="cuda",
                backend="torch",
                vram_mb=80,
                latency_ms=8.5,
                parameters_m=0.079,
                role=ModelRole.SPECIALIST,
                trigger_condition="lux < 40 or night_vision_active",
                fallback="AdaptiveCLAHE",
                status=ModelOperationalStatus.EVENT_TRIGGERED,
                description="Deep curve estimation for zero-light and nocturnal surveillance enhancement."
            ),
            CooperativeModelEntry(
                name="AdaptiveCLAHE",
                architecture="Adaptive Contrast Limited Histogram Equalization",
                task="low_light_restoration",
                version="1.0.0",
                license="BSD-3-Clause",
                weights_path="internal_algorithm",
                device="cpu",
                backend="cv2",
                vram_mb=0,
                latency_ms=2.1,
                role=ModelRole.FALLBACK,
                trigger_condition="low_light_when_neural_restorer_offline",
                status=ModelOperationalStatus.FALLBACK,
                description="Fast classical dynamic range enhancement for low-light frames."
            ),

            # 4. Segmentation Stack
            CooperativeModelEntry(
                name="MobileSAM",
                architecture="MobileSAM (TinyViT Image Encoder + Lightweight Mask Decoder)",
                task="camouflage_segmentation",
                version="1.0.0",
                license="Apache-2.0",
                weights_path="weights/mobile_sam.pt",
                device="cuda",
                backend="ultralytics",
                vram_mb=350,
                latency_ms=57.07,
                parameters_m=10.13,
                accuracy_metrics={"mIoU": 0.74},
                role=ModelRole.SPECIALIST,
                trigger_condition="crawling (aspect_ratio < 0.65) or camouflaged ROI (0.25 <= conf <= 0.55)",
                dependencies=["YOLO11n", "ByteTrack"],
                fallback="FastSAM-s",
                status=ModelOperationalStatus.EVENT_TRIGGERED,
                official_source_url="https://github.com/ChaoningZhang/MobileSAM/raw/master/weights/mobile_sam.pt",
                description="Pixel-level silhouette segmentation on camouflaged and low-profile crawling targets."
            ),
            CooperativeModelEntry(
                name="FastSAM-s",
                architecture="FastSAM (YOLOv8x-seg real-time CNN segmenter)",
                task="fast_segmentation",
                version="1.0.0",
                license="Apache-2.0",
                weights_path="models/segmentation/FastSAM-s.pt",
                device="cuda",
                backend="ultralytics",
                vram_mb=400,
                latency_ms=24.5,
                parameters_m=11.1,
                role=ModelRole.VALIDATOR,
                trigger_condition="fast_boundary_extraction_when_mobilesam_queued",
                status=ModelOperationalStatus.AVAILABLE,
                description="Fast CNN-based segment-anything alternative for prompt-based boundary extraction."
            ),

            # 5. Pose & Temporal Behavior Stack
            CooperativeModelEntry(
                name="YOLOv8n-Pose",
                architecture="YOLOv8n-Pose (17-Keypoint Human Skeleton Estimator)",
                task="pose_temporal_behavior",
                version="1.0.0",
                license="AGPL-3.0",
                weights_path="models/pose/yolov8n-pose.pt",
                device="cuda",
                backend="ultralytics",
                vram_mb=280,
                latency_ms=16.8,
                parameters_m=3.29,
                role=ModelRole.SPECIALIST,
                trigger_condition="person_track_active (triggered selectively on human tracks)",
                dependencies=["ByteTrack"],
                fallback=None,
                status=ModelOperationalStatus.EVENT_TRIGGERED,
                official_source_url="https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n-pose.pt",
                description="Extracts 17 keypoint body pose to classify crawling, fence-climbing, and prone maneuvers."
            ),

            # 6. ANPR / OCR Stack
            CooperativeModelEntry(
                name="EasyOCR",
                architecture="CRAFT Text Detector + ResNet-LSTM-CTC Recognizer",
                task="anpr_ocr",
                version="1.0.0",
                license="Apache-2.0",
                weights_path="internal_weights",
                device="cpu",
                backend="easyocr",
                vram_mb=0,
                latency_ms=185.0,
                role=ModelRole.ASYNC,
                trigger_condition="vehicle_detected (processed asynchronously in background thread pool)",
                dependencies=["ByteTrack"],
                fallback=None,
                status=ModelOperationalStatus.ASYNC,
                description="Asynchronous optical character recognition for vehicle license plate reading."
            ),

            # 7. Biometrics & Re-ID Stack
            CooperativeModelEntry(
                name="ArcFace-512D",
                architecture="ArcFace (ResNet-50 512-Dimensional Deep Biometric Embedding)",
                task="biometric_frs_reid",
                version="1.0.0",
                license="MIT",
                weights_path="weights/arcface_w600k_r50.onnx",
                device="cpu",
                backend="onnxruntime",
                vram_mb=0,
                latency_ms=718.61,
                parameters_m=43.5,
                role=ModelRole.ASYNC,
                trigger_condition="person_face_candidate (processed asynchronously in background thread pool)",
                dependencies=["ByteTrack"],
                fallback=None,
                status=ModelOperationalStatus.ASYNC,
                official_source_url="https://github.com/deepinsight/insightface/releases",
                description="Asynchronous biometric facial verification and multi-camera re-identification."
            ),

            # 8. Monocular Depth & Spatial Reasoning
            CooperativeModelEntry(
                name="MiDaS-v2.1-Small",
                architecture="MiDaS v2.1 Small (Monocular Depth Estimation CNN)",
                task="monocular_depth",
                version="2.1.0",
                license="MIT",
                weights_path="models/depth/midas_v21_small.pt",
                device="cuda",
                backend="torch",
                vram_mb=320,
                latency_ms=28.4,
                parameters_m=21.4,
                role=ModelRole.SPECIALIST,
                trigger_condition="spatial_distance_inquiry_or_perimeter_breach_p0",
                dependencies=["YOLO11n"],
                fallback=None,
                status=ModelOperationalStatus.EVENT_TRIGGERED,
                description="Monocular depth estimation generating relative distance maps for 3D spatial reasoning."
            ),

            # 9. Tactical Multimodal Reasoning
            CooperativeModelEntry(
                name="LocalTacticalVLM",
                architecture="MobileNetV3 + Cross-Attention SITREP Reasoning Agent",
                task="vlm_situational_reasoning",
                version="1.0.0",
                license="MIT",
                weights_path="internal_code",
                device="cuda",
                backend="torch",
                vram_mb=180,
                latency_ms=21.0,
                role=ModelRole.ASYNC,
                trigger_condition="p0_breach_event_or_operator_inquiry",
                dependencies=["ByteTrack", "RuleEngine"],
                fallback=None,
                status=ModelOperationalStatus.ASYNC,
                description="Asynchronous local multimodal agent synthesizing military SITREPs and threat assessments."
            ),
        ]

        for entry in default_entries:
            self._models[entry.name] = entry

    def _load_or_save(self):
        """Loads from disk or writes the initial JSON catalog."""
        if self.catalog_path.exists():
            try:
                with open(self.catalog_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("models", []):
                        m = CooperativeModelEntry.from_dict(item)
                        self._models[m.name] = m
                logger.info("cooperative_registry.loaded", count=len(self._models), path=str(self.catalog_path))
                return
            except Exception as e:
                logger.warning("cooperative_registry.load_error_rewriting", error=str(e))

        # Save to disk
        self.save_catalog()

    def save_catalog(self):
        """Persists catalog to JSON file."""
        os.makedirs(self.catalog_path.parent, exist_ok=True)
        data = {
            "registry_version": "2.0.0",
            "last_updated": "2026-09-29T21:00:00Z",
            "mission": "SIH PS ID 26187 (Sashastra Seema Bal / Ministry of Home Affairs)",
            "total_models": len(self._models),
            "models": [m.to_dict() for m in self._models.values()]
        }
        with open(self.catalog_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("cooperative_registry.persisted", path=str(self.catalog_path))

    def get_model(self, name: str) -> Optional[CooperativeModelEntry]:
        return self._models.get(name)

    def list_models(self, role: Optional[ModelRole] = None, task: Optional[str] = None) -> List[CooperativeModelEntry]:
        results = list(self._models.values())
        if role:
            results = [m for m in results if m.role == role]
        if task:
            results = [m for m in results if m.task == task]
        return results

    def get_ecosystem_summary(self) -> Dict[str, Any]:
        """Provides high-level honest accounting of registered models."""
        counts_by_role: Dict[str, int] = {}
        counts_by_status: Dict[str, int] = {}
        for m in self._models.values():
            r = m.role.value if isinstance(m.role, ModelRole) else str(m.role)
            s = m.status.value if isinstance(m.status, ModelOperationalStatus) else str(m.status)
            counts_by_role[r] = counts_by_role.get(r, 0) + 1
            counts_by_status[s] = counts_by_status.get(s, 0) + 1

        return {
            "total_registered_models": len(self._models),
            "by_role": counts_by_role,
            "by_status": counts_by_status,
            "models_list": [
                {
                    "name": m.name,
                    "task": m.task,
                    "role": m.role.value if isinstance(m.role, ModelRole) else str(m.role),
                    "status": m.status.value if isinstance(m.status, ModelOperationalStatus) else str(m.status),
                    "latency_ms": m.latency_ms,
                    "trigger": m.trigger_condition,
                    "license": m.license
                }
                for m in self._models.values()
            ]
        }
