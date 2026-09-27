@echo off
title IBVAP - CCTV RTSP Simulation Mode
cd /d "%~dp0"
echo ================================================================
echo   IBVAP - Intelligent Border Video Analytics Platform
echo   Starting CCTV RTSP Simulation Demo...
echo ================================================================
powershell -ExecutionPolicy Bypass -File ".\scripts\ibvap.ps1" demo
pause
