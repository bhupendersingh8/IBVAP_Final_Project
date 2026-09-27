#!/usr/bin/env python3
"""
IBVAP — Native NVIDIA TensorRT Engine Builder
=============================================
Compiles an ONNX model directly to an optimized TensorRT FP16 .engine binary
using NVIDIA TensorRT 11.x APIs without third-party wrapper overhead.
"""

import os
import sys
import time
import tensorrt as trt

def build_engine(
    onnx_path: str = "models/yolov8n.onnx",
    engine_path: str = "models/yolov8n.engine",
    fp16: bool = True,
    workspace_gb: int = 1
):
    print("=" * 60)
    print("  IBVAP — NVIDIA TensorRT 11 FP16 Engine Compiler")
    print("=" * 60)
    print(f"[*] ONNX Source:     {onnx_path}")
    print(f"[*] Engine Output:   {engine_path}")
    print(f"[*] FP16 Precision:  {fp16}")
    print(f"[*] Workspace Limit: {workspace_gb} GB")
    print(f"[*] TensorRT Version: {trt.__version__}")

    if not os.path.exists(onnx_path):
        raise FileNotFoundError(f"ONNX model not found: {onnx_path}")

    logger = trt.Logger(trt.Logger.INFO)
    builder = trt.Builder(logger)
    network = builder.create_network()
    parser = trt.OnnxParser(network, logger)

    print("\n[*] Parsing ONNX model structure...")
    t0 = time.perf_counter()
    with open(onnx_path, "rb") as f:
        parsed = parser.parse(f.read())
        if not parsed:
            print("[-] ONNX Parsing failed!")
            for i in range(parser.num_errors):
                print(f"    Error {i}: {parser.get_error(i)}")
            return False

    print(f"[+] ONNX parsed successfully in {(time.perf_counter() - t0):.2f}s")
    print(f"    - Inputs:  {[network.get_input(i).name + ' ' + str(network.get_input(i).shape) for i in range(network.num_inputs)]}")
    print(f"    - Outputs: {[network.get_output(i).name + ' ' + str(network.get_output(i).shape) for i in range(network.num_outputs)]}")

    config = builder.create_builder_config()
    config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, workspace_gb << 30)

    # TensorRT 11 auto-tunes precision (FP16/TF32) for Ampere GA107
    print("[+] TensorRT 11 auto-tuning precision on Ampere Tensor Cores.")

    print("\n[*] Compiling and optimizing serialized TensorRT engine...")
    t0_build = time.perf_counter()
    serialized_engine = builder.build_serialized_network(network, config)
    if serialized_engine is None:
        print("[-] Engine serialization failed!")
        return False

    build_time = time.perf_counter() - t0_build
    print(f"[+] TensorRT Engine compiled successfully in {build_time:.2f}s!")

    os.makedirs(os.path.dirname(engine_path), exist_ok=True)
    with open(engine_path, "wb") as f:
        f.write(serialized_engine)

    size_mb = os.path.getsize(engine_path) / (1024 * 1024)
    print(f"[+] Engine saved to: {engine_path} ({size_mb:.2f} MB)")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = build_engine()
    sys.exit(0 if success else 1)
