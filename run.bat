@echo off
chcp 65001 >nul
cd /d "%~dp0"

call start_chrome_debug.bat

timeout /t 3 /nobreak >nul

start "" pythonw main.py
exit
