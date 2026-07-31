# Wallpaper Engine

A standalone, single-file wallpaper engine. It rotates through photos from a
folder you choose and shows a live **battery indicator** in the corner with a
thumbnail of the current photo sitting **right next to the battery** — so your
picture "shows up by your battery level indicator."

No server, no build step, no dependencies. Just one HTML file.

## Use it

1. Open `wallpaper/index.html` in your browser (double-click it, or drag it into
   a browser window).
2. Click **Choose photo folder** and pick a folder full of photos — or just
   drag & drop image files onto the window.
3. That's it. Photos fill the screen and rotate; the battery badge updates live.

Put it in fullscreen with <kbd>F</kbd> for a true wallpaper feel.

## Where do the photos go?

Any folder on your computer. Point the app at it once. In Chrome/Edge the app
remembers the folder, so next time it can reload the same one and you can just
drop new photos in and hit **Refresh folder**.

## Controls

| Action | How |
| --- | --- |
| Next / previous photo | on-screen buttons, or <kbd>←</kbd> / <kbd>→</kbd> |
| Pause / play rotation | Pause button, or <kbd>Space</kbd> |
| Change interval | the slider (3–120 seconds) |
| Fill vs. fit photo | the **Fit** dropdown |
| Shuffle order | the **Shuffle** checkbox |
| Hide the panel | <kbd>H</kbd> (it also auto-hides when idle) |
| Fullscreen | <kbd>F</kbd> |

Your interval / fit / shuffle preferences are saved automatically.

## Browser notes

- **Choosing a folder that's remembered** and **Refresh folder** use the File
  System Access API — available in **Chrome and Edge**. In other browsers the
  folder picker falls back to a one-time selection (and drag & drop always works).
- The **battery indicator** uses the Battery Status API, supported in
  **Chrome and Edge**. Firefox and Safari have removed it, so there the battery
  shows `N/A` while everything else still works.

For the fullest experience (battery + remembered folder), use **Chrome or Edge**.

## It's fully standalone

This has nothing to do with the Flask pricing app in the rest of this repo —
it's just the `wallpaper/index.html` file. You can copy that one file anywhere
and it works on its own.
