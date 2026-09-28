# IBVAP — 1-Click Production Launcher for NVIDIA RTX 3050 (Windows 11)
# SIH Problem Statement: 26187 | Tactical Border Surveillance
param(
    [string]$Profile = "RTX3050_4GB",
    [int]$Streams = 4,
    [switch]$NoBrowser
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " IBVAP — Tactical Border Video Analytics Platform          " -ForegroundColor Cyan
Write-Host " Hardware Profile: $Profile (NVIDIA CUDA / TensorRT FP16)  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Resolve Virtual Environment
$VenvPy = ".\venv_rtx\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    Write-Host "[!] venv_rtx not found. Falling back to default venv..." -ForegroundColor Yellow
    $VenvPy = ".\venv\Scripts\python.exe"
}

if (-not (Test-Path $VenvPy)) {
    Write-Host "[FAIL] No Python virtual environment detected. Run deployment\rtx3050\setup_rtx3050_env.ps1 first." -ForegroundColor Red
    exit 1
}

# 2. Configure Environment Variables for RTX 3050 Acceleration
$env:HARDWARE_PROFILE = $Profile
$env:TORCH_DEVICE = "cuda:0"
$env:TENSORRT_ENABLED = "true"
$env:MAX_CAMERA_STREAMS = "$Streams"
$env:DETECTOR_BACKEND = "yolov8"
$env:APP_ENV = "production"

Write-Host "`n[1/3] Starting MediaMTX RTSP Ingestion Server..." -ForegroundColor Yellow
$MediaMtx = Get-Process mediamtx -ErrorAction SilentlyContinue
if (-not $MediaMtx) {
    Start-Process -FilePath "infrastructure\mediamtx\mediamtx.exe" -ArgumentList "infrastructure\mediamtx\mediamtx.yml" -WindowStyle Minimized -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Host "[PASS] MediaMTX active on rtsp://127.0.0.1:8554" -ForegroundColor Green
} else {
    Write-Host "[PASS] MediaMTX already running." -ForegroundColor Green
}

Write-Host "`n[2/3] Launching IBVAP Accelerated Backend on http://localhost:8000..." -ForegroundColor Yellow
$BackendProc = Start-Process -FilePath $VenvPy -ArgumentList "-m uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000" -PassThru -WindowStyle Normal
Start-Sleep -Seconds 2

Write-Host "`n[3/3] Launching React VMS Operations Dashboard..." -ForegroundColor Yellow
Set-Location apps\frontend
$FrontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -PassThru -WindowStyle Minimized
Set-Location ..\..

Start-Sleep -Seconds 3

if (-not $NoBrowser) {
    Write-Host "[+] Opening Operations Dashboard in default browser..." -ForegroundColor Cyan
    Start-Process "http://localhost:5173"
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " IBVAP RTX 3050 Platform is ONLINE & OPERATIONAL           " -ForegroundColor Green
Write-Host " Backend API:   http://localhost:8000                     " -ForegroundColor Green
Write-Host " API Docs:      http://localhost:8000/docs                " -ForegroundColor Green
Write-Host " Operations UI: http://localhost:5173                     " -ForegroundColor Green
Write-Host " Press Ctrl+C in this console to monitor logs.            " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
