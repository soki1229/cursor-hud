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
import datetime as _dt
from datetime import datetime, timezone, date as _date
from pathlib import Path

import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox, QSizePolicy,
    QTextEdit, QDialog, QTabWidget, QSystemTrayIcon, QMenu, QAction,
    QShortcut,
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

_THEME: dict = THEMES["dark"]


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
    _THEME = THEMES.get(name, THEMES["dark"])


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
        f" font-size:9px; padding:1px 12px; font-family:Segoe UI; font-weight:600; }}"
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
        f" font-size:9px; font-family:Segoe UI; font-weight:600; }}"
        f" QPushButton:checked{{ color:{ac_hex}; border:2px solid {ac_hex};"
        f" background:rgba({av[0]},{av[1]},{av[2]},25); }}"
        f" QPushButton:hover{{ border:1px solid rgba(128,128,128,0.50); }}"
        f" QPushButton:checked:hover{{ border:2px solid {ac_hex}; }}"
    )


# ══════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════
BASE_URL  = "https://cursor.com"
WIN_W     = 400
WIN_W_MAX = 500
WIN_H     = 660
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
    },
}

DEFAULT_SETTINGS: dict = {
    "lang": "ko", "theme": "dark",
    "show_personal": True, "show_org": True, "show_official": True,
    "pin_on_top": True,
    "win_x": None, "win_y": None, "win_w": WIN_W, "mini_mode": False,
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
    lang = settings.get("lang", "ko")
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
        "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
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
            if not summary:
                self.error.emit(S(load_settings(), "err_api"))
                return
            raw = {
                "summary":    summary,
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

    return {
        "cycle":      cycle,
        "credit":     credit,
        "on_demand":  on_demand,
        "profile":    profile,
        "hint":       s.get("autoModelSelectedDisplayMessage", "") or "",
        "fetched_at": raw.get("fetched_at", ""),
        "is_free":    is_free,
        "is_team":    is_team,
    }


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
        align=Qt.AlignLeft, family: str = "Segoe UI") -> QLabel:
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
            font = QFont("Segoe UI", font_px, QFont.Bold)
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
    vw.setFont(QFont("Segoe UI", 9, QFont.Bold))
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
            f"CursorHUD v4.1  ·  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Python {sys.version.split()[0]}  ·  "
            f"{'EXE (frozen)' if getattr(sys, 'frozen', False) else 'Script'}",
            f"Log → {LOG_FILE}",
            f"Settings → {SETTINGS_FILE}",
            f"Cursor DB → {_cursor_db_path()}",
        ]:
            lb = QLabel(line)
            lb.setFont(QFont("Consolas", 8))
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
            t.setFont(QFont("Consolas", 8))
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
    retry_clicked = pyqtSignal()

    def __init__(self, settings: dict):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.settings = settings
        self._row_refs: dict[str, KVRow] = {}
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

    @staticmethod
    def _bonus_tag_qss() -> str:
        amber = c("c_amber")
        return (
            f"color:{amber.name()};"
            f"background:rgba({amber.red()},{amber.green()},{amber.blue()},22);"
            f"border:1px solid rgba({amber.red()},{amber.green()},{amber.blue()},70);"
            "border-radius:5px;font-size:10px;font-family:Segoe UI;font-weight:700;"
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
        self._hero_used.setFont(QFont("Segoe UI", max(8, int(11 * scale)), QFont.Bold))
        self._hero_of.setFont(QFont("Segoe UI", max(7, int(9 * scale))))
        self._cycle_lbl.setFont(QFont("Segoe UI", max(7, int(8 * scale))))
        kv_px = max(7, int(9 * scale))
        for lw, vw in self._row_refs.values():
            vw.setFont(QFont("Segoe UI", kv_px, QFont.Bold))
            lw.setFont(QFont("Segoe UI", kv_px))
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
            _lang = self.settings.get("lang", "ko")
            self._cycle_lbl.setText(days_left_text(cyc["end"], _lang))
            mu = c("t_dim").name()
            self._status_badge.setText("● Free")
            self._status_badge.setStyleSheet(
                f"color:{mu};background:transparent;"
                "font-size:10px;font-family:Segoe UI;font-weight:700;"
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
        _lang = self.settings.get("lang", "ko")

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
            "font-size:10px;font-family:Segoe UI;font-weight:700;letter-spacing:0.3px;"
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

    def T(self, k): return S(self.settings, k)

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(12,8,12,8); vl.setSpacing(8)
        card = Card("c_green"); cl = QVBoxLayout(card); cl.setContentsMargins(14,12,14,12); cl.setSpacing(6)
        self._hdr_profile = section_hdr(self.T("profile_title"), "c_green")
        cl.addWidget(self._hdr_profile); cl.addWidget(Divider())
        for key, lk in [("name","field_name"),("email","field_email"),("verified","field_verified"),
                        ("since","field_since"),("days","field_days"),("plan","field_plan"),("cycle","field_cycle")]:
            self._rows[key] = kv_row(cl, self.T(lk))
        vl.addWidget(card); vl.addStretch()

    def _rebuild_labels(self):
        self._hdr_profile.setText(self.T("profile_title").upper())
        set_lbl_color(self._hdr_profile, c("c_green"))
        for key, lk in [("name","field_name"),("email","field_email"),("verified","field_verified"),
                        ("since","field_since"),("days","field_days"),("plan","field_plan"),("cycle","field_cycle")]:
            update_kv_label(self._rows[key], self.T(lk))

    def refresh_theme(self):
        """Re-apply colors on theme change."""
        self._rebuild_labels()

    def update_data(self, d: dict):
        pr = d["profile"]; cyc = d["cycle"]
        self._rebuild_labels()
        def sv(k, v, col=None): set_kv(self._rows[k], v, col)
        sv("name",  pr["name"]  or "—")
        sv("email", pr["email"] or "—")
        sv("verified",
           self.T("verified_yes") if pr["verified"] else self.T("verified_no"),
           c("c_green") if pr["verified"] else c("c_red"))
        sv("since", pr["created_at"] or "—")
        sv("days",
           f"{pr['days_member']} {self.T('member_days')}" if pr["days_member"] else "—",
           c("t_muted"))
        sv("plan",  f"{cyc['membership']} / {cyc['limit_type']}")
        sv("cycle", f"{cyc['start']}  →  {cyc['end']}")


# ══════════════════════════════════════════════════════════════
#  PAGE: SETTINGS
# ══════════════════════════════════════════════════════════════
class SettingsPage(QWidget):
    changed             = pyqtSignal()
    height_adjust_needed = pyqtSignal()
    theme_changed = pyqtSignal(str)
    pin_changed   = pyqtSignal(bool)

    TOGGLES_PIN  = [("pin_on_top","pin_top")]
    STARTUP_KEY  = "startup_boot"
    THEMES_ORDER = [("dark","theme_dark"),("light","theme_light"),
                    ("midnight","theme_midnight"),("matrix","theme_matrix")]

    def __init__(self, settings: dict):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.settings = settings
        self._vl = QVBoxLayout(self); self._vl.setContentsMargins(12,8,12,8); self._vl.setSpacing(8)
        self._build()

    def T(self, k): return S(self.settings, k)

    def _build(self):
        """Build widgets once on first use. Language/theme changes are handled by _update_texts() only."""
        card = Card("accent"); cl = QVBoxLayout(card); cl.setContentsMargins(14,12,14,12); cl.setSpacing(8)

        # dict for widget text references
        self._t: dict = {}   # key → QLabel or QPushButton

        self._t["settings_title"] = section_hdr(self.T("settings_title"))
        cl.addWidget(self._t["settings_title"]); cl.addWidget(Divider())

        # Language
        self._t["lang_label"] = ql(self.T("lang_label"), 8, c("t_muted"))
        cl.addWidget(self._t["lang_label"])
        lr = QWidget(); lr.setAttribute(Qt.WA_TranslucentBackground)
        ll = QHBoxLayout(lr); ll.setContentsMargins(0,0,0,0); ll.setSpacing(6)
        ac = c("accent").name(); mu = c("t_muted").name()
        lang_style = (
            f"QPushButton{{color:{mu};background:transparent;border:1px solid rgba(128,128,128,0.28);border-radius:3px;font-size:9px;padding:1px 12px;font-family:Segoe UI;font-weight:600;}}QPushButton:checked{{color:{ac};border:1px solid {ac};background:rgba(128,128,128,0.10);}}"
        )
        for code, lkey in [("en","lang_en"),("ko","lang_ko")]:
            btn = QPushButton(self.T(lkey))
            btn.setCheckable(True); btn.setChecked(self.settings.get("lang","ko") == code)
            btn.setFixedHeight(22); btn.setStyleSheet(lang_style)
            btn.clicked.connect(lambda _, lc=code: self._set_lang(lc))
            ll.addWidget(btn)
            self._t[f"lang_{code}"] = btn
        ll.addStretch(); cl.addWidget(lr); cl.addWidget(Divider())

        # Theme
        self._t["theme_label"] = ql(self.T("theme_label"), 8, c("t_muted"))
        cl.addWidget(self._t["theme_label"])
        cur_theme = self.settings.get("theme", "dark")
        rows = [QWidget(), QWidget()]
        rls  = [QHBoxLayout(r) for r in rows]
        for rl in rls: rl.setContentsMargins(0,0,0,0); rl.setSpacing(6)
        for i, (tname, tkey) in enumerate(self.THEMES_ORDER):
            btn = self._theme_btn(self.T(tkey), THEMES[tname], tname == cur_theme)
            btn.clicked.connect(lambda _, tn=tname: self._set_theme(tn))
            rls[0 if i < 2 else 1].addWidget(btn, 1)
            self._t[f"theme_{tname}"] = btn
        for r in rows: cl.addWidget(r)
        cl.addWidget(Divider())

        # Visibility toggles
        self._sw_refs: dict = {}   # settings_key → (row_widget, label, ToggleSwitch)
        self._t["show_sections"] = ql(self.T("show_sections"), 8, c("t_muted"))
        cl.addWidget(self._t["show_sections"])
        for key, skey, indent in [
            ("show_personal",      "show_personal",      False),
            ("show_org",           "show_org",           False),
            ("show_official",      "show_official",      False),
        ]:
            row, lbl, sw = self._switch_row(self.T(skey), key, self.settings.get(key, True), indent)
            cl.addWidget(row)
            self._t[skey] = lbl
            self._sw_refs[key] = (row, lbl, sw)
        # apply initial disabled state to sub-options
        # no sub-options (show_org is a standalone toggle)

        cl.addWidget(Divider())

        # System options: Always on Top + Start on Boot
        row, lbl, sw = self._switch_row(self.T("pin_top"), "pin_on_top", self.settings.get("pin_on_top", True))
        cl.addWidget(row)
        self._t["pin_top"] = lbl
        self._sw_refs["pin_on_top"] = (row, lbl, sw)

        if sys.platform == "win32":
            row, lbl, _ = self._switch_row(self.T("startup_boot"), "_startup",
                                        self._is_startup_registered())
            cl.addWidget(row)
            self._t["startup_boot"] = lbl

        cl.addWidget(Divider())

        self._t["auto_saved"] = ql(self.T("auto_saved"), 8, c("t_dim"))
        cl.addWidget(self._t["auto_saved"])
        self._vl.addWidget(card); self._vl.addStretch()

    def _update_texts(self):
        """Update texts in-place on language change without rebuilding widgets."""
        for key, widget in self._t.items():
            if not widget: continue
            if key.startswith("lang_") and key != "lang_label":
                # lang_ko / lang_en buttons: update text + checked state
                lang_code = key[len("lang_"):]   # "ko" or "en"
                widget.setText(self.T(key))
                widget.setChecked(self.settings.get("lang", "ko") == lang_code)
            elif key.startswith("theme_"):
                tname = key[6:]
                tkey = next((tk for tn,tk in self.THEMES_ORDER if tn == tname), None)
                if tkey: widget.setText(self.T(tkey))
            else:
                widget.setText(self.T(key) if key != "settings_title"
                                else self.T(key).upper())

    def _switch_row(self, label: str, key: str, enabled: bool,
                    indent: bool = False) -> tuple:
        """Return (row_widget, label_widget, toggle_switch). indent=True indents sub-options."""
        rw = QWidget(); rw.setAttribute(Qt.WA_TranslucentBackground)
        left_margin = 14 if indent else 0
        rl = QHBoxLayout(rw); rl.setContentsMargins(left_margin, 1, 0, 1); rl.setSpacing(8)
        font_size = 8 if indent else 9
        color = c("t_muted") if indent else c("t_body")
        lbl = ql(label, font_size, color)
        rl.addWidget(lbl)
        rl.addStretch()
        sw = ToggleSwitch(checked=enabled)
        sw.toggled.connect(lambda val, k=key: self._on_switch(k, val))
        rl.addWidget(sw)
        return rw, lbl, sw

    def _apply_sub_disabled(self, parent_key: str, child_key: str):
        """Dim and disable child rows when the parent toggle is off."""
        parent_on = self.settings.get(parent_key, True)
        ref = self._sw_refs.get(child_key)
        if not ref: return
        row, lbl, sw = ref
        sw.set_disabled(not parent_on)
        # dim label via opacity
        alpha = 255 if parent_on else 80
        col = c("t_muted")
        lbl.setStyleSheet(
            f"color:rgba({col.red()},{col.green()},{col.blue()},{alpha});"
            "background:transparent;"
        )

    def _on_switch(self, key: str, value: bool):
        if key == "_startup":
            if value:
                exe = str(Path(sys.executable if getattr(sys,"frozen",False) else sys.argv[0]).resolve())
                register_startup(exe); log.debug("startup registered: %s", exe)
            else:
                unregister_startup(); log.debug("startup unregistered")
        else:
            self.settings[key] = value
            save_settings(self.settings)
            # if parent toggle, immediately update sub-option disabled state
            self.changed.emit()
            if key == "pin_on_top":
                self.pin_changed.emit(value)

    def _sync_pin(self, value: bool):
        """Sync the titlebar pin button state with the settings tab toggle (no rebuild)."""
        self.settings["pin_on_top"] = value
        save_settings(self.settings)
        # find pin_on_top switch widget and update directly
        ref = self._sw_refs.get("pin_on_top")
        if ref:
            _, _, sw = ref
            sw.set_checked(value)

    def _is_startup_registered(self) -> bool:
        if sys.platform != "win32": return False
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            winreg.QueryValueEx(k, "CursorHUD"); winreg.CloseKey(k)
            return True
        except Exception:
            return False

    def _theme_btn(self, text: str, theme: dict, checked: bool) -> QPushButton:
        btn = QPushButton(text); btn.setCheckable(True); btn.setChecked(checked)
        btn.setFixedHeight(28)
        av = theme["accent"]; ac_hex = QColor(*av).name()
        bg_hex = QColor(*theme["bg_card"]).name(); mu = c("t_muted").name()
        btn.setStyleSheet(f"QPushButton{{color:{mu};background:{bg_hex};border:1px solid rgba(128,128,128,0.25);border-radius:5px;font-size:9px;font-family:Segoe UI;font-weight:600;}}QPushButton:checked{{color:{ac_hex};border:2px solid {ac_hex};background:rgba({av[0]},{av[1]},{av[2]},25);}}QPushButton:hover:not(:checked){{border:1px solid rgba(128,128,128,0.50);}}")
        return btn

    def refresh_theme(self):
        """Re-apply baked-in colors inside SettingsPage on theme change."""
        ac = c("accent").name(); mu = c("t_muted").name()
        hdr = self._t.get("settings_title")
        if hdr: set_lbl_color(hdr, c("t_muted"))
        for key in ("lang_label", "theme_label", "show_sections"):
            lbl = self._t.get(key)
            if lbl: set_lbl_color(lbl, c("t_muted"))
        lang_style = (
            f"QPushButton{{color:{mu};background:transparent;border:1px solid rgba(128,128,128,0.28);border-radius:3px;font-size:9px;padding:1px 12px;font-family:Segoe UI;font-weight:600;}}QPushButton:checked{{color:{ac};border:1px solid {ac};background:rgba(128,128,128,0.10);}}"
        )
        for code in ("ko", "en"):
            btn = self._t.get(f"lang_{code}")
            if btn: btn.setStyleSheet(lang_style)
        # theme buttons — each theme keeps its own bg_card color; only unchecked labels use t_muted
        cur_theme = self.settings.get("theme", "dark")
        for tname, _ in self.THEMES_ORDER:
            btn = self._t.get(f"theme_{tname}")
            if not btn: continue
            theme = THEMES[tname]
            av = theme["accent"]; ac_hex = QColor(*av).name()
            bg_hex = QColor(*theme["bg_card"]).name(); tmu = c("t_muted").name()
            btn.setStyleSheet(f"QPushButton{{color:{tmu};background:{bg_hex};border:1px solid rgba(128,128,128,0.25);border-radius:5px;font-size:9px;font-family:Segoe UI;font-weight:600;}}QPushButton:checked{{color:{ac_hex};border:2px solid {ac_hex};background:rgba({av[0]},{av[1]},{av[2]},25);}}QPushButton:hover:not(:checked){{border:1px solid rgba(128,128,128,0.50);}}")
            btn.setChecked(tname == cur_theme)
        # toggle row labels
        for key, (row, lbl, sw) in self._sw_refs.items():
            set_lbl_color(lbl, c("t_body"))
        # auto_saved
        lbl = self._t.get("auto_saved")
        if lbl: set_lbl_color(lbl, c("t_dim"))

    def _set_lang(self, code: str):
        if self.settings.get("lang") == code: return
        self.settings["lang"] = code; save_settings(self.settings)
        self._update_texts()   # replace text only, no widget rebuild
        self.changed.emit()
        QTimer.singleShot(60, self._request_height_adjust)

    def _request_height_adjust(self):
        self.height_adjust_needed.emit()

    def _set_theme(self, name: str):
        if self.settings.get("theme") == name: return
        self.settings["theme"] = name; save_settings(self.settings)
        apply_theme(name)
        # update theme button checked state + style in-place (no widget rebuild)
        for tname, tkey in self.THEMES_ORDER:
            btn = self._t.get(f"theme_{tname}")
            if btn:
                btn.setChecked(tname == name)
                av = THEMES[tname]["accent"]; ac_hex = QColor(*av).name()
                bg_hex = QColor(*THEMES[tname]["bg_card"]).name()
                mu = c("t_muted").name()
                btn.setStyleSheet(f"QPushButton{{color:{mu};background:{bg_hex};border:1px solid rgba(128,128,128,0.25);border-radius:5px;font-size:9px;font-family:Segoe UI;font-weight:600;}}QPushButton:checked{{color:{ac_hex};border:2px solid {ac_hex};background:rgba({av[0]},{av[1]},{av[2]},25);}}QPushButton:hover:not(:checked){{border:1px solid rgba(128,128,128,0.50);}}")
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
        self.setFixedHeight(28); self.settings = settings
        hl = QHBoxLayout(self); hl.setContentsMargins(12,0,8,0); hl.setSpacing(5)

        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color:{c('t_muted').name()};font-size:8px;background:transparent;")
        self._dot.setFixedWidth(12); hl.addWidget(self._dot)
        self._last_state = "ok"

        self._clock_lbl = QLabel("—")
        self._clock_lbl.setStyleSheet(
            f"color:{c('t_muted').name()};font-size:9px;background:transparent;font-family:Consolas;"
        )
        hl.addWidget(self._clock_lbl); hl.addStretch()

        self._cd_lbl = QLabel("")
        self._cd_lbl.setStyleSheet(
            f"color:{c('t_dim').name()};font-size:8px;background:transparent;font-family:Segoe UI;"
        )
        hl.addWidget(self._cd_lbl)

        # debug button (small and subtle)
        self._dbg_btn = QPushButton(S(settings, "debug_btn"))
        self._dbg_btn.setFixedSize(30, 22); self._dbg_btn.setCursor(Qt.PointingHandCursor)
        mu = c("t_dim").name()
        self._dbg_btn.setStyleSheet(f"QPushButton{{color:{mu};background:transparent;border:1px solid rgba(128,128,128,0.18);border-radius:3px;font-size:8px;}}QPushButton:hover{{color:{c('t_muted').name()};border-color:rgba(128,128,128,0.40);}}")
        self._dbg_btn.clicked.connect(self.debug_clicked); hl.addWidget(self._dbg_btn)

        # refresh button
        self._rbtn = QPushButton(S(settings, "refresh_btn"))
        self._rbtn.setFixedSize(26, 22); self._rbtn.setCursor(Qt.PointingHandCursor)
        ac = c("accent").name()
        self._rbtn.setStyleSheet(f"QPushButton{{color:{ac};background:rgba(128,128,128,0.08);border:1px solid rgba(128,128,128,0.25);border-radius:4px;font-size:12px;}}QPushButton:hover{{background:rgba(128,128,128,0.18);}}")
        self._rbtn.clicked.connect(self.refresh_clicked); hl.addWidget(self._rbtn)

    def set_status(self, state: str):
        self._last_state = state
        col_map = {"ok": c("c_green"), "loading": c("c_amber"), "error": c("c_red"), "mock": c("accent2")}
        col = col_map.get(state, c("t_muted"))
        is_mock = state == "mock"
        self._dot.setText("T" if is_mock else "●")
        self._dot.setStyleSheet(
            f"color:rgba({col.red()},{col.green()},{col.blue()},255);"
            f"font-size:8px;font-weight:{'700' if is_mock else '400'};background:transparent;"
        )

    def set_clock(self, ts: str): self._clock_lbl.setText(ts)

    def set_countdown(self, secs: int):
        self._cd_lbl.setText(
            f"{S(self.settings,'next_refresh')} {secs}{S(self.settings,'seconds')}"
        )

    def refresh_labels(self):
        """Refresh label texts on language change."""
        self._dbg_btn.setText(S(self.settings, "debug_btn"))

    def refresh_theme(self):
        self.set_status(self._last_state)
        self._clock_lbl.setStyleSheet(
            f"color:{c('t_muted').name()};font-size:9px;background:transparent;font-family:Consolas;"
        )
        self._cd_lbl.setStyleSheet(
            f"color:{c('t_dim').name()};font-size:8px;background:transparent;font-family:Segoe UI;"
        )
        mu = c("t_dim").name()
        self._dbg_btn.setStyleSheet(f"QPushButton{{color:{mu};background:transparent;border:1px solid rgba(128,128,128,0.18);border-radius:3px;font-size:8px;}}QPushButton:hover{{color:{c('t_muted').name()};border-color:rgba(128,128,128,0.40);}}")
        ac = c("accent").name()
        self._rbtn.setStyleSheet(f"QPushButton{{color:{ac};background:rgba(128,128,128,0.08);border:1px solid rgba(128,128,128,0.25);border-radius:4px;font-size:12px;}}QPushButton:hover{{background:rgba(128,128,128,0.18);}}")


# ══════════════════════════════════════════════════════════════
#  NAV BAR
# ══════════════════════════════════════════════════════════════
class NavBar(QWidget):
    tab_clicked = pyqtSignal(int)
    TABS = ["nav_credit", "nav_profile", "nav_settings"]

    def __init__(self, settings: dict):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(36); self.settings = settings
        self._btns: list[QPushButton] = []
        hl = QHBoxLayout(self); hl.setContentsMargins(8,4,8,0); hl.setSpacing(2)
        for i, key in enumerate(self.TABS):
            btn = QPushButton(S(settings, key))
            btn.setCheckable(True); btn.setFixedHeight(28); btn.setCursor(Qt.PointingHandCursor)
            self._apply_style(btn)
            btn.clicked.connect(lambda _, idx=i: self.tab_clicked.emit(idx))
            self._btns.append(btn); hl.addWidget(btn, 1)

    def _apply_style(self, btn):
        ac = c("accent").name(); mu = c("t_muted").name()
        btn.setStyleSheet(f"QPushButton{{color:{mu};background:transparent;border:none;border-bottom:2px solid transparent;font-family:Segoe UI;font-size:9px;font-weight:600;letter-spacing:0.5px;padding:0 4px;}}QPushButton:checked{{color:{ac};border-bottom:2px solid {ac};}}QPushButton:hover:not(:checked){{color:rgba(170,185,215,180);}}")

    def set_active(self, idx: int):
        for i, btn in enumerate(self._btns): btn.setChecked(i == idx)

    def refresh_labels(self):
        for i, key in enumerate(self.TABS): self._btns[i].setText(S(self.settings, key))

    def refresh_theme(self):
        for btn in self._btns: self._apply_style(btn)


# ══════════════════════════════════════════════════════════════
#  RESIZE GRIP
# ══════════════════════════════════════════════════════════════
class ResizeGrip(QWidget):
    """Bottom-right corner drag handle — width-only resize.
    Shows diagonal cursor (standard resize affordance) but only adjusts width;
    height follows compact layout automatically."""
    SIZE = 16   # square hit area

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.SizeFDiagCursor)
        self._dragging = False
        self._start_x  = None
        self._start_w  = None

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        col = QColor(180, 180, 180, 90)
        p.setPen(QPen(col, 1.2))
        s = self.SIZE
        # Draw 3 diagonal tick marks (bottom-right corner convention)
        for i in range(3):
            o = 4 + i * 4
            p.drawLine(s - o, s - 1, s - 1, s - o)
        p.end()

    def reposition(self):
        """Snap to bottom-right corner of the window."""
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
            win.resize(new_w, win.height())   # height follows compact layout

    def mouseReleaseEvent(self, _):
        self._dragging = False


# ══════════════════════════════════════════════════════════════
#  COMPACT STACK  — reflects only current page height, ignores max of other pages
# ══════════════════════════════════════════════════════════════
class CompactStack(QStackedWidget):
    """Override QStackedWidget: sizeHint/minimumSizeHint report only the current page.
    Hidden pages never inflate the window height."""
    def sizeHint(self):
        w = self.currentWidget()
        if w:
            s = w.sizeHint()
            return QSize(max(s.width(), self.width()), s.height())
        return super().sizeHint()

    def minimumSizeHint(self):
        w = self.currentWidget()
        if w:
            s = w.minimumSizeHint()
            return QSize(s.width(), s.height())
        return QSize(0, 0)


# ══════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════
class HUDWindow(QMainWindow):
    def minimumSizeHint(self): return QSize(ARC_MIN_W, 0)
    def sizeHint(self): return QSize(getattr(self, "_cur_win_w", WIN_W), getattr(self, "_target_h", WIN_H))
    def __init__(self, mock_file: str | None = None):
        super().__init__()
        self.setWindowTitle("Cursor HUD")
        self._mock_file = mock_file
        self.settings        = load_settings()
        apply_theme(self.settings.get("theme", "dark"))
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
        self._current_screen = None
        self._cur_win_w      = WIN_W   # updated by _apply_size based on screen
        # Height recalc debounce timer (prevents duplicate fires during drag)
        self._target_h       = WIN_H
        self._height_timer   = QTimer(self)
        self._height_timer.setSingleShot(True)
        self._height_timer.timeout.connect(self._do_adjust_height)
        self._countdown      = REFRESH_MS // 1000
        self._apply_size(QApplication.primaryScreen())
        # Restore saved position (default: bottom-right corner)
        geo = QApplication.primaryScreen().availableGeometry()
        saved_x = self.settings.get("win_x")
        saved_y = self.settings.get("win_y")
        if saved_x is not None and saved_y is not None:
            x = max(geo.left(), min(saved_x, geo.right()  - 60))
            y = max(geo.top(),  min(saved_y, geo.bottom() - 60))
            self.move(x, y)
        else:
            self.move(geo.right() - self._cur_win_w - 20, geo.bottom() - WIN_H - 20)
        self.resize(self._cur_win_w, WIN_H)
        self._mini_mode = self.settings.get("mini_mode", False)
        self._build_ui()
        self._setup_timers()
        if self._mini_mode:   # restore saved mini mode
            self._apply_mini()
        self._fetch()

    def _apply_size(self, screen: QScreen):
        """Called on screen (monitor) change. Width is preserved; height is recalculated.

        Do not manually correct for devicePixelRatio: with Qt AA_EnableHighDpiScaling
        enabled, Qt already maps logical to physical pixels. Adding a manual correction
        would double-apply scale and make the window too large
        (e.g. request 548px -> actual 959px = 548 * 1.75 DPI).

        Do not call resize() here: it re-triggers moveEvent and can cause _apply_size loop.
        """
        if screen == self._current_screen: return
        self._current_screen = screen
        self._cur_win_w = _preset_win_w(screen)   # width preset for current screen
        self.setMinimumWidth(self._cur_win_w)      # prevent narrowing below preset
        self.setMaximumWidth(WIN_W_MAX)             # allow widening freely
        self.resize(self._cur_win_w, self.height())
        # Recalculate compact height after layout settles
        QTimer.singleShot(80, self._adjust_height)

    def _build_ui(self):
        root = QWidget(); root.setAttribute(Qt.WA_TranslucentBackground)
        root.setMinimumSize(0, 0)  # prevent layout minimum from propagating to window
        self.setCentralWidget(root)
        vl = QVBoxLayout(root); vl.setContentsMargins(10,10,10,8); vl.setSpacing(0)
        vl.setSizeConstraint(QVBoxLayout.SetNoConstraint)  # prevent MINMAXINFO conflict

        # Title bar
        tbar = QWidget(); tbar.setAttribute(Qt.WA_TranslucentBackground); tbar.setFixedHeight(32)
        tbar.setCursor(Qt.SizeAllCursor)        # drag cursor hint
        tl = QHBoxLayout(tbar); tl.setContentsMargins(10,0,6,0); tl.setSpacing(8)
        self._tbar = tbar                        # Keep reference for event filter
        tbar.installEventFilter(self)            # drag handled in HUDWindow.eventFilter

        _mu0 = c("t_muted").name(); _br0 = c("t_bright").name()

        self._logo = QLabel("⬡")
        self._logo.setStyleSheet(f"color:{c('accent').name()};font-size:13px;background:transparent;")
        tl.addWidget(self._logo)
        self._title_lbl = QLabel("CursorHUD")
        self._title_lbl.setStyleSheet(
            f"color:{c('t_bright').name()};font-family:Segoe UI;font-size:10px;"
            "font-weight:600;letter-spacing:2px;background:transparent;"
        )
        tl.addWidget(self._title_lbl); tl.addStretch()
        # Theme cycle button — visible only in mini mode, sits just left of mini toggle
        self._theme_btn = QPushButton("◐"); self._theme_btn.setFixedSize(22, 22)
        self._theme_btn.setCursor(Qt.PointingHandCursor)
        self._theme_btn.setToolTip("Next theme")
        self._theme_btn.clicked.connect(self._cycle_theme)
        self._theme_btn.setVisible(False)
        self._theme_btn.setStyleSheet(f"QPushButton{{color:{_mu0};background:transparent;border:none;font-size:11px;}}QPushButton:hover{{color:{_br0};}}")
        tl.addWidget(self._theme_btn)
        # mini mode button
        self._mini_btn = QPushButton("⊟"); self._mini_btn.setFixedSize(22,22)
        self._mini_btn.setCursor(Qt.PointingHandCursor)
        self._mini_btn.setToolTip("Mini mode")
        self._mini_btn.setStyleSheet(f"QPushButton{{color:{_mu0};background:transparent;border:none;font-size:11px;}}QPushButton:hover{{color:{_br0};}}")
        self._mini_btn.clicked.connect(self._toggle_mini)
        tl.addWidget(self._mini_btn)

        # Pin button
        self._pin_btn = QPushButton("⏚" if self._pin_on_top else "⏚")
        self._pin_btn.setFixedSize(22,22); self._pin_btn.setCursor(Qt.PointingHandCursor)
        self._pin_btn.setToolTip("Always on top")
        self._pin_btn.setStyleSheet(f"QPushButton{{color:{_mu0};background:transparent;border:none;font-size:11px;}}QPushButton:hover{{color:{_br0};}}")
        self._pin_btn.clicked.connect(self._toggle_pin)
        tl.addWidget(self._pin_btn)

        self._win_btns: list[tuple[QPushButton, str | None]] = []
        for sym, slot, hc in [("─", self.showMinimized, None), ("✕", self.close, "#FF4660")]:
            btn = QPushButton(sym); btn.setFixedSize(22,22); btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(slot); mu = c("t_muted").name()
            btn.setStyleSheet(f"QPushButton{{color:{mu};background:transparent;border:none;font-size:11px;}}QPushButton:hover{{color:{hc or c('t_bright').name()};}}")
            tl.addWidget(btn)
            self._win_btns.append((btn, hc))
        vl.addWidget(tbar)

        self._nav = NavBar(self.settings)
        self._nav.tab_clicked.connect(self._switch_tab)
        vl.addWidget(self._nav); vl.addWidget(Divider())

        self._stack = CompactStack(); self._stack.setAttribute(Qt.WA_TranslucentBackground)
        self._pg_credits  = CreditsPage(self.settings)
        self._pg_profile  = ProfilePage(self.settings)
        self._pg_settings = SettingsPage(self.settings)
        self._pg_settings.changed.connect(self._on_settings_changed)
        self._pg_settings.height_adjust_needed.connect(self._adjust_height)
        self._pg_settings.theme_changed.connect(self._on_theme_changed)
        self._pg_settings.pin_changed.connect(self._on_pin_changed)
        for pg in [self._pg_credits, self._pg_profile, self._pg_settings]:
            self._stack.addWidget(pg)
        vl.addWidget(self._stack)

        vl.addWidget(Divider())
        self._status = StatusBar(self.settings)
        self._status.refresh_clicked.connect(self._fetch)
        self._status.debug_clicked.connect(self._show_debug)
        # mini mode widget — 3 columns: [gauge bar] [credit remaining / bonus] [Extra]
        self._mini_w = QWidget(); self._mini_w.setAttribute(Qt.WA_TranslucentBackground)
        ml = QVBoxLayout(self._mini_w); ml.setContentsMargins(12,8,12,8); ml.setSpacing(6)
        # gauge bar (full width)
        self._mini_bar = MiniBar(h=10)
        ml.addWidget(self._mini_bar)
        # text row (3 columns)
        row_w = QWidget(); row_w.setAttribute(Qt.WA_TranslucentBackground)
        rl = QHBoxLayout(row_w); rl.setContentsMargins(0,0,0,0); rl.setSpacing(0)
        # remaining credits: main value — 11px bold (balanced with gauge)
        self._mini_credit_lbl = ql("—", 11, c("t_bright"), bold=True)
        # bonus: italic, amber, same 11px
        self._mini_bonus_lbl  = ql("",  11, c("c_amber"))
        self._mini_bonus_lbl.setFont(QFont("Segoe UI", 10, QFont.Normal, True))  # italic
        # Extra: right-aligned, 11px normal muted (dim if zero)
        self._mini_od_lbl     = ql("",  10, c("t_muted"))
        rl.addWidget(self._mini_credit_lbl)
        rl.addSpacing(5)
        rl.addWidget(self._mini_bonus_lbl)
        rl.addStretch()
        rl.addWidget(self._mini_od_lbl)
        ml.addWidget(row_w)
        self._mini_w.hide()
        vl.addWidget(self._mini_w)
        vl.addWidget(self._status)

        # bottom-right resize handle
        self._grip = ResizeGrip(self)
        self._grip.reposition()
        self._switch_tab(0)
        self._refresh_title_btns()

    def _switch_tab(self, idx: int):
        # compute height first → resize → then switch page (prevents flicker)
        self._stack.setCurrentIndex(idx); self._nav.set_active(idx)
        self._adjust_height(delay_ms=0)

    def _on_settings_changed(self):
        self._nav.refresh_labels()
        self._status.refresh_labels()
        self._pg_credits._rebuild_labels()
        self._pg_profile._rebuild_labels()
        # Apply card visibility immediately from settings (even before data arrives)
        cfg = self.settings
        self._pg_credits._personal_card.setVisible(cfg.get("show_personal", True))
        self._pg_credits._org_card.setVisible(cfg.get("show_org", True))
        self._pg_credits._rate_card.setVisible(cfg.get("show_official", True))
        if self._last_data:
            self._pg_credits.update_data(self._last_data)
            self._pg_profile.update_data(self._last_data)
        self._adjust_height(delay_ms=60)

    def _on_theme_changed(self, name: str):
        QApplication.instance().setStyleSheet(self._make_qss())
        # TitleBar
        self._logo.setStyleSheet(f"color:{c('accent').name()};font-size:13px;background:transparent;")
        self._title_lbl.setStyleSheet(
            f"color:{c('t_bright').name()};font-family:Segoe UI;font-size:10px;"
            "font-weight:600;letter-spacing:2px;background:transparent;"
        )
        for btn, hc in self._win_btns:
            mu = c("t_muted").name()
            btn.setStyleSheet(f"QPushButton{{color:{mu};background:transparent;border:none;font-size:11px;}}QPushButton:hover{{color:{hc or c('t_bright').name()};}}")
        # Nav / StatusBar
        self._nav.refresh_theme(); self._status.refresh_theme()
        self._refresh_title_btns()
        # re-apply static colors for Credits / Profile / Settings
        self._pg_credits.refresh_theme()
        self._pg_profile.refresh_theme()
        self._pg_settings.refresh_theme()
        self.update(); self.repaint()
        # re-render data values with new theme colors
        if self._last_data:
            self._pg_credits.update_data(self._last_data)
            self._pg_profile.update_data(self._last_data)
            self._update_mini(self._last_data)

    def _make_qss(self) -> str:
        sb = TH()["scrollbar"]
        return f"""
            QScrollBar:vertical{{background:transparent;width:4px;margin:0;}}
            QScrollBar::handle:vertical{{background:{sb};border-radius:2px;min-height:20px;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}
            QToolTip{{background:#080A12;color:#E6F0FF;
            border:1px solid rgba(128,128,128,0.35);border-radius:4px;padding:4px;}}
        """

    def _refresh_title_btns(self):
        mu = c("t_muted").name(); br = c("t_bright").name()
        def _btn_qss(fg, hv):
            return (
                f"QPushButton{{color:{fg};background:transparent;border:none;font-size:11px;}}"
                f"QPushButton:hover{{color:{hv};}}"
            )
        for btn in [self._theme_btn, self._mini_btn, self._pin_btn]:
            btn.setStyleSheet(_btn_qss(mu, br))
        if self._pin_on_top:
            self._pin_btn.setStyleSheet(_btn_qss(br, br))

    @staticmethod
    def _set_topmost_win32(hwnd: int, on_top: bool):
        """Toggle always-on-top via Windows API without hide/show flicker."""
        try:
            import ctypes
            HWND_TOPMOST    = -1
            HWND_NOTOPMOST  = -2
            SWP_NOMOVE      = 0x0002
            SWP_NOSIZE      = 0x0001
            SWP_NOACTIVATE  = 0x0010
            flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
            insert_after = HWND_TOPMOST if on_top else HWND_NOTOPMOST
            ctypes.windll.user32.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, flags)
        except Exception as ex:
            log.warning("SetWindowPos failed: %s", ex)

    def _apply_pin(self, value: bool):
        """Toggle always-on-top using Qt flags only (setWindowFlags + show)."""
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
        # keep titlebar buttons and settings tab switch in sync
        self._pg_settings._sync_pin(value)

    def _toggle_mini(self):
        self._mini_mode = not self._mini_mode
        self._apply_mini()

    def _cycle_theme(self):
        """Advance to the next theme in THEMES_ORDER, wrapping around."""
        themes = [tn for tn, _ in self._pg_settings.THEMES_ORDER]
        cur    = self.settings.get("theme", "dark")
        nxt    = themes[(themes.index(cur) + 1) % len(themes)] if cur in themes else themes[0]
        self._pg_settings._set_theme(nxt)

    def _apply_mini(self):
        is_mini = self._mini_mode
        self._mini_btn.setText("⊞" if is_mini else "⊟")
        self._nav.setVisible(not is_mini)
        self._stack.setVisible(not is_mini)
        # Theme cycle button: visible only in mini mode, right-aligned before mini toggle
        self._theme_btn.setVisible(is_mini)
        # Logo stays visible in both modes
        # Title label hidden in mini mode (logo only)
        self._title_lbl.setVisible(not is_mini)
        # StatusBar: always visible — hide only _dbg_btn in mini mode
        self._status.setVisible(True)
        self._status._dbg_btn.setVisible(not is_mini)
        # Mini widget: shows used / total credits
        self._mini_w.setVisible(is_mini)
        self.setMinimumWidth(self._cur_win_w)
        self.setMaximumWidth(WIN_W_MAX)
        self.setMaximumHeight(16777215); self.setMinimumHeight(0)
        self._height_timer.stop()
        self._height_timer.start(50)

    def _setup_timers(self):
        if not self._mock_file:
            t1 = QTimer(self); t1.timeout.connect(self._fetch); t1.start(REFRESH_MS)
        t2 = QTimer(self); t2.timeout.connect(self._tick);  t2.start(1000)
        # Show clock/countdown immediately before first timer tick
        self._status.set_clock(datetime.now().strftime("%H:%M:%S"))
        self._status.set_countdown(self._countdown)

    def _tick(self):
        self._countdown = max(0, self._countdown - 1)
        self._status.set_countdown(self._countdown)
        self._status.set_clock(datetime.now().strftime("%H:%M:%S"))

    def _fetch(self):
        if self._mock_file:
            try:
                raw = json.loads(Path(self._mock_file).read_text(encoding="utf-8"))
                raw.setdefault("fetched_at", datetime.now(timezone.utc).isoformat())
                self._on_data(raw)
            except Exception as exc:
                self._on_error(f"mock load failed: {exc}")
            return
        if self._fetcher and self._fetcher.isRunning(): return
        if self._fetcher:
            try:
                self._fetcher.ready.disconnect(); self._fetcher.error.disconnect()
            except TypeError:
                pass
            self._fetcher.quit()
            self._fetcher.wait(2000)  # wait up to 2 seconds, then leave to GC
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
        self._pg_credits.update_data(d)
        self._pg_profile.update_data(d)
        self._pg_credits.set_error("")
        self._status.set_status("mock" if self._mock_file else "ok")
        log.info("%sdata updated — budget %.1f%%",
                 "[MOCK] " if self._mock_file else "", d["credit"]["budget_pct"])
        self._adjust_height(delay_ms=60)
        self._update_mini(d)

    def _update_mini(self, d: dict):
        """Refresh mini-mode 3-column widgets — called from both _on_data and refresh_theme."""
        cr = d["credit"]; od = d["on_demand"]
        rc = remain_color(cr["incl_remain_pct"])
        frac = (cr["incl_remain"] / cr["incl_total"]) if cr["incl_total"] else 0
        self._mini_bar.set_value(frac, rc)
        # remaining credits
        self._mini_credit_lbl.setText(f'{usd(cr["budget_remain"])} / {usd(cr["budget_total"])}')
        set_lbl_color(self._mini_credit_lbl, rc)
        # bonus (italic amber — only when present)
        if cr["bonus_used"] > 0:
            self._mini_bonus_lbl.setText(f'+{usd(cr["bonus_used"])}')
            set_lbl_color(self._mini_bonus_lbl, c("c_amber"))
            self._mini_bonus_lbl.show()
        else:
            self._mini_bonus_lbl.hide()
        # On-Demand — label text from i18n, dim if zero
        od_total  = od["personal"]
        od_label  = S(self.settings, "personal_od")
        self._mini_od_lbl.setText(f'{od_label} {usd(od_total)}')
        set_lbl_color(self._mini_od_lbl, c("c_amber") if od_total > 0 else c("t_dim"))

    def _on_error(self, err: str):
        log.error("fetch error: %s", err)
        self._pg_credits.set_error(S(self.settings, "err_fetch"))
        self._status.set_status("error")

    def _show_debug(self):
        DebugDialog(self.settings, raw_json=getattr(self, "_last_raw", None), parent=self).exec_()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()); ac = c("accent")
        for i in range(12, 0, -3):
            gc = QColor(ac.red(), ac.green(), ac.blue(), i * 3)
            p.setPen(QPen(gc, 1.0)); p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(i,i,-i,-i), 14, 14)
        grad = QLinearGradient(0, 0, 0, r.height())
        grad.setColorAt(0, c("bg_win")); grad.setColorAt(1, c("bg_win2"))
        p.setBrush(QBrush(grad)); p.setPen(QPen(c("border_hi"), 1))
        p.drawRoundedRect(r.adjusted(1,1,-1,-1), 14, 14)
        p.end()

    def _adjust_height(self, delay_ms: int = 80):
        """Recalculate compact height. delay_ms=0 executes immediately."""
        if delay_ms == 0:
            self._do_adjust_height()
        else:
            self._height_timer.stop()
            self._height_timer.start(delay_ms)

    @staticmethod
    def _measure_layout(lyt) -> int:
        """Sum visible widget heights directly from a VBoxLayout.
        Ignores addStretch/QSpacerItem; does not use sizeHint/totalMinimumSize."""
        if not lyt: return 0
        total = 0
        visible = []
        for i in range(lyt.count()):
            item = lyt.itemAt(i)
            if not item: continue
            w = item.widget()
            if w and w.isVisible():
                visible.append(w)
        rows = []
        for i, w in enumerate(visible):
            h = w.sizeHint().height()
            sp = lyt.spacing() if i < len(visible) - 1 else 0
            rows.append(f"  [{i}] {type(w).__name__} sh={h} sp={sp}")
            total += h + sp
        m = lyt.contentsMargins()
        total += m.top() + m.bottom()
        return total

    def _do_adjust_height(self):
        """Compute actual window height (runs after debounce timer fires).
        Traverses visible widgets in page layout directly across all tabs.
        Avoids QStackedWidget.sizeHint/totalMinimumSize — inflated by stretch items."""
        idx = self._stack.currentIndex()

        # chrome: tbar(32) + nav(36) + divider×2(2) + status(28) + vl margins(top=10,bot=8)
        CHROME_H      = 32 + 36 + 2 + 28 + 18
        CHROME_H_MINI = 32 +  0 + 0 + 28 + 18   # mini: no nav, no dividers

        if self._mini_mode:
            # Measure mini widget height directly
            lyt = self._mini_w.layout()
            content_h = self._measure_layout(lyt) if lyt else 50
            target_h  = max(CHROME_H_MINI + 10, CHROME_H_MINI + content_h)
        elif idx == 0:
            # Credits: traverse inner widget VBoxLayout via QScrollArea
            scroll = self._pg_credits.findChild(QScrollArea)
            if scroll and scroll.widget() and scroll.widget().layout():
                content_h = self._measure_layout(scroll.widget().layout()) + 4
                # Fix scroll area height to content — prevents excess space expansion
                scroll.setMaximumHeight(content_h)
            else:
                content_h = 300
            target_h = max(CHROME_H + 20, CHROME_H + content_h)
        else:
            # Profile / Settings: traverse top-level VBoxLayout directly
            page = self._stack.currentWidget()
            lyt  = page.layout() if page else None
            content_h = self._measure_layout(lyt) if lyt else 200
            target_h  = max(CHROME_H + 20, CHROME_H + content_h)
        self.setMinimumWidth(self._cur_win_w)
        self.setMaximumWidth(WIN_W_MAX)
        self.setMaximumHeight(16777215); self.setMinimumHeight(0)
        self._target_h = target_h
        if self.height() != target_h:
            self.resize(self.width(), target_h)

    def _apply_scale(self):
        """Responsive layout: scale all fonts/arc proportionally to window width.
        Base width = 400px (scale=1.0). Fonts grow linearly above that."""
        if not hasattr(self, "_title_lbl"): return

        scale = max(1.0, self.width() / WIN_W)

        # ── Titlebar — fixed size regardless of window width ─────────
        self._logo.setStyleSheet(
            f"color:{c('accent').name()};font-size:13px;background:transparent;"
        )
        self._title_lbl.setStyleSheet(
            f"color:{c('t_bright').name()};font-family:Segoe UI;"
            "font-size:10px;font-weight:600;"
            "letter-spacing:2px;background:transparent;"
        )

        # ── Credits page ─────────────────────────────────────────────
        if hasattr(self, "_pg_credits"):
            arc_size = max(90, min(180, int(150 * scale)))
            self._pg_credits.apply_scale(scale, arc_size=arc_size)

        # ── Mini widget ───────────────────────────────────────────────
        if hasattr(self, "_mini_credit_lbl"):
            mini_main = max(9, int(11 * scale))
            mini_sub  = max(8, int(10 * scale))
            for lbl in [self._mini_credit_lbl, self._mini_bonus_lbl]:
                f = lbl.font(); f.setPointSize(mini_main); lbl.setFont(f)
            f = self._mini_od_lbl.font(); f.setPointSize(mini_sub); self._mini_od_lbl.setFont(f)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_grip"):
            self._grip.reposition()

        # Width change → scale fonts immediately, then schedule height recalc
        prev_w = getattr(self, "_last_resize_w", None)
        cur_w  = self.width()
        if prev_w != cur_w:
            self._last_resize_w = cur_w
            self._apply_scale()
            self._adjust_height()
        else:
            self._apply_scale()

    def eventFilter(self, obj, e):
        """Allow window drag only via the titlebar (tbar) area."""
        if obj is self._tbar:
            t = e.type()
            if t == e.MouseButtonPress and e.button() == Qt.LeftButton:
                self._drag_pos = e.globalPos() - self.pos()
                return True
            if t == e.MouseMove and e.buttons() == Qt.LeftButton and self._drag_pos:
                self.move(e.globalPos() - self._drag_pos)
                return True
            if t == e.MouseButtonRelease:
                self._drag_pos = None
                return True
        return super().eventFilter(obj, e)

    def closeEvent(self, e):
        """Save window position, size, and mini-mode state on close."""
        p = self.pos()
        self.settings["win_x"]    = p.x()
        self.settings["win_y"]    = p.y()
        self.settings["win_w"]    = self.width()
        self.settings["mini_mode"] = self._mini_mode
        save_settings(self.settings)
        super().closeEvent(e)

    def moveEvent(self, event):
        super().moveEvent(event)
        screen = get_screen_for_pos(self.geometry().center())
        if screen != self._current_screen: self._apply_size(screen)


