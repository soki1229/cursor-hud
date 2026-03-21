#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  CURSOR HUD  v4.1  ·  Personal Usage Monitor                 ║
║  3-tab · 4 themes · Tray · Shortcuts · Debug · EXE-safe      ║
╚══════════════════════════════════════════════════════════════╝
Build EXE:
  pip install pyqt5 requests pyinstaller
  python -m PyInstaller --onefile --windowed --name CursorHUD cursor_hud.py
"""

import sys
import os
import sqlite3
import shutil
import logging
import tempfile
import base64
import json
import math
import csv as _csv
import datetime as _dt
from datetime import datetime, timezone, date as _date
from pathlib import Path

import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox, QSizePolicy,
    QTextEdit, QDialog, QTabWidget, QSystemTrayIcon, QMenu, QAction,
    QShortcut, QFileDialog, QLineEdit,
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QRectF, QPointF, QSize, qInstallMessageHandler
from PyQt5.QtGui import (
    QColor, QPainter, QBrush, QPen, QPainterPath, QPixmap, QIcon,
    QLinearGradient, QRadialGradient, QFont, QScreen, QKeySequence,
)

# ══════════════════════════════════════════════════════════════
#  EXE-SAFE PATHS
# ══════════════════════════════════════════════════════════════
def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent

APP_DIR       = _app_dir()
SETTINGS_FILE = APP_DIR / "cursor_hud_settings.json"
LOG_FILE      = APP_DIR / "cursor_hud.log"

# ══════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════
_log_handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
try:
    _log_handlers.insert(0, logging.FileHandler(str(LOG_FILE), encoding="utf-8"))
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=_log_handlers,
)
log = logging.getLogger("CursorHUD")


class _MemHandler(logging.Handler):
    MAX = 300

    def __init__(self):
        super().__init__()
        self.records: list[str] = []
        self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    def emit(self, record):
        self.records.append(self.format(record))
        if len(self.records) > self.MAX:
            self.records = self.records[-self.MAX:]


_mem_log = _MemHandler()
logging.getLogger("CursorHUD").addHandler(_mem_log)

# ══════════════════════════════════════════════════════════════
#  USAGE METRICS (local-only event counters for UX analysis)
# ══════════════════════════════════════════════════════════════
class _UsageMetrics:
    """Simple in-memory event counters — never sent to any server."""

    def __init__(self):
        self.session_start = datetime.now()
        self._counts: dict[str, int] = {}

    def inc(self, event: str):
        self._counts[event] = self._counts.get(event, 0) + 1

    def dump(self) -> str:
        elapsed = (datetime.now() - self.session_start).total_seconds()
        lines = [f"Session: {elapsed:.0f}s"]
        for k, v in sorted(self._counts.items()):
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)


_metrics = _UsageMetrics()

# ══════════════════════════════════════════════════════════════
#  THEME SYSTEM
# ══════════════════════════════════════════════════════════════
THEMES: dict[str, dict] = {
    "dark": {
        "name": "dark",
        "bg_win": (10, 12, 24), "bg_win2": (5, 7, 16), "bg_card": (13, 16, 28),
        "accent": (0, 220, 255), "accent2": (130, 80, 255),
        "c_green": (0, 240, 140), "c_amber": (255, 185, 50), "c_red": (255, 70, 90),
        "t_bright": (230, 240, 255), "t_body": (170, 185, 215),
        "t_muted": (90, 110, 150), "t_dim": (50, 65, 95),
        "border_lo": (255, 255, 255, 18), "border_hi": (0, 220, 255, 45),
        "scrollbar": "rgba(0,220,255,0.22)", "hatch_alpha": 38,
        "track_bg": (255, 255, 255, 30),
    },
    "light": {
        "name": "light",
        "bg_win": (240, 244, 255), "bg_win2": (225, 232, 248), "bg_card": (255, 255, 255),
        "accent": (0, 145, 200), "accent2": (100, 55, 210),
        "c_green": (0, 170, 90), "c_amber": (200, 130, 0), "c_red": (210, 40, 60),
        "t_bright": (15, 20, 45), "t_body": (55, 70, 110),
        "t_muted": (130, 145, 180), "t_dim": (185, 195, 220),
        "border_lo": (0, 0, 0, 20), "border_hi": (0, 145, 200, 60),
        "scrollbar": "rgba(0,145,200,0.30)", "hatch_alpha": 55,
        "track_bg": (0, 0, 0, 22),
    },
    "midnight": {
        "name": "midnight",
        "bg_win": (6, 4, 18), "bg_win2": (2, 1, 9), "bg_card": (12, 8, 28),
        "accent": (160, 80, 255), "accent2": (255, 60, 160),
        "c_green": (0, 220, 120), "c_amber": (255, 160, 40), "c_red": (255, 50, 80),
        "t_bright": (240, 230, 255), "t_body": (185, 165, 220),
        "t_muted": (100, 80, 145), "t_dim": (55, 40, 90),
        "border_lo": (255, 255, 255, 14), "border_hi": (160, 80, 255, 55),
        "scrollbar": "rgba(160,80,255,0.28)", "hatch_alpha": 35,
        "track_bg": (255, 255, 255, 24),
    },
    "matrix": {
        "name": "matrix",
        "bg_win": (0, 8, 0), "bg_win2": (0, 4, 0), "bg_card": (0, 14, 0),
        "accent": (0, 255, 70), "accent2": (0, 200, 50),
        "c_green": (0, 255, 70), "c_amber": (180, 255, 0), "c_red": (255, 100, 0),
        "t_bright": (200, 255, 200), "t_body": (100, 200, 100),
        "t_muted": (40, 110, 40), "t_dim": (20, 55, 20),
        "border_lo": (0, 255, 70, 16), "border_hi": (0, 255, 70, 50),
        "scrollbar": "rgba(0,255,70,0.25)", "hatch_alpha": 30,
        "track_bg": (0, 255, 70, 22),
    },
}

_THEME: dict = THEMES["light"]


def TH() -> dict:
    return _THEME


def c(key: str) -> QColor:
    v = _THEME.get(key)
    if v is None:
        log.warning("Unknown theme key: %s", key)
        return QColor(255, 0, 255)  # magenta = obvious debug indicator
    if isinstance(v, str):
        return QColor()
    return QColor(*v) if len(v) == 3 else QColor(v[0], v[1], v[2], v[3])


def apply_theme(name: str):
    global _THEME
    _THEME = THEMES.get(name, THEMES["light"])


def hatch_alpha() -> int:
    return _THEME.get("hatch_alpha", 38)


def track_bg() -> QColor:
    v = _THEME.get("track_bg", (255, 255, 255, 28))
    return QColor(v[0], v[1], v[2], v[3])


# ══════════════════════════════════════════════════════════════
#  QSS HELPERS  — deduplicated style generators
# ══════════════════════════════════════════════════════════════
def _icon_btn_qss(fg: str = None, hv: str = None, sz: int = 11) -> str:
    """Minimal icon-style button (no bg, no border)."""
    fg = fg or c("t_muted").name()
    hv = hv or c("t_bright").name()
    return (
        f"QPushButton{{color:{fg};background:transparent;"
        f"border:none;font-size:{sz}px;}}"
        f"QPushButton:hover{{color:{hv};}}"
    )


def _pill_btn_qss(active_color: str = None) -> str:
    """Small pill button with border (language / debug / refresh)."""
    mu = c("t_muted").name()
    ac = active_color or c("accent").name()
    return (
        f"QPushButton{{ color:{mu}; background:transparent;"
        f" border:1px solid rgba(128,128,128,0.28); border-radius:3px;"
        f" font-size:9px; padding:1px 12px; font-family:{_UI_FONT}; font-weight:600; }}"
        f" QPushButton:checked{{ color:{ac}; border:1px solid {ac};"
        f" background:rgba(128,128,128,0.10); }}"
    )


def _theme_btn_qss(theme: dict, checked: bool = False) -> str:
    av = theme["accent"]
    ac_hex = QColor(*av).name()
    bg_hex = QColor(*theme["bg_card"]).name()
    mu = c("t_muted").name()
    return (
        f"QPushButton{{ color:{mu}; background:{bg_hex};"
        f" border:1px solid rgba(128,128,128,0.25); border-radius:5px;"
        f" font-size:9px; font-family:{_UI_FONT}; font-weight:600; }}"
        f" QPushButton:checked{{ color:{ac_hex}; border:2px solid {ac_hex};"
        f" background:rgba({av[0]},{av[1]},{av[2]},25); }}"
        f" QPushButton:hover{{ border:1px solid rgba(128,128,128,0.50); }}"
        f" QPushButton:checked:hover{{ border:2px solid {ac_hex}; }}"
    )


# ══════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════
VERSION   = "1.0.0-beta.7"
BASE_URL  = "https://cursor.com"

# Platform-appropriate fonts — avoids Qt alias-lookup penalty for missing families
if sys.platform == "win32":
    _UI_FONT   = "Segoe UI"
    _MONO_FONT = "Consolas"
elif sys.platform == "darwin":
    _UI_FONT   = "Helvetica Neue"
    _MONO_FONT = "Menlo"
else:
    _UI_FONT   = "DejaVu Sans"
    _MONO_FONT = "DejaVu Sans Mono"
WIN_W     = 400
WIN_W_MAX = 500
WIN_H     = 660
SNAP_PX       = 30      # px threshold for edge-snap on drag release
MINI_AMOUNT_W = 56      # mini-mode: fixed amount column width (px)
CHIP_W        = 8       # mini-mode: chip width (px)
CHIP_H        = 6       # mini-mode: chip height (px)
CHIP_GAP      = 3       # mini-mode: gap between chips (px)
CHIPS_MAX     = 10      # mini-mode: max chips per row
CHIPS_AREA_W  = CHIPS_MAX * CHIP_W + (CHIPS_MAX - 1) * CHIP_GAP  # fixed chips area width
ARC_MIN_W = 240


def _preset_win_w(screen=None) -> int:
    return WIN_W


try:
    REFRESH_MS = max(5000, int(os.environ.get("CURSOR_REFRESH_MS", "60000")))
except (ValueError, TypeError):
    REFRESH_MS = 60000

# ══════════════════════════════════════════════════════════════
#  I18N
# ══════════════════════════════════════════════════════════════
STRINGS: dict[str, dict[str, str]] = {
    "ko": {
        "nav_credit": "크레딧", "nav_profile": "프로필", "nav_settings": "설정",
        "spent_label": "소진", "remain_label": "잔여", "bonus_saved": "보너스 절약",
        "personal_section": "개인 크레딧",
        "incl_row": "기본 포함", "bonus_row": "보너스 사용", "bonus_free_label": "무료 처리됨",
        "status_included": "기본 크레딧 사용 중", "status_bonus": "보너스 크레딧 사용 중",
        "status_od": "추가 과금 사용 중",
        "status_badge_incl": "기본 크레딧 소진 중", "status_badge_bonus": "보너스 크레딧 소진 중",
        "status_badge_od": "PAYG",
        "row_incl": "기본 플랜", "row_bonus": "보너스", "row_extra": "추가 과금",
        "personal_od": "추가 과금", "org_section": "조직 크레딧", "org_od": "추가 과금 (팀)",
        "not_used": "미사용",
        "official_pct": "Cursor 공식 사용률",
        "auto_pct": "Auto 모델 사용률", "api_pct": "Named 모델 사용률",
        "profile_title": "계정", "field_name": "이름", "field_email": "이메일",
        "field_verified": "인증", "field_since": "가입일", "field_days": "가입 기간",
        "field_plan": "플랜", "field_cycle": "청구 주기",
        "verified_yes": "✓ 인증됨", "verified_no": "✗ 미인증", "member_days": "일",
        "settings_title": "설정", "lang_label": "언어", "theme_label": "테마",
        "theme_dark": "다크", "theme_light": "라이트",
        "theme_midnight": "미드나잇", "theme_matrix": "매트릭스",
        "show_sections": "표시 항목",
        "show_personal": "개인 크레딧", "show_org": "조직 크레딧", "show_official": "공식 사용률",
        "auto_saved": "자동 저장됨", "refresh_btn": "↻",
        "next_refresh": "갱신까지", "seconds": "초",
        "err_no_db": "Cursor DB를 찾을 수 없음\n",
        "err_token": "토큰 읽기 실패", "err_api": "API 응답 없음",
        "err_fetch": "데이터를 불러올 수 없습니다.",
        "err_retry": "재시도",
        "free_plan_notice": "크레딧 미제공 플랜",
        "lang_ko": "한국어", "lang_en": "English",
        "debug_btn": "로그", "debug_title": "디버그 로그",
        "debug_copy": "복사", "debug_close": "닫기",
        "startup_boot": "부팅 시 자동실행", "pin_top": "항상 위",
        "tray_show": "열기", "tray_refresh": "새로고침", "tray_quit": "종료",
        "csv_export": "CSV 내보내기", "csv_save_title": "사용 이벤트 CSV 저장",
        "csv_err_no_team": "팀 ID를 찾을 수 없습니다. 설정에서 직접 입력해 주세요.",
        "csv_err_fetch": "CSV 다운로드 실패", "csv_saved": "저장 완료",
        "csv_team_id_label": "팀 ID (CSV 내보내기)",
        "csv_team_id_placeholder": "선택 사항 — 비워두면 개인 데이터",
        "experimental_section": "실험적 기능",
        "experimental_toggle":  "실험적 기능 활성화",
        "experimental_hint":    "불안정하거나 변경될 수 있는 기능입니다",
        "nav_analytics":        "분석",
        "analytics_refresh":    "새로고침",
        "analytics_loading":    "불러오는 중…",
        "analytics_waiting":    "데이터 대기 중…",
        "analytics_error":      "불러오기 실패",
        "analytics_no_data":    "데이터 없음",
        "analytics_no_team_id": "팀 ID 없음 — 설정에서 입력하세요",
        "analytics_team_spend": "팀 지출",
        "analytics_model_usage": "모델 사용량",
        "analytics_cycle_label": "청구 주기",
        "analytics_members":    "명",
    },
    "en": {
        "nav_credit": "Credits", "nav_profile": "Profile", "nav_settings": "Settings",
        "spent_label": "Spent", "remain_label": "remaining", "bonus_saved": "bonus saved",
        "personal_section": "Personal Credits",
        "incl_row": "Included", "bonus_row": "Bonus Used", "bonus_free_label": "free of charge",
        "status_included": "On included credits", "status_bonus": "On bonus credits",
        "status_od": "On-Demand active",
        "status_badge_incl": "On included credits", "status_badge_bonus": "On bonus credits",
        "status_badge_od": "PAYG",
        "row_incl": "Plan credits", "row_bonus": "Bonus", "row_extra": "On-Demand",
        "personal_od": "On-Demand", "org_section": "Organization Credits",
        "org_od": "On-Demand (Team)", "not_used": "Not Used",
        "official_pct": "Cursor Official Usage",
        "auto_pct": "Auto Model Usage", "api_pct": "Named Model Usage",
        "profile_title": "Account", "field_name": "Name", "field_email": "Email",
        "field_verified": "Verified", "field_since": "Member Since",
        "field_days": "Membership", "field_plan": "Plan", "field_cycle": "Billing Cycle",
        "verified_yes": "✓ Verified", "verified_no": "✗ Not Verified", "member_days": "days",
        "settings_title": "Settings", "lang_label": "Language", "theme_label": "Theme",
        "theme_dark": "Dark", "theme_light": "Light",
        "theme_midnight": "Midnight", "theme_matrix": "Matrix",
        "show_sections": "Visible Sections",
        "show_personal": "Personal Credits", "show_org": "Organization Credits",
        "show_official": "Usage Rates",
        "auto_saved": "Auto-saved", "refresh_btn": "↻",
        "next_refresh": "Next refresh", "seconds": "s",
        "err_no_db": "Cursor DB not found\n",
        "err_token": "Failed to read token", "err_api": "No API response",
        "err_fetch": "Failed to load data.",
        "err_retry": "Retry",
        "free_plan_notice": "No credit data on Free plan",
        "lang_ko": "한국어", "lang_en": "English",
        "debug_btn": "Log", "debug_title": "Debug Log",
        "debug_copy": "Copy", "debug_close": "Close",
        "startup_boot": "Start on Boot", "pin_top": "Always on Top",
        "tray_show": "Show", "tray_refresh": "Refresh", "tray_quit": "Quit",
        "csv_export": "Export CSV", "csv_save_title": "Save Usage Events CSV",
        "csv_err_no_team": "Team ID not found. Enter it manually in Settings.",
        "csv_err_fetch": "CSV download failed", "csv_saved": "Saved",
        "csv_team_id_label": "Team ID (CSV export)",
        "csv_team_id_placeholder": "optional — blank = personal data",
        "experimental_section": "Experimental",
        "experimental_toggle":  "Enable experimental features",
        "experimental_hint":    "Features that may change or break",
        "nav_analytics":        "Analytics",
        "analytics_refresh":    "Refresh",
        "analytics_loading":    "Loading…",
        "analytics_waiting":    "Waiting for data…",
        "analytics_error":      "Failed to load",
        "analytics_no_data":    "No data",
        "analytics_no_team_id": "No team ID — enter in Settings",
        "analytics_team_spend": "Team Spend",
        "analytics_model_usage": "Model Usage",
        "analytics_cycle_label": "Billing cycle",
        "analytics_members":    "members",
    },
}

DEFAULT_SETTINGS: dict = {
    "lang": "en", "theme": "light",
    "show_personal": True, "show_org": True, "show_official": True,
    "pin_on_top": True,
    "win_x": None, "win_y": None, "win_w": WIN_W, "mini_mode": False,
    "csv_team_id": "",        # override for CSV export teamId (empty = auto-detect)
    "show_experimental": False,  # gates all Experimental features
}


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT_SETTINGS, **saved}
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(s: dict):
    try:
        SETTINGS_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")
    except Exception as e:
        log.error("save_settings failed: %s", e)


def S(settings: dict, key: str) -> str:
    lang = settings.get("lang", "en")
    return STRINGS.get(lang, STRINGS["ko"]).get(key, key)


# ══════════════════════════════════════════════════════════════
#  TOKEN / DB
# ══════════════════════════════════════════════════════════════
def _cursor_db_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", ""))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    return base / "Cursor" / "User" / "globalStorage" / "state.vscdb"


def decode_jwt(token: str) -> dict:
    try:
        p = token.split(".")[1]
        p += "=" * (4 - len(p) % 4)
        return json.loads(base64.urlsafe_b64decode(p))
    except Exception:
        return {}


def read_cursor_token() -> tuple[str, str]:
    db_path = _cursor_db_path()
    if not db_path.exists():
        return "", ""
    fd, tmp_str = tempfile.mkstemp(suffix=".vscdb")
    tmp = Path(tmp_str)
    try:
        try:
            os.close(fd)
        except OSError:
            pass
        shutil.copy2(db_path, tmp)
        conn = sqlite3.connect(str(tmp))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        def _r(k):
            cur.execute("SELECT value FROM ItemTable WHERE key=? LIMIT 1", (k,))
            row = cur.fetchone()
            return (row["value"] or "").strip() if row else ""

        token = _r("cursorAuth/accessToken")
        email = _r("cursorAuth/cachedEmail")
        conn.close()
        if not token:
            return "", email
        sub = decode_jwt(token).get("sub", "")
        uid = sub.split("|")[-1] if "|" in sub else sub
        return f"{uid}%3A%3A{token}", email
    except Exception as exc:
        log.error("read_cursor_token: %s", exc)
        return "", ""
    finally:
        tmp.unlink(missing_ok=True)


def api_headers(cookie: str) -> dict:
    return {
        "Cookie":       f"WorkosCursorSessionToken={cookie}",
        "Content-Type": "application/json",
        "Accept":       "application/json",
        "Origin":       "https://cursor.com",
        "Referer":      "https://cursor.com/",
        "User-Agent":   "Mozilla/5.0 (X11; Linux x86_64) Chrome/122.0.0.0",
    }


# ══════════════════════════════════════════════════════════════
#  DATA FETCHER  — blockSignals guard on replacement
# ══════════════════════════════════════════════════════════════
class DataFetcher(QThread):
    ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def _get(self, session, path):
        r = session.get(f"{BASE_URL}{path}", allow_redirects=False, timeout=12)
        if r.status_code in (301, 302, 307, 308):
            loc = r.headers.get("Location", "")
            if loc.startswith("/"):
                loc = BASE_URL + loc
            r = session.get(loc, timeout=12)
        log.debug("GET %s → %s", path, r.status_code)
        return r.json() if r.ok else None

    def run(self):
        cookie = ""
        try:
            cookie, email = read_cursor_token()
            if not cookie:
                self.error.emit(S(load_settings(), "err_token"))
                return
            sess = requests.Session()
            sess.headers.update(api_headers(cookie))
            summary = self._get(sess, "/api/usage-summary")
            profile = self._get(sess, "/api/auth/me")
            raw = {
                "summary":    summary or {},
                "summary_ok": summary is not None,
                "profile":    profile or {},
                "email":      email,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            self.ready.emit(raw)
        except Exception as exc:
            cookie = "[REDACTED]"  # prevent token leaking in traceback
            log.exception("DataFetcher.run")
            self.error.emit(str(exc))


# ══════════════════════════════════════════════════════════════
#  DATA MODEL
# ══════════════════════════════════════════════════════════════
def _safe_int(v, default: int = 0) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return default


def _safe_float(v, default: float = 0.0) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return default


def parse_data(raw: dict) -> dict:
    s  = raw.get("summary", {}) or {}
    pr = raw.get("profile", {}) or {}

    ind  = s.get("individualUsage", {})
    plan = ind.get("plan", {})
    bk   = plan.get("breakdown", {})
    od_p = ind.get("onDemand", {})
    od_t = s.get("teamUsage", {}).get("onDemand", {})

    cycle = {
        "start":      s.get("billingCycleStart", "")[:10],
        "end":        s.get("billingCycleEnd",   "")[:10],
        "membership": s.get("membershipType", "—").upper(),
        "limit_type": s.get("limitType",      "—").upper(),
    }

    incl_total  = _safe_int(bk.get("included", 0))
    bonus_used  = _safe_int(bk.get("bonus",    0))
    used_total  = _safe_int(plan.get("used",   0))

    plan_limit  = plan.get("limit")
    plan_remain = plan.get("remaining")
    if plan_limit:
        budget_total = _safe_int(plan_limit)
    elif plan_remain is not None:
        budget_total = used_total + _safe_int(plan_remain)
    else:
        budget_total = _safe_int(bk.get("total", 0))
    budget_remain = (_safe_int(plan_remain) if plan_remain is not None
                     else max(0, budget_total - used_total))
    incl_remain = max(0, budget_total - used_total)

    credit = {
        "incl_total":       budget_total,
        "incl_used":        used_total,
        "incl_remain":      incl_remain,
        "incl_remain_pct":  (incl_remain / budget_total * 100) if budget_total else 0,
        "bonus_used":       bonus_used,
        "budget_total":     budget_total,
        "budget_used":      used_total,
        "budget_pct":       (used_total / budget_total * 100) if budget_total else 0,
        "budget_remain":    budget_remain,
        "budget_remain_pct": (budget_remain / budget_total * 100) if budget_total else 0,
        "api_pct":          _safe_float(plan.get("apiPercentUsed",   0)),
        "auto_pct":         _safe_float(plan.get("autoPercentUsed",  0)),
        "total_pct":        _safe_float(plan.get("totalPercentUsed", 0)),
    }

    on_demand = {
        "personal": _safe_int(od_p.get("used", 0)),
        "team":     _safe_int(od_t.get("used", 0)),
    }

    created = pr.get("created_at", "") or ""
    days_member = 0
    if created:
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            days_member = (datetime.now(timezone.utc) - dt).days
        except Exception:
            pass

    profile = {
        "name":        pr.get("name",  "") or raw.get("email", ""),
        "email":       pr.get("email", "") or raw.get("email", ""),
        "verified":    bool(pr.get("email_verified", False)),
        "created_at":  created[:10],
        "days_member": days_member,
    }

    is_free = s.get("membershipType", "").lower() in ("free", "hobby")
    membership = s.get("membershipType", "").lower()
    is_team = membership in ("team", "enterprise", "business")
    is_enterprise = membership == "enterprise"

    # teamId for CSV export — try several paths (undocumented API, field name varies).
    # pr.get("id") is deliberately excluded: it is the userId, not the teamId.
    _team_candidates = {
        "summary.teamId":              s.get("teamId"),
        "summary.teamUsage.teamId":    s.get("teamUsage", {}).get("teamId"),
        "summary.organizationId":      s.get("organizationId"),
        "profile.teamId":              pr.get("teamId"),
        "profile.organizationId":      pr.get("organizationId"),
    }
    log.debug("teamId candidates: %s", _team_candidates)
    team_id = next((str(v) for v in _team_candidates.values() if v), "")

    return {
        "cycle":        cycle,
        "credit":       credit,
        "on_demand":    on_demand,
        "profile":      profile,
        "hint":         s.get("autoModelSelectedDisplayMessage", "") or "",
        "fetched_at":   raw.get("fetched_at", ""),
        "is_free":      is_free,
        "is_team":      is_team,
        "is_enterprise": is_enterprise,
        "team_id":      str(team_id),
    }


# ══════════════════════════════════════════════════════════════
#  CSV FETCHER
# ══════════════════════════════════════════════════════════════
def _date_to_ms(date_str: str) -> int:
    """Convert 'YYYY-MM-DD' to UTC millisecond timestamp (start of day)."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        return 0


