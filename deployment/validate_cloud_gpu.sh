#!/usr/bin/env bash
# IBVAP — Cloud / Remote NVIDIA GPU 1-Click Validation Launcher
# SIH Problem Statement: 26187 | Tactical Border Surveillance

set -e

echo "=========================================================="
echo " Starting IBVAP Cloud / Remote GPU Validation"
echo "=========================================================="

# Check Python environment
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

$PYTHON_CMD -c "import sys; print(f'Python Interpreter: {sys.executable}')"

# Run validation
$PYTHON_CMD deployment/validate_cloud_gpu.py
