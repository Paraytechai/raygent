@echo off
title RAYGENT MASTER LAUNCHER (ComfyUI + LivePortrait + OmniVoice + Raygent)
cd /d "c:\Users\cyber\Favorites\Downloads\raygent"

echo =====================================================================
echo    STARTING COMPLETE RAYGENT SUITE WITH RTX 5060 Ti GPU ACCELERATION
echo    1. Starting ComfyUI & LivePortrait Backend
echo    2. Starting OmniVoice Neural TTS & Gemini Agent
echo    3. Opening RAYGENT.AI.STUDIO in Browser
echo =====================================================================

rem 1. Launch ComfyUI in background if not already running
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [ComfyUI] Python processes active. Checking ComfyUI...
)
start "ComfyUI GPU Server" /min "D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe" "D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\main.py" --port 8189 --listen 127.0.0.1

rem 2. Launch Raygent Server with GPU Python Environment
start /min cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8765"
"D:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe" run_server.py

pause
