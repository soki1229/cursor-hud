# Edge Snap, Screen Clamp & App Icon Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add window edge-snapping and screen-clamp helpers to keep the HUD
fully visible, and wire up a custom app icon loaded from `assets/`.

**Architecture:** Feature A adds two pure-position methods (`_snap_to_edge`,
`_clamp_to_screen`) to `HUDWindow` and hooks them into the existing drag and
height-adjust code paths. Feature B adds a graceful icon-load block in `main()`
and updates PyInstaller flags in CI; the icon files themselves are generated
manually by the user and committed to `assets/`.

**Tech Stack:** Python 3.10+, PyQt5 — single file `cursor_hud.py` (~2900 lines).
CI: `.github/workflows/release.yml`.

**Spec:** `docs/superpowers/specs/2026-03-18-edge-snap-and-icon-design.md`

---

## Chunk 1: Feature A — Edge Snap + Screen Clamp

### Task 1: Add `SNAP_PX` constant

**Files:**
- Modify: `cursor_hud.py` (~line 251, CONSTANTS section)

- [ ] **Step 1: Add constant after `WIN_H`**

  Find the line `WIN_H     = 660` (~line 251). Add immediately after:
  ```python
  SNAP_PX   = 30          # px threshold for edge-snap on drag release
  ```

- [ ] **Step 2: Verify syntax**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 -c "import ast; ast.parse(open('cursor_hud.py').read()); print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 3: Commit**
  ```bash
  git add cursor_hud.py
  git commit -m "feat(snap): add SNAP_PX constant"
  ```

---

### Task 2: Add `_clamp_to_screen` method

**Files:**
- Modify: `cursor_hud.py` — add new method to `HUDWindow`

The method should live near `_apply_size` (~line 2394) and before `_build_ui`.

- [ ] **Step 1: Add `_clamp_to_screen` after `_apply_size`**

  Find the line `def _apply_size(self, screen: QScreen):` (~line 2394).
  Scroll to the end of `_apply_size` (it ends around line 2401). After it, add:

  ```python
  def _clamp_to_screen(self, screen: "QScreen") -> None:
      """Slide window back on-screen if any part is clipped after a resize."""
      avail    = screen.availableGeometry()
      r        = self.frameGeometry()
      a_right  = avail.left() + avail.width()
      a_bottom = avail.top()  + avail.height()
      x_lo = avail.left()
      x_hi = max(avail.left(), a_right  - r.width())
      y_lo = avail.top()
      y_hi = max(avail.top(),  a_bottom - r.height())
      nx   = max(x_lo, min(r.x(), x_hi))
      ny   = max(y_lo, min(r.y(), y_hi))
      if nx != r.x() or ny != r.y():
          self.move(nx, ny)
  ```

  `get_screen_for_pos()` is the codebase's existing helper for resolving a screen
  from a point (module-level function at line ~753). `_clamp_to_screen` receives
  the screen as a parameter, so callers are responsible for using it.

- [ ] **Step 2: Verify syntax**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 -c "import ast; ast.parse(open('cursor_hud.py').read()); print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 3: Commit**
  ```bash
  git add cursor_hud.py
  git commit -m "feat(snap): add _clamp_to_screen method"
  ```

---

### Task 3: Call `_clamp_to_screen` in `__init__` (startup)

**Files:**
- Modify: `cursor_hud.py` ~lines 2323–2329

- [ ] **Step 1: Replace the inline bounds-check**

  Find this block (~lines 2323–2329):
  ```python
  if saved_x is not None and saved_y is not None:
      x = max(geo.left(), min(saved_x, geo.right() - 60))
      y = max(geo.top(), min(saved_y, geo.bottom() - 60))
      self.move(x, y)
  else:
      self.move(geo.right() - self._cur_win_w - 20, geo.bottom() - WIN_H - 20)
  self.resize(self._cur_win_w, WIN_H)
  ```

  Replace with:
  ```python
  if saved_x is not None and saved_y is not None:
      self.move(saved_x, saved_y)
  else:
      self.move(geo.right() - self._cur_win_w - 20, geo.bottom() - WIN_H - 20)
  self.resize(self._cur_win_w, WIN_H)
  self._clamp_to_screen(QApplication.primaryScreen())
  ```

