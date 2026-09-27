@echo off
title IBVAP - Stop Services
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\scripts\ibvap.ps1" stop
pause
