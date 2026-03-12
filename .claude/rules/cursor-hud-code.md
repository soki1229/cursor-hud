---
paths:
  - cursor_hud.py
---

# cursor_hud.py Section Map

Grep for the banner text (`# ══.*<TEXT>`) to jump to each section.

| Banner               | Key symbols                                                              |
|----------------------|--------------------------------------------------------------------------|
| `EXE-SAFE PATHS`     | `_app_dir()`, `APP_DIR`, `SETTINGS_FILE`, `LOG_FILE`                     |
| `LOGGING`            | `_MemHandler` (300-record ring buffer)                                   |
| `USAGE METRICS`      | `_UsageMetrics` — local-only counters, never sent                        |
| `THEME SYSTEM`       | `THEMES`, `c()`, `apply_theme()`, `TH()`, `track_bg()`                  |
| `QSS HELPERS`        | `_icon_btn_qss()`, `_pill_btn_qss()`, `_theme_btn_qss()`                |
| `CONSTANTS`          | `VERSION`, `BASE_URL`, `WIN_W`, `WIN_H`, `REFRESH_MS`                   |
| `I18N`               | `STRINGS` (ko/en), `DEFAULT_SETTINGS`, `load_settings()`, `S()`         |
| `TOKEN / DB`         | `_cursor_db_path()`, `decode_jwt()`, `read_cursor_token()`, `api_headers()` |
| `DATA FETCHER`       | `DataFetcher(QThread)` — calls `/api/usage-summary` + `/api/auth/me`     |
| `DATA MODEL`         | `parse_data()`, `_safe_int()`, `_safe_float()`                           |
| `UI HELPERS`         | `usd()`, `fmt_date()`, `days_left_text()`, `pct_color()`, `remain_color()` |
| `HATCH HELPER`       | `_get_hatch_pixmap()`, `_draw_hatch()`                                   |
| `PRIMITIVE WIDGETS`  | `ArcGauge`, `SegBar`, `MiniBar`, `Card`, `Divider`, `ToggleSwitch`       |
| `KV-ROW FACTORY`     | `kv_row()`, `set_kv()`, `section_hdr()`, `KVRow`                        |
| `DEBUG DIALOG`       | `DebugDialog` — Logs / JSON / Metrics tabs                               |
| `PAGE: CREDITS`      | `CreditsPage` — hero card, arc gauge, seg bars, OD display                |
| `PAGE: PROFILE`      | `ProfilePage` — account info                                             |
| `PAGE: SETTINGS`     | `SettingsPage` — lang, theme, toggles, startup reg                        |
| `STATUS BAR`         | `StatusBar` — countdown, log button                                       |
| `NAV BAR`            | `NavBar` — Credits / Profile / Settings tabs                              |
| `MAIN WINDOW`        | `HUDWindow` — drag, tray, shortcuts, data flow                           |
| `PLATFORM HELPERS`   | `enable_dpi()`, `register_startup()`, `unregister_startup()`              |
| `ENTRY POINT`        | `main()` — `--mock`, `--install-startup`, `--uninstall-startup`           |

## Color thresholds

`pct_color(pct)`: 0-74 accent, 75-89 amber, 90-100 red.
`remain_color(remain_pct)`: 51-100 green, 26-50 amber, 0-25 red.

## Settings keys

`lang`, `theme`, `show_personal`, `show_org`, `show_official`, `pin_on_top`,
`win_x`, `win_y`, `win_w`, `mini_mode`.
