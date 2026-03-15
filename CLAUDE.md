# CLAUDE.md

Cursor subscription credit monitor — always-on-top HUD (Windows, macOS, Linux).

## Stack

Python 3.10+ · PyQt5 · requests · single-file (`cursor_hud.py`, ~2,800 lines) · PyInstaller EXE.
Single-file is intentional (trivial build/distribution). **Do not split.**

## Commands

```bash
python cursor_hud.py            # run
python cursor_hud.py --mock     # mock data, no API calls
pip install pyqt5 requests pyinstaller
python -m PyInstaller --onefile --windowed --name CursorHUD cursor_hud.py
```

## Architecture (key decisions only)

- **Code layout**: sections delimited by `# ══════…` banners — grep banner text
  to navigate (e.g. `THEME SYSTEM`, `DATA FETCHER`, `PAGE: CREDITS`).
- **DB access**: copy `state.vscdb` → temp file → read → delete (avoids lock).
- **Async data**: `DataFetcher(QThread)` → `ready` / `error` signals → UI.
- **Themes**: global `_THEME` dict of RGB(A) tuples; `c(key)` → `QColor`.
- **Settings**: `cursor_hud_settings.json` next to EXE (gitignored).
- **API**: `GET /api/usage-summary`, `GET /api/auth/me`; auth via
  `WorkosCursorSessionToken` cookie. Undocumented — may break.

## Conventions (non-obvious only)

- Add both `ko` and `en` entries in `STRINGS` dict for any new UI text.
- Use `c("key")` for colors — never hard-code hex in widgets.
- `KVRow = tuple[QLabel, QLabel]`; create with `kv_row()`, update with `set_kv()`.
- Widgets use `paintEvent` override for custom rendering.
- Preserve `# ══════…` banner pattern when adding new sections.

## Gotchas

- **Never commit** `cursor_hud_settings.json` or `cursor_hud.log`.
- **Redact** tokens/emails as `[REDACTED]` in any log or debug output.
- `register_startup()` is cross-platform: Windows → registry (`HKCU\...\Run`), macOS → `~/Library/LaunchAgents/com.cursor-hud.plist`, Linux → `~/.config/autostart/cursor-hud.desktop` (XDG-aware).
- Refresh default 60 s; override with `CURSOR_REFRESH_MS` env var (min 5 s).
- CI: `.github/workflows/release.yml` — `v*` tag → 3 parallel builds (Windows `.exe`, macOS `.app` zip, Linux binary) → single GitHub Release.
