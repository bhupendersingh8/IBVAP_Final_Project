@echo off
title IBVAP AI Sentinel - Border Surveillance Platform
cd /d "%~dp0"
echo =====================================================================
echo   IBVAP - AI-Based Intelligent Video Analytics Platform (SIH 26187)
echo   Initializing Cyber-Defense AI Sentinel Suite...
echo =====================================================================
echo.
powershell -ExecutionPolicy Bypass -File ".\scripts\start_sih_demo.ps1"
echo.
echo Opening AI Neon Operations Command Dashboard...
start http://localhost:5173
echo.
echo All systems operational. Press any key to stop all services.
pause
powershell -ExecutionPolicy Bypass -File ".\scripts\stop_sih_demo.ps1"
