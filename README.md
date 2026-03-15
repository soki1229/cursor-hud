# Cursor HUD

> An always-on-top desktop HUD for monitoring your [Cursor](https://cursor.com) subscription usage in real time.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15%2B-green?logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?logo=windowsterminal&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Why this exists

The AI coding era has made subscription management more important than ever. Cursor's credit system — included credits, bonus credits, On-Demand spend — changes in real time as you code, but there's no native way to watch it without switching to a browser.

Cursor HUD sits on top of your other windows and shows everything at a glance, so you can stay focused and in control of your spend while you work.

---

## Who is this for

- Individual Cursor **Pro / Pro+ / Ultra** users who want passive spend awareness
- **Business / Enterprise** team members who want to track personal and team On-Demand costs
- Anyone who has ever been surprised by an unexpected Cursor bill

> **Free (Hobby) plan**: The app works, but Cursor does not expose credit data for free accounts via its API. Profile information is displayed; credit gauges are not available.

---

## How it compares

| Project | Form | Difference |
|---|---|---|
| cursor-stats | Cursor extension | Text only in IDE status bar |
| cursor-usage-monitor | VSCode extension | Requires IDE to be open |
| cursorusage.com | macOS menu bar | macOS only, commercial |
| cursor_costs | Web app | Requires manual token input |
| cursor-usage-tracker | Server + Slack bot | Enterprise only, team-focused |

**Cursor HUD** is the only standalone cross-platform desktop overlay — zero configuration, always visible, no IDE required.

---

## Features

- **Always-on-top HUD** — frameless window, stays visible while you code
- **Auto token detection** — reads auth token from Cursor's local SQLite DB, no manual setup
- **Credit breakdown** — included credits, bonus credits, On-Demand spend (personal + team)
- **Visual gauges** — arc gauge + color-coded progress bars
- **Usage rates** — Cursor official usage %, team pool share
- **4 themes** — Dark · Light · Midnight · Matrix
- **Korean / English UI**
- **60-second auto-refresh** with live countdown
- **In-app debug log** panel for troubleshooting
- **Start on Boot** — native startup registration (Windows registry, macOS LaunchAgent, Linux XDG autostart)
- **Pre-built binaries** — no installation required

---

## Screenshots

| Dark (Pro) | Light (Enterprise) |
|---|---|
| ![Credits (Pro) — Dark](assets/dark/credits_pro.jpg) | ![Credits (Enterprise) — Light](assets/light/credits_enterprise.jpg) |

→ [All screenshots by theme](SCREENSHOTS.md)

---

## Requirements

**Python (run from source) — all platforms:**
```
Python 3.10+
pip install pyqt5 requests
```

**Pre-built binary:**

| Platform | Requirement |
|---|---|
| Windows 10 / 11 | [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) (usually already installed) |
| macOS 13+ (Apple Silicon) | Unzip, then `xattr -cr CursorHUD.app` to clear quarantine before first run |
| Linux (glibc 2.35+, x11) | `chmod +x CursorHUD-Linux` before running; XCB libraries required |

---

## Quick Start

### Run from source

```bash
git clone https://github.com/soki1229/cursor-hud.git
cd cursor-hud
pip install pyqt5 requests
python cursor_hud.py
```

### Build a standalone binary

**Windows** — produces `dist/CursorHUD.exe`:
```powershell
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name CursorHUD cursor_hud.py
```

**macOS** — produces `dist/CursorHUD.app` (zipped for distribution):
```bash
pip install pyinstaller
python -m PyInstaller --windowed --name CursorHUD cursor_hud.py
zip -r CursorHUD-macOS.zip dist/CursorHUD.app
```

**Linux** — produces a single executable `dist/CursorHUD`:
```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name CursorHUD cursor_hud.py
```

---

## How it works

1. Cursor stores your session token in a local SQLite database:

   | Platform | Path |
   |---|---|
   | Windows | `%APPDATA%\Cursor\User\globalStorage\state.vscdb` |
   | macOS | `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` |
   | Linux | `~/.config/Cursor/User/globalStorage/state.vscdb` |

2. The app copies this file to a temp path (to avoid file locking), reads the token, and decodes the user ID from the JWT payload.
3. It calls Cursor's internal API (`/api/usage-summary`, `/api/auth/me`) using the session cookie.
4. Data is parsed and rendered. The temp copy is deleted immediately.
5. Repeats every 60 seconds.

No credentials are stored. No data leaves your machine except the API call to `cursor.com`.

---

## Plan support

| Plan | Credit gauges | On-Demand | Team data | Profile |
|---|---|---|---|---|
| Free (Hobby) | ✗ | ✗ | ✗ | ✓ |
| Pro / Pro+ / Ultra | ✓ | ✓ | ✗ | ✓ |
| Business / Enterprise | ✓ | ✓ | ✓ | ✓ |

Free accounts return zero credit data from Cursor's API — this is a Cursor platform limitation, not a bug in this app.

---

## Color logic

**`pct_color`** — usage-based (arc gauge, official usage rate bars)

| Usage | Color |
|---|---|
| 0 – 74% | accent (theme color) |
| 75 – 89% | amber |
| 90 – 100% | red |

**`remain_color`** — remaining credit bars (traffic-light, independent of theme)

| Remaining | Color |
|---|---|
| 51 – 100% | green |
| 26 – 50% | amber |
| 0 – 25% | red |

---

## Settings

| Setting | Description |
|---|---|
| Language | Korean / English |
| Theme | Dark / Light / Midnight / Matrix |
| Show Team Data | Toggle team On-Demand row |
| Show On-Demand Costs | Toggle OD cost card |
| Show Official Usage Rate | Toggle usage rate card |
| Start on Boot | Register / unregister OS startup (Windows: registry · macOS: LaunchAgent · Linux: XDG autostart) |

Settings are saved to `cursor_hud_settings.json` next to the executable.

---

## Project structure

```
cursor-hud/
├── cursor_hud.py              # Entire application — single file
├── README.md
├── .gitignore
└── assets/
    ├── dark/                  # All 3 tabs
    │   ├── credits_pro.jpg
    │   ├── credits_enterprise.jpg
    │   ├── profile_pro.jpg
    │   └── settings.jpg
    ├── light/                 # Credits only
    │   ├── credits_pro.jpg
    │   └── credits_enterprise.jpg
    ├── midnight/
    │   ├── credits_pro.jpg
    │   └── credits_enterprise.jpg
    └── matrix/
        ├── credits_pro.jpg
        └── credits_enterprise.jpg
```

Kept as a single file intentionally — binary build stays trivial, distribution stays simple. Internal sections are clearly delimited:

```
EXE-SAFE PATHS · LOGGING · THEME SYSTEM · CONSTANTS · I18N + SETTINGS
TOKEN / DB · DATA FETCHER · DATA PARSER · UI HELPERS
WIDGETS (ArcGauge, SegBar, MiniBar, Card, ToggleSwitch)
KV-ROW FACTORY · DEBUG DIALOG
PAGE: CREDITS · PAGE: PROFILE · PAGE: SETTINGS
STATUS BAR · NAV BAR · MAIN WINDOW · PLATFORM HELPERS · ENTRY POINT
```

---

## Privacy

- No telemetry, no analytics, no external services
- Token is read from local disk and used only to call `cursor.com`
- Temp DB copy is deleted immediately after reading
- Logs written locally to `cursor_hud.log` next to the executable

---

## Disclaimer

This project is not affiliated with or endorsed by Cursor / Anysphere Inc.
It uses undocumented internal API endpoints that may change without notice.
Use at your own risk.

---

## Contributing

Issues and PRs are welcome. The entire codebase is a single Python file — no build system knowledge required beyond `pip install pyqt5 requests`.

For bug reports, please include the contents of the in-app **Log** panel (bottom-right button).

---

## License

MIT © 2026 soki1229

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