class CsvFetcher(QThread):
    """Download usage-events CSV from the Cursor dashboard API."""
    ready = pyqtSignal(str)   # raw CSV text
    error = pyqtSignal(str)

    def __init__(self, team_id: str, start_ms: int, end_ms: int,
                 is_enterprise: bool):
        super().__init__()
        self._team_id       = team_id
        self._start_ms      = start_ms
        self._end_ms        = end_ms
        self._is_enterprise = is_enterprise

    def run(self):
        try:
            cookie, _ = read_cursor_token()
            if not cookie:
                self.error.emit("No auth token found.")
                return
            params = {
                "isEnterprise": str(self._is_enterprise).lower(),
                "startDate":    self._start_ms,
                "endDate":      self._end_ms,
                "strategy":     "tokens",
            }
            if self._team_id:
                params["teamId"] = self._team_id
            hdrs = api_headers(cookie)
            hdrs["Accept"] = "text/csv,*/*"
            r = requests.get(
                f"{BASE_URL}/api/dashboard/export-usage-events-csv",
                params=params, headers=hdrs, timeout=30, allow_redirects=True,
            )
            log.info("CsvFetcher → HTTP %s  len=%d", r.status_code,
                     len(r.content))
            if r.ok:
                self.ready.emit(r.text)
            else:
                self.error.emit(f"HTTP {r.status_code}: {r.text[:120]}")
        except Exception:
            log.exception("CsvFetcher.run")
            self.error.emit("Request failed — see log for details.")


class AnalyticsFetcher(QThread):
    """Fetch Analytics data: team spend (POST) + model cost aggregation (CSV stream).

    Emits ready(dict) with keys:
      "team_spend"  : list[dict]  — members sorted by spendCents desc
      "model_usage" : dict        — {model_name: {"count": int, "cost_cents": int}}
    """
    ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, team_id: str, start_ms: int, end_ms: int,
                 is_enterprise: bool):
        super().__init__()
        self._team_id       = team_id
        self._start_ms      = start_ms
        self._end_ms        = end_ms
        self._is_enterprise = is_enterprise

    def run(self):
        try:
            cookie, _ = read_cursor_token()
            if not cookie:
                self.error.emit("No auth token found.")
                return
            hdrs = api_headers(cookie)

            # ── 1. Team Spend ───────────────────────────────────────
            team_spend: list[dict] = []
            if self._team_id:
                try:
                    team_id_int = int(self._team_id)
                except ValueError:
                    log.warning("AnalyticsFetcher: invalid teamId %r, skipping team-spend",
                                self._team_id)
                    team_id_int = None
                if team_id_int is not None:
                    post_hdrs = dict(hdrs)
                    post_hdrs["content-type"] = "application/json"
                    post_hdrs["origin"]       = "https://cursor.com"
                    post_hdrs["referer"]      = "https://cursor.com/dashboard"
                    body = {
                        "teamId":        team_id_int,
                        "pageSize":      5000,
                        "sortBy":        "name",
                        "sortDirection": "asc",
                        "page":          1,
                    }
                    r = requests.post(
                        f"{BASE_URL}/api/dashboard/get-team-spend",
                        json=body, headers=post_hdrs, timeout=30,
                    )
                    log.info("AnalyticsFetcher team-spend → HTTP %s", r.status_code)
                    if r.ok:
                        members = r.json().get("teamMemberSpend", [])
                        team_spend = sorted(
                            members,
                            key=lambda m: m.get("spendCents", 0),
                            reverse=True,
                        )
                    else:
                        log.warning("team-spend HTTP %s: %s", r.status_code,
                                    r.text[:120])

            # ── 2. Model cost aggregation via CSV stream ─────────────
            model_agg: dict[str, dict] = {}
            csv_params = {
                "isEnterprise": str(self._is_enterprise).lower(),
                "startDate":    self._start_ms,
                "endDate":      self._end_ms,
                "strategy":     "tokens",
            }
            if self._team_id:
                csv_params["teamId"] = self._team_id
            csv_hdrs = dict(hdrs)
            csv_hdrs["Accept"] = "text/csv,*/*"
            first_line = True
            with requests.get(
                f"{BASE_URL}/api/dashboard/export-usage-events-csv",
                params=csv_params, headers=csv_hdrs,
                stream=True, timeout=30, allow_redirects=True,
            ) as r:
                if r.ok:
                    for raw_line in r.iter_lines():
                        if not raw_line:
                            continue
                        line = raw_line.decode("utf-8", errors="replace")
                        if first_line:          # skip CSV header row
                            first_line = False
                            continue
                        try:
                            cols = next(_csv.reader([line]))
                        except Exception:
                            continue
                        if len(cols) < 12:
                            continue
                        model    = cols[3].strip()
                        cost_str = cols[-1].strip().lstrip("$")
                        try:
                            cost_cents = int(round(float(cost_str or "0") * 100))
                        except ValueError:
                            cost_cents = 0
                        if not model:
                            continue
                        entry = model_agg.setdefault(
                            model, {"count": 0, "cost_cents": 0})
                        entry["count"]      += 1
                        entry["cost_cents"] += cost_cents
                else:
                    log.warning("AnalyticsFetcher CSV → HTTP %s", r.status_code)

            log.info("AnalyticsFetcher done — %d members, %d models",
                     len(team_spend), len(model_agg))
            self.ready.emit({
                "team_spend":  team_spend,
                "model_usage": model_agg,
            })
        except Exception:
            log.exception("AnalyticsFetcher.run")
            self.error.emit("Request failed — see log for details.")


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
def usd(cents: int) -> str:
    return f"${cents / 100:.2f}"


_MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_date(iso: str, lang: str) -> str:
    try:
        d = _date.fromisoformat(iso[:10])
    except Exception:
        return iso
    if lang == "ko":
        return f"{d.year}년 {d.month}월 {d.day}일"
    return f"{d.day} {_MONTHS_EN[d.month - 1]} {d.year}"


def days_left_text(end_iso: str, lang: str) -> str:
    try:
        end   = _date.fromisoformat(end_iso[:10])
        today = _date.today()
        delta = (end - today).days + 1
    except Exception:
        return end_iso
    if lang == "ko":
        if delta > 1:  return f"{delta}일 남음"
        if delta == 1: return "내일 갱신"
        if delta == 0: return "오늘 갱신"
        return f"D+{abs(delta)}"
    else:
        if delta > 1:  return f"{delta} days left"
        if delta == 1: return "Renews tomorrow"
        if delta == 0: return "Renews today"
        return f"D+{abs(delta)}"


def pct_color(pct: float) -> QColor:
    if pct >= 90: return c("c_red")
    if pct >= 75: return c("c_amber")
    return c("accent")


def remain_color(remain_pct: float) -> QColor:
    if remain_pct <= 25: return c("c_red")
    if remain_pct <= 50: return c("c_amber")
    return c("c_green")


def ql(text: str = "", size: int = 10, color: QColor = None, bold: bool = False,
        align=Qt.AlignLeft, family: str = _UI_FONT) -> QLabel:
    w = QLabel(text)
    f = QFont(family, size)
    f.setBold(bold)
    w.setFont(f)
    w.setAlignment(align)
    col = color or c("t_body")
    w.setStyleSheet(
        f"color:rgba({col.red()},{col.green()},{col.blue()},{col.alpha()});"
        "background:transparent;"
    )
    return w


def set_lbl_color(lbl: QLabel, color: QColor):
    lbl.setStyleSheet(
        f"color:rgba({color.red()},{color.green()},{color.blue()},255);"
        "background:transparent;"
    )


def get_screen_for_pos(pos) -> QScreen:
    for s in QApplication.screens():
        if s.geometry().contains(pos):
            return s
    best, best_dist = QApplication.primaryScreen(), float("inf")
    for s in QApplication.screens():
        ct = s.geometry().center()
        d = (ct.x() - pos.x()) ** 2 + (ct.y() - pos.y()) ** 2
        if d < best_dist:
            best, best_dist = s, d
    return best


# ══════════════════════════════════════════════════════════════
#  HATCH HELPER  — cached QPixmap for 45° diagonal hatch
# ══════════════════════════════════════════════════════════════
_hatch_cache: dict[tuple, QPixmap] = {}


def _get_hatch_pixmap(w: int, h: int, step: int = 5) -> QPixmap:
    """Return a cached QPixmap with 45° hatch lines."""
    key = (w, h, step, hatch_alpha())
    pm = _hatch_cache.get(key)
    if pm is not None:
        return pm
    pm = QPixmap(max(1, w), max(1, h))
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setPen(QPen(QColor(128, 128, 128, hatch_alpha()), 1.0))
    ih = int(h)
    for i in range(-ih, int(w) + ih, step):
        p.drawLine(i, 0, i + ih, ih)
    p.end()
    _hatch_cache[key] = pm
    return pm


