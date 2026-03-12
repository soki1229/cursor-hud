# Changelog

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