# Changelog

## v1.0.0-beta.9 — 2026-03-23

### Features
- **Leaderboard tab** (experimental gate): new tab at index 2 (Credits → Analytics → Leaderboard → Profile → Settings).
  - Tab / Composer sub-toggle: two checkable buttons switch between the two leaderboard views without re-fetching.
  - Tab leaderboard columns: rank · name · accepts · acceptance ratio (%) · favourite model.
  - Composer leaderboard columns: rank · name · diff accepts · line acceptance ratio (%) · favourite model.
  - Members with zero activity rendered at 50 % opacity.
  - Billing cycle label and member count shown in card header.
  - Keyboard shortcuts: Ctrl+3 (Leaderboard), Ctrl+4 (Profile), Ctrl+5 (Settings).
  - Data source: `GET /api/v2/analytics/team/leaderboard` with session token auth.
- **Analytics tab — JSON API migration**: replaced the CSV streaming pipeline with `POST /api/dashboard/get-filtered-usage-events`; no longer requires a team ID.
  - `pageSize: 500` retrieves the full billing-cycle event log in a single request.
  - Cost priority per event: `chargedCents` → `tokenUsage.totalCents` → 0.0 (float accumulation, no truncation).
  - Card header now shows an event-count badge (e.g. "351 events") alongside the billing cycle label.
- **CSV export removed**: the CSV export button and its pipeline (`CsvFetcher`, `AnalyticsFetcher`, csv import, QFileDialog) have been deleted. The `csv_team_id` settings field has been removed.
- **`set_experimental_visible()`** on `NavBar` (renamed from `set_analytics_visible`): hides / shows both Analytics and Leaderboard tabs together; switching off while on either tab redirects to Credits.

### Fixes
- `_trigger_analytics_fetch` no longer extracts `team_id` / `is_enterprise` from data; `UsageEventsFetcher` takes only `start_ms` / `end_ms`.

---

## v1.0.0-beta.8 — 2026-03-21

### Features
- **Analytics tab** (experimental gate): new tab between Credits and Profile.
  - Tab order: Credits → Analytics → Profile → Settings (Settings always last).
  - Model usage donut pie chart: each model gets a distinct color; center shows
    total cost for the billing cycle.
  - Legend rows below the chart: color swatch · model name · % share · cost.
  - Billing cycle label and Refresh button in the card header.
  - CSV-based cost aggregation via `GET /api/dashboard/export-usage-events-csv`;
    parsed with `csv.reader` for RFC 4180 compliance.
  - Team Spend section removed (enterprise API does not expose per-member spend).
  - Fetcher deferred until `_on_data` has fired; cancelled cleanly when
    experimental features are disabled.
  - Keyboard shortcut: Ctrl+2.
- **Settings page**: version label (`v1.0.0-beta.8`) and GitHub link in the card
  header; both update color on theme change.
- **`scripts/check_api.py`**: API endpoint explorer — tests GET + POST endpoints
  and prints full response bodies to help diagnose token/team-ID issues.
- **`PieChart` widget**: donut-style pie chart with antialiasing, configurable
  hole ratio, and center text label.

### Fixes
- `DataFetcher.run()` no longer early-returns when `/api/usage-summary` fails;
  always emits `ready()` with `summary_ok: bool` so the Profile tab populates
  even when the summary endpoint returns an error.
- `DataFetcher._get()`: wrap `r.json()` in `try/except ValueError` to handle
  empty or non-JSON 2xx responses without raising `JSONDecodeError`.
- `log.exception` → `log.error(exc_info=False)` to suppress 3× chained
  traceback spam from urllib3 in the debug log.
- Analytics tab background was transparent (showing desktop) due to
  `WA_TranslucentBackground` on `QScrollArea`; fixed by removing the attribute
  and using unscoped `"background:transparent;"` stylesheet.
- CSV column guard corrected from `< 12` to `< 11` (actual column count);
  previously caused all CSV rows to be silently skipped, resulting in empty
  Model Usage display.
- Language buttons now correctly i18n'd: Korean UI shows "한국어" / "영어";
  English UI shows "Korean" / "English".

---

## v1.0.0-beta.7 — 2026-03-20

### Features
- **Mini-mode redesigned**: credit rows now use a 2-line layout per credit type.
  - Line 1: type name (Plan / Bonus / On-Demand) with right-aligned chips showing
    full units consumed beyond the base limit; dollar amount displayed at the far right.
  - Line 2: full-width MiniBar progress bar showing progress within the current unit.
  - Chips are fixed-size (8 × 6 px) and built right-to-left; up to 10 chips per row.
  - All MiniBar right edges share the same axis as the amount label right edge.

### Fixes
- Mini-mode label text was invisible due to `setStyleSheet` overriding the color set
  by `set_lbl_color()`; redundant stylesheet call removed.

---

## v1.0.0-beta.6 — 2026-03-19

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
- **Experimental section**: Settings tab now has an "Experimental" section at
  the bottom (disabled by default). Enable it to reveal CSV export controls.
  - Toggle OFF (default): CSV export button and Team ID field are hidden.
  - Toggle ON: CSV export button appears in Credits tab; Team ID input appears
    in Settings tab.
- `show_experimental` setting added to `DEFAULT_SETTINGS` (default: `False`).
- **App icon**: custom icon assets embedded into all platform builds.
  - Place `assets/icon.ico` (Windows), `assets/icon.icns` (macOS), `assets/icon_256.png`
    (Linux/fallback) before building.
  - Dev mode (non-frozen): `app.setWindowIcon()` loads the raster PNG/ICO at startup if
    the file is present; no-op when the asset is absent.
  - Release builds: PyInstaller `--icon` flag embeds the icon into EXE / `.app` / Linux
    binary so the taskbar/Dock icon is correct without any runtime file.
- **Edge snap**: window snaps to screen edges (left/right/top/taskbar boundary)
  when released within 30 px of an edge. Works on all platforms; respects
  taskbar area via `availableGeometry()`. Multi-monitor aware.
- **Screen clamp**: window is automatically repositioned to remain fully
  visible whenever its height changes (tab switch, mini↔full mode toggle,
  data load) or on startup with a saved position.

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