def _draw_hatch(p: QPainter, w: float, h: float, step: int = 5):
    """Draw cached hatch pattern within the current clip region."""
    pm = _get_hatch_pixmap(int(w), int(h), step)
    p.drawPixmap(0, 0, pm)


# ══════════════════════════════════════════════════════════════
#  PRIMITIVE WIDGETS
# ══════════════════════════════════════════════════════════════
class ArcGauge(QWidget):
    """Concentric double-semicircle arc gauge with rounded ends."""
    _OUTER_SW = 9
    _INNER_SW = 6
    _GAP      = 5
    _GLOW_PAD = 22   # increased: prevents glow clipping at arc top

    def __init__(self, size: int = 160):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        pad = self._GLOW_PAD
        self.setFixedSize(size + pad * 2, size // 2 + pad + 10)
        self._outer_r = size // 2 - 8
        self._inner_r = (self._outer_r - self._OUTER_SW // 2
                         - self._GAP - self._INNER_SW // 2)
        self._outer_pct   = 0.0
        self._outer_color = c("accent")
        self._inner_pct   = None
        self._inner_color = c("c_amber")
        self._label_text  = ""
        self._label_color = c("accent")

    def set_value(self, pct: float, color: QColor = None):
        self._outer_pct   = max(0.0, min(100.0, pct))
        self._outer_color = color or c("accent")
        self.update()

    def set_bonus(self, pct: float | None, color: QColor = None):
        if pct is None:
            self._inner_pct = None
        else:
            self._inner_pct   = max(0.0, min(100.0, pct))
            self._inner_color = color or c("c_amber")
        self.update()

    def resize_arcs(self, outer_r: int):
        self._outer_r = outer_r
        self._inner_r = (outer_r - self._OUTER_SW // 2
                         - self._GAP - self._INNER_SW // 2)
        self.update()

    def set_label(self, text: str, color: QColor = None):
        self._label_text  = text
        self._label_color = color or c("accent")
        self.update()

    def _draw_track(self, p: QPainter, cx, cy, r, sw):
        """Draw the empty track as a 180° arc with RoundCap — both ends are rounded."""
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(track_bg(), sw, Qt.SolidLine, Qt.RoundCap))
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        p.drawArc(rect, 180 * 16, -180 * 16)
        # Hatch overlay: clip to a donut region, then draw hatch
        outer_r = r + sw / 2
        inner_r = max(1.0, r - sw / 2)
        clip = QPainterPath()
        clip.moveTo(cx - outer_r, cy)
        clip.arcTo(QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2), 180, -180)
        clip.lineTo(cx + inner_r, cy)
        clip.arcTo(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2), 0, 180)
        clip.closeSubpath()
        p.setClipPath(clip)
        _draw_hatch(p, self.width(), self.height(), step=5)
        p.setClipping(False)

    def _draw_arc(self, p: QPainter, cx, cy, r, sw, pct, color):
        """Draw filled arc with RoundCap (rounded at both ends) + tip glow."""
        if pct <= 0:
            # At 0%: show a small dot at the start (left end)
            tx = cx - r
            ty = float(cy)
            dot_r = sw / 2
            glow = QRadialGradient(tx, ty, dot_r * 2.5)
            glow.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 160))
            glow.setColorAt(1, Qt.transparent)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(QPointF(tx, ty), dot_r * 2.5, dot_r * 2.5)
            p.setBrush(QBrush(color))
            p.drawEllipse(QPointF(tx, ty), dot_r, dot_r)
            return
        span = int(pct / 100 * 180)
        g = QLinearGradient(cx - r, 0, cx + r, 0)
        g.setColorAt(0, color.darker(150))
        g.setColorAt(1, color)
        p.setPen(QPen(QBrush(g), sw, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        p.drawArc(rect, 180 * 16, -span * 16)
        # Tip glow at the arc end
        ang = (180 - pct / 100 * 180) * math.pi / 180
        tx = cx + r * math.cos(ang)
        ty = cy - r * math.sin(ang)
        glow = QRadialGradient(tx, ty, 14)
        glow.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 130))
        glow.setColorAt(1, Qt.transparent)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(tx, ty), 14, 14)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad = self._GLOW_PAD
        cx = w // 2
        cy = h - pad - 6
        self._draw_track(p, cx, cy, self._outer_r, self._OUTER_SW)
        self._draw_arc(p, cx, cy, self._outer_r, self._OUTER_SW,
                       self._outer_pct, self._outer_color)
        if self._inner_pct is not None:
            self._draw_track(p, cx, cy, self._inner_r, self._INNER_SW)
            self._draw_arc(p, cx, cy, self._inner_r, self._INNER_SW,
                           self._inner_pct, self._inner_color)
        if self._label_text:
            inner_r = self._inner_r if self._inner_pct is not None else self._outer_r
            font_px = max(10, min(22, int(inner_r * 0.52)))
            font = QFont(_UI_FONT, font_px, QFont.Bold)
            p.setFont(font)
            p.setPen(self._label_color)
            fm = p.fontMetrics()
            text_w = fm.horizontalAdvance(self._label_text)
            p.drawText(cx - text_w // 2, cy, self._label_text)
        p.end()


class SegBar(QWidget):
    def __init__(self, h: int = 7):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(h)
        self._segs: list[tuple[float, QColor]] = []

    def set_segments(self, segs):
        self._segs = segs
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), r, r)
        p.setClipPath(clip)
        p.setBrush(QBrush(track_bg()))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)
        _draw_hatch(p, w, h, step=5)
        p.setClipping(False)
        p.setPen(Qt.NoPen)
        x = 0.0
        for frac, color in self._segs:
            fw = max(0.0, min(1.0, frac)) * w
            if fw < 1:
                x += fw
                continue
            sc = QPainterPath()
            sc.addRoundedRect(QRectF(x, 0, fw, h), r, r)
            p.setClipPath(sc)
            g = QLinearGradient(x, 0, x + fw, 0)
            g.setColorAt(0, color.darker(130))
            g.setColorAt(1, color)
            p.setBrush(QBrush(g))
            p.drawRoundedRect(QRectF(x, 0, fw, h), r, r)
            p.setClipping(False)
            x += fw
        p.end()


class MiniBar(QWidget):
    def __init__(self, h: int = 4):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(h)
        self._frac  = 0.0
        self._color = c("accent")

    def set_value(self, frac: float, color: QColor = None):
        self._frac  = max(0.0, min(1.0, frac))
        self._color = color or c("accent")
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), r, r)
        p.setClipPath(clip)
        p.setBrush(QBrush(track_bg()))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)
        _draw_hatch(p, w, h, step=4)
        p.setClipping(False)
        # At frac=0, show only hatch track (no filled bar)
        if self._frac <= 0:
            p.end()
            return
        fw = max(r * 2, w * self._frac)
        fc = QPainterPath()
        fc.addRoundedRect(QRectF(0, 0, fw, h), r, r)
        p.setClipPath(fc)
        g = QLinearGradient(0, 0, fw, 0)
        g.setColorAt(0, self._color.darker(140))
        g.setColorAt(1, self._color)
        p.setBrush(QBrush(g))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0, 0, fw, h), r, r)
        p.setClipping(False)
        p.end()


class Card(QWidget):
    def __init__(self, accent_key: str = "accent"):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._accent_key = accent_key

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setBrush(QBrush(c("bg_card")))
        p.setPen(QPen(c("border_lo"), 1))
        p.drawRoundedRect(r, 10, 10)
        ac = c(self._accent_key)
        pen = QPen(ac, 1.5)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(r.left() + 14, r.top() + 0.75),
                   QPointF(r.left() + 56, r.top() + 0.75))
        p.end()


