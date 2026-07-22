#!/usr/bin/env bash
# Launches Chrome with remote debugging enabled (Linux/macOS).
# --remote-allow-origins=* is required since Chrome 111.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE_DIR="$DIR/chrome_debug_profile"

if [[ "$OSTYPE" == "darwin"* ]]; then
    CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
else
    CHROME="$(command -v google-chrome || command -v google-chrome-stable || command -v chromium-browser || command -v chromium)"
fi

if [[ -z "$CHROME" || ! -e "$CHROME" ]]; then
    echo "Chrome/Chromium not found. Set the CHROME path manually in this file."
    exit 1
fi

"$CHROME" --remote-debugging-port=9222 --user-data-dir="$PROFILE_DIR" --remote-allow-origins=* --start-maximized https://soundcloud.com &
