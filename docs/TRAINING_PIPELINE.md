# IBVAP Model Training & Evaluation Pipeline

**Version**: 1.0.0  
**Target Inference Runtime**: Ultralytics YOLOv8 / ONNX / OpenVINO  

---

## 1. Reproducible Fine-Tuning Workflow

### Prerequisites
- Python 3.10+
- PyTorch 2.4+ (CPU or CUDA)
- Ultralytics 8.2+

### Fine-Tuning Command
```bash
yolo task=detect mode=train model=yolov8n.pt data=dataset/dataset.yaml epochs=50 imgsz=640 batch=16 device=cpu
```

---

## 2. Evaluation Metrics & Promotion Gates

To promote a model to `PRODUCTION`, the following acceptance gates must be passed:
- `mAP@50`: >= 0.82 on validation split
- `mAP@50-95`: >= 0.55
- `False Positive Rate`: <= 3.5% on empty perimeter negative samples
- `CPU Inference Latency`: <= 45ms per frame on Intel Core i3 @ 640x640

---

## 3. Export to Optimized Edge Runtimes

### ONNX Export:
```bash
yolo export model=runs/detect/train/weights/best.pt format=onnx imgsz=640 dynamic=False
```

### OpenVINO Export (for Intel Iris / CPU acceleration):
```bash
yolo export model=runs/detect/train/weights/best.pt format=openvino imgsz=640
```
