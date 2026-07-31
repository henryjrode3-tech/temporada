#!/bin/bash
# One-command launcher for the Wallpaper Engine menu bar app.
# Uses a self-contained virtual environment so it never fights with the
# system Python. Installs dependencies on first run, then starts the app.
set -e
cd "$(dirname "$0")"

echo "Wallpaper Engine — starting…"

# Create an isolated environment the first time (avoids the
# "externally-managed-environment" pip error on modern macOS).
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment (first run only)…"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if ! python -c "import rumps" 2>/dev/null; then
  echo "Installing dependencies (rumps, pyobjc)… this can take a minute."
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
fi

echo "Launching. Look for a 🖼 icon in your menu bar (top-right)."
echo "Leave this Terminal window open while you use it. Ctrl-C to stop."
exec python wallpaper_engine.py
