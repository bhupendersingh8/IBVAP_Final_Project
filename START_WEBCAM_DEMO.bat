@echo off
title IBVAP - Laptop Webcam Mode
cd /d "%~dp0"
echo ================================================================
echo   IBVAP - Intelligent Border Video Analytics Platform
echo   Starting Laptop Webcam Demo...
echo ================================================================
powershell -ExecutionPolicy Bypass -File ".\scripts\ibvap.ps1" webcam
pause
