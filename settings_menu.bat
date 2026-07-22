@echo off
chcp 65001 >nul
title SoundCloudRPC - Настройки
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python не найден в PATH. Установи Python 3.9+ с python.org
    echo и поставь галку "Add python.exe to PATH" при установке.
    pause
    exit /b 1
)

set PYTHONIOENCODING=utf-8
python settings_menu.py

exit /b 0
