<#
.SYNOPSIS
    Stops all IBVAP demonstration processes cleanly.
#>

$ErrorActionPreference = "Continue"

Write-Host "Stopping all running IBVAP demonstration processes..." -ForegroundColor Yellow

if (Test-Path "demo_pids.json") {
    try {
        $pids = Get-Content "demo_pids.json" | ConvertFrom-Json
        foreach ($prop in $pids.PSObject.Properties) {
            $pId = $prop.Value
            if ($pId) {
                Stop-Process -Id $pId -Force -ErrorAction SilentlyContinue
                Write-Host "Stopped $($prop.Name) (PID: $pId)" -ForegroundColor Green
            }
        }
        Remove-Item "demo_pids.json" -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Host "Error parsing demo_pids.json" -ForegroundColor Red
    }
}

# Fallback cleanup
Get-Process -Name "mediamtx" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "ffmpeg" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "All IBVAP demo processes terminated." -ForegroundColor Green
