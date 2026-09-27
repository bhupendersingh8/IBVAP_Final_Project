# NVIDIA Deployment Directory

This directory contains configuration templates, model export recipes, and execution runbooks for deploying IBVAP on NVIDIA GPU accelerators (T4, A30, RTX series) and embedded Jetson modules using NVIDIA DeepStream 9.1 and TensorRT.

## Key Assets

- `deepstream_config_template.txt`: Standard DeepStream GStreamer pipeline definition integrating `nvurisrcbin`, `nvstreammux`, `nvinfer`, and `nvtracker`.
- See `docs/NVIDIA_DEPLOYMENT.md` for full hardware benchmarks, prerequisites, and integration architecture.
