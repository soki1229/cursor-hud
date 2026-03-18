# Edge Snap, Screen Clamp & App Icon Design

## Feature A: Edge Snapping + Screen Clamp

### Goal
Two complementary window-position helpers that keep the HUD fully visible and
let the user dock it to screen edges with a single drag gesture.

### Scope
- **`_snap_to_edge()`** — called once when the user releases a drag; snaps the
  window to the nearest screen edge if within a threshold distance.
- **`_clamp_to_screen(screen)`** — called whenever the window height changes or
  at startup; slides the window back on-screen if any part would be clipped.

Neither helper changes window _size_; they only change _position_.

### Coordinate convention (both methods)

PyQt5's `QRect.right()` = `left() + width() − 1` and `QRect.bottom()` =
`top() + height() − 1` (historical off-by-one). To avoid ambiguity, **all**
right-edge and bottom-edge values are computed as:

```
right  = rect.left() + rect.width()
bottom = rect.top()  + rect.height()
```

This applies to both the window rect (`r`) and the available geometry (`avail`).

---

### `_snap_to_edge()`

**Trigger:** `HUDWindow.eventFilter` → `MouseButtonRelease` branch.

The **current** `eventFilter` has **no guard** on `_drag_pos` at release — it
clears it unconditionally. The implementation must **add** the guard:

```python
if t == e.MouseButtonRelease:
    if self._drag_pos:      # NEW: snap only after a real drag, not a bare click
        self._snap_to_edge()
    self._drag_pos = None
    return True
```

`_snap_to_edge()` does not read `_drag_pos`; the guard only decides whether a
real drag occurred.

**Algorithm:**
```python
def _snap_to_edge(self) -> None:
    screen = (QApplication.screenAt(self.frameGeometry().center())
              or QApplication.primaryScreen())
    avail  = screen.availableGeometry()
    r      = self.frameGeometry()

    a_right  = avail.left() + avail.width()
    a_bottom = avail.top()  + avail.height()
    r_right  = r.left() + r.width()
    r_bottom = r.top()  + r.height()

    # X axis
    if   abs(r.left()  - avail.left()) <= SNAP_PX:  nx = avail.left()
    elif abs(r_right   - a_right)      <= SNAP_PX:  nx = a_right - r.width()
    else:                                            nx = r.left()

    # Y axis
    if   abs(r.top()   - avail.top())  <= SNAP_PX:  ny = avail.top()
    elif abs(r_bottom  - a_bottom)     <= SNAP_PX:  ny = a_bottom - r.height()
    else:                                            ny = r.top()

    if nx != r.left() or ny != r.top():
        self.move(nx, ny)
```

`_clamp_to_screen()` is **not** called after snap — the snapped position is by
definition on a valid edge.

**Snap + height growth:** if the user snaps to the bottom edge and a subsequent
`_do_adjust_height()` increases the window height, `_clamp_to_screen()` (called
at the end of `_do_adjust_height()`) will move the window up to fit. This is
the expected behavior — keeping the window fully visible takes priority.

**Constant:** `SNAP_PX = 30` — add in the `CONSTANTS` section alongside
`WIN_W`, `WIN_H`, etc.

---

### `_clamp_to_screen(screen: QScreen)`

The screen is passed as a parameter so callers control which screen is used
(startup always passes `primaryScreen()`; `_do_adjust_height()` resolves
dynamically).

**Trigger points (both required):**

| Call site | Screen argument | When it fires |
|-----------|----------------|---------------|
| `_do_adjust_height()` — after `self.resize(self.width(), target_h)` | `QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()` | Tab switch, mini↔full toggle, data load |
| `HUDWindow.__init__` — after `self.move(saved_x, saved_y)` + `self.resize(...)` | `QApplication.primaryScreen()` (unconditional) | App startup |

**Startup timing:** `show()` is called in `main()`, **after** `HUDWindow.__init__`
returns. The clamp call in `__init__` therefore happens before `show()`.
Because `HUDWindow` uses `Qt.FramelessWindowHint`, the OS does not add a window
frame, so `geometry()` is fully controlled by `move()` + `resize()` and is
accurate before `show()`. Using `primaryScreen()` unconditionally avoids any
reliance on `screenAt()` before the window is shown.

**Algorithm:**
```python
def _clamp_to_screen(self, screen: "QScreen") -> None:
    avail    = screen.availableGeometry()
    r        = self.frameGeometry()

    a_right  = avail.left() + avail.width()
    a_bottom = avail.top()  + avail.height()

    x_lo = avail.left()
    x_hi = max(avail.left(), a_right  - r.width())   # guard: window wider than screen
    y_lo = avail.top()
    y_hi = max(avail.top(),  a_bottom - r.height())  # guard: window taller than screen

    nx = max(x_lo, min(r.x(), x_hi))
    ny = max(y_lo, min(r.y(), y_hi))

    if nx != r.x() or ny != r.y():
        self.move(nx, ny)
```

**Startup: replace existing bounds-check (inside the `if saved_x is not None` branch only).**

Current `__init__` structure:
```python
if saved_x is not None and saved_y is not None:
    x = max(geo.left(), min(saved_x, geo.right() - 60))   # ← replace these 3 lines
    y = max(geo.top(),  min(saved_y, geo.bottom() - 60))
    self.move(x, y)
else:
    self.move(geo.right() - self._cur_win_w - 20, geo.bottom() - WIN_H - 20)   # ← keep unchanged
self.resize(self._cur_win_w, WIN_H)
```

