@echo off
TITLE IBVAP - NVIDIA RTX 3050 Launcher
COLOR 0B
echo ==========================================================
echo  IBVAP Tactical Border Video Analytics Platform (RTX 3050)
echo ==========================================================

powershell -ExecutionPolicy Bypass -File "%~dp0start_ibvap_rtx3050.ps1"
pause
