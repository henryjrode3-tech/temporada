#!/usr/bin/env python3
"""Wallpaper Engine — a macOS menu bar app.

Rotates your desktop wallpaper through the photos in a folder you choose.
Because the macOS lock screen shows your current desktop picture, this
updates the lock screen background too. Lives in the menu bar (top-right,
next to your battery / wifi / clock).

Run:  python3 wallpaper_engine.py
Needs: pip3 install rumps pyobjc
"""

import os
import json
import random
import subprocess

try:
    import rumps
except ImportError:  # pragma: no cover - guidance for first-time users
    raise SystemExit(
        "\nThis app needs the 'rumps' package (macOS menu bar library).\n"
        "Install it, then run again:\n\n"
        "    pip3 install rumps pyobjc\n"
    )

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".heic",
              ".tiff", ".tif", ".bmp", ".webp"}

SUPPORT_DIR = os.path.expanduser("~/Library/Application Support/WallpaperEngine")
CONFIG_PATH = os.path.join(SUPPORT_DIR, "config.json")
LAUNCH_AGENT_PATH = os.path.expanduser(
    "~/Library/LaunchAgents/com.wallpaperengine.menubar.plist")

INTERVAL_CHOICES = [
    ("10 seconds", 10),
    ("30 seconds", 30),
    ("1 minute", 60),
    ("5 minutes", 300),
    ("15 minutes", 900),
    ("30 minutes", 1800),
    ("1 hour", 3600),
]


def set_wallpaper(path):
    """Set the wallpaper on every display/space via System Events.

    The macOS lock screen mirrors the desktop picture, so this also changes
    what shows when the screen is locked.
    """
    script = (
        'tell application "System Events" to tell every desktop '
        'to set picture to "%s"' % path.replace('"', '\\"')
    )
    subprocess.run(["osascript", "-e", script], check=False)


def choose_folder():
    """Open the native macOS folder picker and return the chosen POSIX path."""
    script = ('POSIX path of (choose folder with prompt '
              '"Choose your wallpaper photos folder")')
    try:
        out = subprocess.run(["osascript", "-e", script],
                             capture_output=True, text=True)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None  # user cancelled


