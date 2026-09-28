<#
.SYNOPSIS
    Starts the full real IBVAP stack:
    1. MediaMTX RTSP/WebRTC Server
    2. FFmpeg CAM-01 Publisher
    3. FastAPI Backend
    4. Inference Worker (Detection + Tracking + Restricted Polygon + Telemetry Broadcast)
    5. React Operations Dashboard
#>

$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " STARTING IBVAP LOCAL SIH LIVE DEMONSTRATION" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Resolve paths
$IBVAP_ROOT = (Resolve-Path "$PSScriptRoot\..").Path
$bundledFfmpeg = "$IBVAP_ROOT\infrastructure\ffmpeg\bin\ffmpeg.exe"
if (Test-Path $bundledFfmpeg) {
    $ffmpegPath = $bundledFfmpeg
} else {
    $ffmpegCmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($ffmpegCmd) {
        $ffmpegPath = $ffmpegCmd.Source
    } else {
        $ffmpegPath = (Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter "ffmpeg.exe" -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
    }
}
$mediamtxExe = "infrastructure\mediamtx\mediamtx.exe"
$testVideo = "data\raw\test_video.mp4"

$venvPython = "$IBVAP_ROOT\..\venv\Scripts\python.exe"
$localVenv = "$IBVAP_ROOT\.venv\Scripts\python.exe"
$gpuVenv = "$IBVAP_ROOT\.venv_gpu\Scripts\python.exe"

if (Test-Path $gpuVenv) {
    $PYTHON_EXE = $gpuVenv
} elseif (Test-Path $venvPython) {
    $PYTHON_EXE = $venvPython
} elseif (Test-Path $localVenv) {
    $PYTHON_EXE = $localVenv
} else {
    $PYTHON_EXE = "python"
}

# Ensure directories exist
New-Item -ItemType Directory -Force -Path "data\evidence" | Out-Null

# 2. Start MediaMTX
Write-Host "`n[1/5] Starting MediaMTX RTSP/WebRTC Server on 127.0.0.1:8554 & 127.0.0.1:8889..." -ForegroundColor Yellow
$mtxProc = Start-Process -FilePath $mediamtxExe -ArgumentList "infrastructure\mediamtx\mediamtx.yml" -PassThru -NoNewWindow
Start-Sleep -Seconds 2

# 3. Start FFmpeg CAM-01 Publisher
Write-Host "[2/5] Publishing local video stream to rtsp://127.0.0.1:8554/CAM-01..." -ForegroundColor Yellow
$pubProc = Start-Process -FilePath $ffmpegPath -ArgumentList "-re -stream_loop -1 -i `"$testVideo`" -c copy -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:8554/CAM-01" -PassThru -NoNewWindow
Start-Sleep -Seconds 3

# 4. Start FastAPI Backend
Write-Host "[3/5] Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
$env:PYTHONPATH = "."
$backProc = Start-Process -FilePath $PYTHON_EXE -ArgumentList "-m uvicorn apps.backend.main:app --host 127.0.0.1 --port 8000" -PassThru -NoNewWindow
Start-Sleep -Seconds 3

# 5. Start Inference Worker
Write-Host "[4/5] Starting Real Inference Worker ($PYTHON_EXE + Tracker + Zones)..." -ForegroundColor Yellow
$workerProc = Start-Process -FilePath $PYTHON_EXE -ArgumentList "services\inference\main_inference_worker.py --camera CAM-01 --rtsp rtsp://127.0.0.1:8554/CAM-01" -PassThru -NoNewWindow
Start-Sleep -Seconds 3

# 6. Start Frontend Dashboard
Write-Host "[5/5] Starting React Operations Dashboard on http://localhost:5173..." -ForegroundColor Yellow
$frontProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory "apps\frontend" -PassThru -NoNewWindow
Start-Sleep -Seconds 3

# Record PIDs for clean shutdown
$pidsData = @{
    MediaMTX = $mtxProc.Id
    Publisher = $pubProc.Id
    Backend = $backProc.Id
    Inference = $workerProc.Id
    Frontend = $frontProc.Id
}
$pidsData | ConvertTo-Json | Set-Content "demo_pids.json"

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " IBVAP LIVE DEMO IS FULLY ACTIVE AND STREAMING!" -ForegroundColor Green
Write-Host " Open URL in Browser: http://localhost:5173" -ForegroundColor Cyan
Write-Host " Stop with: powershell scripts\stop_sih_demo.ps1" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Green
