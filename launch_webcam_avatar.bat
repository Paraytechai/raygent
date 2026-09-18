@echo off
title LivePortrait Real-Time Webcam Avatar Driver
cd /d "%~dp0"
echo ==================================================================
echo       STARTING LIVEPORTRAIT REAL-TIME WEBCAM DRIVER
echo ==================================================================
python liveportrait_webcam_runner.py
pause