# ══════════════════════════════════════════════════════════════
#  PLATFORM HELPERS
# ══════════════════════════════════════════════════════════════
def enable_dpi():
    if sys.platform != "win32": return
    try:
        import ctypes; ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes; ctypes.windll.user32.SetProcessDPIAware()
        except Exception: pass

def register_startup(exe: str):
    if sys.platform != "win32": return
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, "CursorHUD", 0, winreg.REG_SZ, exe); winreg.CloseKey(k)
    except Exception as e: log.error("register_startup: %s", e)

def unregister_startup():
    if sys.platform != "win32": return
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(k, "CursorHUD"); winreg.CloseKey(k)
    except Exception as e: log.error("unregister_startup: %s", e)

# ══════════════════════════════════════════════════════════════
#  ENTRY
# ══════════════════════════════════════════════════════════════
def _qt_msg_handler(msg_type, context, msg):
    if "Unable to set geometry" in msg: return
    log.warning("Qt: %s", msg)

def main():
    if "--install-startup" in sys.argv:
        exe = str(Path(sys.executable if getattr(sys,"frozen",False) else sys.argv[0]).resolve())
        register_startup(exe); return
    if "--uninstall-startup" in sys.argv:
        unregister_startup(); return

    # --mock <path/to/file.json>  — load JSON directly, skip real API calls
    mock_file = None
    if "--mock" in sys.argv:
        idx = sys.argv.index("--mock")
        if idx + 1 < len(sys.argv):
            mock_file = sys.argv[idx + 1]
            if not Path(mock_file).is_file():
                print(f"[CursorHUD] --mock: file not found: {mock_file}", file=sys.stderr)
                sys.exit(1)
            log.info("mock mode: %s", mock_file)
        else:
            print("[CursorHUD] --mock requires a file path argument.", file=sys.stderr)
            sys.exit(1)

    enable_dpi()
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps,    True)
    app = QApplication(sys.argv)
    qInstallMessageHandler(_qt_msg_handler)
    app.setApplicationName("CursorHUD")
    app.setQuitOnLastWindowClosed(True)

    init_settings = load_settings()
    apply_theme(init_settings.get("theme", "dark"))
    app.setStyleSheet(f"""
        QScrollBar:vertical{{background:transparent;width:4px;margin:0;}}
        QScrollBar::handle:vertical{{background:{TH()["scrollbar"]};border-radius:2px;min-height:20px;}}
        QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}
        QToolTip{{background:#080A12;color:#E6F0FF;
        border:1px solid rgba(128,128,128,0.35);border-radius:4px;padding:4px;}}
    """)

    db = _cursor_db_path()
    if not mock_file and not db.exists():
        QMessageBox.critical(None, "CursorHUD",
            S(init_settings, "err_no_db") + str(db))
        sys.exit(1)

    win = HUDWindow(mock_file=mock_file)
    win.show()
    QTimer.singleShot(100, win._adjust_height)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()