class Divider(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet("background:rgba(128,128,128,0.15);border:none;")


# ══════════════════════════════════════════════════════════════
#  TOGGLE SWITCH  — entire row clickable
# ══════════════════════════════════════════════════════════════
class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)
    W, H = 34, 18

    def __init__(self, checked: bool = False):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.W, self.H)
        self.setCursor(Qt.PointingHandCursor)
        self._checked  = checked
        self._disabled = False

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, val: bool):
        self._checked = val
        self.update()

    def set_disabled(self, val: bool):
        self._disabled = val
        self.setCursor(Qt.ForbiddenCursor if val else Qt.PointingHandCursor)
        self.update()

    def toggle(self):
        """Programmatic toggle (called from row click)."""
        if self._disabled:
            return
        self._checked = not self._checked
        self.update()
        self.toggled.emit(self._checked)

    def mousePressEvent(self, _):
        self.toggle()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.W, self.H
        r = h / 2
        if self._disabled:
            p.setOpacity(0.30)
        track_color = c("accent") if self._checked else QColor(128, 128, 128, 60)
        p.setBrush(QBrush(track_color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)
        knob_r = h / 2 - 2
        knob_x = (w - h + 2 + knob_r) if self._checked else (2 + knob_r)
        knob_y = h / 2
        p.setBrush(QBrush(QColor(255, 255, 255, 230)))
        p.drawEllipse(QPointF(knob_x, knob_y), knob_r, knob_r)
        p.end()


# ══════════════════════════════════════════════════════════════
#  KV-ROW FACTORY
# ══════════════════════════════════════════════════════════════
KVRow = tuple


def kv_row(parent_layout, label: str) -> KVRow:
    row = QWidget()
    row.setAttribute(Qt.WA_TranslucentBackground)
    rl = QHBoxLayout(row)
    rl.setContentsMargins(0, 1, 0, 1)
    rl.setSpacing(4)
    lw = ql(label, 9, c("t_muted"))
    lw.setWordWrap(False)
    lw.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    vw = QLabel("—")
    vw.setFont(QFont(_UI_FONT, 9, QFont.Bold))
    vw.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    vw.setWordWrap(False)
    vw.setTextInteractionFlags(Qt.NoTextInteraction)
    vw.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    vw.setMinimumWidth(0)
    col = c("t_bright")
    vw.setStyleSheet(
        f"color:rgba({col.red()},{col.green()},{col.blue()},255);background:transparent;"
    )
    rl.addWidget(lw, 0)
    rl.addWidget(vw, 1)
    parent_layout.addWidget(row)
    return lw, vw


def set_kv(row: KVRow, value: str, color: QColor = None):
    _, vw = row
    vw.setText(value)
    set_lbl_color(vw, color or c("t_bright"))


def update_kv_label(row: KVRow, label: str):
    lw, _ = row
    lw.setText(label)
    set_lbl_color(lw, c("t_muted"))


def section_hdr(text: str, accent_key: str = "t_muted") -> QLabel:
    w = ql(text.upper(), 8, c(accent_key), bold=True)
    w.setWordWrap(False)
    w.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    w.setStyleSheet(w.styleSheet() + "letter-spacing:1.5px;")
    return w


# ══════════════════════════════════════════════════════════════
#  DEBUG DIALOG
# ══════════════════════════════════════════════════════════════
class DebugDialog(QDialog):
    def __init__(self, settings: dict, raw_json: dict | None = None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(S(settings, "debug_title"))
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.resize(600, 500)
        self.setStyleSheet(
            f"background:{c('bg_win').name()};color:{c('t_body').name()};"
        )
        vl = QVBoxLayout(self)
        vl.setContentsMargins(12, 12, 12, 10)
        vl.setSpacing(8)

        for line in [
            f"CursorHUD {VERSION}  ·  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Python {sys.version.split()[0]}  ·  "
            f"{'EXE (frozen)' if getattr(sys, 'frozen', False) else 'Script'}",
            f"Log → {LOG_FILE}",
            f"Settings → {SETTINGS_FILE}",
            f"Cursor DB → {_cursor_db_path()}",
        ]:
            lb = QLabel(line)
            lb.setFont(QFont(_MONO_FONT, 8))
            lb.setStyleSheet(f"color:{c('t_muted').name()};background:transparent;")
            vl.addWidget(lb)

        vl.addWidget(Divider())

        tabs = QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane{{ border:none; }}"
            f" QTabBar::tab{{ background:rgba(128,128,128,0.08); color:{c('t_muted').name()};"
            f" border:1px solid rgba(128,128,128,0.2); border-radius:4px 4px 0 0;"
            f" padding:3px 14px; font-size:9px; margin-right:2px; }}"
            f" QTabBar::tab:selected{{ background:{c('accent').name()}; color:#fff;"
            f" border-color:{c('accent').name()}; }}"
        )

        def _make_text(content: str) -> QTextEdit:
            t = QTextEdit()
            t.setReadOnly(True)
            t.setFont(QFont(_MONO_FONT, 8))
            t.setStyleSheet(
                f"background:{c('bg_card').name()};color:{c('t_body').name()};"
                "border:none;border-radius:6px;padding:6px;"
            )
            t.setPlainText(content)
            t.verticalScrollBar().setValue(t.verticalScrollBar().maximum())
            return t

        self._log_txt = _make_text("\n".join(_mem_log.records) or "(no logs)")
        tabs.addTab(self._log_txt, "Logs")

        # Redact sensitive fields from JSON display
        json_display = raw_json
        if raw_json:
            json_display = dict(raw_json)
            if "profile" in json_display and isinstance(json_display["profile"], dict):
                safe_profile = dict(json_display["profile"])
                for k in ("email", "cursorAuth"):
                    if k in safe_profile:
                        safe_profile[k] = "[REDACTED]"
                json_display["profile"] = safe_profile
            if "email" in json_display:
                json_display["email"] = "[REDACTED]"
        json_str = (json.dumps(json_display, indent=2, ensure_ascii=False)
                    if json_display else "(no data yet)")
        self._json_txt = _make_text(json_str)
        tabs.addTab(self._json_txt, "JSON")

        # Metrics tab
        self._metrics_txt = _make_text(_metrics.dump())
        tabs.addTab(self._metrics_txt, "Metrics")

        self._tabs = tabs
        vl.addWidget(tabs, 1)

        br = QWidget()
        bl = QHBoxLayout(br)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(6)
        bl.addStretch()
        for lkey, slot in [("debug_copy", self._copy), ("debug_close", self.accept)]:
            btn = QPushButton(S(settings, lkey))
            btn.setFixedHeight(26)
            btn.setStyleSheet(_pill_btn_qss())
            btn.clicked.connect(slot)
            bl.addWidget(btn)
        vl.addWidget(br)

    def _copy(self):
        cur = self._tabs.currentWidget()
        QApplication.clipboard().setText(cur.toPlainText() if cur else "")


# ══════════════════════════════════════════════════════════════
#  PAGE: CREDITS
# ══════════════════════════════════════════════════════════════
class CreditsPage(QWidget):
    retry_clicked     = pyqtSignal()
    export_csv_clicked = pyqtSignal()

    def __init__(self, settings: dict):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.settings  = settings
        self._row_refs: dict[str, KVRow] = {}
        self._last_data: dict | None = None
        self._build()

    def T(self, k):
        return S(self.settings, k)

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("background:transparent;")
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        inner = QWidget()
        inner.setAttribute(Qt.WA_TranslucentBackground)
        inner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        inner.setMinimumWidth(0)
        vl = QVBoxLayout(inner)
        vl.setContentsMargins(12, 8, 12, 8)
        vl.setSpacing(8)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # Error bar with retry button
        err_row = QWidget()
        err_row.setAttribute(Qt.WA_TranslucentBackground)
        erl = QHBoxLayout(err_row)
        erl.setContentsMargins(12, 0, 12, 0)
        erl.setSpacing(6)
        self._err_lbl = ql("", 9, c("c_red"))
        self._err_lbl.setWordWrap(True)
        erl.addWidget(self._err_lbl, 1)
        self._retry_btn = QPushButton(self.T("err_retry"))
        self._retry_btn.setFixedHeight(22)
        self._retry_btn.setCursor(Qt.PointingHandCursor)
        self._retry_btn.setStyleSheet(_pill_btn_qss(c("c_red").name()))
        self._retry_btn.clicked.connect(self.retry_clicked)
        erl.addWidget(self._retry_btn)
        self._err_row = err_row
        err_row.hide()
        outer.addWidget(err_row)

        # Hero card
        hero = Card("accent")
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(14, 8, 14, 8)
        hl.setSpacing(8)
        self._arc = ArcGauge(size=150)
        # Size is set by ArcGauge.__init__ based on GLOW_PAD
        arc_col = QWidget()
        arc_col.setAttribute(Qt.WA_TranslucentBackground)
        arc_col.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        acl = QVBoxLayout(arc_col)
        acl.setContentsMargins(0, 0, 0, 0)
        acl.setSpacing(0)
        acl.addWidget(self._arc)
        self._bonus_tag = QLabel("")
        self._bonus_tag.setAlignment(Qt.AlignCenter)
        self._bonus_tag.setMaximumHeight(0)
        self._bonus_tag.setVisible(False)
        acl.addWidget(self._bonus_tag)
        hl.addWidget(arc_col, 0)
        info = QWidget()
        info.setAttribute(Qt.WA_TranslucentBackground)
        il = QVBoxLayout(info)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(2)
        il.setAlignment(Qt.AlignVCenter)
        self._hero_used = ql("$—", 11, c("t_bright"), bold=True)
        self._hero_of   = ql("/ $—", 9, c("t_muted"))
        self._cycle_lbl = ql("", 8, c("t_dim"))
        for _lbl in [self._hero_used, self._hero_of, self._cycle_lbl]:
            _lbl.setWordWrap(False)
            _lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._status_badge = QLabel("")
        self._status_badge.setFixedHeight(20)
        self._status_badge.setWordWrap(False)
        self._status_badge.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        for w in [self._hero_used, self._hero_of, self._cycle_lbl, self._status_badge]:
            il.addWidget(w)
        self._free_notice_lbl = ql("", 8, c("t_muted"))
        self._free_notice_lbl.setWordWrap(True)
        self._free_notice_lbl.hide()
        il.addWidget(self._free_notice_lbl)
        hl.addWidget(info, 1)
        vl.addWidget(hero)

        # Personal Credits card
        self._personal_card = pc = Card("accent")
        pl = QVBoxLayout(pc)
        pl.setContentsMargins(14, 11, 14, 11)
        pl.setSpacing(6)
        self._hdr_personal = section_hdr(self.T("personal_section"), "accent")
        pl.addWidget(self._hdr_personal)
        pl.addWidget(Divider())
        self._row_refs["row_incl"]  = kv_row(pl, self.T("row_incl"))
        self._row_refs["row_bonus"] = kv_row(pl, self.T("row_bonus"))
        self._row_refs["row_extra"] = kv_row(pl, self.T("row_extra"))
        vl.addWidget(pc)

        # Organization Credits card
        self._org_card = Card("c_green")
        ogl = QVBoxLayout(self._org_card)
        ogl.setContentsMargins(14, 6, 14, 8)
        ogl.setSpacing(3)
        self._hdr_org = section_hdr(self.T("org_section"), "c_green")
        ogl.addWidget(self._hdr_org)
        ogl.addWidget(Divider())
        self._row_refs["od_t"] = kv_row(ogl, self.T("org_od"))
        vl.addWidget(self._org_card)

        # Usage rates card
        self._rate_card = Card("accent2")
        rl2 = QVBoxLayout(self._rate_card)
        rl2.setContentsMargins(14, 11, 14, 11)
        rl2.setSpacing(5)
        self._hdr_rates = section_hdr("USAGE RATES", "accent2")
        rl2.addWidget(self._hdr_rates)
        rl2.addWidget(Divider())
        self._auto_w = QWidget()
        self._auto_w.setAttribute(Qt.WA_TranslucentBackground)
        awl = QVBoxLayout(self._auto_w)
        awl.setContentsMargins(0, 0, 0, 0)
        awl.setSpacing(3)
        self._row_refs["auto_pct"] = kv_row(awl, self.T("auto_pct"))
        self._auto_bar = MiniBar(h=4)
        awl.addWidget(self._auto_bar)
        rl2.addWidget(self._auto_w)
        self._api_w = QWidget()
        self._api_w.setAttribute(Qt.WA_TranslucentBackground)
        apl = QVBoxLayout(self._api_w)
        apl.setContentsMargins(0, 0, 0, 0)
        apl.setSpacing(3)
        self._row_refs["api_pct"] = kv_row(apl, self.T("api_pct"))
        self._api_bar = MiniBar(h=4)
        apl.addWidget(self._api_bar)
        rl2.addWidget(self._api_w)
        self._hint_lbl = ql("", 8, c("t_muted"))
        self._hint_lbl.setWordWrap(True)
        self._hint_lbl.setMaximumHeight(0)
        self._hint_lbl.setVisible(False)
        rl2.addWidget(self._hint_lbl)
        vl.addWidget(self._rate_card)

        # CSV export row — small muted action link at the bottom of the scroll area
        export_row = QWidget()
        export_row.setAttribute(Qt.WA_TranslucentBackground)
        exl = QHBoxLayout(export_row)
        exl.setContentsMargins(4, 2, 4, 2)
        exl.setSpacing(0)
        exl.addStretch()
        self._csv_btn = QPushButton(self.T("csv_export"))
        self._csv_btn.setFixedHeight(20)
        self._csv_btn.setCursor(Qt.PointingHandCursor)
        self._csv_btn.setStyleSheet(
            f"QPushButton{{color:{c('t_dim').name()};background:transparent;"
            f"border:none;font-size:8px;font-family:{_UI_FONT};"
            f"text-decoration:underline;padding:0 4px;}}"
            f"QPushButton:hover{{color:{c('t_muted').name()};}}"
        )
        self._csv_btn.clicked.connect(self.export_csv_clicked)
        exl.addWidget(self._csv_btn)
        self._csv_container = QWidget()
        self._csv_container.setAttribute(Qt.WA_TranslucentBackground)
        _ccl = QVBoxLayout(self._csv_container)
        _ccl.setContentsMargins(0, 0, 0, 0)
        _ccl.setSpacing(0)
        _ccl.addWidget(export_row)
        self._csv_container.setVisible(
            self.settings.get("show_experimental", False)
        )
        vl.addWidget(self._csv_container)

    def _rebuild_labels(self):
        update_kv_label(self._row_refs["row_incl"],  self.T("row_incl"))
        update_kv_label(self._row_refs["row_bonus"], self.T("row_bonus"))
        update_kv_label(self._row_refs["row_extra"], self.T("row_extra"))
        update_kv_label(self._row_refs["od_t"],      self.T("org_od"))
        update_kv_label(self._row_refs["auto_pct"],  self.T("auto_pct"))
        update_kv_label(self._row_refs["api_pct"],   self.T("api_pct"))
        self._hdr_personal.setText(self.T("personal_section").upper())
        self._hdr_org.setText(self.T("org_section").upper())
        set_lbl_color(self._hdr_personal, c("accent"))
        set_lbl_color(self._hdr_org,      c("c_green"))
        set_lbl_color(self._hdr_rates,    c("accent2"))
        self._retry_btn.setText(self.T("err_retry"))
        self._csv_btn.setText(self.T("csv_export"))

    def set_experimental_visible(self, visible: bool) -> None:
        """Show/hide CSV export controls (gated by Experimental toggle)."""
        self._csv_container.setVisible(visible)

    @staticmethod
    def _bonus_tag_qss() -> str:
        amber = c("c_amber")
        return (
            f"color:{amber.name()};"
            f"background:rgba({amber.red()},{amber.green()},{amber.blue()},22);"
            f"border:1px solid rgba({amber.red()},{amber.green()},{amber.blue()},70);"
            f"border-radius:5px;font-size:10px;font-family:{_UI_FONT};font-weight:700;"
            "padding:0 8px;"
        )

    def set_error(self, msg: str):
        if msg:
            self._err_lbl.setText(f"⚠  {msg}")
            self._err_row.show()
        else:
            self._err_row.hide()

    def refresh_theme(self):
        set_lbl_color(self._err_lbl, c("c_red"))
        set_lbl_color(self._hint_lbl, c("t_muted"))
        set_lbl_color(self._free_notice_lbl, c("t_muted"))
        self._arc.set_label(self._arc._label_text, c("accent"))
        set_lbl_color(self._hero_used, c("t_bright"))
        set_lbl_color(self._hero_of,   c("t_muted"))
        set_lbl_color(self._cycle_lbl, c("t_dim"))
        set_lbl_color(self._hdr_personal, c("accent"))
        set_lbl_color(self._hdr_org,      c("c_green"))
        set_lbl_color(self._hdr_rates,    c("accent2"))
        for row in self._row_refs.values():
            lw, vw = row
            set_lbl_color(lw, c("t_muted"))
            set_lbl_color(vw, c("t_bright"))
        if self._bonus_tag.isVisible():
            self._bonus_tag.setStyleSheet(self._bonus_tag_qss())
        self._retry_btn.setStyleSheet(_pill_btn_qss(c("c_red").name()))

    def apply_scale(self, scale: float, arc_size: int = None):
        self._hero_used.setFont(QFont(_UI_FONT, max(8, int(11 * scale)), QFont.Bold))
        self._hero_of.setFont(QFont(_UI_FONT, max(7, int(9 * scale))))
        self._cycle_lbl.setFont(QFont(_UI_FONT, max(7, int(8 * scale))))
        kv_px = max(7, int(9 * scale))
        for lw, vw in self._row_refs.values():
            vw.setFont(QFont(_UI_FONT, kv_px, QFont.Bold))
            lw.setFont(QFont(_UI_FONT, kv_px))
        sec_px = max(7, int(8 * scale))
        for hdr in [self._hdr_personal, self._hdr_org, self._hdr_rates]:
            f = hdr.font()
            f.setPointSize(sec_px)
            hdr.setFont(f)
        if arc_size is None:
            arc_size = max(90, int(150 * scale))
        pad = ArcGauge._GLOW_PAD
        self._arc.setFixedSize(arc_size + pad * 2, arc_size // 2 + pad + 10)
        self._arc.resize_arcs(arc_size // 2 - 8)

    def update_data(self, d: dict):
        self._last_data = d
        cr = d["credit"]
        od = d["on_demand"]
        cyc = d["cycle"]
        cfg = self.settings
        self._rebuild_labels()

        if d.get("is_free"):
            self._arc.set_value(0, c("t_muted"))
            self._arc.set_bonus(None)
            self._arc.set_label("FREE", c("accent"))
            self._hero_used.hide()
            self._hero_of.hide()
            _lang = self.settings.get("lang", "en")
            self._cycle_lbl.setText(days_left_text(cyc["end"], _lang))
            mu = c("t_dim").name()
            self._status_badge.setText("● Free")
            self._status_badge.setStyleSheet(
                f"color:{mu};background:transparent;"
                f"font-size:10px;font-family:{_UI_FONT};font-weight:700;"
            )
            self._org_card.hide()
            self._rate_card.hide()
            self._personal_card.setVisible(cfg.get("show_personal", True))
            self._free_notice_lbl.setText(self.T("free_plan_notice"))
            self._free_notice_lbl.show()
            self._hint_lbl.setMaximumHeight(0)
            self._hint_lbl.setVisible(False)
            return

        self._free_notice_lbl.hide()
        self._hero_used.show()
        self._hero_of.show()

        incl_remain_pct = cr["incl_remain_pct"]
        bonus_used = cr["bonus_used"]
        _lang = self.settings.get("lang", "en")

        # ── Arc + Hero: 3-phase credit display ────────────────────────
        # Priority order (highest = most urgent for user):
        #   Phase 3: On-Demand active (real money!) → red, PAYG label
        #   Phase 2: base exhausted + bonus active  → amber, BONUS label
        #   Phase 1: base credits remaining          → normal % display
        base_exhausted = incl_remain_pct <= 0
        bonus_active   = bonus_used > 0
        od_active      = od["personal"] > 0

        if base_exhausted and od_active:
            # Phase 3: On-Demand — real charges, highest priority
            rc = c("c_red")
            self._arc.set_value(0, rc)
            self._arc.set_label("PAYG", rc)
            self._hero_used.setText(usd(od["personal"]))
            set_lbl_color(self._hero_used, rc)
            self._hero_of.setText(self.T("personal_od"))
        elif base_exhausted and bonus_active:
            # Phase 2: Bonus mode — free coverage, amber
            bc = c("c_amber")
            self._arc.set_value(0, bc)
            self._arc.set_label("BONUS", bc)
            self._hero_used.setText(usd(bonus_used))
            set_lbl_color(self._hero_used, bc)
            self._hero_of.setText(self.T("bonus_saved"))
        else:
            # Phase 1: base credits remaining (or exhausted with nothing active)
            hc = remain_color(incl_remain_pct)
            self._arc.set_value(incl_remain_pct, hc)
            self._arc.set_label(f"{incl_remain_pct:.1f}%", hc)
            self._hero_used.setText(usd(cr["budget_remain"]))
            set_lbl_color(self._hero_used, c("t_bright"))
            self._hero_of.setText(
                f"/ {usd(cr['budget_total'])}  {self.T('remain_label')}"
            )

        self._cycle_lbl.setText(days_left_text(cyc["end"], _lang))

        # Bonus tag (always shown when bonus > 0, regardless of phase)
        if bonus_used > 0:
            self._bonus_tag.setText(f"✦  +{usd(bonus_used)}  {self.T('bonus_saved')}")
            self._bonus_tag.setStyleSheet(self._bonus_tag_qss())
            self._bonus_tag.setMaximumHeight(22)
            self._bonus_tag.setVisible(True)
        else:
            self._bonus_tag.setMaximumHeight(0)
            self._bonus_tag.setVisible(False)
        self._arc.set_bonus(None)

        active_incl  = cr["incl_remain"] > 0
        active_bonus = cr["bonus_used"]  > 0
        active_od    = od["personal"]    > 0
        if active_od:
            badge_text  = self.T("status_badge_od")
            badge_color = c("c_red")
        elif active_bonus:
            badge_text  = self.T("status_badge_bonus")
            badge_color = c("c_amber")
        else:
            badge_text  = self.T("status_badge_incl")
            badge_color = c("accent")
        self._status_badge.setText(f"● {badge_text}")
        self._status_badge.setStyleSheet(
            f"color:{badge_color.name()};background:transparent;"
            f"font-size:10px;font-family:{_UI_FONT};font-weight:700;letter-spacing:0.3px;"
        )

        show_personal = cfg.get("show_personal", True)
        self._personal_card.setVisible(show_personal)
        if show_personal:
            set_kv(self._row_refs["row_incl"],
                   usd(cr["incl_used"]),
                   c("accent") if active_incl else c("t_muted"))
            set_kv(self._row_refs["row_bonus"],
                   usd(cr["bonus_used"]) if cr["bonus_used"] > 0 else self.T("not_used"),
                   c("c_amber") if active_bonus else c("t_dim"))
            set_kv(self._row_refs["row_extra"],
                   usd(od["personal"]) if od["personal"] > 0 else self.T("not_used"),
                   c("c_red") if active_od else c("t_dim"))

        show_org = cfg.get("show_org", True)
        self._org_card.setVisible(show_org)
        if show_org:
            set_kv(self._row_refs["od_t"],
                   usd(od["team"]) if od["team"] else "—",
                   c("c_amber") if od["team"] > 0 else c("t_muted"))

        show_rate = cfg.get("show_official", True)
        self._rate_card.setVisible(show_rate)
        if show_rate:
            ap = cr["auto_pct"]
            ac = pct_color(ap)
            nmp = cr["api_pct"]
            nc = pct_color(nmp)
            set_kv(self._row_refs["auto_pct"], f"{ap:.1f}%", ac)
            self._auto_bar.set_value(ap / 100, ac)
            set_kv(self._row_refs["api_pct"], f"{nmp:.1f}%", nc)
            self._api_bar.set_value(nmp / 100, nc)
            hint = d.get("hint", "")
            if hint:
                self._hint_lbl.setText(f"ℹ  {hint}")
                self._hint_lbl.setMaximumHeight(16777215)
                self._hint_lbl.setVisible(True)
            else:
                self._hint_lbl.setMaximumHeight(0)
                self._hint_lbl.setVisible(False)


# ══════════════════════════════════════════════════════════════
#  PAGE: PROFILE
# ══════════════════════════════════════════════════════════════
class ProfilePage(QWidget):
    def __init__(self, settings: dict):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.settings = settings
        self._rows: dict[str, KVRow] = {}
        self._build()

    def T(self, k):
        return S(self.settings, k)

    def _build(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(12, 8, 12, 8)
        vl.setSpacing(8)
        card = Card("c_green")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(6)
        self._hdr_profile = section_hdr(self.T("profile_title"), "c_green")
        cl.addWidget(self._hdr_profile)
        cl.addWidget(Divider())
        for key, lk in [
            ("name", "field_name"), ("email", "field_email"),
            ("verified", "field_verified"), ("since", "field_since"),
            ("days", "field_days"), ("plan", "field_plan"), ("cycle", "field_cycle"),
        ]:
            self._rows[key] = kv_row(cl, self.T(lk))
        vl.addWidget(card)
        vl.addStretch()

    def _rebuild_labels(self):
        self._hdr_profile.setText(self.T("profile_title").upper())
        set_lbl_color(self._hdr_profile, c("c_green"))
        for key, lk in [
            ("name", "field_name"), ("email", "field_email"),
            ("verified", "field_verified"), ("since", "field_since"),
            ("days", "field_days"), ("plan", "field_plan"), ("cycle", "field_cycle"),
        ]:
            update_kv_label(self._rows[key], self.T(lk))

    def refresh_theme(self):
        self._rebuild_labels()

    def update_data(self, d: dict):
        pr = d["profile"]
        cyc = d["cycle"]
        self._rebuild_labels()

        def sv(k, v, col=None):
            set_kv(self._rows[k], v, col)

        sv("name", pr["name"] or "—")
        sv("email", pr["email"] or "—")
        sv("verified",
           self.T("verified_yes") if pr["verified"] else self.T("verified_no"),
           c("c_green") if pr["verified"] else c("c_red"))
        sv("since", pr["created_at"] or "—")
        sv("days",
           f"{pr['days_member']} {self.T('member_days')}" if pr["days_member"] else "—",
           c("t_muted"))
        sv("plan", f"{cyc['membership']} / {cyc['limit_type']}")
        sv("cycle", f"{cyc['start']}  →  {cyc['end']}")


# ══════════════════════════════════════════════════════════════
#  PAGE: SETTINGS
# ══════════════════════════════════════════════════════════════
class SettingsPage(QWidget):
    changed              = pyqtSignal()
    height_adjust_needed = pyqtSignal()
    theme_changed        = pyqtSignal(str)
    pin_changed          = pyqtSignal(bool)

    TOGGLES_PIN  = [("pin_on_top", "pin_top")]
    STARTUP_KEY  = "startup_boot"
    THEMES_ORDER = [
        ("light", "theme_light"), ("dark", "theme_dark"),
        ("midnight", "theme_midnight"), ("matrix", "theme_matrix"),
    ]

    def __init__(self, settings: dict):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.settings = settings
        self._vl = QVBoxLayout(self)
        self._vl.setContentsMargins(12, 8, 12, 8)
        self._vl.setSpacing(8)
        self._build()

    def T(self, k):
        return S(self.settings, k)

    def _build(self):
        card = Card("accent")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(8)
        self._t: dict = {}

        self._t["settings_title"] = section_hdr(self.T("settings_title"))
        cl.addWidget(self._t["settings_title"])
        cl.addWidget(Divider())

        # Language
        self._t["lang_label"] = ql(self.T("lang_label"), 8, c("t_muted"))
        cl.addWidget(self._t["lang_label"])
        lr = QWidget()
        lr.setAttribute(Qt.WA_TranslucentBackground)
        ll = QHBoxLayout(lr)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(6)
        for code, lkey in [("en", "lang_en"), ("ko", "lang_ko")]:
            btn = QPushButton(self.T(lkey))
            btn.setCheckable(True)
            btn.setChecked(self.settings.get("lang", "en") == code)
            btn.setFixedHeight(22)
            btn.setStyleSheet(_pill_btn_qss())
            btn.clicked.connect(lambda _, lc=code: self._set_lang(lc))
            ll.addWidget(btn)
            self._t[f"lang_{code}"] = btn
        ll.addStretch()
        cl.addWidget(lr)
        cl.addWidget(Divider())

        # Theme
        self._t["theme_label"] = ql(self.T("theme_label"), 8, c("t_muted"))
        cl.addWidget(self._t["theme_label"])
        cur_theme = self.settings.get("theme", "light")
        rows = [QWidget(), QWidget()]
        for r in rows:
            r.setAttribute(Qt.WA_TranslucentBackground)
        rls = [QHBoxLayout(r) for r in rows]
        for rl in rls:
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(6)
        for i, (tname, tkey) in enumerate(self.THEMES_ORDER):
            btn = QPushButton(self.T(tkey))
            btn.setCheckable(True)
            btn.setChecked(tname == cur_theme)
            btn.setFixedHeight(28)
            btn.setStyleSheet(_theme_btn_qss(THEMES[tname]))
            btn.clicked.connect(lambda _, tn=tname: self._set_theme(tn))
            rls[0 if i < 2 else 1].addWidget(btn, 1)
            self._t[f"theme_{tname}"] = btn
        for r in rows:
            cl.addWidget(r)
        cl.addWidget(Divider())

        # Visibility toggles
        self._sw_refs: dict = {}
        self._t["show_sections"] = ql(self.T("show_sections"), 8, c("t_muted"))
        cl.addWidget(self._t["show_sections"])
        for key, skey in [
            ("show_personal", "show_personal"),
            ("show_org", "show_org"),
            ("show_official", "show_official"),
        ]:
            row, lbl, sw = self._switch_row(
                self.T(skey), key, self.settings.get(key, True))
            cl.addWidget(row)
            self._t[skey] = lbl
            self._sw_refs[key] = (row, lbl, sw)
        cl.addWidget(Divider())

        # System options
        row, lbl, sw = self._switch_row(
            self.T("pin_top"), "pin_on_top", self.settings.get("pin_on_top", True))
        cl.addWidget(row)
        self._t["pin_top"] = lbl
        self._sw_refs["pin_on_top"] = (row, lbl, sw)

        row, lbl, _ = self._switch_row(
            self.T("startup_boot"), "_startup", self._is_startup_registered())
        cl.addWidget(row)
        self._t["startup_boot"] = lbl
        cl.addWidget(Divider())

        # ── Experimental section ──────────────────────────────────
        self._t["experimental_section"] = ql(
            f"⚗  {self.T('experimental_section')}", 9, c("t_muted"))
        cl.addWidget(self._t["experimental_section"])
        self._t["experimental_hint"] = ql(self.T("experimental_hint"), 8, c("t_dim"))
        cl.addWidget(self._t["experimental_hint"])
        cl.addWidget(Divider())

        row_exp, lbl_exp, sw_exp = self._switch_row(
            self.T("experimental_toggle"), "show_experimental",
            self.settings.get("show_experimental", False),
        )
        cl.addWidget(row_exp)
        self._t["experimental_toggle"] = lbl_exp
        self._sw_refs["show_experimental"] = (row_exp, lbl_exp, sw_exp)

        # Detail widgets shown only when Experimental is ON
        self._experimental_detail = QWidget()
        self._experimental_detail.setAttribute(Qt.WA_TranslucentBackground)
        _edl = QVBoxLayout(self._experimental_detail)
        _edl.setContentsMargins(0, 0, 0, 0)
        _edl.setSpacing(4)

        self._t["csv_team_id_label"] = ql(self.T("csv_team_id_label"), 9, c("t_body"))
        _edl.addWidget(self._t["csv_team_id_label"])

        self._team_id_input = QLineEdit()
        self._team_id_input.setFixedHeight(24)
        self._team_id_input.setPlaceholderText(self.T("csv_team_id_placeholder"))
        self._team_id_input.setText(self.settings.get("csv_team_id", ""))
        self._team_id_input.setStyleSheet(
            f"QLineEdit{{background:{c('bg_card').name()};color:{c('t_body').name()};"
            f"border:1px solid rgba(128,128,128,0.30);border-radius:4px;"
            f"padding:0 6px;font-size:9px;font-family:{_UI_FONT};}}"
            f"QLineEdit:focus{{border:1px solid {c('accent').name()};}}"
        )
        self._team_id_input.editingFinished.connect(self._on_team_id_edited)
        _edl.addWidget(self._team_id_input)

        cl.addWidget(self._experimental_detail)
        self._experimental_detail.setVisible(
            self.settings.get("show_experimental", False)
        )
        cl.addWidget(Divider())

        self._t["auto_saved"] = ql(self.T("auto_saved"), 8, c("t_dim"))
        cl.addWidget(self._t["auto_saved"])
        self._vl.addWidget(card)
        self._vl.addStretch()

    def _update_texts(self):
        for key, widget in self._t.items():
            if not widget:
                continue
            if key.startswith("lang_") and key != "lang_label":
                lang_code = key[len("lang_"):]
                widget.setText(self.T(key))
                widget.setChecked(self.settings.get("lang", "en") == lang_code)
            elif key.startswith("theme_"):
                tname = key[6:]
                tkey = next((tk for tn, tk in self.THEMES_ORDER if tn == tname), None)
                if tkey:
                    widget.setText(self.T(tkey))
            else:
                widget.setText(
                    self.T(key).upper() if key == "settings_title" else self.T(key))

    def _switch_row(self, label: str, key: str, enabled: bool,
                    indent: bool = False) -> tuple:
        rw = QWidget()
        rw.setAttribute(Qt.WA_TranslucentBackground)
        rw.setCursor(Qt.PointingHandCursor)  # entire row is clickable
        left_margin = 14 if indent else 0
        rl = QHBoxLayout(rw)
        rl.setContentsMargins(left_margin, 1, 0, 1)
        rl.setSpacing(8)
        font_size = 8 if indent else 9
        color = c("t_muted") if indent else c("t_body")
        lbl = ql(label, font_size, color)
        rl.addWidget(lbl)
        rl.addStretch()
        sw = ToggleSwitch(checked=enabled)
        sw.toggled.connect(lambda val, k=key: self._on_switch(k, val))
        rl.addWidget(sw)

        # Make the entire row clickable (toggle the switch)
        def _row_click(event, _sw=sw):
            _sw.toggle()
        rw.mousePressEvent = _row_click

        return rw, lbl, sw

    def _on_team_id_edited(self):
        val = self._team_id_input.text().strip()
        self.settings["csv_team_id"] = val
        save_settings(self.settings)
        log.info("csv_team_id set to: %s", val or "(auto-detect)")

    def _on_switch(self, key: str, value: bool):
        _metrics.inc(f"toggle_{key}")
        if key == "_startup":
            if value:
                exe = str(Path(
                    sys.executable if getattr(sys, "frozen", False) else sys.argv[0]
                ).resolve())
                register_startup(exe)
            else:
                unregister_startup()
        else:
            self.settings[key] = value
            save_settings(self.settings)
            self.changed.emit()
            if key == "pin_on_top":
                self.pin_changed.emit(value)
            elif key == "show_experimental":
                self._experimental_detail.setVisible(value)

    def _sync_pin(self, value: bool):
        self.settings["pin_on_top"] = value
        save_settings(self.settings)
        ref = self._sw_refs.get("pin_on_top")
        if ref:
            _, _, sw = ref
            sw.set_checked(value)

    def _is_startup_registered(self) -> bool:
        if sys.platform == "win32":
            try:
                import winreg
                k = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_READ)
                winreg.QueryValueEx(k, "CursorHUD")
                winreg.CloseKey(k)
                return True
            except Exception:
                return False
        elif sys.platform == "darwin":
            return _macos_launchagent_path().exists()
        else:
            return _linux_autostart_path().exists()

    def refresh_theme(self):
        if hasattr(self, "_team_id_input"):
            self._team_id_input.setStyleSheet(
                f"QLineEdit{{background:{c('bg_card').name()};color:{c('t_body').name()};"
                f"border:1px solid rgba(128,128,128,0.30);border-radius:4px;"
                f"padding:0 6px;font-size:9px;font-family:{_UI_FONT};}}"
                f"QLineEdit:focus{{border:1px solid {c('accent').name()};}}"
            )
        if hasattr(self, "_experimental_detail"):
            self._experimental_detail.setVisible(
                self.settings.get("show_experimental", False)
            )
        lbl = self._t.get("experimental_section")
        if lbl:
            set_lbl_color(lbl, c("t_muted"))
        lbl = self._t.get("experimental_hint")
        if lbl:
            set_lbl_color(lbl, c("t_dim"))
        hdr = self._t.get("settings_title")
        if hdr:
            set_lbl_color(hdr, c("t_muted"))
        for key in ("lang_label", "theme_label", "show_sections"):
            lbl = self._t.get(key)
            if lbl:
                set_lbl_color(lbl, c("t_muted"))
        for code in ("ko", "en"):
            btn = self._t.get(f"lang_{code}")
            if btn:
                btn.setStyleSheet(_pill_btn_qss())
        cur_theme = self.settings.get("theme", "light")
        for tname, _ in self.THEMES_ORDER:
            btn = self._t.get(f"theme_{tname}")
            if btn:
                btn.setStyleSheet(_theme_btn_qss(THEMES[tname]))
                btn.setChecked(tname == cur_theme)
        for key, (row, lbl, sw) in self._sw_refs.items():
            set_lbl_color(lbl, c("t_body"))
        lbl = self._t.get("auto_saved")
        if lbl:
            set_lbl_color(lbl, c("t_dim"))

    def _set_lang(self, code: str):
        if self.settings.get("lang") == code:
            return
        _metrics.inc("lang_change")
        self.settings["lang"] = code
        save_settings(self.settings)
        self._update_texts()
        self.changed.emit()
        QTimer.singleShot(60, self.height_adjust_needed.emit)

    def _set_theme(self, name: str):
        if self.settings.get("theme") == name:
            return
        _metrics.inc(f"theme_{name}")
        self.settings["theme"] = name
        save_settings(self.settings)
        apply_theme(name)
        _hatch_cache.clear()  # invalidate hatch pixmap cache on theme change
        for tname, tkey in self.THEMES_ORDER:
            btn = self._t.get(f"theme_{tname}")
            if btn:
                btn.setChecked(tname == name)
                btn.setStyleSheet(_theme_btn_qss(THEMES[tname]))
        self.theme_changed.emit(name)


# ══════════════════════════════════════════════════════════════
#  STATUS BAR
# ══════════════════════════════════════════════════════════════
class StatusBar(QWidget):
    refresh_clicked = pyqtSignal()
    debug_clicked   = pyqtSignal()

    def __init__(self, settings: dict):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(28)
        self.settings = settings
        hl = QHBoxLayout(self)
        hl.setContentsMargins(12, 0, 8, 0)
        hl.setSpacing(5)

        self._dot = QLabel("●")
        self._dot.setStyleSheet(
            f"color:{c('t_muted').name()};font-size:8px;background:transparent;")
        self._dot.setFixedWidth(12)
        hl.addWidget(self._dot)
        self._last_state = "ok"

        self._clock_lbl = QLabel("—")
        self._clock_lbl.setStyleSheet(
            f"color:{c('t_muted').name()};font-size:9px;"
            f"background:transparent;font-family:{_MONO_FONT};")
        hl.addWidget(self._clock_lbl)
        hl.addStretch()

        self._cd_lbl = QLabel("")
        self._cd_lbl.setStyleSheet(
            f"color:{c('t_dim').name()};font-size:8px;"
            f"background:transparent;font-family:{_UI_FONT};")
        hl.addWidget(self._cd_lbl)

        self._dbg_btn = QPushButton(S(settings, "debug_btn"))
        self._dbg_btn.setFixedSize(30, 22)
        self._dbg_btn.setCursor(Qt.PointingHandCursor)
        mu = c("t_dim").name()
        self._dbg_btn.setStyleSheet(
            f"QPushButton{{ color:{mu}; background:transparent;"
            f" border:1px solid rgba(128,128,128,0.18); border-radius:3px; font-size:8px; }}"
            f" QPushButton:hover{{ color:{c('t_muted').name()};"
            f" border-color:rgba(128,128,128,0.40); }}"
        )
        self._dbg_btn.clicked.connect(self.debug_clicked)
        hl.addWidget(self._dbg_btn)

        self._rbtn = QPushButton(S(settings, "refresh_btn"))
        self._rbtn.setFixedSize(26, 22)
        self._rbtn.setCursor(Qt.PointingHandCursor)
        ac = c("accent").name()
        self._rbtn.setStyleSheet(
            f"QPushButton{{ color:{ac}; background:rgba(128,128,128,0.08);"
            f" border:1px solid rgba(128,128,128,0.25); border-radius:4px; font-size:12px; }}"
            f" QPushButton:hover{{ background:rgba(128,128,128,0.18); }}"
        )
        self._rbtn.clicked.connect(self.refresh_clicked)
        hl.addWidget(self._rbtn)

    def set_status(self, state: str):
        self._last_state = state
        col_map = {
            "ok": c("c_green"), "loading": c("c_amber"),
            "error": c("c_red"), "mock": c("accent2"),
        }
        col = col_map.get(state, c("t_muted"))
        is_mock = state == "mock"
        self._dot.setText("T" if is_mock else "●")
        self._dot.setStyleSheet(
            f"color:rgba({col.red()},{col.green()},{col.blue()},255);"
            f"font-size:8px;font-weight:{'700' if is_mock else '400'};"
            "background:transparent;")
        # Refresh button: show spinner text while loading
        if state == "loading":
            self._rbtn.setText("…")
        else:
            self._rbtn.setText(S(self.settings, "refresh_btn"))

    def set_clock(self, ts: str):
        self._clock_lbl.setText(ts)

    def set_countdown(self, secs: int):
        self._cd_lbl.setText(
            f"{S(self.settings, 'next_refresh')} {secs}{S(self.settings, 'seconds')}")

    def refresh_labels(self):
        self._dbg_btn.setText(S(self.settings, "debug_btn"))

    def refresh_theme(self):
        self.set_status(self._last_state)
        self._clock_lbl.setStyleSheet(
            f"color:{c('t_muted').name()};font-size:9px;"
            f"background:transparent;font-family:{_MONO_FONT};")
        self._cd_lbl.setStyleSheet(
            f"color:{c('t_dim').name()};font-size:8px;"
            f"background:transparent;font-family:{_UI_FONT};")
        mu = c("t_dim").name()
        self._dbg_btn.setStyleSheet(
            f"QPushButton{{ color:{mu}; background:transparent;"
            f" border:1px solid rgba(128,128,128,0.18); border-radius:3px; font-size:8px; }}"
            f" QPushButton:hover{{ color:{c('t_muted').name()};"
            f" border-color:rgba(128,128,128,0.40); }}"
        )
        ac = c("accent").name()
        self._rbtn.setStyleSheet(
            f"QPushButton{{ color:{ac}; background:rgba(128,128,128,0.08);"
            f" border:1px solid rgba(128,128,128,0.25); border-radius:4px; font-size:12px; }}"
            f" QPushButton:hover{{ background:rgba(128,128,128,0.18); }}"
        )


# ══════════════════════════════════════════════════════════════
#  PAGE: ANALYTICS
# ══════════════════════════════════════════════════════════════
class AnalyticsPage(QWidget):
    """Analytics tab — Team Spend + Model Usage.

    Layout (matches CreditsPage pattern):
      Header row: title label + Refresh button + billing-cycle label
      section_hdr("TEAM SPEND") + scrollable member rows
      section_hdr("MODEL USAGE") + model rows with progress bars
    """
    refresh_clicked = pyqtSignal()

    def __init__(self, settings: dict):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.settings = settings

        # ── outer scroll area (full page) ──────────────────────
        outer = QScrollArea()
        outer.setWidgetResizable(True)
        outer.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        outer.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        outer.setAttribute(Qt.WA_TranslucentBackground)

        inner = QWidget()
        inner.setAttribute(Qt.WA_TranslucentBackground)
        self._cl = QVBoxLayout(inner)
        self._cl.setContentsMargins(12, 8, 12, 12)
        self._cl.setSpacing(4)

        # ── header row ─────────────────────────────────────────
        hdr_row = QWidget()
        hdr_row.setAttribute(Qt.WA_TranslucentBackground)
        hl = QHBoxLayout(hdr_row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        self._title_lbl = ql(S(settings, "nav_analytics"), 10, c("t_bright"), bold=True)
        self._title_lbl.setStyleSheet(self._title_lbl.styleSheet() +
                                      f"letter-spacing:1px;font-family:{_UI_FONT};")
        hl.addWidget(self._title_lbl, 1)
        self._cycle_lbl = ql("", 8, c("t_dim"))
        hl.addWidget(self._cycle_lbl, 0)
        self._refresh_btn = QPushButton(S(settings, "analytics_refresh"))
        self._refresh_btn.setFixedHeight(20)
        self._refresh_btn.setCursor(Qt.PointingHandCursor)
        self._refresh_btn.clicked.connect(self.refresh_clicked)
        hl.addWidget(self._refresh_btn, 0)
        self._cl.addWidget(hdr_row)

        # ── Team Spend section ──────────────────────────────────
        self._team_card = Card("accent")
        tcl = QVBoxLayout(self._team_card)
        tcl.setContentsMargins(10, 8, 10, 10)
        tcl.setSpacing(4)
        self._hdr_team = section_hdr(S(settings, "analytics_team_spend"), "accent")
        tcl.addWidget(self._hdr_team)
        self._team_status = ql(S(settings, "analytics_loading"), 9, c("t_dim"))
        tcl.addWidget(self._team_status)
        self._team_scroll = QScrollArea()
        self._team_scroll.setWidgetResizable(True)
        self._team_scroll.setMaximumHeight(150)
        self._team_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._team_scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}")
        self._team_scroll.setAttribute(Qt.WA_TranslucentBackground)
        self._team_scroll.hide()
        tcl.addWidget(self._team_scroll)
        self._cl.addWidget(self._team_card)

        # ── Model Usage section ─────────────────────────────────
        self._cl.addSpacing(6)
        self._model_card = Card("accent")
        mcl = QVBoxLayout(self._model_card)
        mcl.setContentsMargins(10, 8, 10, 10)
        mcl.setSpacing(4)
        self._hdr_model = section_hdr(S(settings, "analytics_model_usage"), "accent")
        mcl.addWidget(self._hdr_model)
        self._model_status = ql(S(settings, "analytics_loading"), 9, c("t_dim"))
        mcl.addWidget(self._model_status)
        self._model_container = QWidget()
        self._model_container.setAttribute(Qt.WA_TranslucentBackground)
        self._model_vbox = QVBoxLayout(self._model_container)
        self._model_vbox.setContentsMargins(0, 0, 0, 0)
        self._model_vbox.setSpacing(4)
        self._model_container.hide()
        mcl.addWidget(self._model_container)
        self._cl.addWidget(self._model_card)

        self._cl.addStretch(1)
        outer.setWidget(inner)

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(outer)

        self._apply_btn_style()

    # ── Public API ────────────────────────────────────────────

    def show_waiting(self):
        """Show 'waiting for data' state (DataFetcher not yet ready)."""
        self._team_status.setText(S(self.settings, "analytics_waiting"))
        self._team_scroll.hide()
        self._model_status.setText(S(self.settings, "analytics_waiting"))
        self._model_container.hide()
        self._cycle_lbl.setText("")

    def show_loading(self):
        """Show loading state while AnalyticsFetcher is running."""
        self._team_status.setText(S(self.settings, "analytics_loading"))
        self._team_status.show()
        self._team_scroll.hide()
        self._model_status.setText(S(self.settings, "analytics_loading"))
        self._model_status.show()
        self._model_container.hide()

    def show_error(self, msg: str):
        txt = f"{S(self.settings, 'analytics_error')}: {msg}"
        self._team_status.setText(txt)
        self._team_status.show()
        self._team_scroll.hide()
        self._model_status.setText(txt)
        self._model_status.show()
        self._model_container.hide()

    def show_no_team(self):
        """Show no-team-id message in Team Spend section only."""
        self._team_status.setText(S(self.settings, "analytics_no_team_id"))
        self._team_status.show()
        self._team_scroll.hide()

    def set_cycle_label(self, start: str, end: str):
        """Set billing cycle label. start/end are YYYY-MM-DD strings."""
        self._cycle_start = start
        self._cycle_end   = end
        self._cycle_lbl.setText(
            f"{S(self.settings, 'analytics_cycle_label')}: {start} – {end}")

    def update_data(self, data: dict):
        """Populate both sections from AnalyticsFetcher ready() payload."""
        self._update_team_spend(data.get("team_spend", []))
        self._update_model_usage(data.get("model_usage", {}))

    def _update_team_spend(self, members: list):
        if not members:
            self._team_status.setText(S(self.settings, "analytics_no_data"))
            self._team_status.show()
            self._team_scroll.hide()
            return

        total_cents = sum(m.get("spendCents", 0) for m in members)
        n = len(members)
        badge = (f"{n} {S(self.settings, 'analytics_members')}"
                 f" · {usd(total_cents)}")
        self._hdr_team.setText(
            S(self.settings, "analytics_team_spend").upper()
            + f"  {badge}")

        inner = QWidget()
        inner.setAttribute(Qt.WA_TranslucentBackground)
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(0, 2, 0, 2)
        vbox.setSpacing(0)

        for m in sorted(members, key=lambda x: x.get("spendCents", 0), reverse=True):
            spend = m.get("spendCents", 0)
            row = QWidget()
            row.setAttribute(Qt.WA_TranslucentBackground)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 2, 0, 2)
            rl.setSpacing(4)
            name_lbl = ql(m.get("name", "—"), 9, c("t_body"))
            if spend == 0:
                name_lbl.setStyleSheet(
                    name_lbl.styleSheet() + "color:rgba(180,190,210,128);")
            rl.addWidget(name_lbl, 1)
            cost_lbl = ql(usd(spend), 9,
                          c("t_body") if spend == 0 else c("c_amber"))
            if spend == 0:
                cost_lbl.setStyleSheet(
                    cost_lbl.styleSheet() + "color:rgba(180,190,210,100);")
            cost_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            rl.addWidget(cost_lbl, 0)
            vbox.addWidget(row)

        vbox.addStretch(1)
        self._team_scroll.setWidget(inner)
        self._team_status.hide()
        self._team_scroll.show()

    def _update_model_usage(self, model_agg: dict):
        # Clear previous rows
        while self._model_vbox.count():
            item = self._model_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not model_agg:
            self._model_status.setText(S(self.settings, "analytics_no_data"))
            self._model_status.show()
            self._model_container.hide()
            return

        total_cents = sum(v["cost_cents"] for v in model_agg.values())
        if total_cents == 0:
            self._model_status.setText(S(self.settings, "analytics_no_data"))
            self._model_status.show()
            self._model_container.hide()
            return

        sorted_models = sorted(model_agg.items(),
                               key=lambda x: x[1]["cost_cents"], reverse=True)
        n = len(sorted_models)
        max_cents = sorted_models[0][1]["cost_cents"]

        for rank, (model_name, entry) in enumerate(sorted_models):
            cost_cents = entry["cost_cents"]
            pct = cost_cents / total_cents if total_cents else 0.0
            bar_frac = cost_cents / max_cents if max_cents else 0.0
            # opacity: rank 0 → 1.0, last → 0.4 (linear)
            opacity = 1.0 - (rank / max(n - 1, 1)) * 0.6

            row = QWidget()
            row.setAttribute(Qt.WA_TranslucentBackground)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 1, 0, 1)
            rl.setSpacing(6)

            name_lbl = ql(model_name, 8, c("t_body"))
            alpha = int(opacity * 255)
            col = c("t_body")
            name_lbl.setStyleSheet(
                f"background:transparent;color:rgba({col.red()},"
                f"{col.green()},{col.blue()},{alpha});")
            rl.addWidget(name_lbl, 2)

            bar = MiniBar(h=4)
            bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            bar.set_value(bar_frac, c("accent"))
            rl.addWidget(bar, 3)

            pct_lbl = ql(f"{pct:.0%}", 8, c("t_dim"))
            pct_lbl.setFixedWidth(32)
            pct_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            rl.addWidget(pct_lbl, 0)

            cost_col = c("accent")
            cost_lbl = ql(usd(cost_cents), 8)
            cost_lbl.setStyleSheet(
                f"background:transparent;color:rgba({cost_col.red()},"
                f"{cost_col.green()},{cost_col.blue()},{alpha});")
            cost_lbl.setFixedWidth(48)
            cost_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            rl.addWidget(cost_lbl, 0)

            self._model_vbox.addWidget(row)

        self._model_status.hide()
        self._model_container.show()

    def refresh_theme(self):
        self._apply_btn_style()
        set_lbl_color(self._cycle_lbl, c("t_dim"))
        set_lbl_color(self._team_status, c("t_dim"))
        set_lbl_color(self._model_status, c("t_dim"))
        self._hdr_team.setStyleSheet(
            ql("", 8, c("accent"), bold=True).styleSheet()
            + "letter-spacing:1.5px;")
        self._hdr_model.setStyleSheet(
            ql("", 8, c("accent"), bold=True).styleSheet()
            + "letter-spacing:1.5px;")

    def refresh_labels(self):
        self._refresh_btn.setText(S(self.settings, "analytics_refresh"))
        self._title_lbl.setText(S(self.settings, "nav_analytics"))
        if hasattr(self, "_cycle_start"):
            self._cycle_lbl.setText(
                f"{S(self.settings, 'analytics_cycle_label')}: "
                f"{self._cycle_start} – {self._cycle_end}")

    def _apply_btn_style(self):
        ac = c("accent").name()
        mu = c("t_muted").name()
        self._refresh_btn.setStyleSheet(
            f"QPushButton{{color:{mu};background:rgba(255,255,255,0.05);"
            f"border:1px solid rgba(255,255,255,0.1);border-radius:3px;"
            f"font-family:{_UI_FONT};font-size:8px;padding:2px 6px;}}"
            f"QPushButton:hover{{color:{ac};border-color:{ac};}}"
        )


# ══════════════════════════════════════════════════════════════
#  NAV BAR
# ══════════════════════════════════════════════════════════════
class NavBar(QWidget):
    tab_clicked = pyqtSignal(int)
    TABS = ["nav_credit", "nav_profile", "nav_settings"]

    def __init__(self, settings: dict):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(36)
        self.settings = settings
        self._btns: list[QPushButton] = []
        hl = QHBoxLayout(self)
        hl.setContentsMargins(8, 4, 8, 0)
        hl.setSpacing(2)
        for i, key in enumerate(self.TABS):
            btn = QPushButton(S(settings, key))
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            self._apply_style(btn)
            btn.clicked.connect(lambda _, idx=i: self.tab_clicked.emit(idx))
            self._btns.append(btn)
            hl.addWidget(btn, 1)

        # Analytics tab — experimental, hidden by default
        self._analytics_btn = QPushButton(S(settings, "nav_analytics"))
        self._analytics_btn.setCheckable(True)
        self._analytics_btn.setFixedHeight(28)
        self._analytics_btn.setCursor(Qt.PointingHandCursor)
        self._apply_style(self._analytics_btn)
        self._analytics_btn.clicked.connect(
            lambda: self.tab_clicked.emit(3))
        self._analytics_btn.setVisible(
            settings.get("show_experimental", False))
        self._btns.append(self._analytics_btn)
        hl.addWidget(self._analytics_btn, 1)

    def _apply_style(self, btn):
        ac = c("accent").name()
        mu = c("t_muted").name()
        btn.setStyleSheet(
            f"QPushButton{{ color:{mu}; background:transparent; border:none;"
            f" border-bottom:2px solid transparent; font-family:{_UI_FONT};"
            f" font-size:9px; font-weight:600; letter-spacing:0.5px; padding:0 4px; }}"
            f" QPushButton:checked{{ color:{ac}; border-bottom:2px solid {ac}; }}"
            f" QPushButton:hover{{ color:rgba(170,185,215,180); }}"
            f" QPushButton:checked:hover{{ color:{ac}; }}"
        )

    def set_active(self, idx: int):
        for i, btn in enumerate(self._btns):
            btn.setChecked(i == idx)

    def set_analytics_visible(self, visible: bool):
        self._analytics_btn.setVisible(visible)

    def refresh_labels(self):
        for i, key in enumerate(self.TABS):
            self._btns[i].setText(S(self.settings, key))
        self._analytics_btn.setText(S(self.settings, "nav_analytics"))

    def refresh_theme(self):
        for btn in self._btns:
            self._apply_style(btn)


# ══════════════════════════════════════════════════════════════
#  RESIZE GRIP
# ══════════════════════════════════════════════════════════════
class ResizeGrip(QWidget):
    SIZE = 16

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.SizeFDiagCursor)
        self._dragging = False
        self._start_x  = None
        self._start_w  = None

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        col = QColor(180, 180, 180, 90)
        p.setPen(QPen(col, 1.2))
        s = self.SIZE
        for i in range(3):
            o = 4 + i * 4
            p.drawLine(s - o, s - 1, s - 1, s - o)
        p.end()

    def reposition(self):
        win = self.window()
        self.move(win.width() - self.SIZE, win.height() - self.SIZE)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = True
            self._start_x = e.globalPos().x()
            self._start_w = self.window().width()

    def mouseMoveEvent(self, e):
        if self._dragging and self._start_x is not None:
            delta_x = e.globalPos().x() - self._start_x
            win = self.window()
            new_w = max(win.minimumWidth(), min(WIN_W_MAX, self._start_w + delta_x))
            win.resize(new_w, win.height())

    def mouseReleaseEvent(self, _):
        self._dragging = False