Replace only the **`if` branch** body:
```python
if saved_x is not None and saved_y is not None:
    self.move(saved_x, saved_y)                            # raw saved position
else:
    self.move(geo.right() - self._cur_win_w - 20, geo.bottom() - WIN_H - 20)
self.resize(self._cur_win_w, WIN_H)
self._clamp_to_screen(QApplication.primaryScreen())        # clamp after both branches
```

The `_clamp_to_screen()` call goes **after** `self.resize()` and applies in both
branches — the default position is already within bounds, so it's a no-op on
first launch. The `- 60` heuristic is superseded by the full-window clamp.

---

## Feature B: App Icon — Workflow Guide

### Goal
Set a custom application icon so the HUD shows a branded image in the OS
taskbar, Dock, and Alt+Tab switcher.

### Icon generation (Gemini Imagen prompt)

```
App icon for a desktop monitoring utility. Minimalist tech / HUD aesthetic.

Design: a circular arc gauge (like a system monitor or speedometer dial)
at approximately 70% fill, drawn with clean vector-style strokes in bright
cyan (#00E5FF) on a very dark charcoal background (#1A1A2E). The arc should
have a subtle neon glow effect. A small vertical stack of three thin progress
bars sits below-centre of the arc, each in a slightly different shade of
cyan/teal, representing usage metrics. No text, no letters, no numbers.

Style: flat icon with minimal depth, suitable for desktop taskbar / macOS
Dock / Windows system tray. Crisp edges, high contrast.
Output: 1024×1024 pixels, square canvas, dark background.
```

Save the output as `assets/icon_1024.png` (committed to the repo).

---

### Per-platform conversion

| Platform | Format | Size layers | Tool |
|----------|--------|-------------|------|
| Windows | `icon.ico` | 256, 128, 64, 32, 16 px | ImageMagick `convert` or online |
| macOS | `icon.icns` | 16 → 1024 px set | `iconutil` (built-in on macOS) |
| Linux | `icon_256.png` | 256 × 256 | `sips` or ImageMagick resize |

Converted files live in `assets/` (all committed):
```
assets/
  icon_1024.png
  icon.ico
  icon.icns
  icon_256.png
```

**macOS ICNS procedure (run once on macOS):**
```bash
mkdir icon.iconset
sips -z 16   16   assets/icon_1024.png --out icon.iconset/icon_16x16.png
sips -z 32   32   assets/icon_1024.png --out icon.iconset/icon_16x16@2x.png
sips -z 32   32   assets/icon_1024.png --out icon.iconset/icon_32x32.png
sips -z 64   64   assets/icon_1024.png --out icon.iconset/icon_32x32@2x.png
sips -z 128  128  assets/icon_1024.png --out icon.iconset/icon_128x128.png
sips -z 256  256  assets/icon_1024.png --out icon.iconset/icon_128x128@2x.png
sips -z 256  256  assets/icon_1024.png --out icon.iconset/icon_256x256.png
sips -z 512  512  assets/icon_1024.png --out icon.iconset/icon_256x256@2x.png
sips -z 512  512  assets/icon_1024.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 assets/icon_1024.png --out icon.iconset/icon_512x512@2x.png
iconutil -c icns icon.iconset -o assets/icon.icns
rm -rf icon.iconset
```

**Windows ICO (ImageMagick, any platform):**
```bash
convert assets/icon_1024.png -define icon:auto-resize=256,128,64,32,16 assets/icon.ico
```

---

### Runtime icon (cursor_hud.py)

`_app_dir()` returns a `pathlib.Path`. Use the `/` operator (matching codebase
style). `os`, `sys`, and `QIcon` are already imported in `cursor_hud.py`.

In `main()`, after `app = QApplication(sys.argv)` and **before** the
`apply_theme()` / `app.setStyleSheet(...)` block:

```python
# Runtime app icon — platform-specific, graceful fallback if file absent
if sys.platform == "win32":
    _icon_p = _app_dir() / "assets" / "icon.ico"
elif sys.platform == "darwin":
    _icon_p = _app_dir() / "assets" / "icon.icns"
else:
    _icon_p = _app_dir() / "assets" / "icon_256.png"
if _icon_p.exists():
    app.setWindowIcon(QIcon(str(_icon_p)))
```

Graceful fallback: if the file is absent the default OS icon is used; no crash.

---

### PyInstaller build flags

Update `.github/workflows/release.yml`:

| Job | Flag to add |
|-----|-------------|
| `build-windows` | `--icon=assets/icon.ico` |
| `build-macos` | `--icon=assets/icon.icns` |
| `build-linux` | _(no `--icon` flag; ELF binaries do not embed icons)_ |

`--icon` controls the icon shown in Windows Explorer / macOS Finder before the
app launches. The runtime `setWindowIcon()` call controls the icon in the
taskbar and Alt+Tab while the app is running. Both are needed for complete icon
coverage on Windows and macOS.

**Linux launcher icon** (out of scope): branded icon in GNOME/KDE launchers
requires a separate `.desktop` file; `setWindowIcon()` only covers taskbar
and Alt+Tab on X11/Wayland.

---

## Out of scope
- System tray icon (inherits `windowIcon` via Qt automatically)
- Animated or per-theme icons
- Snap during drag (magnetic mode)
- Corner snapping (two-axis simultaneous snap)
- Linux `.desktop` launcher icon
