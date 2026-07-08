@echo off
chcp 65001 >nul
title SoundCloudRPC (debug)
cd /d "%~dp0"

call start_chrome_debug.bat

timeout /t 3 /nobreak >nul

python main.py --console

echo.
echo Script stopped. Press any key to close this window.
pause >nul
