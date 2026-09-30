<#
.SYNOPSIS
    Ralph Loop Autonomous Iteration Harness for IBVAP
.DESCRIPTION
    Implements the Ralph Wiggum autonomous execution pattern on Windows PowerShell.
    Iteratively executes verification tests, logs progress to .gsd/STATE.md, and maintains
    a clean loop without memory/context exhaustion.
#>
param(
    [int]$MaxIterations = 10,
    [switch]$RunTestsOnly
)

$ErrorActionPreference = "Continue"
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  IBVAP - Ralph Autonomous Execution Loop                 " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$Iteration = 1
while ($Iteration -le $MaxIterations) {
    Write-Host "`n>>> [Iteration $Iteration/$MaxIterations] Starting cycle..." -ForegroundColor Yellow
    
    # 1. Check frontend build integrity
    Write-Host " [Step 1] Auditing Frontend TypeScript & Vite build..." -ForegroundColor Cyan
    Push-Location "apps\frontend"
    npm run build --silent
    $FrontendStatus = $LASTEXITCODE
    Pop-Location

    if ($FrontendStatus -ne 0) {
        Write-Host " [!] Frontend build failed with exit code $FrontendStatus" -ForegroundColor Red
    } else {
        Write-Host " [PASS] Frontend build verified." -ForegroundColor Green
    }

    # 2. Check Python backend test runner if virtualenv exists
    $PyExe = ".\venv_rtx\Scripts\python.exe"
    if (-not (Test-Path $PyExe)) {
        $PyExe = ".\venv\Scripts\python.exe"
    }
    if (Test-Path $PyExe) {
        Write-Host " [Step 2] Executing Backend Standalone Test Suite..." -ForegroundColor Cyan
        & $PyExe run_tests_standalone.py
        $BackendStatus = $LASTEXITCODE
        if ($BackendStatus -eq 0) {
            Write-Host " [PASS] Backend tests successfully passed!" -ForegroundColor Green
        } else {
            Write-Host " [!] Backend test failures detected (Code $BackendStatus)." -ForegroundColor Red
        }
    } else {
        Write-Host " [!] Notice: Python virtualenv not yet initialized (venv_rtx). Skipping Python test run." -ForegroundColor DarkYellow
    }

    if ($RunTestsOnly) {
        Write-Host "`n[DONE] Single test cycle complete." -ForegroundColor Green
        break
    }

    # Pause before next cycle
    Write-Host "`nWaiting 10 seconds before next iteration (Ctrl+C to break)..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
    $Iteration++
}
