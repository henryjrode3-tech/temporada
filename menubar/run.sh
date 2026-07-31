#!/bin/bash
# One-command launcher for the Wallpaper Engine menu bar app.
# Installs dependencies on first run, then starts the app.
set -e
cd "$(dirname "$0")"

echo "Wallpaper Engine — starting…"

# Make sure rumps is available; install into the user site if not.
if ! python3 -c "import rumps" 2>/dev/null; then
  echo "Installing dependencies (rumps, pyobjc)…"
  python3 -m pip install --user -r requirements.txt
fi

exec python3 wallpaper_engine.py
