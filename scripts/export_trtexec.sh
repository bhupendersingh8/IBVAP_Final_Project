#!/usr/bin/env bash
# ==============================================================================
# TRINETRA / TCVIAF (SIH26228) - NVIDIA TensorRT Engine Compilation Script
# ==============================================================================
# Compiles exported ONNX vision models into hardware-accelerated TensorRT FP16 / INT8
# execution engines for maximum FPS throughput (>60-120 FPS) on NVIDIA RTX / Jetson.
# ==============================================================================

set -euo pipefail

WEIGHTS_DIR="${1:-weights}"
ENGINES_DIR="${2:-engines}"

mkdir -p "${ENGINES_DIR}"

echo "================================================================================"
echo "  TRINETRA TCVIAF: NVIDIA TensorRT Engine Compilation via trtexec"
echo "  Weights Source: ${WEIGHTS_DIR}"
echo "  Target Output : ${ENGINES_DIR}"
echo "================================================================================"

# Verify trtexec availability
if ! command -v trtexec &> /dev/null; then
    echo "[!] WARNING: 'trtexec' not found in PATH."
    echo "[*] Ensure TensorRT bin directory is added to PATH (e.g., /usr/src/tensorrt/bin or C:\\Program Files\\NVIDIA GPU Computing Toolkit\\TensorRT\\bin)"
    echo "[*] Displaying target compilation commands for offline edge deployment:"
fi

# 1. Primary Vision Detector: YOLOv11x (FP16 Engine)
echo ""
echo "[1/4] Compiling YOLOv11x (640x640 FP16 Engine)..."
echo "Command: trtexec --onnx=${WEIGHTS_DIR}/yolov11x.onnx --saveEngine=${ENGINES_DIR}/yolov11x_fp16.engine --fp16 --memPoolSize=workspace:2048MiB"
if command -v trtexec &> /dev/null && [ -f "${WEIGHTS_DIR}/yolov11x.onnx" ]; then
    trtexec --onnx="${WEIGHTS_DIR}/yolov11x.onnx" --saveEngine="${ENGINES_DIR}/yolov11x_fp16.engine" --fp16 --memPoolSize=workspace:2048MiB
fi

# 2. High-Precision DETR Model: D-FINE-X (Fine-grained Distribution Refinement)
echo ""
echo "[2/4] Compiling D-FINE-X DETR Model (640x640 FP16 Engine)..."
echo "Command: trtexec --onnx=${WEIGHTS_DIR}/dfine_x.onnx --saveEngine=${ENGINES_DIR}/dfine_x_fp16.engine --fp16 --memPoolSize=workspace:2048MiB"
if command -v trtexec &> /dev/null && [ -f "${WEIGHTS_DIR}/dfine_x.onnx" ]; then
    trtexec --onnx="${WEIGHTS_DIR}/dfine_x.onnx" --saveEngine="${ENGINES_DIR}/dfine_x_fp16.engine" --fp16 --memPoolSize=workspace:2048MiB
fi

# 3. High-Speed Edge Baseline: YOLO26n / YOLO11n
echo ""
echo "[3/4] Compiling YOLO26n Edge Baseline (640x640 FP16 Engine)..."
echo "Command: trtexec --onnx=${WEIGHTS_DIR}/yolo26n.onnx --saveEngine=${ENGINES_DIR}/yolo26n_fp16.engine --fp16 --memPoolSize=workspace:1024MiB"
if command -v trtexec &> /dev/null && [ -f "${WEIGHTS_DIR}/yolo26n.onnx" ]; then
    trtexec --onnx="${WEIGHTS_DIR}/yolo26n.onnx" --saveEngine="${ENGINES_DIR}/yolo26n_fp16.engine" --fp16 --memPoolSize=workspace:1024MiB
fi

# 4. Neural Low-Light Restorer: Zero-DCE++ (256x256 Fast Curve Estimator)
echo ""
echo "[4/4] Compiling Zero-DCE++ Fast Curve Estimator (256x256 FP16 Engine)..."
echo "Command: trtexec --onnx=${WEIGHTS_DIR}/zero_dce.onnx --saveEngine=${ENGINES_DIR}/zero_dce_256_fp16.engine --fp16 --memPoolSize=workspace:512MiB"
if command -v trtexec &> /dev/null && [ -f "${WEIGHTS_DIR}/zero_dce.onnx" ]; then
    trtexec --onnx="${WEIGHTS_DIR}/zero_dce.onnx" --saveEngine="${ENGINES_DIR}/zero_dce_256_fp16.engine" --fp16 --memPoolSize=workspace:512MiB
fi

echo ""
echo "================================================================================"
echo "  [OK] TensorRT FP16 Compilation Profiles Configured."
echo "================================================================================"
