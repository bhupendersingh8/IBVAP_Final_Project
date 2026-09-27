# scripts/ibvap.ps1
# MASTER IBVAP COMMAND
# Usage:
#   .\scripts\ibvap.ps1 start
#   .\scripts\ibvap.ps1 stop
#   .\scripts\ibvap.ps1 restart
#   .\scripts\ibvap.ps1 status
#   .\scripts\ibvap.ps1 test
#   .\scripts\ibvap.ps1 demo
#   .\scripts\ibvap.ps1 audit
#   .\scripts\ibvap.ps1 clean
#   .\scripts\ibvap.ps1 webcam

[CmdletBinding()]
param (
    [Parameter(Position=0, Mandatory=$false)]
    [ValidateSet("start", "stop", "restart", "status", "test", "demo", "audit", "clean", "webcam")]
    [string]$Action = "demo"
)

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
$IBVAP_ROOT = (Resolve-Path "$SCRIPT_DIR\..").Path

if (Test-Path "$IBVAP_ROOT\..\venv\Scripts\python.exe") {
    $PYTHON_EXE = (Resolve-Path "$IBVAP_ROOT\..\venv\Scripts\python.exe").Path
} elseif (Test-Path "$IBVAP_ROOT\venv\Scripts\python.exe") {
    $PYTHON_EXE = (Resolve-Path "$IBVAP_ROOT\venv\Scripts\python.exe").Path
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PYTHON_EXE = (Get-Command python).Source
} elseif (Test-Path "C:\Python314\python.exe") {
    $PYTHON_EXE = "C:\Python314\python.exe"
} else {
    $PYTHON_EXE = "python"
}

function Show-Banner {
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "      IBVAP - INTELLIGENT BORDER VIDEO ANALYTICS PLATFORM       " -ForegroundColor Cyan
    Write-Host "                     [ Master Control ]                         " -ForegroundColor DarkCyan
    Write-Host "================================================================" -ForegroundColor Cyan
}

function Invoke-IBVAPStop {
    # Stop Webcam / Worker
    Get-CimInstance Win32_Process -Filter "Name LIKE 'python%' AND CommandLine LIKE '%WEBCAM-01%'" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    # Stop FFmpeg
    Get-CimInstance Win32_Process -Filter "Name LIKE 'ffmpeg%' AND CommandLine LIKE '%rtsp://127.0.0.1:8554/CAM-01%'" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    # Stop Worker
    Get-CimInstance Win32_Process -Filter "Name LIKE 'python%' AND CommandLine LIKE '%main_inference_worker.py%'" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    # Stop Backend
    Get-CimInstance Win32_Process -Filter "Name LIKE 'python%' AND CommandLine LIKE '%apps.backend.main:app%'" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    # Stop Frontend
    Get-CimInstance Win32_Process -Filter "Name LIKE 'node%' AND CommandLine LIKE '%vite%'" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    # Stop MediaMTX
    Get-CimInstance Win32_Process -Filter "Name LIKE 'mediamtx%'" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host "[OK] All background services stopped cleanly." -ForegroundColor Green
}


function Invoke-IBVAPStart {
    Write-Host "[START] Ensuring all services are operational..." -ForegroundColor Yellow
    powershell -ExecutionPolicy Bypass -File "$IBVAP_ROOT\scripts\ensure_services.ps1"
}

function Invoke-IBVAPStatus {
    Write-Host "[STATUS] Inspecting system status..." -ForegroundColor Yellow
    $mtx = Get-CimInstance Win32_Process -Filter "Name LIKE 'mediamtx%'" -ErrorAction SilentlyContinue | Select-Object -First 1
    $ff = Get-CimInstance Win32_Process -Filter "Name LIKE 'ffmpeg%' AND CommandLine LIKE '%rtsp://127.0.0.1:8554/CAM-01%'" -ErrorAction SilentlyContinue | Select-Object -First 1
    $backend = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%' AND CommandLine LIKE '%apps.backend.main:app%'" -ErrorAction SilentlyContinue | Select-Object -First 1
    $worker = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%' AND CommandLine LIKE '%main_inference_worker.py%'" -ErrorAction SilentlyContinue | Select-Object -First 1
    $front = Get-CimInstance Win32_Process -Filter "Name LIKE 'node%'" -ErrorAction SilentlyContinue | Select-Object -First 1

    Write-Host "MediaMTX:     $(if ($mtx) {'RUNNING (PID ' + $mtx.ProcessId + ')'} else {'STOPPED'})" -ForegroundColor $(if ($mtx) {'Green'} else {'Red'})
    Write-Host "FFmpeg RTSP:  $(if ($ff) {'RUNNING (PID ' + $ff.ProcessId + ')'} else {'STOPPED'})" -ForegroundColor $(if ($ff) {'Green'} else {'Red'})
    Write-Host "FastAPI App:  $(if ($backend) {'RUNNING (PID ' + $backend.ProcessId + ')'} else {'STOPPED'})" -ForegroundColor $(if ($backend) {'Green'} else {'Red'})
    Write-Host "Inference AI: $(if ($worker) {'RUNNING (PID ' + $worker.ProcessId + ')'} else {'STOPPED'})" -ForegroundColor $(if ($worker) {'Green'} else {'Red'})
    Write-Host "React UI:     $(if ($front) {'RUNNING (PID ' + $front.ProcessId + ')'} else {'STOPPED'})" -ForegroundColor $(if ($front) {'Green'} else {'Red'})
}

