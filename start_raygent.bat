@echo off
title Raygent Personal Talking Avatar Agent (OmniVoice RTX 5060 Ti)
echo Starting Raygent Assistant with GPU CUDA Acceleration on RTX 5060 Ti...
cd /d "c:\Users\cyber\Favorites\Downloads\raygent"

rem Automatically open Raygent in default web browser
start /min cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8765"

"D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\standalone-env\python.exe" run_server.py
pause