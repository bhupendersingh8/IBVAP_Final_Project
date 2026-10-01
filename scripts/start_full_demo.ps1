# scripts/start_full_demo.ps1
# Starts all components of IBVAP in order: MediaMTX, FFmpeg Streamer, Backend API, Worker, and Frontend

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   IBVAP FULL STACK DEMO STARTER          " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$IBVAP_ROOT = (Resolve-Path "$PSScriptRoot\..").Path
$rtxVenv = "$IBVAP_ROOT\venv_rtx\Scripts\python.exe"
$baselineGpuVenv = "$IBVAP_ROOT\..\IBVAP_Final_Project\.venv_gpu\Scripts\python.exe"
$gpuVenv = "$IBVAP_ROOT\.venv_gpu\Scripts\python.exe"
$localVenv = "$IBVAP_ROOT\.venv\Scripts\python.exe"

if (Test-Path $rtxVenv) {
    $PYTHON_EXE = $rtxVenv
} elseif (Test-Path $baselineGpuVenv) {
    $PYTHON_EXE = $baselineGpuVenv
} elseif (Test-Path $gpuVenv) {
    $PYTHON_EXE = $gpuVenv
} elseif (Test-Path $localVenv) {
    $PYTHON_EXE = $localVenv
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PYTHON_EXE = (Get-Command python).Source
} else {
    $PYTHON_EXE = "python"
}

# 1. MediaMTX
$mtx = Get-Process -Name mediamtx -ErrorAction SilentlyContinue
if (-not $mtx) {
    Write-Host "[1/5] Starting MediaMTX..." -ForegroundColor Yellow
    Start-Process -FilePath "$IBVAP_ROOT\infrastructure\mediamtx\mediamtx.exe" -ArgumentList "$IBVAP_ROOT\infrastructure\mediamtx\mediamtx.yml" -WorkingDirectory "$IBVAP_ROOT\infrastructure\mediamtx" -WindowStyle Hidden
    Start-Sleep -Seconds 2
} else {
    Write-Host "[1/5] MediaMTX is already running (PID $($mtx.Id))." -ForegroundColor Green
}

# 2. FFmpeg Publisher
$ff = Get-Process -Name ffmpeg -ErrorAction SilentlyContinue
if (-not $ff) {
    Write-Host "[2/5] Starting FFmpeg RTSP Streamer for CAM-01..." -ForegroundColor Yellow
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
    Start-Process -FilePath $ffmpegPath -ArgumentList "-re -stream_loop -1 -i `"$IBVAP_ROOT\data\raw\test_video.mp4`" -c copy -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:8554/CAM-01" -WorkingDirectory $IBVAP_ROOT -WindowStyle Hidden
    Start-Sleep -Seconds 2
} else {
    Write-Host "[2/5] FFmpeg RTSP Streamer is already running (PID $($ff.Id))." -ForegroundColor Green
}

# 3. Backend API
$backend = Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%uvicorn apps.backend.main:app%'" -ErrorAction SilentlyContinue
if (-not $backend) {
    Write-Host "[3/5] Starting FastAPI Backend on :8000..." -ForegroundColor Yellow
    Start-Process -FilePath $PYTHON_EXE -ArgumentList "-m uvicorn apps.backend.main:app --host 127.0.0.1 --port 8000" -WorkingDirectory $IBVAP_ROOT -WindowStyle Hidden
    Start-Sleep -Seconds 3
} else {
    Write-Host "[3/5] FastAPI Backend is already running (PID $($backend.ProcessId))." -ForegroundColor Green
}

# 4. Inference Worker
$worker = Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%main_inference_worker.py%'" -ErrorAction SilentlyContinue
if (-not $worker) {
    Write-Host "[4/5] Starting Main Inference Worker..." -ForegroundColor Yellow
    Start-Process -FilePath $PYTHON_EXE -ArgumentList "services\inference\main_inference_worker.py --camera CAM-01 --rtsp rtsp://127.0.0.1:8554/CAM-01" -WorkingDirectory $IBVAP_ROOT -WindowStyle Hidden
    Start-Sleep -Seconds 3
} else {
    Write-Host "[4/5] Main Inference Worker is already running (PID $($worker.ProcessId))." -ForegroundColor Green
}

# 5. Frontend
$frontend = Get-Process -Name node -ErrorAction SilentlyContinue
if (-not $frontend) {
    Write-Host "[5/5] Starting Vite Frontend on :5173..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory "$IBVAP_ROOT\apps\frontend" -WindowStyle Hidden
    Start-Sleep -Seconds 3
} else {
    Write-Host "[5/5] Vite Frontend is already running." -ForegroundColor Green
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " DEMO RUNNING: http://localhost:5173" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
