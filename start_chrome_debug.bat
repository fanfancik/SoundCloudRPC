@echo off
chcp 65001 >nul
REM Launches Chrome with remote debugging enabled.
REM --remote-allow-origins=* is required since Chrome 111,
REM otherwise the browser rejects the WebSocket connection.

set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
set PROFILE_DIR=%~dp0chrome_debug_profile

if not exist %CHROME_PATH% (
    set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

start "" %CHROME_PATH% --remote-debugging-port=9222 --user-data-dir="%PROFILE_DIR%" --remote-allow-origins=* --start-maximized https://soundcloud.com
