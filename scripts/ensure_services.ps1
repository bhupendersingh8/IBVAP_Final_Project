# scripts/ensure_services.ps1
# Reliably inspects exact IBVAP services using ports, command lines, and health endpoints.
# Starts only missing services without duplicating processes.

[CmdletBinding()]
param(
    [switch]$ForceRestart,
    [switch]$WebcamOnly
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " IBVAP SERVICE ORCHESTRATOR & HEALTH CHECK" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
$IBVAP_ROOT = (Resolve-Path "$SCRIPT_DIR\..").Path

if (Test-Path "$IBVAP_ROOT\..\venv\Scripts\python.exe") {
    $PYTHON_EXE = (Resolve-Path "$IBVAP_ROOT\..\venv\Scripts\python.exe").Path
} elseif (Test-Path "$IBVAP_ROOT\venv\Scripts\python.exe") {
    $PYTHON_EXE = (Resolve-Path "$IBVAP_ROOT\venv\Scripts\python.exe").Path
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PYTHON_EXE = (Get-Command python).Source
} else {
    $PYTHON_EXE = "python"
}

function Test-PortOpen([string]$HostName, [int]$Port) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $connect = $tcp.BeginConnect($HostName, $Port, $null, $null)
        $wait = $connect.AsyncWaitHandle.WaitOne(1000, $false)
        if ($wait) {
            $tcp.EndConnect($connect)
            $tcp.Close()
            return $true
        }
        $tcp.Close()
        return $false
    } catch {
        return $false
    }
}

function Wait-UntilReady([scriptblock]$CheckBlock, [string]$ServiceName, [int]$TimeoutSec = 20) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
        if (& $CheckBlock) {
            Write-Host "[OK] $ServiceName is READY ($([math]::Round($sw.Elapsed.TotalSeconds, 1))s)." -ForegroundColor Green
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    Write-Host "[ERROR] $ServiceName FAILED readiness check within ${TimeoutSec}s." -ForegroundColor Red
    return $false
}

# 1. MediaMTX (Skipped in WebcamOnly mode)
if (-not $WebcamOnly) {
    Write-Host "`n[1/5] Checking MediaMTX Service..." -ForegroundColor Gray
    $mtxProc = Get-CimInstance Win32_Process -Filter "Name LIKE 'mediamtx%'" -ErrorAction SilentlyContinue
    $mtxPort = Test-PortOpen "127.0.0.1" 8554

    if ($ForceRestart -and $mtxProc) {
        Stop-Process -Id $mtxProc.ProcessId -Force -ErrorAction SilentlyContinue
        $mtxProc = $null
    }

    if (-not $mtxProc -or -not $mtxPort) {
        Write-Host "Starting MediaMTX (infrastructure\mediamtx\mediamtx.exe)..." -ForegroundColor Yellow
        Start-Process -FilePath "$IBVAP_ROOT\infrastructure\mediamtx\mediamtx.exe" -ArgumentList "$IBVAP_ROOT\infrastructure\mediamtx\mediamtx.yml" -WorkingDirectory "$IBVAP_ROOT\infrastructure\mediamtx" -WindowStyle Hidden
    }

    $mtxReady = Wait-UntilReady { Test-PortOpen "127.0.0.1" 8554 -and (Test-PortOpen "127.0.0.1" 8889) } "MediaMTX (RTSP:8554, WebRTC:8889)"
} else {
    $mtxReady = $true
}

