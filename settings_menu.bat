@echo off
title SoundCloudRPC Settings
cd /d "%~dp0"
 
where python >nul 2>nul
if errorlevel 1 (
    echo Python not found in PATH. Install Python 3.9+ from python.org
    echo and check "Add python.exe to PATH" during install.
    pause
    exit /b 1
)
 
set PYTHONIOENCODING=utf-8
python settings_menu.py
 
exit /b 0
