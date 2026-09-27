# Edge Deployment Guide

This directory contains container specs, systemd unit templates, and provisioning playbooks for running IBVAP on standalone, low-power industrial edge devices (NVIDIA Jetson, Intel Industrial NUCs).

## Hardware Targets
- **NVIDIA Jetson Orin Series**: JetPack 6.x, TensorRT, GStreamer hardware acceleration.
- **Intel Industrial N100 / Core i3**: Ubuntu Server 22.04 LTS, OpenVINO runtime or CPU-only Ultralytics.

See `docs/EDGE_DEPLOYMENT.md` for architectural specifications.
