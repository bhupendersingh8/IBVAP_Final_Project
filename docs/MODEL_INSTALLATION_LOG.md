# IBVAP — MODEL INSTALLATION & ADAPTATION LOG
=============================================
*Log Timestamp: 2026-09-27 20:38:34 UTC*

## 1. Summary of Completed Installations

- **Total Cataloged Models:** 121
- **LOCAL_OPERATIONAL:** 31
- **REMOTE_OPERATIONAL:** 39
- **PACKAGE_AND_WEIGHTS_READY:** 20
- **HARDWARE_BLOCKED:** 28
- **LICENSE_BLOCKED:** 2
- **DEPENDENCY_BLOCKED:** 1
- **FAILED_WITH_REASON:** 0

## 2. Key Local Physical Weight Artifacts

- `models/detection/yolov8n.pt` (6.25 MB) — Verified real-time detector
- `models/detection/yolov8s.pt` (21.54 MB) — Verified small detector
- `models/detection/yolov8x.pt` (136.89 MB) — Verified enterprise heavy detector
- `models/detection/rtdetr-l.pt` (63.43 MB) — Verified real-time transformer detector
- `models/segmentation/yolov8n-seg.pt` (6.74 MB) — Verified instance segmentation
- `models/segmentation/FastSAM-s.pt` (22.75 MB) — Verified fast segment anything
- `models/pose/yolov8n-pose.pt` (6.52 MB) — Verified 17-keypoint skeleton regressor
- `models/face/face_detection_yunet_2023mar.onnx` (0.22 MB) — Verified YuNet detector
- `models/face/face_recognition_sface_2021dec.onnx` (36.90 MB) — Verified SFace identity embedder
- `models/vision/dinov2_vits14.pth` (84.20 MB) — Verified foundation vision model
- `models/yolov8n.onnx` (12.26 MB) — Verified portable ONNX artifact

## 3. Standard Model Adapters Added

- `ml/adapters/base_adapter.py`: Abstract `BaseModelAdapter` standardizing `load()`, `predict()`, `validate()`, and `metadata()`.
- `ml/adapters/family_adapters.py`: Implements `DetectionModelAdapter`, `TrackingModelAdapter`, `SegmentationModelAdapter`, `PoseModelAdapter`, `FaceModelAdapter`, `ReIDModelAdapter`, `ANPRModelAdapter`, `RestorationModelAdapter`, `VisionEmbeddingModelAdapter`, and `VLMModelAdapter`.