class WallpaperEngine(rumps.App):
    def __init__(self):
        super().__init__("Wallpaper Engine", title="\U0001F5BC",
                         quit_button=None)
        self.cfg = self.load_config()
        self.photos = []
        self.pos = 0
        self.paused = False

        # Informational line (no callback => greyed / disabled)
        self.now_item = rumps.MenuItem("No folder chosen yet")

        self.pause_item = rumps.MenuItem("Pause", callback=self.toggle_pause)

        self.interval_menu = rumps.MenuItem("Change Every")
        for label, secs in INTERVAL_CHOICES:
            item = rumps.MenuItem(label, callback=self.make_interval_setter(secs))
            item.state = 1 if secs == self.cfg["interval"] else 0
            self.interval_menu.add(item)

        self.shuffle_item = rumps.MenuItem("Shuffle", callback=self.toggle_shuffle)
        self.shuffle_item.state = 1 if self.cfg["shuffle"] else 0

        self.login_item = rumps.MenuItem("Start at Login", callback=self.toggle_login)
        self.login_item.state = 1 if os.path.exists(LAUNCH_AGENT_PATH) else 0

        self.menu = [
            self.now_item,
            None,
            rumps.MenuItem("Choose Photo Folder…", callback=self.on_choose_folder),
            rumps.MenuItem("Open Current Folder", callback=self.on_open_folder),
            None,
            rumps.MenuItem("Next Wallpaper", callback=self.on_next),
            rumps.MenuItem("Previous Wallpaper", callback=self.on_prev),
            self.pause_item,
            None,
            self.interval_menu,
            self.shuffle_item,
            None,
            self.login_item,
            rumps.MenuItem("Quit", callback=self.on_quit),
        ]

        self.timer = rumps.Timer(self.on_tick, self.cfg["interval"])

        if self.cfg.get("folder") and os.path.isdir(self.cfg["folder"]):
            self.scan_folder(self.cfg["folder"], keep_pos=True)
        self.timer.start()

    # ---------- config ----------
    def load_config(self):
        cfg = {"folder": None, "interval": 300, "shuffle": True, "pos": 0}
        try:
            with open(CONFIG_PATH) as f:
                cfg.update(json.load(f))
        except Exception:
            pass
        return cfg

    def save_config(self):
        try:
            os.makedirs(SUPPORT_DIR, exist_ok=True)
            self.cfg["pos"] = self.pos
            with open(CONFIG_PATH, "w") as f:
                json.dump(self.cfg, f)
        except Exception:
            pass

    # ---------- folder / photos ----------
    def scan_folder(self, folder, keep_pos=False):
        try:
            names = sorted(os.listdir(folder))
        except Exception:
            names = []
        self.photos = [
            os.path.join(folder, n) for n in names
            if os.path.splitext(n)[1].lower() in IMAGE_EXTS
        ]
        self.cfg["folder"] = folder
        if self.cfg["shuffle"]:
            random.shuffle(self.photos)
        self.pos = self.cfg.get("pos", 0) if keep_pos else 0
        self.save_config()
        if self.photos:
            self.apply_current()
        else:
            self.now_item.title = "No images in that folder"

    def apply_current(self):
        if not self.photos:
            return
        self.pos %= len(self.photos)
        path = self.photos[self.pos]
        set_wallpaper(path)
        self.now_item.title = "Now: %s  (%d/%d)" % (
            os.path.basename(path), self.pos + 1, len(self.photos))
        self.save_config()

    # ---------- timer ----------
    def on_tick(self, _):
        if self.paused or not self.photos:
            return
        self.pos = (self.pos + 1) % len(self.photos)
        self.apply_current()

    # ---------- menu callbacks ----------
    def on_choose_folder(self, _):
        folder = choose_folder()
        if folder:
            self.scan_folder(folder)

    def on_open_folder(self, _):
        if self.cfg.get("folder"):
            subprocess.run(["open", self.cfg["folder"]], check=False)

    def on_next(self, _):
        if self.photos:
            self.pos = (self.pos + 1) % len(self.photos)
            self.apply_current()

    def on_prev(self, _):
        if self.photos:
            self.pos = (self.pos - 1) % len(self.photos)
            self.apply_current()

    def toggle_pause(self, sender):
        self.paused = not self.paused
        sender.title = "Resume" if self.paused else "Pause"

    def make_interval_setter(self, secs):
        def setter(sender):
            self.cfg["interval"] = secs
            self.save_config()
            for item in self.interval_menu.values():
                item.state = 0
            sender.state = 1
            self.timer.stop()
            self.timer.interval = secs
            self.timer.start()
        return setter

    def toggle_shuffle(self, sender):
        self.cfg["shuffle"] = not self.cfg["shuffle"]
        sender.state = 1 if self.cfg["shuffle"] else 0
        self.save_config()
        if self.photos:
            if self.cfg["shuffle"]:
                random.shuffle(self.photos)
            else:
                self.photos.sort()
            self.pos = 0
            self.apply_current()

    def toggle_login(self, sender):
        if os.path.exists(LAUNCH_AGENT_PATH):
            subprocess.run(["launchctl", "unload", LAUNCH_AGENT_PATH], check=False)
            try:
                os.remove(LAUNCH_AGENT_PATH)
            except Exception:
                pass
            sender.state = 0
        else:
            self.write_launch_agent()
            sender.state = 1

    def write_launch_agent(self):
        script_path = os.path.abspath(__file__)
        which = subprocess.run(["which", "python3"], capture_output=True, text=True)
        python = which.stdout.strip() or "/usr/bin/python3"
        plist = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n'
            '<dict>\n'
            '    <key>Label</key><string>com.wallpaperengine.menubar</string>\n'
            '    <key>ProgramArguments</key>\n'
            '    <array>\n'
            '        <string>%s</string>\n'
            '        <string>%s</string>\n'
            '    </array>\n'
            '    <key>RunAtLoad</key><true/>\n'
            '</dict>\n'
            '</plist>\n' % (python, script_path)
        )
        os.makedirs(os.path.dirname(LAUNCH_AGENT_PATH), exist_ok=True)
        with open(LAUNCH_AGENT_PATH, "w") as f:
            f.write(plist)
        subprocess.run(["launchctl", "load", LAUNCH_AGENT_PATH], check=False)

    def on_quit(self, _):
        rumps.quit_application()


if __name__ == "__main__":
    WallpaperEngine().run()