# ══════════════════════════════════════════════════════════════
#  COMPACT STACK
# ══════════════════════════════════════════════════════════════
class CompactStack(QStackedWidget):
    def sizeHint(self):
        w = self.currentWidget()
        if w:
            s = w.sizeHint()
            return QSize(max(s.width(), self.width()), s.height())
        return super().sizeHint()

    def minimumSizeHint(self):
        w = self.currentWidget()
        if w:
            return QSize(w.minimumSizeHint().width(), w.minimumSizeHint().height())
        return QSize(0, 0)


# ══════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════
class HUDWindow(QMainWindow):
    def minimumSizeHint(self):
        return QSize(ARC_MIN_W, 0)

    def sizeHint(self):
        return QSize(
            getattr(self, "_cur_win_w", WIN_W),
            getattr(self, "_target_h", WIN_H))

    def __init__(self, mock_file: str | None = None):
        super().__init__()
        self.setWindowTitle("Cursor HUD")
        self._mock_file = mock_file
        self.settings   = load_settings()
        apply_theme(self.settings.get("theme", "light"))
        self._pin_on_top = self.settings.get("pin_on_top", True)
        self._mini_mode  = False
        flags = Qt.FramelessWindowHint
        if self._pin_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos       = None
        self._fetcher        = None
        self._last_data      = None
        self._last_raw       = None
        self._current_screen = None
        self._cur_win_w      = WIN_W
        self._target_h       = WIN_H
        self._height_timer   = QTimer(self)
        self._height_timer.setSingleShot(True)
        self._height_timer.timeout.connect(self._do_adjust_height)
        self._countdown      = REFRESH_MS // 1000
        self._tray           = None
        self._apply_size(QApplication.primaryScreen())

        geo = QApplication.primaryScreen().availableGeometry()
        saved_x = self.settings.get("win_x")
        saved_y = self.settings.get("win_y")
        if saved_x is not None and saved_y is not None:
            self.move(saved_x, saved_y)
        else:
            self.move(geo.right() - self._cur_win_w - 20, geo.bottom() - WIN_H - 20)
        self.resize(self._cur_win_w, WIN_H)
        self._clamp_to_screen(QApplication.primaryScreen())
        self._mini_mode = self.settings.get("mini_mode", False)
        self._build_ui()
        self._setup_shortcuts()
        self._setup_tray()
        self._setup_timers()
        if self._mini_mode:
            self._apply_mini()
        self._fetch()

    # ── System tray ───────────────────────────────────────────
    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray = QSystemTrayIcon(self)
        # Create a simple colored icon
        pm = QPixmap(32, 32)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(0, 220, 255)))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(2, 2, 28, 28), 6, 6)
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.setFont(QFont(_UI_FONT, 14, QFont.Bold))
        p.drawText(QRectF(0, 0, 32, 32), Qt.AlignCenter, "C")
        p.end()
        self._tray.setIcon(QIcon(pm))
        self._tray.setToolTip("Cursor HUD")

        menu = QMenu()
        show_act = menu.addAction(S(self.settings, "tray_show"))
        show_act.triggered.connect(self._tray_show)
        refresh_act = menu.addAction(S(self.settings, "tray_refresh"))
        refresh_act.triggered.connect(self._fetch)
        menu.addSeparator()
        quit_act = menu.addAction(S(self.settings, "tray_quit"))
        quit_act.triggered.connect(QApplication.quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _tray_show(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._tray_show()

    # ── Keyboard shortcuts ────────────────────────────────────
    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+R"), self, self._fetch)
        QShortcut(QKeySequence("Ctrl+M"), self, self._toggle_mini)
        QShortcut(QKeySequence("Escape"), self, self._on_escape)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self._switch_tab(0))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self._switch_tab(1))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self._switch_tab(2))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self._switch_tab(3))

    def _on_escape(self):
        if self._mini_mode:
            return
        self._toggle_mini()

    def _apply_size(self, screen: QScreen):
        if screen == self._current_screen:
            return
        self._current_screen = screen
        self._cur_win_w = _preset_win_w(screen)
        self.setMinimumWidth(self._cur_win_w)
        self.setMaximumWidth(WIN_W_MAX)
        self.resize(self._cur_win_w, self.height())
        QTimer.singleShot(80, self._adjust_height)

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

    def _build_ui(self):
        root = QWidget()
        root.setAttribute(Qt.WA_TranslucentBackground)
        root.setMinimumSize(0, 0)
        self.setCentralWidget(root)
        vl = QVBoxLayout(root)
        vl.setContentsMargins(10, 10, 10, 8)
        vl.setSpacing(0)
        vl.setSizeConstraint(QVBoxLayout.SetNoConstraint)

        # Title bar
        tbar = QWidget()
        tbar.setAttribute(Qt.WA_TranslucentBackground)
        tbar.setFixedHeight(32)
        tbar.setCursor(Qt.SizeAllCursor)
        tl = QHBoxLayout(tbar)
        tl.setContentsMargins(10, 0, 6, 0)
        tl.setSpacing(8)
        self._tbar = tbar
        tbar.installEventFilter(self)

        self._logo = QLabel("⬡")
        self._logo.setStyleSheet(
            f"color:{c('accent').name()};font-size:13px;background:transparent;")
        tl.addWidget(self._logo)
        self._title_lbl = QLabel("CursorHUD")
        self._title_lbl.setStyleSheet(
            f"color:{c('t_bright').name()};font-family:{_UI_FONT};font-size:10px;"
            "font-weight:600;letter-spacing:2px;background:transparent;")
        tl.addWidget(self._title_lbl)
        tl.addStretch()

        self._theme_btn = QPushButton("◐")
        self._theme_btn.setFixedSize(22, 22)
        self._theme_btn.setCursor(Qt.PointingHandCursor)
        self._theme_btn.setToolTip("Next theme")
        self._theme_btn.clicked.connect(self._cycle_theme)
        self._theme_btn.setVisible(False)
        self._theme_btn.setStyleSheet(_icon_btn_qss())
        tl.addWidget(self._theme_btn)

        self._mini_btn = QPushButton("⊟")
        self._mini_btn.setFixedSize(22, 22)
        self._mini_btn.setCursor(Qt.PointingHandCursor)
        self._mini_btn.setToolTip("Mini mode  (Ctrl+M)")
        self._mini_btn.setStyleSheet(_icon_btn_qss())
        self._mini_btn.clicked.connect(self._toggle_mini)
        tl.addWidget(self._mini_btn)

        self._pin_btn = QPushButton("⏚")
        self._pin_btn.setFixedSize(22, 22)
        self._pin_btn.setCursor(Qt.PointingHandCursor)
        self._pin_btn.setToolTip("Always on top")
        self._pin_btn.setStyleSheet(_icon_btn_qss())
        self._pin_btn.clicked.connect(self._toggle_pin)
        tl.addWidget(self._pin_btn)

        self._win_btns: list[tuple[QPushButton, str | None]] = []
        for sym, slot, hc in [("─", self.showMinimized, None), ("✕", self.close, "#FF4660")]:
            btn = QPushButton(sym)
            btn.setFixedSize(22, 22)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(slot)
            btn.setStyleSheet(_icon_btn_qss(hv=hc))
            tl.addWidget(btn)
            self._win_btns.append((btn, hc))
        vl.addWidget(tbar)

        self._nav = NavBar(self.settings)
        self._nav.tab_clicked.connect(self._switch_tab)
        vl.addWidget(self._nav)
        vl.addWidget(Divider())

        self._stack = CompactStack()
        self._stack.setAttribute(Qt.WA_TranslucentBackground)
        self._pg_credits  = CreditsPage(self.settings)
        self._pg_credits.retry_clicked.connect(self._fetch)
        self._pg_credits.export_csv_clicked.connect(self._on_export_csv)
        self._csv_fetcher: CsvFetcher | None = None
        self._analytics_fetcher: AnalyticsFetcher | None = None
        self._analytics_data: dict | None = None  # None until first successful fetch
        self._analytics_pending: bool = False  # True when tab shown before _on_data fires
        self._pg_profile  = ProfilePage(self.settings)
        self._pg_settings = SettingsPage(self.settings)
        self._pg_settings.changed.connect(self._on_settings_changed)
        self._pg_settings.height_adjust_needed.connect(self._adjust_height)
        self._pg_settings.theme_changed.connect(self._on_theme_changed)
        self._pg_settings.pin_changed.connect(self._on_pin_changed)
        self._pg_analytics = AnalyticsPage(self.settings)
        self._pg_analytics.refresh_clicked.connect(self._on_analytics_refresh)
        for pg in [self._pg_credits, self._pg_profile,
                   self._pg_settings, self._pg_analytics]:
            self._stack.addWidget(pg)
        vl.addWidget(self._stack)
        vl.addWidget(Divider())

        self._status = StatusBar(self.settings)
        self._status.refresh_clicked.connect(self._fetch)
        self._status.debug_clicked.connect(self._show_debug)

        # Mini mode widget — multi-bar credit breakdown
        # Each row: [MiniBar] [label $amount]
        # Bars use base plan limit as one full unit; overflow adds extra bars
        self._mini_w = QWidget()
        self._mini_w.setAttribute(Qt.WA_TranslucentBackground)
        self._mini_layout = QVBoxLayout(self._mini_w)
        self._mini_layout.setContentsMargins(12, 6, 12, 6)
        self._mini_layout.setSpacing(3)
        # Rows are created dynamically in _update_mini
        self._mini_groups: list[tuple] = []  # (label_lbl, amount_lbl) per credit type group
        self._mini_w.hide()
        vl.addWidget(self._mini_w)
        vl.addWidget(self._status)

        self._grip = ResizeGrip(self)
        self._grip.reposition()
        self._switch_tab(0)
        self._refresh_title_btns()

    def _switch_tab(self, idx: int):
        if idx == 3 and not self.settings.get("show_experimental", False):
            return
        _metrics.inc(f"tab_{idx}")
        self._stack.setCurrentIndex(idx)
        self._nav.set_active(idx)
        self._adjust_height(delay_ms=0)
        if idx == 3:
            self._trigger_analytics_fetch(force=False)

    def _trigger_analytics_fetch(self, force: bool = False):
        """Start AnalyticsFetcher. If _last_data not yet available, defer."""
        if self._last_data is None:
            self._pg_analytics.show_waiting()
            self._analytics_pending = True
            return
        self._analytics_pending = False
        d = self._last_data
        team_id  = (self.settings.get("csv_team_id", "").strip()
                    or d.get("team_id", ""))
        cyc      = d["cycle"]
        start_ms = _date_to_ms(cyc["start"])
        end_ms   = _date_to_ms(cyc["end"])
        is_ent   = d.get("is_enterprise", False)
        self._pg_analytics.set_cycle_label(cyc["start"], cyc["end"])

        if not team_id:
            self._pg_analytics.show_no_team()
            # Still fetch model usage (no teamId needed for personal CSV)
        if not force and self._analytics_data is not None:
            # Already have successfully-fetched data — don't re-fetch unless forced
            return
        if self._analytics_fetcher:
            self._analytics_fetcher.blockSignals(True)
            self._analytics_fetcher.quit()
            self._analytics_fetcher.wait(2000)
            self._analytics_fetcher.deleteLater()
            self._analytics_fetcher = None
        self._pg_analytics.show_loading()
        self._analytics_fetcher = AnalyticsFetcher(
            team_id, start_ms, end_ms, is_ent)
        self._analytics_fetcher.ready.connect(self._on_analytics_data)
        self._analytics_fetcher.error.connect(self._on_analytics_error)
        self._analytics_fetcher.start()
        log.debug("AnalyticsFetcher started")

    def _on_analytics_refresh(self):
        """Force re-fetch triggered by Refresh button."""
        if self._last_data is None:
            return
        self._trigger_analytics_fetch(force=True)

    def _on_analytics_data(self, data: dict):
        self._analytics_data = data
        self._pg_analytics.update_data(data)
        self._adjust_height(delay_ms=60)
        log.info("AnalyticsFetcher data received — %d members, %d models",
                 len(data.get("team_spend", [])),
                 len(data.get("model_usage", {})))

    def _on_analytics_error(self, msg: str):
        self._pg_analytics.show_error(msg)
        log.error("AnalyticsFetcher error: %s", msg)

    def _on_settings_changed(self):
        self._pg_analytics.refresh_labels()
        self._nav.refresh_labels()
        self._status.refresh_labels()
        self._pg_credits._rebuild_labels()
        self._pg_profile._rebuild_labels()
        cfg = self.settings
        self._pg_credits._personal_card.setVisible(cfg.get("show_personal", True))
        self._pg_credits._org_card.setVisible(cfg.get("show_org", True))
        self._pg_credits._rate_card.setVisible(cfg.get("show_official", True))
        show_exp = cfg.get("show_experimental", False)
        self._pg_credits.set_experimental_visible(show_exp)
        self._nav.set_analytics_visible(show_exp)
        if not show_exp:
            self._analytics_pending = False
            self._analytics_data = None
            if self._analytics_fetcher:
                self._analytics_fetcher.blockSignals(True)
                self._analytics_fetcher.quit()
                self._analytics_fetcher.wait(2000)
                self._analytics_fetcher.deleteLater()
                self._analytics_fetcher = None
            if self._stack.currentIndex() == 3:
                self._switch_tab(0)
        if self._last_data:
            self._pg_credits.update_data(self._last_data)
            self._pg_profile.update_data(self._last_data)
        self._adjust_height(delay_ms=60)

    def _on_theme_changed(self, name: str):
        QApplication.instance().setStyleSheet(self._make_qss())
        self._logo.setStyleSheet(
            f"color:{c('accent').name()};font-size:13px;background:transparent;")
        self._title_lbl.setStyleSheet(
            f"color:{c('t_bright').name()};font-family:{_UI_FONT};font-size:10px;"
            "font-weight:600;letter-spacing:2px;background:transparent;")
        for btn, hc in self._win_btns:
            btn.setStyleSheet(_icon_btn_qss(hv=hc))
        self._nav.refresh_theme()
        self._status.refresh_theme()
        self._refresh_title_btns()
        self._pg_credits.refresh_theme()
        self._pg_profile.refresh_theme()
        self._pg_settings.refresh_theme()
        self._pg_analytics.refresh_theme()
        self.update()
        self.repaint()
        if self._last_data:
            self._pg_credits.update_data(self._last_data)
            self._pg_profile.update_data(self._last_data)
            self._update_mini(self._last_data)

    def _make_qss(self) -> str:
        sb = TH()["scrollbar"]
        return (
            "QScrollBar:vertical{background:transparent;width:4px;margin:0;}"
            f"QScrollBar::handle:vertical{{background:{sb};"
            "border-radius:2px;min-height:20px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
            "QToolTip{background:#080A12;color:#E6F0FF;"
            "border:1px solid rgba(128,128,128,0.35);border-radius:4px;padding:4px;}"
        )

    def _refresh_title_btns(self):
        mu = c("t_muted").name()
        br = c("t_bright").name()
        for btn in [self._theme_btn, self._mini_btn, self._pin_btn]:
            btn.setStyleSheet(_icon_btn_qss())
        if self._pin_on_top:
            self._pin_btn.setStyleSheet(_icon_btn_qss(fg=br, hv=br))

    def _apply_pin(self, value: bool):
        self._pin_on_top = value
        self.settings["pin_on_top"] = value
        save_settings(self.settings)
        flags = Qt.FramelessWindowHint
        if value:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        self._refresh_title_btns()

    def _toggle_pin(self):
        self._apply_pin(not self._pin_on_top)
        self._pg_settings._sync_pin(self._pin_on_top)

    def _on_pin_changed(self, value: bool):
        self._apply_pin(value)
        self._pg_settings._sync_pin(value)

    def _toggle_mini(self):
        _metrics.inc("mini_toggle")
        self._mini_mode = not self._mini_mode
        self._apply_mini()

    def _cycle_theme(self):
        themes = [tn for tn, _ in self._pg_settings.THEMES_ORDER]
        cur = self.settings.get("theme", "light")
        nxt = themes[(themes.index(cur) + 1) % len(themes)] if cur in themes else themes[0]
        self._pg_settings._set_theme(nxt)

    def _apply_mini(self):
        is_mini = self._mini_mode
        self._mini_btn.setText("⊞" if is_mini else "⊟")
        self._nav.setVisible(not is_mini)
        self._stack.setVisible(not is_mini)
        self._theme_btn.setVisible(is_mini)
        self._title_lbl.setVisible(not is_mini)
        self._status.setVisible(True)
        self._status._dbg_btn.setVisible(not is_mini)
        self._mini_w.setVisible(is_mini)
        self.setMinimumWidth(self._cur_win_w)
        self.setMaximumWidth(WIN_W_MAX)
        self.setMaximumHeight(16777215)
        self.setMinimumHeight(0)
        self._height_timer.stop()
        self._height_timer.start(50)

    def _setup_timers(self):
        if not self._mock_file:
            t1 = QTimer(self)
            t1.timeout.connect(self._fetch)
            t1.start(REFRESH_MS)
        t2 = QTimer(self)
        t2.timeout.connect(self._tick)
        t2.start(1000)
        self._status.set_clock(datetime.now().strftime("%H:%M:%S"))
        self._status.set_countdown(self._countdown)

    def _tick(self):
        self._countdown = max(0, self._countdown - 1)
        self._status.set_countdown(self._countdown)
        self._status.set_clock(datetime.now().strftime("%H:%M:%S"))

    def _on_export_csv(self):
        """Handle Export CSV button: fetch CSV using current billing cycle dates."""
        d = self._pg_credits._last_data
        if not d:
            QMessageBox.warning(self, "CursorHUD",
                                S(self.settings, "csv_err_fetch"))
            return
        # Settings override takes priority over auto-detected value.
        # teamId is optional: omitting it returns personal usage data only;
        # providing a team ID returns all team members' usage.
        team_id = self.settings.get("csv_team_id", "").strip() or d.get("team_id", "")
        if team_id:
            log.info("CSV export — teamId=%s (source=%s)", team_id,
                     "settings" if self.settings.get("csv_team_id", "").strip() else "auto")
        else:
            log.info("CSV export — personal data (no teamId)")

        cyc = d["cycle"]
        start_ms = _date_to_ms(cyc["start"])
        end_ms   = _date_to_ms(cyc["end"])
        is_ent   = d.get("is_enterprise", False)

        # Propose a default file name based on billing cycle
        default_name = f"cursor_usage_{cyc['start']}_{cyc['end']}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, S(self.settings, "csv_save_title"),
            str(Path.home() / "Downloads" / default_name),
            "CSV files (*.csv);;All files (*)",
        )
        if not path:
            return  # user cancelled

        self._pg_credits._csv_btn.setEnabled(False)
        self._pg_credits._csv_btn.setText("…")

        if self._csv_fetcher:
            self._csv_fetcher.blockSignals(True)
            self._csv_fetcher.quit()
            self._csv_fetcher.wait(2000)
            self._csv_fetcher.deleteLater()

        self._csv_fetcher = CsvFetcher(team_id, start_ms, end_ms, is_ent)
        self._csv_fetcher.ready.connect(lambda text, p=path: self._on_csv_ready(text, p))
        self._csv_fetcher.error.connect(self._on_csv_error)
        self._csv_fetcher.start()
        log.info("CsvFetcher started — teamId=%s start=%d end=%d",
                 team_id or "(personal)", start_ms, end_ms)

    def _on_csv_ready(self, text: str, path: str):
        self._pg_credits._csv_btn.setEnabled(True)
        self._pg_credits._csv_btn.setText(S(self.settings, "csv_export"))
        try:
            Path(path).write_text(text, encoding="utf-8")
            log.info("CSV saved → %s (%d bytes)", path, len(text))
            self._pg_credits._csv_btn.setText(S(self.settings, "csv_saved"))
            QTimer.singleShot(3000, lambda: self._pg_credits._csv_btn.setText(
                S(self.settings, "csv_export")))
        except Exception as exc:
            log.error("CSV write failed: %s", exc)
            QMessageBox.critical(self, "CursorHUD",
                                 f"{S(self.settings, 'csv_err_fetch')}: {exc}")

    def _on_csv_error(self, msg: str):
        self._pg_credits._csv_btn.setEnabled(True)
        self._pg_credits._csv_btn.setText(S(self.settings, "csv_export"))
        log.error("CsvFetcher error: %s", msg)
        QMessageBox.warning(self, "CursorHUD",
                            f"{S(self.settings, 'csv_err_fetch')}: {msg}")

    def _fetch(self):
        _metrics.inc("fetch")
        if self._mock_file:
            try:
                raw = json.loads(Path(self._mock_file).read_text(encoding="utf-8"))
                raw.setdefault("fetched_at", datetime.now(timezone.utc).isoformat())
                self._on_data(raw)
            except Exception as exc:
                self._on_error(f"mock load failed: {exc}")
            return
        # Block signals on old fetcher to prevent stale data arrival
        if self._fetcher:
            self._fetcher.blockSignals(True)
            self._fetcher.quit()
            self._fetcher.wait(2000)
            self._fetcher.deleteLater()
            self._fetcher = None
        self._countdown = REFRESH_MS // 1000
        self._status.set_countdown(self._countdown)
        self._status.set_status("loading")
        self._fetcher = DataFetcher()
        self._fetcher.ready.connect(self._on_data)
        self._fetcher.error.connect(self._on_error)
        self._fetcher.start()
        log.debug("DataFetcher started")

    def _on_data(self, raw: dict):
        self._last_raw  = raw
        self._last_data = parse_data(raw)
        d = self._last_data
        self._pg_profile.update_data(d)
        if not raw.get("summary_ok", True):
            self._pg_credits.set_error(S(self.settings, "err_api"))
            self._status.set_status("error")
        else:
            self._pg_credits.update_data(d)
            self._pg_credits.set_error("")
            self._status.set_status("mock" if self._mock_file else "ok")
        if raw.get("summary_ok", True):
            cr = d["credit"]
            od = d["on_demand"]
            msg = (f"{'[MOCK] ' if self._mock_file else ''}data updated — "
                   f"({cr['budget_pct']:.1f}%) | {usd(cr['budget_used'])} | "
                   f"{usd(cr['bonus_used'])} | {usd(od['personal'])} |")
            log.info("%s", msg)
        else:
            log.warning("data updated (profile only — usage-summary unavailable)")
        self._adjust_height(delay_ms=60)
        self._update_mini(d)
        # If Analytics tab was opened before first data arrived, fetch now
        if self._analytics_pending:
            self._trigger_analytics_fetch(force=False)

        # Update tray tooltip with credit remaining
        if self._tray:
            cr = d["credit"]
            self._tray.setToolTip(
                f"Cursor HUD — {usd(cr['budget_remain'])} / {usd(cr['budget_total'])}")

    def _update_mini(self, d: dict):
        """Rebuild mini-mode credit groups — 2 rows per credit type.

        Row 1 (header+chips):  [type name (stretch)] [chips right-aligned (CHIPS_AREA_W)] [$amount (MINI_AMOUNT_W)]
        Row 2 (bar):           [MiniBar full width]

        MiniBar extends to the window right edge, same as the amount label.
        Chips are right-aligned inside CHIPS_AREA_W (addStretch before them).

        Chips are right-aligned inside CHIPS_AREA_W (addStretch before them).
        full_units formula: (amount-1)//base_limit so amount==base_limit shows
        bar at 100% with no chips (still within the first unit).
        """
        # ── clear previous widgets ─────────────────────────────────────────
        while self._mini_layout.count():
            item = self._mini_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._mini_groups = []  # reset for _apply_scale

        cr         = d["credit"]
        od         = d["on_demand"]
        base_limit = max(1, cr["budget_total"])

        rows_spec: list[tuple[str, int, QColor]] = [
            ("row_incl", cr["incl_used"],  c("accent")),
        ]
        if cr["bonus_used"] > 0:
            rows_spec.append(("row_bonus", cr["bonus_used"], c("c_amber")))
        if od["personal"] > 0:
            rows_spec.append(("row_extra", od["personal"],   c("c_red")))

        for label_key, amount, color in rows_spec:
            label_text   = S(self.settings, label_key)
            full_units   = (amount - 1) // base_limit if amount > 0 else 0
            partial_frac = (amount - full_units * base_limit) / base_limit
            filled       = min(full_units, CHIPS_MAX)

            group = QWidget()
            group.setAttribute(Qt.WA_TranslucentBackground)
            gvbox = QVBoxLayout(group)
            gvbox.setContentsMargins(0, 0, 0, 2)
            gvbox.setSpacing(1)

            # ── row 1: [label (stretch)] [chips right-aligned] [spacer] ──
            hdr_row = QWidget()
            hdr_row.setAttribute(Qt.WA_TranslucentBackground)
            hl1 = QHBoxLayout(hdr_row)
            hl1.setContentsMargins(0, 0, 0, 0)
            hl1.setSpacing(4)

            lbl = QLabel(label_text)
            lbl.setFont(QFont(_UI_FONT, 8))
            set_lbl_color(lbl, color)
            hl1.addWidget(lbl, 1)

            chips_w = QWidget()
            chips_w.setAttribute(Qt.WA_TranslucentBackground)
            chips_w.setFixedWidth(CHIPS_AREA_W)
            cl = QHBoxLayout(chips_w)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(CHIP_GAP)
            cl.addStretch(1)  # push chips to the right
            for _ in range(filled):
                chip = MiniBar(h=CHIP_H)
                chip.setFixedWidth(CHIP_W)
                chip.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                chip.set_value(1.0, color)
                cl.addWidget(chip)
            hl1.addWidget(chips_w, 0)

            al = QLabel(usd(amount))
            al.setFont(QFont(_UI_FONT, 9, QFont.Bold))
            al.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            al.setFixedWidth(MINI_AMOUNT_W)
            al.setStyleSheet("background:transparent;")
            set_lbl_color(al, color)
            hl1.addWidget(al, 0)

            gvbox.addWidget(hdr_row)

            # ── row 2: [MiniBar full width] ───────────────────────────────
            bar_row = QWidget()
            bar_row.setAttribute(Qt.WA_TranslucentBackground)
            hl2 = QHBoxLayout(bar_row)
            hl2.setContentsMargins(0, 0, 0, 0)
            hl2.setSpacing(0)

            bar = MiniBar(h=CHIP_H)
            bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            bar.set_value(partial_frac, color)
            hl2.addWidget(bar, 1)

            gvbox.addWidget(bar_row)
            self._mini_layout.addWidget(group)
            self._mini_groups.append((lbl, al))

    def _on_error(self, err: str):
        _metrics.inc("fetch_error")
        log.error("fetch error: %s", err)
        self._pg_credits.set_error(S(self.settings, "err_fetch"))
        self._status.set_status("error")

    def _show_debug(self):
        DebugDialog(self.settings, raw_json=self._last_raw, parent=self).exec_()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        ac = c("accent")
        for i in range(12, 0, -3):
            gc = QColor(ac.red(), ac.green(), ac.blue(), i * 3)
            p.setPen(QPen(gc, 1.0))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(i, i, -i, -i), 14, 14)
        grad = QLinearGradient(0, 0, 0, r.height())
        grad.setColorAt(0, c("bg_win"))
        grad.setColorAt(1, c("bg_win2"))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(c("border_hi"), 1))
        p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 14, 14)
        p.end()

    def _adjust_height(self, delay_ms: int = 80):
        if delay_ms == 0:
            QApplication.processEvents()  # settle layout before measurement
            self._do_adjust_height()
        else:
            self._height_timer.stop()
            self._height_timer.start(delay_ms)

    @staticmethod
    def _measure_layout(lyt) -> int:
        if not lyt:
            return 0
        total = 0
        visible = []
        for i in range(lyt.count()):
            item = lyt.itemAt(i)
            if not item:
                continue
            w = item.widget()
            if w and w.isVisible():
                visible.append(w)
        for i, w in enumerate(visible):
            h = w.sizeHint().height()
            sp = lyt.spacing() if i < len(visible) - 1 else 0
            total += h + sp
        m = lyt.contentsMargins()
        total += m.top() + m.bottom()
        return total

    def _do_adjust_height(self):
        CHROME_H      = 32 + 36 + 2 + 28 + 18
        CHROME_H_MINI = 32 + 0  + 0 + 28 + 18

        if self._mini_mode:
            lyt = self._mini_w.layout()
            content_h = self._measure_layout(lyt) if lyt else 50
            target_h = max(CHROME_H_MINI + 10, CHROME_H_MINI + content_h)
        elif self._stack.currentIndex() == 0:
            scroll = self._pg_credits.findChild(QScrollArea)
            if scroll and scroll.widget() and scroll.widget().layout():
                content_h = self._measure_layout(scroll.widget().layout()) + 4
                scroll.setMaximumHeight(content_h)
            else:
                content_h = 300
            target_h = max(CHROME_H + 20, CHROME_H + content_h)
        else:
            page = self._stack.currentWidget()
            lyt = page.layout() if page else None
            content_h = self._measure_layout(lyt) if lyt else 200
            target_h = max(CHROME_H + 20, CHROME_H + content_h)

        self.setMinimumWidth(self._cur_win_w)
        self.setMaximumWidth(WIN_W_MAX)
        self.setMaximumHeight(16777215)
        self.setMinimumHeight(0)
        self._target_h = target_h
        if self.height() != target_h:
            self.resize(self.width(), target_h)
            self._clamp_to_screen(get_screen_for_pos(self.geometry().center()))

    def _apply_scale(self):
        if not hasattr(self, "_title_lbl"):
            return
        scale = max(1.0, self.width() / WIN_W)
        self._logo.setStyleSheet(
            f"color:{c('accent').name()};font-size:13px;background:transparent;")
        self._title_lbl.setStyleSheet(
            f"color:{c('t_bright').name()};font-family:{_UI_FONT};"
            "font-size:10px;font-weight:600;letter-spacing:2px;background:transparent;")
        if hasattr(self, "_pg_credits"):
            arc_size = max(90, min(180, int(150 * scale)))
            self._pg_credits.apply_scale(scale, arc_size=arc_size)
        if hasattr(self, "_mini_groups"):
            mini_px = max(8, int(9 * scale))
            hdr_px  = max(7, int(8 * scale))
            for label_lbl, amount_lbl in self._mini_groups:
                if amount_lbl is not None:
                    f = amount_lbl.font()
                    f.setPointSize(mini_px)
                    amount_lbl.setFont(f)
                if label_lbl is not None:
                    f2 = label_lbl.font()
                    f2.setPointSize(hdr_px)
                    label_lbl.setFont(f2)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_grip"):
            self._grip.reposition()
        prev_w = getattr(self, "_last_resize_w", None)
        cur_w = self.width()
        if prev_w != cur_w:
            self._last_resize_w = cur_w
            self._apply_scale()
            self._adjust_height()
        else:
            self._apply_scale()

    def eventFilter(self, obj, e):
        if obj is self._tbar:
            t = e.type()
            if t == e.MouseButtonPress and e.button() == Qt.LeftButton:
                self._drag_pos = e.globalPos() - self.pos()
                return True
            if t == e.MouseMove and e.buttons() == Qt.LeftButton and self._drag_pos:
                self.move(e.globalPos() - self._drag_pos)
                return True
            if t == e.MouseButtonRelease:
                if self._drag_pos:          # snap only after a real drag, not a bare click
                    self._snap_to_edge()
                self._drag_pos = None
                return True
        return super().eventFilter(obj, e)

    def closeEvent(self, e):
        p = self.pos()
        self.settings["win_x"]     = p.x()
        self.settings["win_y"]     = p.y()
        self.settings["win_w"]     = self.width()
        self.settings["mini_mode"] = self._mini_mode
        save_settings(self.settings)
        if self._tray:
            self._tray.hide()
        super().closeEvent(e)

    def moveEvent(self, event):
        super().moveEvent(event)
        screen = get_screen_for_pos(self.geometry().center())
        if screen != self._current_screen:
            self._apply_size(screen)


