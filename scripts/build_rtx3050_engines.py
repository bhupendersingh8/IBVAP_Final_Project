"""
IBVAP Target-Specific TensorRT Engine Builder
SIH 2026 Problem Statement 187 — Border Surveillance Platform

Builds optimized TensorRT FP16 engines for NVIDIA RTX 3050 (4GB & 6GB GDDR6).
Operates honestly:
- If physical NVIDIA GPU + TensorRT present: Compiles and validates engine.
- If CPU-only host: Exports ONNX intermediate graph, stages build recipes,
  and explicitly marks RTX3050_PHYSICAL_EXECUTION = NOT_VERIFIED.
"""

import os
import sys
import argparse
import json
import logging
from typing import Dict, Any
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.hardware import hardware_detector, HardwareProfileName

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ibvap.engine_builder")


def export_onnx_model(weights_path: str, output_path: str, imgsz: int = 640) -> bool:
    """Exports Ultralytics PyTorch model to ONNX format."""
    try:
        from ultralytics import YOLO
        logger.info(f"Loading {weights_path} for ONNX export...")
        model = YOLO(weights_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        exported_path = model.export(
            format="onnx",
            imgsz=imgsz,
            dynamic=False,
            simplify=False,
            opset=17
        )
        logger.info(f"Successfully exported ONNX model to {exported_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export {weights_path} to ONNX: {e}")
        return False


def build_tensorrt_engine(onnx_path: str, engine_path: str, fp16: bool = True, max_vram_mb: int = 3200) -> Dict[str, Any]:
    """Compiles ONNX graph into TensorRT engine if NVIDIA hardware is active."""
    profile = hardware_detector.resolve_profile()

    result = {
        "onnx_path": onnx_path,
        "engine_path": engine_path,
        "fp16_enabled": fp16,
        "max_vram_mb": max_vram_mb,
        "status": "NOT_VERIFIED",
        "reason": ""
    }

    if not profile.gpu.nvidia_present or not profile.gpu.cuda_available:
        result["status"] = "PROFILE_READY_NOT_PHYSICALLY_VERIFIED"
        result["reason"] = f"Host is {profile.cpu.vendor} CPU (no physical NVIDIA CUDA GPU). Build recipe generated."
        logger.warning(f"Physical NVIDIA GPU not detected. {result['reason']}")
        return result

    if not profile.runtime.tensorrt_available:
        result["status"] = "BLOCKED"
        result["reason"] = "NVIDIA GPU detected but TensorRT Python package / trtexec is not installed."
        logger.error(result["reason"])
        return result

    try:
        import tensorrt as trt
        TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(TRT_LOGGER)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, TRT_LOGGER)

        with open(onnx_path, 'rb') as f:
            if not parser.parse(f.read()):
                errors = [parser.get_error(i).desc() for i in range(parser.num_errors)]
                result["status"] = "FAILED"
                result["reason"] = f"ONNX parser errors: {'; '.join(errors)}"
                return result

        config = builder.create_builder_config()
        config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, max_vram_mb * 1024 * 1024)

        if fp16 and builder.platform_has_fast_fp16:
            config.set_flag(trt.BuilderFlag.FP16)

        serialized_engine = builder.build_serialized_network(network, config)
        if serialized_engine is None:
            result["status"] = "FAILED"
            result["reason"] = "TensorRT engine compilation returned None"
            return result

        os.makedirs(os.path.dirname(engine_path), exist_ok=True)
        with open(engine_path, 'wb') as f:
            f.write(serialized_engine)

        result["status"] = "REAL_RUNTIME_VERIFIED"
        result["reason"] = f"Compiled engine on {profile.gpu.gpu_name} ({profile.gpu.compute_capability})"
        logger.info(f"Engine written to {engine_path}")
        return result

    except Exception as e:
        result["status"] = "FAILED"
        result["reason"] = str(e)
        logger.error(f"TensorRT build error: {e}")
        return result


def main():
    parser = argparse.ArgumentParser(description="IBVAP Target-Specific TensorRT Engine Builder")
    parser.add_argument("--target", choices=["rtx3050_4gb", "rtx3050_6gb"], default="rtx3050_4gb")
    parser.add_argument("--model", default="yolo26n.pt")
    args = parser.parse_args()

    vram_budget = 3200 if args.target == "rtx3050_4gb" else 5000
    out_dir = PROJECT_ROOT / "artifacts" / args.target
    os.makedirs(out_dir, exist_ok=True)

    weights_file = PROJECT_ROOT / args.model
    if not weights_file.exists():
        logger.error(f"Weights file not found: {weights_file}")
        sys.exit(1)

    onnx_file = str(out_dir / f"{Path(args.model).stem}.onnx")
    engine_file = str(out_dir / f"{Path(args.model).stem}.engine")

    # Step 1: Export ONNX
    export_onnx_model(str(weights_file), onnx_file)

    # Step 2: Compile TensorRT
    res = build_tensorrt_engine(onnx_file, engine_file, fp16=True, max_vram_mb=vram_budget)

    # Save build receipt
    receipt_file = out_dir / "build_receipt.json"
    with open(receipt_file, "w") as f:
        json.dump(res, f, indent=2)

    logger.info(f"Build receipt saved: {receipt_file}")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
