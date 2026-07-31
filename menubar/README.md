# Wallpaper Engine — macOS menu bar app

A little app that lives in your **menu bar** (top-right, next to the battery,
wifi and clock) and rotates your **desktop wallpaper** through the photos in a
folder you choose.

Because macOS uses your current desktop picture for the **lock screen**, this
changes your lock screen background too.

## What it does

- Sits in the menu bar as a 🖼 icon — click it for the menu.
- Cycles your wallpaper through every photo in a folder you pick.
- Works on **desktop and lock screen** (see the note below on the login window).
- Adjustable interval, shuffle, next/previous, pause, and "Start at Login".
- Remembers your folder and settings.

## Requirements

- macOS
- Python 3 (macOS ships with it; or install from python.org / Homebrew)

## Run it

From this folder:

```bash
./run.sh
```

That installs the two dependencies the first time (`rumps`, `pyobjc`) and starts
the app. Or do it manually:

```bash
pip3 install -r requirements.txt
python3 wallpaper_engine.py
```

A 🖼 icon appears in your menu bar. Click it → **Choose Photo Folder…**, pick a
folder of photos, and you're done.

### First-run permission prompt

The first time it changes the wallpaper, macOS asks to let it control
**System Events** (that's how it sets the wallpaper). Click **OK / Allow**.
If you miss it, go to **System Settings → Privacy & Security → Automation** and
enable it for Terminal (or Python).

## The menu

| Item | What it does |
| --- | --- |
| **Now: …** | shows the current photo and position |
| **Choose Photo Folder…** | pick the folder your photos live in |
| **Open Current Folder** | open that folder in Finder to add/remove photos |
| **Next / Previous Wallpaper** | jump manually |
| **Pause / Resume** | stop or restart the rotation |
| **Change Every** | 10s up to 1 hour |
| **Shuffle** | random vs. alphabetical order |
| **Start at Login** | launch automatically when you log in |
| **Quit** | exit |

Add photos anytime: drop them into your chosen folder, then click
**Next Wallpaper** (or reopen the folder via **Choose Photo Folder…**) to pick
them up.

## About the lock screen (important)

- **Lock screen (while logged in):** ✅ covered. macOS shows your current desktop
  wallpaper on the lock screen, so rotating the desktop picture rotates the lock
  screen background too.
- **Login window (before anyone logs in):** ⚠️ not changed. That background is a
  protected system setting Apple doesn't allow apps to rotate. This app leaves it
  alone on purpose.

## Make it feel like a real app (optional)

The `run.sh` script and **Start at Login** are enough for daily use. If you want
a double-clickable `.app` in your Applications folder, you can bundle it with
[`py2app`](https://py2app.readthedocs.io/):

```bash
pip3 install py2app
# (a setup.py would be needed; ask and I can add one)
```

## Note

This is completely separate from the Flask "Temporada" pricing app in the rest
of the repo. It's just the files in this `menubar/` folder.