# ══════════════════════════════════════════════════════════════
#  PLATFORM HELPERS
# ══════════════════════════════════════════════════════════════
def enable_dpi():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    # macOS and Linux: Qt handles DPI scaling via AA_EnableHighDpiScaling


def _macos_launchagent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / "com.cursor-hud.plist"


def _linux_autostart_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME",
                               str(Path.home() / ".config"))) / "autostart" / "cursor-hud.desktop"


def register_startup(exe: str):
    if sys.platform == "win32":
        try:
            import winreg
            k = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "CursorHUD", 0, winreg.REG_SZ, exe)
            winreg.CloseKey(k)
        except Exception as e:
            log.error("register_startup (win32): %s", e)

    elif sys.platform == "darwin":
        plist = _macos_launchagent_path()
        plist.parent.mkdir(parents=True, exist_ok=True)
        plist.write_text(
            f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cursor-hud</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
""",
            encoding="utf-8",
        )
        log.info("register_startup (darwin): wrote %s", plist)

    else:  # Linux / XDG
        desktop = _linux_autostart_path()
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text(
            f"""[Desktop Entry]
Type=Application
Name=CursorHUD
Exec={exe}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
""",
            encoding="utf-8",
        )
        log.info("register_startup (linux): wrote %s", desktop)


def unregister_startup():
    if sys.platform == "win32":
        try:
            import winreg
            k = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(k, "CursorHUD")
            winreg.CloseKey(k)
        except Exception as e:
            log.error("unregister_startup (win32): %s", e)

    elif sys.platform == "darwin":
        plist = _macos_launchagent_path()
        try:
            plist.unlink()
            log.info("unregister_startup (darwin): removed %s", plist)
        except FileNotFoundError:
            pass
        except Exception as e:
            log.error("unregister_startup (darwin): %s", e)

    else:  # Linux / XDG
        desktop = _linux_autostart_path()
        try:
            desktop.unlink()
            log.info("unregister_startup (linux): removed %s", desktop)
        except FileNotFoundError:
            pass
        except Exception as e:
            log.error("unregister_startup (linux): %s", e)


# ══════════════════════════════════════════════════════════════
#  ENTRY
# ══════════════════════════════════════════════════════════════
def _qt_msg_handler(msg_type, context, msg):
    if "Unable to set geometry" in msg:
        return
    log.warning("Qt: %s", msg)


def main():
    if "--install-startup" in sys.argv:
        exe = str(Path(
            sys.executable if getattr(sys, "frozen", False) else sys.argv[0]
        ).resolve())
        register_startup(exe)
        return
    if "--uninstall-startup" in sys.argv:
        unregister_startup()
        return

    mock_file = None
    if "--mock" in sys.argv:
        idx = sys.argv.index("--mock")
        if idx + 1 < len(sys.argv):
            mock_file = sys.argv[idx + 1]
            if not Path(mock_file).is_file():
                print(f"[CursorHUD] --mock: file not found: {mock_file}",
                      file=sys.stderr)
                sys.exit(1)
            log.info("mock mode: %s", mock_file)
        else:
            print("[CursorHUD] --mock requires a file path argument.",
                  file=sys.stderr)
            sys.exit(1)

    enable_dpi()
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    qInstallMessageHandler(_qt_msg_handler)
    app.setApplicationName("CursorHUD")
    app.setQuitOnLastWindowClosed(True)  # close window = quit app (tray is supplementary)

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "com.cursor-hud.app"
            )
        except Exception:
            pass
    if getattr(sys, "frozen", False):
        if sys.platform == "win32":
            # Load icon from the EXE's embedded resource (set by PyInstaller --icon)
            app.setWindowIcon(QIcon(sys.executable))
    else:
        if sys.platform == "win32":
            _icon_p = _app_dir() / "assets" / "icon.ico"
        else:
            _icon_p = _app_dir() / "assets" / "icon_256.png"
        if _icon_p.exists():
            app.setWindowIcon(QIcon(str(_icon_p)))

    init_settings = load_settings()
    apply_theme(init_settings.get("theme", "light"))
    app.setStyleSheet(
        "QScrollBar:vertical{background:transparent;width:4px;margin:0;}"
        f"QScrollBar::handle:vertical{{background:{TH()['scrollbar']};"
        "border-radius:2px;min-height:20px;}"
        "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        "QToolTip{background:#080A12;color:#E6F0FF;"
        "border:1px solid rgba(128,128,128,0.35);border-radius:4px;padding:4px;}"
    )

    db = _cursor_db_path()
    if not mock_file and not db.exists():
        QMessageBox.critical(
            None, "CursorHUD", S(init_settings, "err_no_db") + str(db))
        sys.exit(1)

    win = HUDWindow(mock_file=mock_file)
    win.show()
    QTimer.singleShot(100, win._adjust_height)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()