- [ ] **Step 2: Verify syntax**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 -c "import ast; ast.parse(open('cursor_hud.py').read()); print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 3: Smoke-test startup clamp**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 cursor_hud.py --mock &
  sleep 3
  ```
  App should launch fully on-screen. No crash.

- [ ] **Step 4: Commit**
  ```bash
  git add cursor_hud.py
  git commit -m "feat(snap): clamp window to screen on startup"
  ```

---

### Task 4: Call `_clamp_to_screen` in `_do_adjust_height`

**Files:**
- Modify: `cursor_hud.py` ~lines 2943–2945

- [ ] **Step 1: Add clamp call after resize in `_do_adjust_height`**

  Find this block near the end of `_do_adjust_height` (~lines 2943–2945):
  ```python
  self._target_h = target_h
  if self.height() != target_h:
      self.resize(self.width(), target_h)
  ```

  Replace with:
  ```python
  self._target_h = target_h
  if self.height() != target_h:
      self.resize(self.width(), target_h)
      self._clamp_to_screen(get_screen_for_pos(self.geometry().center()))
  ```

  `get_screen_for_pos()` is a module-level helper (~line 753) already used by
  `moveEvent`. Calling `_clamp_to_screen` **inside** the `if` block (only when
  height actually changed) prevents the `moveEvent → _apply_size →
  _do_adjust_height → _clamp_to_screen → move()` re-entrant chain from firing
  on every height-check tick.

- [ ] **Step 2: Verify syntax**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 -c "import ast; ast.parse(open('cursor_hud.py').read()); print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 3: Smoke-test height-change clamp**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 cursor_hud.py --mock &
  sleep 3
  ```
  Switch between Credits / Profile / Settings tabs. App should stay fully on-screen after each tab switch. Toggle mini mode — app should stay on-screen.

- [ ] **Step 4: Commit**
  ```bash
  git add cursor_hud.py
  git commit -m "feat(snap): clamp window to screen after height change"
  ```

---

### Task 5: Add `_snap_to_edge` method and wire `eventFilter`

**Files:**
- Modify: `cursor_hud.py` — add method near `_clamp_to_screen`, update `eventFilter`

- [ ] **Step 1: Add `_snap_to_edge` method after `_clamp_to_screen`**

  Add immediately after the `_clamp_to_screen` method (just added in Task 2):

  ```python
  def _snap_to_edge(self) -> None:
      """Snap window to nearest screen edge when within SNAP_PX pixels."""
      screen   = get_screen_for_pos(self.geometry().center())
      avail    = screen.availableGeometry()
      r        = self.frameGeometry()
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

- [ ] **Step 2: Update `eventFilter` — add guard and snap call**

  Find the `MouseButtonRelease` branch in `eventFilter` (~line 2992):
  ```python
  if t == e.MouseButtonRelease:
      self._drag_pos = None
      return True
  ```

  Replace with:
  ```python
  if t == e.MouseButtonRelease:
      if self._drag_pos:          # snap only after a real drag, not a bare click
          self._snap_to_edge()
      self._drag_pos = None
      return True
  ```

- [ ] **Step 3: Verify syntax**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 -c "import ast; ast.parse(open('cursor_hud.py').read()); print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 4: Smoke-test snap behavior**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 cursor_hud.py --mock &
  sleep 3
  ```
  - Drag the window to within ~20px of the left edge → release → should snap to left edge
  - Drag to within ~20px of the right edge → release → should snap to right edge
  - Drag to within ~20px of the top → release → should snap to top
  - Drag to within ~20px of the bottom (taskbar boundary) → release → should snap to taskbar boundary
  - Drag to the middle of the screen → release → should NOT snap
  - Click the title bar without dragging → should NOT snap

- [ ] **Step 5: Commit**
  ```bash
  git add cursor_hud.py
  git commit -m "feat(snap): add _snap_to_edge on drag release"
  ```

---

### Task 6: Update CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add entries to `## v1.0.0-beta.6 — Unreleased`**

  In the `### Features` section under `## v1.0.0-beta.6 — Unreleased`, add:
  ```markdown
  - **Edge snap**: window snaps to screen edges (left/right/top/taskbar boundary)
    when released within 30 px of an edge. Works on all platforms; respects
    taskbar area via `availableGeometry()`. Multi-monitor aware.
  - **Screen clamp**: window is automatically repositioned to remain fully
    visible whenever its height changes (tab switch, mini↔full mode toggle,
    data load) or on startup with a saved position.
  ```

- [ ] **Step 2: Commit**
  ```bash
  git add CHANGELOG.md
  git commit -m "docs(changelog): add edge snap and screen clamp entries"
  ```

---

## Chunk 2: Feature B — App Icon

### Task 7: Create `assets/` directory and document icon workflow

**Files:**
- Create: `assets/` directory with `.gitkeep`

- [ ] **Step 1: Create assets directory**
  ```bash
  mkdir -p assets
  touch assets/.gitkeep
  ```

- [ ] **Step 2: Commit placeholder**
  ```bash
  git add assets/.gitkeep
  git commit -m "chore: add assets/ directory for app icon files"
  ```

- [ ] **Step 3: (Manual — user action required) Generate icon with Gemini**

  Use this prompt in Gemini Imagen:
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

  Save the result as `assets/icon_1024.png`.