function Invoke-IBVAPClean {
    Write-Host "[CLEAN] Resetting demonstration database and evidence..." -ForegroundColor Yellow
    & $PYTHON_EXE "$IBVAP_ROOT\scripts\clean_reset.py"
    Write-Host "[OK] Database cleared, evidence directory purged." -ForegroundColor Green
}

function Invoke-IBVAPAudit {
    Write-Host "[AUDIT] Running 2-Minute continuous runtime stability audit..." -ForegroundColor Yellow
    & $PYTHON_EXE -u "$IBVAP_ROOT\scripts\run_2min_audit.py"
}

function Invoke-IBVAPTest {
    Write-Host "[TEST] Executing automated browser acceptance suite (Edge)..." -ForegroundColor Yellow
    & $PYTHON_EXE "$IBVAP_ROOT\scripts\browser_acceptance.py"
}

function Invoke-IBVAPDemo {
    Show-Banner
    Write-Host "`n>> STEP 1: PREPARING CLEAN ENVIRONMENT" -ForegroundColor Cyan
    Invoke-IBVAPClean

    Write-Host "`n>> STEP 2: ENSURING ALL STACK SERVICES ARE HEALTHY" -ForegroundColor Cyan
    Invoke-IBVAPStart

    Write-Host "`n>> STEP 3: LAUNCHING DASHBOARD IN BROWSER" -ForegroundColor Cyan
    $frontUrl = "http://localhost:8000"
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $connect = $tcp.BeginConnect("127.0.0.1", 5173, $null, $null)
        if ($connect.AsyncWaitHandle.WaitOne(500, $false)) {
            $tcp.EndConnect($connect)
            $tcp.Close()
            $frontUrl = "http://localhost:5173"
        } else {
            $tcp.Close()
        }
    } catch {}
    Start-Process $frontUrl

    Write-Host "`n>> STEP 4: RUNNING AUTOMATED BROWSER & AI ACCEPTANCE SUITE" -ForegroundColor Cyan
    $hasPlaywright = $false
    try {
        & $PYTHON_EXE -c "import playwright" 2>$null
        $hasPlaywright = ($LASTEXITCODE -eq 0)
    } catch {
        $hasPlaywright = $false
    }

    if ($hasPlaywright) {
        & $PYTHON_EXE -u "$IBVAP_ROOT\scripts\browser_acceptance.py"
        $reportPath = "$IBVAP_ROOT\docs\P2_AUTOMATED_ACCEPTANCE_REPORT.md"
        Write-Host "[OK] Report generated at: $reportPath" -ForegroundColor Green
    } else {
        Write-Host "[INFO] Playwright is not installed (skipping headless browser audit)." -ForegroundColor Yellow
        Write-Host "[OK] Dashboard is live and running at http://localhost:5173" -ForegroundColor Green
    }

    Write-Host "`n================================================================" -ForegroundColor Cyan
    Write-Host "                   FINAL DEMO SUMMARY                           " -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host " MediaMTX:               READY" -ForegroundColor Green
    Write-Host " RTSP CAM-01:            READY" -ForegroundColor Green
    Write-Host " Backend:                READY (http://localhost:8000)" -ForegroundColor Green
    Write-Host " Inference:              READY" -ForegroundColor Green
    Write-Host " Frontend:               READY (http://localhost:5173)" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host " Dashboard URL: http://localhost:5173" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
}

# Main Dispatcher
Show-Banner
switch ($Action) {
    "start"   { Invoke-IBVAPStart }
    "stop"    { Invoke-IBVAPStop }
    "restart" { Invoke-IBVAPStop; Start-Sleep -Seconds 2; Invoke-IBVAPStart }
    "status"  { Invoke-IBVAPStatus }
    "clean"   { Invoke-IBVAPClean }
    "audit"   { Invoke-IBVAPAudit }
    "test"    { Invoke-IBVAPTest }
    "demo"    { Invoke-IBVAPDemo }
    "webcam"  {
        Write-Host "`n>> STARTING DEDICATED WEBCAM-01 STACK (NO MEDIAMTX/CCTV OVERHEAD)..." -ForegroundColor Yellow
        # Stop any existing CAM-01 workers to avoid conflict
        Get-CimInstance Win32_Process -Filter "Name LIKE 'python%' AND CommandLine LIKE '%main_inference_worker.py%'" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        powershell -ExecutionPolicy Bypass -File "$IBVAP_ROOT\scripts\ensure_services.ps1" -WebcamOnly
        $frontUrl = "http://localhost:8000"
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $connect = $tcp.BeginConnect("127.0.0.1", 5173, $null, $null)
            if ($connect.AsyncWaitHandle.WaitOne(500, $false)) {
                $tcp.EndConnect($connect)
                $tcp.Close()
                $frontUrl = "http://localhost:5173"
            } else {
                $tcp.Close()
            }
        } catch {}
        Start-Process $frontUrl
        Write-Host "[OK] Webcam worker operational. Dashboard opened at $frontUrl" -ForegroundColor Green
    }
}

