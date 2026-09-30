# IBVAP — Offline Wheel Downloader for NVIDIA RTX 3050 Deployment
# Run this script on an INTERNET-CONNECTED machine to prepare the offline package for USB transfer.
param(
    [string]$OutputDir = ".\offline_wheels_rtx3050"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " IBVAP RTX 3050 Offline Wheel Packager (Windows 11 / cu124)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "[+] Created output directory: $OutputDir" -ForegroundColor Green
}

Write-Host "[*] Downloading PyTorch CUDA 12.4 wheels..." -ForegroundColor Yellow
pip download torch==2.4.1+cu124 torchvision==0.19.1+cu124 torchaudio==2.4.1+cu124 `
    --extra-index-url https://download.pytorch.org/whl/cu124 `
    --dest $OutputDir

Write-Host "[*] Downloading remaining dependencies from manifest..." -ForegroundColor Yellow
pip download -r .\deployment\rtx3050\OFFLINE_WHEELS_MANIFEST.txt `
    --dest $OutputDir

Write-Host "==========================================================" -ForegroundColor Green
Write-Host " Successfully prepared offline wheels in: $OutputDir" -ForegroundColor Green
Write-Host " Copy the entire folder + project to USB drive for air-gapped field deployment." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