- [ ] **Step 4: (Manual — run on macOS) Convert to ICNS**
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

- [ ] **Step 5: (Manual) Convert to ICO (Windows)**
  If ImageMagick is available:
  ```bash
  convert assets/icon_1024.png -define icon:auto-resize=256,128,64,32,16 assets/icon.ico
  ```
  Alternatively use an online converter (e.g. convertico.com). Target: `assets/icon.ico`.

- [ ] **Step 6: (Manual) Resize for Linux**
  ```bash
  sips -z 256 256 assets/icon_1024.png --out assets/icon_256.png
  ```

- [ ] **Step 7: Commit icon files once all four are present**
  ```bash
  git add assets/icon_1024.png assets/icon.ico assets/icon.icns assets/icon_256.png
  git rm assets/.gitkeep
  git commit -m "feat(icon): add app icon assets (1024px source + platform formats)"
  ```

---

### Task 8: Wire runtime icon in `main()`

**Files:**
- Modify: `cursor_hud.py` ~line 3173 (`main()` function)

- [ ] **Step 1: Add icon load block after `app.setQuitOnLastWindowClosed`**

  Find this line (~line 3172):
  ```python
  app.setQuitOnLastWindowClosed(True)  # close window = quit app (tray is supplementary)
  ```

  Add immediately after it:
  ```python
  # App icon — dev-mode only: load from assets/ when running as a script.
  # Frozen builds (PyInstaller --onefile / .app bundle) rely on the --icon flag
  # which embeds the icon into the binary; the OS shows it in taskbar/Dock
  # automatically without a setWindowIcon() call.
  if not getattr(sys, "frozen", False):
      if sys.platform == "win32":
          _icon_p = _app_dir() / "assets" / "icon.ico"
      else:
          # macOS and Linux: Qt requires a raster format (PNG); .icns is OS-only
          _icon_p = _app_dir() / "assets" / "icon_256.png"
      if _icon_p.exists():
          app.setWindowIcon(QIcon(str(_icon_p)))
  ```

- [ ] **Step 2: Verify syntax**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 -c "import ast; ast.parse(open('cursor_hud.py').read()); print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 3: Smoke-test icon (macOS)**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 cursor_hud.py --mock &
  sleep 3
  ```
  The Dock and taskbar should show the custom icon (requires `assets/icon.icns` to exist).
  If icon files are not yet generated, app should start normally with the default icon (graceful fallback).

- [ ] **Step 4: Commit**
  ```bash
  git add cursor_hud.py
  git commit -m "feat(icon): load platform-specific app icon in main()"
  ```

---

### Task 9: Update PyInstaller flags in CI

**Files:**
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: Update `build-windows` PyInstaller command**

  Find (~line 25):
  ```yaml
  run: python -m PyInstaller --onefile --windowed --name CursorHUD cursor_hud.py
  ```
  _(under `build-windows` job)_

  Replace with:
  ```yaml
  run: python -m PyInstaller --onefile --windowed --name CursorHUD --icon=assets/icon.ico cursor_hud.py
  ```

- [ ] **Step 2: Update `build-macos` PyInstaller command**

  Find (~line 46):
  ```yaml
  run: python -m PyInstaller --windowed --name CursorHUD cursor_hud.py
  ```
  _(under `build-macos` job)_

  Replace with:
  ```yaml
  run: python -m PyInstaller --windowed --name CursorHUD --icon=assets/icon.icns cursor_hud.py
  ```

- [ ] **Step 3: Update `build-linux` PyInstaller command**

  Find (~line 86):
  ```yaml
  run: python -m PyInstaller --onefile --windowed --name CursorHUD cursor_hud.py
  ```
  _(under `build-linux` job)_

  Replace with:
  ```yaml
  run: python -m PyInstaller --onefile --windowed --name CursorHUD --icon=assets/icon_256.png cursor_hud.py
  ```

- [ ] **Step 3: Verify YAML syntax**
  ```bash
  python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml')); print('OK')"
  ```
  Expected: `OK` (requires `pip install pyyaml` if not present)

- [ ] **Step 4: Add CHANGELOG entry for icon in build**

  In `CHANGELOG.md`, under `### Features` in `## v1.0.0-beta.6 — Unreleased`, add:
  ```markdown
  - **App icon**: custom HUD icon displayed in OS taskbar, Dock, and Alt+Tab.
    Icon files live in `assets/`; PyInstaller bundles them into the EXE / .app.
    Graceful fallback to default OS icon if files are absent.
  ```

- [ ] **Step 5: Commit**
  ```bash
  git add .github/workflows/release.yml CHANGELOG.md
  git commit -m "feat(icon): add --icon flag to Windows and macOS PyInstaller builds"
  ```