# 2. FFmpeg RTSP Publisher (Skipped in WebcamOnly mode)
if (-not $WebcamOnly) {
    Write-Host "`n[2/5] Checking FFmpeg RTSP Publisher for CAM-01..." -ForegroundColor Gray
    $ffProc = Get-CimInstance Win32_Process -Filter "Name LIKE 'ffmpeg%' AND CommandLine LIKE '%rtsp://127.0.0.1:8554/CAM-01%'" -ErrorAction SilentlyContinue

    if ($ForceRestart -and $ffProc) {
        Stop-Process -Id $ffProc.ProcessId -Force -ErrorAction SilentlyContinue
        $ffProc = $null
    }

    if (-not $ffProc) {
        Write-Host "Starting FFmpeg publisher for CAM-01..." -ForegroundColor Yellow
        $ffmpegPath = "ffmpeg.exe"
        if (Test-Path "$IBVAP_ROOT\infrastructure\ffmpeg\bin\ffmpeg.exe") {
            $ffmpegPath = "$IBVAP_ROOT\infrastructure\ffmpeg\bin\ffmpeg.exe"
        } elseif (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
            $found = (Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter "ffmpeg.exe" -ErrorAction SilentlyContinue | Select-Object -First 1)
            if ($found) { $ffmpegPath = $found.FullName }
        }
        Start-Process -FilePath $ffmpegPath -ArgumentList "-re -stream_loop -1 -i `"$IBVAP_ROOT\data\raw\test_video.mp4`" -c copy -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:8554/CAM-01" -WorkingDirectory $IBVAP_ROOT -WindowStyle Hidden
    }

    $camReady = Wait-UntilReady {
        try {
            $res = Invoke-WebRequest -Uri "http://127.0.0.1:8889/CAM-01/" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            return ($res.StatusCode -eq 200)
        } catch { return $false }
    } "RTSP CAM-01 WebRTC Stream"
} else {
    $camReady = $true
}

# 3. FastAPI Backend
Write-Host "`n[3/5] Checking FastAPI Backend (:8000)..." -ForegroundColor Gray
$backendProc = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%' AND CommandLine LIKE '%apps.backend.main:app%'" -ErrorAction SilentlyContinue

if ($ForceRestart -and $backendProc) {
    Stop-Process -Id $backendProc.ProcessId -Force -ErrorAction SilentlyContinue
    $backendProc = $null
}

if (-not $backendProc) {
    Write-Host "Starting FastAPI Backend..." -ForegroundColor Yellow
    Start-Process -FilePath $PYTHON_EXE -ArgumentList "-m uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory $IBVAP_ROOT -WindowStyle Hidden
}

$backendReady = Wait-UntilReady {
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -ErrorAction Stop
        return ($res.status -eq "ok")
    } catch { return $false }
} "FastAPI Backend (/health)"

# 4. Inference Worker
Write-Host "`n[4/5] Checking Inference Worker..." -ForegroundColor Gray
$workerCamera = if ($WebcamOnly) { "WEBCAM-01" } else { "CAM-01" }
$workerRtsp = if ($WebcamOnly) { "webcam:0" } else { "rtsp://127.0.0.1:8554/CAM-01" }

$workerProc = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%' AND CommandLine LIKE '%main_inference_worker.py%'" -ErrorAction SilentlyContinue

# If worker is running for a different camera, restart it for the requested camera
if ($workerProc -and ($ForceRestart -or ($workerProc.CommandLine -notlike "*--camera $workerCamera*"))) {
    Write-Host "Stopping previous worker process (PID: $($workerProc.ProcessId)) to switch to $workerCamera..." -ForegroundColor Yellow
    Stop-Process -Id $workerProc.ProcessId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
    $workerProc = $null
}

if (-not $workerProc) {
    Write-Host "Starting Inference Worker for $workerCamera..." -ForegroundColor Yellow
    Start-Process -FilePath $PYTHON_EXE -ArgumentList "services\inference\main_inference_worker.py --camera $workerCamera --rtsp $workerRtsp" -WorkingDirectory $IBVAP_ROOT -WindowStyle Hidden
}

$workerReady = Wait-UntilReady {
    $p = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%' AND CommandLine LIKE '%main_inference_worker.py%'" -ErrorAction SilentlyContinue
    return ($p -ne $null)
} "Inference Worker ($workerCamera)"

# 5. Frontend
Write-Host "`n[5/5] Checking React Frontend..." -ForegroundColor Gray
$nodeProc = Get-CimInstance Win32_Process -Filter "Name LIKE 'node%'" -ErrorAction SilentlyContinue
$frontPort = Test-PortOpen "127.0.0.1" 5173

if ($ForceRestart -and $nodeProc) {
    Stop-Process -Id $nodeProc.ProcessId -Force -ErrorAction SilentlyContinue
    $nodeProc = $null
}

if (-not $frontPort -and (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "Starting Vite Dev Server..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory "$IBVAP_ROOT\apps\frontend" -WindowStyle Hidden
}

$frontReady = Wait-UntilReady {
    try {
        $res = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        return ($res.StatusCode -eq 200)
    } catch {
        if (Test-Path "$IBVAP_ROOT\apps\frontend\dist\index.html") {
            try {
                $res8000 = Invoke-WebRequest -Uri "http://localhost:8000/" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
                return ($res8000.StatusCode -eq 200)
            } catch { return $false }
        }
        return $false
    }
} "React Frontend (UI Dashboard)"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " SERVICE STATUS SUMMARY:" -ForegroundColor Cyan
Write-Host " MediaMTX:    $(if ($mtxReady) {'READY'} else {'FAIL'})" -ForegroundColor $(if ($mtxReady) {'Green'} else {'Red'})
Write-Host " CAM-01 RTSP: $(if ($camReady) {'READY'} else {'FAIL'})" -ForegroundColor $(if ($camReady) {'Green'} else {'Red'})
Write-Host " Backend:     $(if ($backendReady) {'READY'} else {'FAIL'})" -ForegroundColor $(if ($backendReady) {'Green'} else {'Red'})
Write-Host " Inference:   $(if ($workerReady) {'READY'} else {'FAIL'})" -ForegroundColor $(if ($workerReady) {'Green'} else {'Red'})
Write-Host " Frontend:    $(if ($frontReady) {'READY'} else {'FAIL'})" -ForegroundColor $(if ($frontReady) {'Green'} else {'Red'})
Write-Host "==========================================" -ForegroundColor Cyan
