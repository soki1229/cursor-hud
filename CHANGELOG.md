# Changelog

## v1.0.0-beta.6 — Unreleased

### Features
- **Export CSV**: "Export CSV" button added at the bottom of the Credits page.
  - Calls `GET /api/dashboard/export-usage-events-csv` with the current billing
    cycle's start/end dates and the team ID extracted from the API response.
  - Parameters: `teamId`, `isEnterprise`, `startDate`/`endDate` (ms timestamps),
    `strategy=tokens`.
  - Opens a native file-save dialog (defaults to `~/Downloads/cursor_usage_<start>_<end>.csv`).
  - Button temporarily shows "Saved" / "…" feedback during fetch/write.
  - `CsvFetcher(QThread)` runs the download off the main thread; errors are
    surfaced via `QMessageBox`.
- `_date_to_ms()` helper converts `YYYY-MM-DD` billing cycle strings to UTC ms timestamps.
- `parse_data()` now extracts `team_id` (tries `teamId`, `organizationId`, `id` across
  summary and profile responses) and `is_enterprise` flag.

### Fixes
- **CSV export without Team ID**: The "Export CSV" button no longer requires a
  Team ID to be set. When no Team ID is configured the endpoint is called without
  `teamId`, which returns the current user's personal usage events (On-Demand).
  Providing a Team ID in Settings still exports aggregate team usage as before.
- Settings page placeholder updated (`"optional — blank = personal data"`) to
  communicate that the field is not required.
- `CsvFetcher`: `teamId` parameter is omitted from the HTTP request when the
  value is empty (previously it sent `teamId=` which is the same as omitting it,
  but the code is now explicit).

---

## v1.0.0-beta.5 — 2026-03-15

### Fixes
- **Font warning eliminated**: replaced all hardcoded `Segoe UI` / `Consolas` references
  with platform-appropriate constants (`_UI_FONT`, `_MONO_FONT`).
  - Windows: `Segoe UI` / `Consolas` (unchanged)
  - macOS: `Helvetica Neue` / `Menlo`
  - Linux: `DejaVu Sans` / `DejaVu Sans Mono`
  Eliminates the 88 ms Qt alias-lookup penalty on macOS/Linux at startup.

### Build
- **macOS bundle size** reduced from 79 MB to 69 MB by removing unused Qt frameworks
  (`QtQuick`, `QtQml`, `QtQmlModels`, `QtNetwork`, `QtWebSockets`) post-build.
  `QtPrintSupport` is retained as it is a required dependency of the cocoa platform plugin.
  CI workflow updated with a "Strip unused Qt frameworks" step.

---

## v1.0.0-beta.4 — 2026-03-15

### Features
- **Cross-platform support**: app now runs on macOS and Linux in addition to Windows.
  - DB path: `~/Library/Application Support/Cursor/...` (macOS), `~/.config/Cursor/...` (Linux).
  - Start on Boot: macOS uses a LaunchAgent plist (`~/Library/LaunchAgents/com.cursor-hud.plist`); Linux uses an XDG autostart `.desktop` file (`~/.config/autostart/cursor-hud.desktop`, `XDG_CONFIG_HOME`-aware). Windows registry unchanged.
  - DPI awareness: Windows ctypes path preserved; macOS/Linux delegate to Qt `AA_EnableHighDpiScaling`.
  - "Start on Boot" settings toggle now visible on all platforms.

### CI
- Release workflow split into three parallel build jobs (`build-windows`, `build-macos`, `build-linux`) + a single `release` job that waits for all three and uploads all artifacts to the GitHub Release.
  - Windows: `CursorHUD.exe` (PyInstaller `--onefile --windowed`)
  - macOS: `CursorHUD-macOS.zip` (`.app` bundle, `macos-latest` / Apple Silicon)
  - Linux: `CursorHUD-Linux` (PyInstaller `--onefile --windowed`, XCB dependencies pre-installed)

---

## v1.0.0-beta.3 — 2026-03-12

### UI
- **Mini mode (credits)**: Section headers (Included / Bonus / Extra) shown above the first bar of each group; dollar amount shown on the last bar only (overflow bars no longer repeat the amount on every segment). Narrower amount column (56px); header and amount labels both scale with window DPI.

### Docs & tooling
- Claude rules and `CLAUDE.md`: project conventions, section map, context-sync rule.

### Refactors
- Default settings: language/theme default to `en` / `light`; theme order and fallbacks aligned.
- Logging: consistent defaults and docstrings.

### Chore
- Project line endings normalized to LF; README fix.

---

## v1.0.0-beta.2 — 2026-03-10

### Features
- System tray: minimize to tray, show/hide from tray menu
- Global shortcuts: Escape to close/minimize
- Usage metrics (local event counts; no server upload)
- Debug panel and credits page improvements; section header helper

### Refactors
- Docstring and imports cleanup; v4 → v4.1
- Settings/API: `load_settings`, `read_cursor_token`, `api_headers`, DataFetcher, `parse_data`
- QSS helpers, hatch pixmap cache; ArcGauge, SegBar, MiniBar, Card, ToggleSwitch (full-row click, `toggle()`)
- ProfilePage, SettingsPage (row click); StatusBar, NavBar, ResizeGrip, CompactStack
- HUDWindow: tray, shortcuts, size/position handling; `main()` tweaks

### CI
- Release workflow: CHANGELOG extraction with `index()` and debug echo

---

## v1.0.0-beta.1 — 2026-03-10

First release (beta).

### Features
- Always-on-top HUD for monitoring Cursor subscription usage
- Auto token detection from Cursor’s local SQLite DB
- Credit breakdown: included, bonus, On-Demand (personal + team)
- Arc gauge and color-coded progress bars; responsive window width
- 4 themes: Dark · Light · Midnight · Matrix
- Korean / English UI; locale-friendly date and “days left” until billing renewal
- Settings: window position/size persistence, pin-on-top, show/hide personal & org credits
- 60-second auto-refresh with live countdown
- In-app debug log panel
- Start on Boot (Windows startup registration)
- Free plan detection with graceful fallback UI
- Single-file EXE distribution