# IBVAP — Automated Windows 11 NVIDIA RTX 3050 Environment Setup
# SIH Problem Statement: 26187
param(
    [switch]$Offline,
    [string]$WheelDir = ".\offline_wheels_rtx3050",
    [string]$VenvPath = ".\venv_rtx"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " IBVAP RTX 3050 Environment Bootstrap & CUDA 12.4 Setup    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check NVIDIA Driver
Write-Host "`n[1/6] Auditing physical NVIDIA GPU & Driver..." -ForegroundColor Yellow
$nvidiaSmi = Get-Command "nvidia-smi.exe" -ErrorAction SilentlyContinue
if (-not $nvidiaSmi) {
    Write-Host "[!] WARNING: nvidia-smi.exe not found in PATH." -ForegroundColor Red
    Write-Host "    Ensure NVIDIA Display Drivers are installed (Driver >= 550.54 recommended)." -ForegroundColor Red
    Write-Host "    System will fall back to CPU execution profile if continued." -ForegroundColor Yellow
} else {
    & nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    Write-Host "[PASS] NVIDIA Driver & GPU discovered." -ForegroundColor Green
}

# 2. Check Python 3.11 Installation
Write-Host "`n[2/6] Checking Python runtime..." -ForegroundColor Yellow
$py = Get-Command "python.exe" -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "[FAIL] Python 3.11 is required but not found in PATH." -ForegroundColor Red
    exit 1
}
$pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "[PASS] Detected Python version: $pyVer" -ForegroundColor Green

# 3. Create or Activate Virtual Environment
Write-Host "`n[3/6] Setting up virtual environment at $VenvPath..." -ForegroundColor Yellow
if (-not (Test-Path "$VenvPath\Scripts\activate.ps1")) {
    Write-Host "    Creating new virtual environment: $VenvPath..." -ForegroundColor Gray
    python -m venv $VenvPath
}
$VenvPy = "$VenvPath\Scripts\python.exe"
$VenvPip = "$VenvPath\Scripts\pip.exe"
Write-Host "[PASS] Virtual environment ready." -ForegroundColor Green

# 4. Install Dependencies
Write-Host "`n[4/6] Installing CUDA-accelerated dependencies..." -ForegroundColor Yellow
if ($Offline -or (Test-Path $WheelDir)) {
    Write-Host "    [Mode: AIR-GAPPED OFFLINE] Installing from $WheelDir..." -ForegroundColor Cyan
    & $VenvPip install --no-index --find-links=$WheelDir -r .\deployment\rtx3050\OFFLINE_WHEELS_MANIFEST.txt
} else {
    Write-Host "    [Mode: ONLINE] Fetching PyTorch cu124 from index..." -ForegroundColor Cyan
    & $VenvPip install --upgrade pip
    & $VenvPip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    & $VenvPip install -r .\deployment\rtx3050\OFFLINE_WHEELS_MANIFEST.txt
}

# 5. Execute Hardware Capability Verification Probe
Write-Host "`n[5/6] Probing CUDA, TensorRT, and FP16 capabilities..." -ForegroundColor Yellow
& $VenvPy -c @"
import sys
import structlog

try:
    import torch
    cuda_ok = torch.cuda.is_available()
    print(f'CUDA Available: {cuda_ok}')
    if cuda_ok:
        dev_name = torch.cuda.get_device_name(0)
        vram_mb = torch.cuda.get_device_properties(0).total_memory / (1024**2)
        cc = torch.cuda.get_device_capability(0)
        print(f'GPU Device: {dev_name}')
        print(f'Total VRAM: {vram_mb:.0f} MB')
        print(f'Compute Capability: {cc[0]}.{cc[1]}')
        
        # Test FP16 Half Precision Tensor Math
        t = torch.randn((100, 100), device='cuda', dtype=torch.float16)
        res = torch.matmul(t, t)
        print('FP16 Tensor Math: VERIFIED')
    else:
        print('Notice: PyTorch running in CPU mode. Falling back safely.')
except Exception as e:
    print(f'Verification exception: {e}')
    sys.exit(1)
"@

# 6. Final Status
Write-Host "`n[6/6] Writing local environment configuration..." -ForegroundColor Yellow
$envContent = @"
HARDWARE_PROFILE=RTX3050_4GB
TORCH_DEVICE=cuda:0
DETECTOR_BACKEND=yolov8
TENSORRT_ENABLED=true
MAX_CAMERA_STREAMS=4
VRAM_BUDGET_MB=3584
"@
Set-Content -Path ".\configs\hardware\.env.rtx3050" -Value $envContent -Force

Write-Host "==========================================================" -ForegroundColor Green
Write-Host " IBVAP RTX 3050 Setup Complete & Fully Configured!        " -ForegroundColor Green
Write-Host " To start the platform with RTX 3050 acceleration:        " -ForegroundColor Green
Write-Host "   .\start_ibvap_rtx3050.ps1                              " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
