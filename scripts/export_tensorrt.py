"""
IBVAP NVIDIA TensorRT Production Model Exporter
SIH PS-26187: Hardware-Agnostic Intelligent Surveillance

Exports PyTorch/YOLOv8 weights to high-throughput NVIDIA TensorRT (.engine) format
for deployment on NVIDIA Jetson Orin / RTX edge appliances.
"""

import os
import sys
import argparse
import structlog

logger = structlog.get_logger()

def export_to_tensorrt(
    model_path: str = "models/yolov8n.pt",
    imgsz: int = 640,
    device: int = 0,
    half: bool = True,
    dynamic: bool = False
):
    """
    Exports YOLOv8 weights to an optimized TensorRT engine.
    """
    try:
        import torch
        if not torch.cuda.is_available():
            logger.error("CUDA is not available on this host. TensorRT export requires an NVIDIA GPU.")
            print("[ERROR] NVIDIA GPU with CUDA drivers required for TensorRT compilation.")
            return False

        from ultralytics import YOLO
        print(f"[*] Loading model from: {model_path}")
        model = YOLO(model_path)

        print(f"[*] Exporting to TensorRT (half={half}, imgsz={imgsz}, dynamic={dynamic})...")
        engine_path = model.export(
            format="engine",
            imgsz=imgsz,
            device=device,
            half=half,
            dynamic=dynamic
        )
        print(f"[+] Successfully exported TensorRT engine: {engine_path}")
        logger.info("TensorRT export complete", engine_path=str(engine_path))
        return True
    except ImportError as e:
        logger.error("Required libraries (torch, ultralytics) missing", error=str(e))
        return False
    except Exception as e:
        logger.error("TensorRT export failed", error=str(e))
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IBVAP NVIDIA TensorRT Model Exporter")
    parser.add_argument("--model", default="models/yolov8n.pt", help="Path to input PyTorch model")
    parser.add_argument("--imgsz", type=int, default=640, help="Inference resolution")
    parser.add_argument("--device", type=int, default=0, help="CUDA device index")
    parser.add_argument("--fp32", action="store_true", help="Use FP32 instead of FP16")
    args = parser.parse_args()

    success = export_to_tensorrt(
        model_path=args.model,
        imgsz=args.imgsz,
        device=args.device,
        half=not args.fp32
    )
    sys.exit(0 if success else 1)
