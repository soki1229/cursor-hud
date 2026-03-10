#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  CURSOR HUD  v4  ·  Personal Usage Monitor                   ║
║  3-tab · 4 themes · Live clock · Debug panel · EXE-safe      ║
╚══════════════════════════════════════════════════════════════╝
Build EXE:
  pip install pyqt5 requests pyinstaller
  python -m PyInstaller --onefile --windowed --name CursorHUD cursor_hud.py
"""

import sys, os, sqlite3, shutil, logging, tempfile, base64, json, math, traceback
from datetime import datetime, timezone
from pathlib import Path

import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox, QCheckBox, QSizePolicy,
    QTextEdit, QDialog,
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import (
    QColor, QPainter, QBrush, QPen, QPainterPath,
    QLinearGradient, QRadialGradient, QFont, QScreen,
)

# ══════════════════════════════════════════════════════════════
#  EXE-SAFE PATHS
#  EXE: directory next to sys.executable / py: directory next to script
# ══════════════════════════════════════════════════════════════
def _app_dir() -> Path:
    if getattr(sys, "frozen", False):       # PyInstaller EXE
        return Path(sys.executable).parent
    return Path(__file__).parent

APP_DIR       = _app_dir()
SETTINGS_FILE = APP_DIR / "cursor_hud_settings.json"
LOG_FILE      = APP_DIR / "cursor_hud.log"

# ══════════════════════════════════════════════════════════════
#  LOGGING  — app continues even if file write fails
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

# ── in-memory log buffer (for debug panel) ──────────────────────
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
#  THEME SYSTEM
# ══════════════════════════════════════════════════════════════
THEMES: dict[str, dict] = {
    "dark": {
        "name": "dark",
        "bg_win":  (10, 12, 24), "bg_win2": ( 5,  7, 16), "bg_card": (13, 16, 28),
        "accent":  ( 0,220,255), "accent2": (130, 80,255),
        "c_green": (  0,240,140),"c_amber": (255,185, 50), "c_red":   (255, 70, 90),
        "t_bright":(230,240,255),"t_body":  (170,185,215),
        "t_muted": ( 90,110,150),"t_dim":   ( 50, 65, 95),
        "border_lo":(255,255,255,18), "border_hi":(0,220,255,45),
        "scrollbar":"rgba(0,220,255,0.22)", "hatch_alpha":38,
    },
    "light": {
        "name": "light",
        "bg_win":  (240,244,255),"bg_win2": (225,232,248),"bg_card": (255,255,255),
        "accent":  (  0,145,200),"accent2": (100, 55,210),
        "c_green": (  0,170, 90),"c_amber": (200,130,  0),"c_red":   (210, 40, 60),
        "t_bright":(15,  20, 45),"t_body":  ( 55, 70,110),
        "t_muted": (130,145,180),"t_dim":   (185,195,220),
        "border_lo":(0,0,0,20),  "border_hi":(0,145,200,60),
        "scrollbar":"rgba(0,145,200,0.30)", "hatch_alpha":55,
    },
    "midnight": {
        "name": "midnight",
        "bg_win":  ( 6,  4, 18),"bg_win2": ( 2,  1,  9),"bg_card": (12,  8, 28),
        "accent":  (160, 80,255),"accent2": (255, 60,160),
        "c_green": (  0,220,120),"c_amber": (255,160, 40),"c_red":   (255, 50, 80),
        "t_bright":(240,230,255),"t_body":  (185,165,220),
        "t_muted": (100, 80,145),"t_dim":   ( 55, 40, 90),
        "border_lo":(255,255,255,14),"border_hi":(160,80,255,55),
        "scrollbar":"rgba(160,80,255,0.28)", "hatch_alpha":35,
    },
    "matrix": {
        "name": "matrix",
        "bg_win":  ( 0,  8,  0),"bg_win2": ( 0,  4,  0),"bg_card": ( 0, 14,  0),
        "accent":  ( 0,255, 70),"accent2": ( 0,200, 50),
        "c_green": (  0,255, 70),"c_amber": (180,255,  0),"c_red":   (255,100,  0),
        "t_bright":(200,255,200),"t_body":  (100,200,100),
        "t_muted": ( 40,110, 40),"t_dim":   ( 20, 55, 20),
        "border_lo":(0,255,70,16),"border_hi":(0,255,70,50),
        "scrollbar":"rgba(0,255,70,0.25)", "hatch_alpha":30,
    },
}

_THEME: dict = THEMES["dark"]

def TH() -> dict: return _THEME

def c(key: str) -> QColor:
    v = _THEME.get(key)
    if v is None or isinstance(v, str): return QColor()   # guard against string keys (e.g. scrollbar)
    return QColor(*v) if len(v) == 3 else QColor(v[0], v[1], v[2], v[3])

def apply_theme(name: str):
    global _THEME
    _THEME = THEMES.get(name, THEMES["dark"])

def hatch_alpha() -> int:
    return _THEME.get("hatch_alpha", 38)

# ══════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════
BASE_URL     = "https://cursor.com"
WIN_W, WIN_H = 440, 660

try:
    REFRESH_MS = max(5000, int(os.environ.get("CURSOR_REFRESH_MS", "60000")))
except (ValueError, TypeError):
    REFRESH_MS = 60000

# ══════════════════════════════════════════════════════════════
#  I18N
# ══════════════════════════════════════════════════════════════
STRINGS: dict[str, dict[str, str]] = {
    "ko": {
        "nav_credit":"크레딧","nav_profile":"프로필","nav_settings":"설정",
        "spent_label":"소진","personal_section":"개인 크레딧",
        "incl_row":"기본 포함","bonus_row":"보너스 크레딧",
        "od_label":"On-Demand","od_personal":"개인 OD","od_team":"팀 OD 누적",
        "official_pct":"Cursor 공식 사용률","pool_pct":"팀 풀 내 비중",
        "profile_title":"계정","field_name":"이름","field_email":"이메일",
        "field_verified":"인증","field_since":"가입일","field_days":"가입 기간",
        "field_plan":"플랜","field_cycle":"청구 주기",
        "verified_yes":"✓ 인증됨","verified_no":"✗ 미인증","member_days":"일",
        "settings_title":"설정","lang_label":"언어","theme_label":"테마",
        "theme_dark":"다크","theme_light":"라이트","theme_midnight":"미드나잇","theme_matrix":"매트릭스",
        "show_sections":"표시 항목","show_team":"팀 데이터",
        "show_od":"On-Demand 비용","show_official":"공식 사용률",
        "auto_saved":"자동 저장됨","refresh_btn":"↻",
        "next_refresh":"갱신까지","seconds":"초",
        "err_no_db":"Cursor DB를 찾을 수 없음\n",
        "err_token":"토큰 읽기 실패","err_api":"API 응답 없음",
        "err_fetch":"데이터를 불러올 수 없습니다.",
        "free_plan_notice":"Free 플랜은 크레딧 정보를 제공하지 않습니다.\n프로필 탭에서 계정 정보를 확인하세요.",
        "lang_ko":"한국어","lang_en":"English",
        "debug_btn":"로그","debug_title":"디버그 로그",
        "debug_copy":"복사","debug_close":"닫기",
        "startup_boot":"부팅 시 자동실행",
    },
    "en": {
        "nav_credit":"Credits","nav_profile":"Profile","nav_settings":"Settings",
        "spent_label":"Spent","personal_section":"Personal Credits",
        "incl_row":"Included","bonus_row":"Bonus Credits",
        "od_label":"On-Demand","od_personal":"Personal OD","od_team":"Team OD Total",
        "official_pct":"Cursor Official Usage","pool_pct":"My Share of Team Pool",
        "profile_title":"Account","field_name":"Name","field_email":"Email",
        "field_verified":"Verified","field_since":"Member Since","field_days":"Membership",
        "field_plan":"Plan","field_cycle":"Billing Cycle",
        "verified_yes":"✓ Verified","verified_no":"✗ Not Verified","member_days":"days",
        "settings_title":"Settings","lang_label":"Language","theme_label":"Theme",
        "theme_dark":"Dark","theme_light":"Light","theme_midnight":"Midnight","theme_matrix":"Matrix",
        "show_sections":"Visible Sections","show_team":"Team Data",
        "show_od":"On-Demand Costs","show_official":"Official Usage Rate",
        "auto_saved":"Auto-saved","refresh_btn":"↻",
        "next_refresh":"Next refresh","seconds":"s",
        "err_no_db":"Cursor DB not found\n",
        "err_token":"Failed to read token","err_api":"No API response",
        "err_fetch":"Failed to load data.",
        "free_plan_notice":"Free plan does not include credit data.\nCheck the Profile tab for account info.",
        "lang_ko":"한국어","lang_en":"English",
        "debug_btn":"Log","debug_title":"Debug Log",
        "debug_copy":"Copy","debug_close":"Close",
        "startup_boot":"Start on Boot",
    },
}

DEFAULT_SETTINGS: dict = {
    "lang":"ko","theme":"dark",
    "show_team":True,"show_od":True,"show_official":True,
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
    if sys.platform == "win32":    base = Path(os.environ.get("APPDATA", ""))
    elif sys.platform == "darwin": base = Path.home() / "Library" / "Application Support"
    else:                          base = Path.home() / ".config"
    return base / "Cursor" / "User" / "globalStorage" / "state.vscdb"

def decode_jwt(token: str) -> dict:
    try:
        p = token.split(".")[1]; p += "=" * (4 - len(p) % 4)
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
        os.close(fd)
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
#  DATA FETCHER
# ══════════════════════════════════════════════════════════════
class DataFetcher(QThread):
    ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def _get(self, session, path):
        r = session.get(f"{BASE_URL}{path}", allow_redirects=False, timeout=12)
        if r.status_code in (301, 302, 307, 308):
            loc = r.headers.get("Location", "")
            if loc.startswith("/"): loc = BASE_URL + loc
            r = session.get(loc, timeout=12)
        log.info("GET %s → %s", path, r.status_code)
        return r.json() if r.ok else None

    def run(self):
        try:
            cookie, email = read_cursor_token()
            if not cookie:
                self.error.emit(S(load_settings(), "err_token")); return
            sess = requests.Session()
            sess.headers.update(api_headers(cookie))
            summary = self._get(sess, "/api/usage-summary")
            profile = self._get(sess, "/api/auth/me")
            if not summary:
                self.error.emit(S(load_settings(), "err_api")); return
            raw = {
                "summary":    summary,
                "profile":    profile or {},
                "email":      email,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            self.ready.emit(raw)
        except Exception as exc:
            log.exception("DataFetcher.run")
            self.error.emit(str(exc))

# ══════════════════════════════════════════════════════════════
#  DATA MODEL
# ══════════════════════════════════════════════════════════════
def parse_data(raw: dict) -> dict:
    s  = raw.get("summary", {})
    pr = raw.get("profile", {})

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

    incl_total    = int(bk.get("included", 0) or 0)
    bonus_total   = int(bk.get("bonus",    0) or 0)
    budget_total  = int(bk.get("total",    0) or 0)
    used_total    = int(plan.get("used",   0) or 0)
    used_on_incl  = min(used_total, incl_total)
    used_on_bonus = max(0, used_total - incl_total)
    bonus_remain  = max(0, bonus_total - used_on_bonus)
    incl_remain   = max(0, incl_total  - used_on_incl)

    credit = {
        "incl_total":       incl_total,
        "incl_used":        used_on_incl,
        "incl_remain":      incl_remain,
        "incl_remain_pct":  (incl_remain   / incl_total  * 100) if incl_total  else 0,
        "bonus_total":      bonus_total,
        "bonus_used":       used_on_bonus,
        "bonus_remain":     bonus_remain,
        "bonus_remain_pct": (bonus_remain  / bonus_total * 100) if bonus_total else 0,
        "budget_total":     budget_total,
        "budget_used":      used_total,
        "budget_pct":       (used_total    / budget_total * 100) if budget_total else 0,
        "budget_remain":    max(0, budget_total - used_total),
        "api_pct":          float(plan.get("apiPercentUsed",   0) or 0),
        "total_pct":        float(plan.get("totalPercentUsed", 0) or 0),
    }

    on_demand = {
        "personal": int(od_p.get("used", 0) or 0),
        "team":     int(od_t.get("used", 0) or 0),
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

    return {
        "cycle":      cycle,
        "credit":     credit,
        "on_demand":  on_demand,
        "profile":    profile,
        "hint":       s.get("autoModelSelectedDisplayMessage", "") or "",
        "fetched_at": raw.get("fetched_at", ""),
        "is_free":    is_free,
    }

# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
def usd(cents: int) -> str:
    return f"${cents / 100:.2f}"

def pct_color(pct: float) -> QColor:
    """Usage-based color — more consumed means more urgent color."""
    if pct >= 90: return c("c_red")
    if pct >= 75: return c("c_amber")
    return c("accent")

def remain_color(remain_pct: float) -> QColor:
    """Remaining-based color — traffic-light 3-zone (semantic, independent of theme accent).
     0~25%  : c_red    danger
    26~50%  : c_amber  caution
    51~100% : c_green  ok
    """
    if remain_pct <= 25: return c("c_red")
    if remain_pct <= 50: return c("c_amber")
    return c("c_green")

def ql(text: str = "", size: int = 10, color: QColor = None, bold: bool = False,
        align=Qt.AlignLeft, family: str = "Segoe UI") -> QLabel:
    w = QLabel(text)
    f = QFont(family, size); f.setBold(bold)
    w.setFont(f); w.setAlignment(align)
    col = color or c("t_body")
    w.setStyleSheet(
        f"color:rgba({col.red()},{col.green()},{col.blue()},{col.alpha()});"
        "background:transparent;"
    )
    return w

def set_lbl_color(lbl: QLabel, color: QColor):
    col = color
    lbl.setStyleSheet(
        f"color:rgba({col.red()},{col.green()},{col.blue()},255);background:transparent;"
    )

def get_screen_for_pos(pos) -> QScreen:
    for s in QApplication.screens():
        if s.geometry().contains(pos): return s
    return QApplication.primaryScreen()

# ══════════════════════════════════════════════════════════════
#  HATCH HELPER — shared 45-degree diagonal hatch pattern
# ══════════════════════════════════════════════════════════════
def _draw_hatch(p: QPainter, w: float, h: float, step: int = 5):
    """Draw 45° diagonal hatch lines within the current clip region."""
    p.setPen(QPen(QColor(128, 128, 128, hatch_alpha()), 1.0))
    ih = int(h)
    for i in range(-ih, int(w) + ih, step):
        p.drawLine(i, 0, i + ih, ih)

# ══════════════════════════════════════════════════════════════
#  PRIMITIVE WIDGETS
# ══════════════════════════════════════════════════════════════
class ArcGauge(QWidget):
    """Concentric double-semicircle arc gauge; empty track uses diagonal hatch."""
    def __init__(self, size: int = 160):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(size, size // 2 + 12)
        self._r      = size // 2 - 8
        self._pct    = 0.0
        self._color  = c("accent")
        self._stroke = 9

    def set_value(self, pct: float, color: QColor = None):
        self._pct   = max(0.0, min(100.0, pct))
        self._color = color or c("accent")
        self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy, r, sw = w // 2, h - 6, self._r, self._stroke

        # Empty track: semicircle donut path, then diagonal hatch
        # Donut = outer semicircle (L→R) + inner semicircle (R→L)
        outer_r = r + sw // 2
        inner_r = max(1, r - sw // 2)
        track = QPainterPath()
        # Outer semicircle: 180° → 0° (counter-clockwise; Qt positive span = CCW)
        track.moveTo(cx - outer_r, cy)
        track.arcTo(QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2),
                    180, -180)  # start at 180°, -180° span = semicircle clockwise
        # Inner semicircle: 0° → 180° (opposite direction to close)
        track.lineTo(cx + inner_r, cy)
        track.arcTo(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2),
                    0, 180)
        track.closeSubpath()

        p.setClipPath(track)
        p.setBrush(QBrush(QColor(128, 128, 128, 22))); p.setPen(Qt.NoPen)
        p.drawPath(track)
        _draw_hatch(p, w, h, step=5)
        p.setClipping(False)

        # Filled arc
        if self._pct > 0:
            span = int(self._pct / 100 * 180)
            g = QLinearGradient(cx - r, 0, cx + r, 0)
            g.setColorAt(0, self._color.darker(150)); g.setColorAt(1, self._color)
            p.setPen(QPen(QBrush(g), sw, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            p.drawArc(cx-r, cy-r, r*2, r*2, 180*16, -span*16)
            # Tip glow
            ang = (180 - self._pct / 100 * 180) * math.pi / 180
            tx = cx + r * math.cos(ang); ty = cy - r * math.sin(ang)
            glow = QRadialGradient(tx, ty, 14)
            glow.setColorAt(0, QColor(self._color.red(), self._color.green(),
                                      self._color.blue(), 140))
            glow.setColorAt(1, Qt.transparent)
            p.setPen(Qt.NoPen); p.setBrush(QBrush(glow))
            p.drawEllipse(QPointF(tx, ty), 14, 14)
        p.end()


class SegBar(QWidget):
    """Horizontal segment bar; empty track uses diagonal hatch."""
    def __init__(self, h: int = 7):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(h)
        self._segs: list[tuple[float, QColor]] = []

    def set_segments(self, segs: list[tuple[float, QColor]]):
        self._segs = segs; self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height(); r = h / 2

        # Empty track hatch
        clip = QPainterPath(); clip.addRoundedRect(QRectF(0,0,w,h), r, r)
        p.setClipPath(clip)
        p.setBrush(QBrush(QColor(128,128,128,18))); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0,0,w,h), r, r)
        _draw_hatch(p, w, h, step=5)
        p.setClipping(False)

        # Filled segments
        p.setPen(Qt.NoPen); x = 0.0
        for frac, color in self._segs:
            fw = max(0.0, min(1.0, frac)) * w
            if fw < 1: x += fw; continue
            sc = QPainterPath(); sc.addRoundedRect(QRectF(x,0,fw,h), r, r)
            p.setClipPath(sc)
            g = QLinearGradient(x, 0, x+fw, 0)
            g.setColorAt(0, color.darker(130)); g.setColorAt(1, color)
            p.setBrush(QBrush(g))
            p.drawRoundedRect(QRectF(x,0,fw,h), r, r)
            p.setClipping(False); x += fw
        p.end()


class MiniBar(QWidget):
    """Solid horizontal bar; empty track uses diagonal hatch."""
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
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height(); r = h / 2

        # Empty track hatch
        clip = QPainterPath(); clip.addRoundedRect(QRectF(0,0,w,h), r, r)
        p.setClipPath(clip)
        p.setBrush(QBrush(QColor(128,128,128,18))); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0,0,w,h), r, r)
        _draw_hatch(p, w, h, step=4)
        p.setClipping(False)

        # Filled bar
        fw = max(r*2, w * self._frac)
        fc = QPainterPath(); fc.addRoundedRect(QRectF(0,0,fw,h), r, r)
        p.setClipPath(fc)
        g = QLinearGradient(0,0,fw,0)
        g.setColorAt(0, self._color.darker(140)); g.setColorAt(1, self._color)
        p.setBrush(QBrush(g)); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0,0,fw,h), r, r)
        p.setClipping(False)
        p.end()


class Card(QWidget):
    def __init__(self, accent_key: str = "accent"):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._accent_key = accent_key

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setBrush(QBrush(c("bg_card"))); p.setPen(QPen(c("border_lo"), 1))
        p.drawRoundedRect(r, 10, 10)
        ac = c(self._accent_key)
        pen = QPen(ac, 1.5); pen.setCapStyle(Qt.RoundCap); p.setPen(pen)
        p.drawLine(QPointF(r.left()+14, r.top()+0.75),
                   QPointF(r.left()+56, r.top()+0.75))
        p.end()


class Divider(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.HLine); self.setFixedHeight(1)
        self.setStyleSheet("background:rgba(128,128,128,0.15);border:none;")


# ══════════════════════════════════════════════════════════════
#  TOGGLE SWITCH WIDGET
# ══════════════════════════════════════════════════════════════
class ToggleSwitch(QWidget):
    """Minimal toggle switch without animation."""
    toggled = pyqtSignal(bool)

    W, H = 34, 18

    def __init__(self, checked: bool = False):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.W, self.H)
        self.setCursor(Qt.PointingHandCursor)
        self._checked = checked

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, val: bool):
        self._checked = val
        self.update()

    def mousePressEvent(self, _):
        self._checked = not self._checked
        self.update()
        self.toggled.emit(self._checked)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.W, self.H
        r = h / 2

        # Track
        track_color = c("accent") if self._checked else QColor(128, 128, 128, 60)
        p.setBrush(QBrush(track_color)); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        # Knob
        knob_r = h / 2 - 2
        knob_x = (w - h + 2 + knob_r) if self._checked else (2 + knob_r)
        knob_y = h / 2
        p.setBrush(QBrush(QColor(255, 255, 255, 230))); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(knob_x, knob_y), knob_r, knob_r)
        p.end()

# ══════════════════════════════════════════════════════════════
#  KV-ROW FACTORY
# ══════════════════════════════════════════════════════════════
KVRow = tuple  # (label_QLabel, value_QLabel)

def kv_row(parent_layout, label: str) -> KVRow:
    row = QWidget(); row.setAttribute(Qt.WA_TranslucentBackground)
    rl = QHBoxLayout(row); rl.setContentsMargins(0,1,0,1); rl.setSpacing(4)
    lw = ql(label, 9, c("t_muted"))
    lw.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    vw = QLabel("—")
    vw.setFont(QFont("Segoe UI", 9, QFont.Bold))
    vw.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    vw.setWordWrap(False); vw.setTextInteractionFlags(Qt.NoTextInteraction)
    vw.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); vw.setMinimumWidth(0)
    col = c("t_bright")
    vw.setStyleSheet(f"color:rgba({col.red()},{col.green()},{col.blue()},255);background:transparent;")
    rl.addWidget(lw, 0); rl.addWidget(vw, 1)
    parent_layout.addWidget(row)
    return lw, vw

def set_kv(row: KVRow, value: str, color: QColor = None):
    _, vw = row; vw.setText(value)
    set_lbl_color(vw, color or c("t_bright"))

def update_kv_label(row: KVRow, label: str):
    lw, _ = row; lw.setText(label)
    set_lbl_color(lw, c("t_muted"))

def section_hdr(text: str, accent_key: str = "t_muted") -> QLabel:
    w = ql(text.upper(), 8, c(accent_key), bold=True)
    w.setStyleSheet(w.styleSheet() + "letter-spacing:1.5px;")
    return w

# ══════════════════════════════════════════════════════════════
#  DEBUG DIALOG
# ══════════════════════════════════════════════════════════════
class DebugDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(S(settings, "debug_title"))
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setFixedSize(560, 420)
        self.setStyleSheet(
            f"background:{c('bg_win').name()}; color:{c('t_body').name()};"
        )
        vl = QVBoxLayout(self); vl.setContentsMargins(12,12,12,10); vl.setSpacing(8)

        for line in [
            f"CursorHUD  ·  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Python {sys.version.split()[0]}  ·  "
            f"{'EXE (frozen)' if getattr(sys,'frozen',False) else 'Script'}",
            f"Log → {LOG_FILE}",
            f"Settings → {SETTINGS_FILE}",
            f"Cursor DB → {_cursor_db_path()}",
        ]:
            lb = QLabel(line); lb.setFont(QFont("Consolas", 8))
            lb.setStyleSheet(f"color:{c('t_muted').name()};background:transparent;")
            vl.addWidget(lb)

        vl.addWidget(Divider())

        self._txt = QTextEdit()
        self._txt.setReadOnly(True); self._txt.setFont(QFont("Consolas", 8))
        self._txt.setStyleSheet(
            f"background:{c('bg_card').name()};color:{c('t_body').name()};"
            "border:none;border-radius:6px;padding:6px;"
        )
        self._txt.setPlainText("\n".join(_mem_log.records) or "(no logs)")
        self._txt.verticalScrollBar().setValue(self._txt.verticalScrollBar().maximum())
        vl.addWidget(self._txt, 1)

        br = QWidget(); bl = QHBoxLayout(br); bl.setContentsMargins(0,0,0,0); bl.setSpacing(6)
        bl.addStretch()
        for lkey, slot in [("debug_copy", self._copy), ("debug_close", self.accept)]:
            btn = QPushButton(S(settings, lkey)); btn.setFixedHeight(26)
            ac = c("accent").name(); mu = c("t_muted").name()
            btn.setStyleSheet(f"""
                QPushButton{{color:{mu};background:rgba(128,128,128,0.08);
                border:1px solid rgba(128,128,128,0.25);border-radius:4px;
                font-size:9px;padding:0 12px;}}
                QPushButton:hover{{color:{ac};border-color:{ac};}}
            """)
            btn.clicked.connect(slot); bl.addWidget(btn)
        vl.addWidget(br)

    def _copy(self):
        QApplication.clipboard().setText(self._txt.toPlainText())

# ══════════════════════════════════════════════════════════════
#  PAGE: CREDITS
# ══════════════════════════════════════════════════════════════
class CreditsPage(QWidget):
    def __init__(self, settings: dict):
        super().__init__()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.settings = settings
        self._row_refs: dict[str, KVRow] = {}
        self._build()

    def T(self, k): return S(self.settings, k)

    def _build(self):
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent;")
        inner = QWidget(); inner.setAttribute(Qt.WA_TranslucentBackground)
        inner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        inner.setMinimumWidth(0)
        vl = QVBoxLayout(inner); vl.setContentsMargins(12,8,12,8); vl.setSpacing(8)
        scroll.setWidget(inner); outer.addWidget(scroll)

        self._err_lbl = ql("", 9, c("c_red")); self._err_lbl.setWordWrap(True)
        self._err_lbl.hide()
        ew = QVBoxLayout(); ew.setContentsMargins(12,0,12,4); ew.addWidget(self._err_lbl)
        outer.addLayout(ew)

        # Hero card
        hero = Card("accent"); hl = QHBoxLayout(hero); hl.setContentsMargins(14,12,14,12); hl.setSpacing(8)
        self._arc = ArcGauge(size=150); self._arc.setFixedSize(150, 87)
        hl.addWidget(self._arc, 0)
        info = QWidget(); info.setAttribute(Qt.WA_TranslucentBackground)
        il = QVBoxLayout(info); il.setContentsMargins(0,0,0,0); il.setSpacing(2)
        self._hero_pct  = ql("—%",  20, c("accent"),  bold=True)
        self._hero_used = ql("$—",  11, c("t_bright"), bold=True)
        self._hero_of   = ql("/ $—", 9, c("t_muted"))
        self._cycle_lbl = ql("",     8, c("t_dim")); self._cycle_lbl.setWordWrap(True)
        il.addStretch()
        for w in [self._hero_pct, self._hero_used, self._hero_of]:
            il.addWidget(w)
        self._free_notice_lbl = ql("", 8, c("t_muted")); self._free_notice_lbl.setWordWrap(True)
        self._free_notice_lbl.hide()
        il.addSpacing(4); il.addWidget(self._free_notice_lbl); il.addWidget(self._cycle_lbl); il.addStretch()
        hl.addWidget(info, 1); vl.addWidget(hero)

        # Personal credits card
        pc = Card("accent"); pl = QVBoxLayout(pc); pl.setContentsMargins(14,11,14,11); pl.setSpacing(5)
        self._hdr_personal = section_hdr(self.T("personal_section"))
        pl.addWidget(self._hdr_personal); pl.addWidget(Divider())
        self._incl_bar = SegBar(h=6); pl.addWidget(self._incl_bar)
        self._row_refs["incl"] = kv_row(pl, self.T("incl_row"))
        # Bonus (conditionally shown)
        self._bonus_w = QWidget(); self._bonus_w.setAttribute(Qt.WA_TranslucentBackground)
        bwl = QVBoxLayout(self._bonus_w); bwl.setContentsMargins(0,0,0,0); bwl.setSpacing(3)
        bwl.addSpacing(2)
        self._bonus_bar = SegBar(h=6); bwl.addWidget(self._bonus_bar)
        self._row_refs["bonus"] = kv_row(bwl, self.T("bonus_row"))
        pl.addWidget(self._bonus_w); vl.addWidget(pc)

        # On-Demand card
        self._od_card = Card("c_amber"); ol = QVBoxLayout(self._od_card); ol.setContentsMargins(14,11,14,11); ol.setSpacing(5)
        self._hdr_od = section_hdr(self.T("od_label"), "c_amber")
        ol.addWidget(self._hdr_od); ol.addWidget(Divider())
        self._row_refs["od_p"] = kv_row(ol, self.T("od_personal"))
        self._od_team_w = QWidget(); self._od_team_w.setAttribute(Qt.WA_TranslucentBackground)
        otl = QVBoxLayout(self._od_team_w); otl.setContentsMargins(0,0,0,0); otl.setSpacing(0)
        self._row_refs["od_t"] = kv_row(otl, self.T("od_team"))
        ol.addWidget(self._od_team_w); vl.addWidget(self._od_card)

        # Usage rates card
        self._rate_card = Card("accent2"); rl2 = QVBoxLayout(self._rate_card); rl2.setContentsMargins(14,11,14,11); rl2.setSpacing(5)
        self._hdr_rates = section_hdr("USAGE RATES", "accent2")
        rl2.addWidget(self._hdr_rates); rl2.addWidget(Divider())
        self._off_w = QWidget(); self._off_w.setAttribute(Qt.WA_TranslucentBackground)
        owl = QVBoxLayout(self._off_w); owl.setContentsMargins(0,0,0,0); owl.setSpacing(3)
        self._row_refs["off"] = kv_row(owl, self.T("official_pct"))
        self._off_bar = MiniBar(h=4); owl.addWidget(self._off_bar); rl2.addWidget(self._off_w)
        self._pool_w = QWidget(); self._pool_w.setAttribute(Qt.WA_TranslucentBackground)
        pwl = QVBoxLayout(self._pool_w); pwl.setContentsMargins(0,0,0,0); pwl.setSpacing(3)
        self._row_refs["pool"] = kv_row(pwl, self.T("pool_pct"))
        self._pool_bar = MiniBar(h=4); pwl.addWidget(self._pool_bar); rl2.addWidget(self._pool_w)
        self._hint_lbl = ql("", 8, c("t_muted")); self._hint_lbl.setWordWrap(True)
        self._hint_lbl.hide(); rl2.addWidget(self._hint_lbl)
        vl.addWidget(self._rate_card); vl.addStretch()

    def _rebuild_labels(self):
        update_kv_label(self._row_refs["incl"],  self.T("incl_row"))
        update_kv_label(self._row_refs["bonus"], self.T("bonus_row"))
        update_kv_label(self._row_refs["od_p"],  self.T("od_personal"))
        update_kv_label(self._row_refs["od_t"],  self.T("od_team"))
        update_kv_label(self._row_refs["off"],   self.T("official_pct"))
        update_kv_label(self._row_refs["pool"],  self.T("pool_pct"))
        self._hdr_personal.setText(self.T("personal_section").upper())
        set_lbl_color(self._hdr_personal, c("t_muted"))
        self._hdr_od.setText(self.T("od_label").upper())
        set_lbl_color(self._hdr_od, c("c_amber"))
        set_lbl_color(self._hdr_rates, c("accent2"))

    def set_error(self, msg: str):
        if msg: self._err_lbl.setText(f"⚠  {msg}"); self._err_lbl.show()
        else:   self._err_lbl.hide()

    def refresh_theme(self):
        """Reapply all fixed colors when theme changes."""
        # Error / hint
        set_lbl_color(self._err_lbl,   c("c_red"))
        set_lbl_color(self._hint_lbl,        c("t_muted"))
        set_lbl_color(self._free_notice_lbl, c("t_muted"))
        # Hero static labels
        set_lbl_color(self._hero_used, c("t_bright"))
        set_lbl_color(self._hero_of,   c("t_muted"))
        set_lbl_color(self._cycle_lbl, c("t_dim"))
        # Section headers
        set_lbl_color(self._hdr_personal, c("t_muted"))
        set_lbl_color(self._hdr_od,       c("c_amber"))
        set_lbl_color(self._hdr_rates,    c("accent2"))
        # All kv_row: reapply label(t_muted) + value(t_bright)
        # (update_data overwrites when present, so safe)
        for row in self._row_refs.values():
            lw, vw = row
            set_lbl_color(lw, c("t_muted"))
            set_lbl_color(vw, c("t_bright"))

    def update_data(self, d: dict):
        cr = d["credit"]; od = d["on_demand"]; cyc = d["cycle"]; cfg = self.settings
        self._rebuild_labels()

        # Free plan: hide credit card, show notice only
        if d.get("is_free"):
            self._arc.set_value(0, c("t_muted"))
            self._hero_pct.setText("FREE"); set_lbl_color(self._hero_pct, c("t_muted"))
            self._hero_used.setText(""); self._hero_of.setText("")
            self._cycle_lbl.setText(f"{cyc['start']} → {cyc['end']} · {cyc['membership']}")
            self._incl_bar.set_segments([]); set_kv(self._row_refs["incl"], "—")
            self._bonus_w.hide()
            self._od_card.hide(); self._rate_card.hide()
            self._free_notice_lbl.setText(self.T("free_plan_notice"))
            self._free_notice_lbl.show()
            self._hint_lbl.hide()
            return

        self._free_notice_lbl.hide()

        # Hero
        pct = cr["budget_pct"]; hc = pct_color(pct)
        self._arc.set_value(pct, hc)
        self._hero_pct.setText(f"{pct:.1f}%"); set_lbl_color(self._hero_pct, hc)
        self._hero_used.setText(usd(cr["budget_used"]))
        self._hero_of.setText(f"/ {usd(cr['budget_total'])}  {self.T('spent_label')}")
        self._cycle_lbl.setText(f"{cyc['start']} → {cyc['end']} · {cyc['membership']}")

        # Included credits bar
        incl_rc   = remain_color(cr["incl_remain_pct"])
        incl_frac = (cr["incl_remain"] / cr["incl_total"]) if cr["incl_total"] else 0
        self._incl_bar.set_segments([(incl_frac, incl_rc)])
        set_kv(self._row_refs["incl"],
               f"{usd(cr['incl_remain'])} / {usd(cr['incl_total'])}  ({cr['incl_remain_pct']:.0f}%)",
               incl_rc)

        # Bonus credits bar
        if cr["bonus_total"] > 0:
            self._bonus_w.show()
            bonus_rc   = remain_color(cr["bonus_remain_pct"])
            bonus_frac = (cr["bonus_remain"] / cr["bonus_total"]) if cr["bonus_total"] else 0
            self._bonus_bar.set_segments([(bonus_frac, bonus_rc)])
            set_kv(self._row_refs["bonus"],
                   f"{usd(cr['bonus_remain'])} / {usd(cr['bonus_total'])}  ({cr['bonus_remain_pct']:.0f}%)",
                   bonus_rc)
        else:
            self._bonus_w.hide()

        # On-Demand
        show_od = cfg.get("show_od", True); self._od_card.setVisible(show_od)
        if show_od:
            set_kv(self._row_refs["od_p"],
                   usd(od["personal"]) if od["personal"] else "—",
                   c("c_amber") if od["personal"] > 0 else c("t_muted"))
            self._od_team_w.setVisible(cfg.get("show_team", True))
            set_kv(self._row_refs["od_t"],
                   usd(od["team"]) if od["team"] else "—",
                   c("c_amber") if od["team"] > 0 else c("t_muted"))

        # Usage Rates
        show_rate = cfg.get("show_official", True); self._rate_card.setVisible(show_rate)
        if show_rate:
            tp = cr["total_pct"]; tc = pct_color(tp)
            ap = cr["api_pct"];   ac = pct_color(ap)
            set_kv(self._row_refs["off"], f"{tp:.1f}%", tc)
            self._off_bar.set_value(tp / 100, tc)
            self._pool_w.setVisible(cfg.get("show_team", True))
            set_kv(self._row_refs["pool"], f"{ap:.1f}%", ac)
            self._pool_bar.set_value(ap / 100, ac)
            hint = d.get("hint", "")
            if hint: self._hint_lbl.setText(f"ℹ  {hint}"); self._hint_lbl.show()
            else:    self._hint_lbl.hide()


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
        """Reapply colors when theme changes."""
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
    changed       = pyqtSignal()
    theme_changed = pyqtSignal(str)

    TOGGLES      = [("show_team","show_team"),("show_od","show_od"),("show_official","show_official")]
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
        while self._vl.count():
            item = self._vl.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        card = Card("accent"); cl = QVBoxLayout(card); cl.setContentsMargins(14,12,14,12); cl.setSpacing(8)
        cl.addWidget(section_hdr(self.T("settings_title"))); cl.addWidget(Divider())

        # Language — radio style
        cl.addWidget(ql(self.T("lang_label"), 8, c("t_muted")))
        lr = QWidget(); lr.setAttribute(Qt.WA_TranslucentBackground)
        ll = QHBoxLayout(lr); ll.setContentsMargins(0,0,0,0); ll.setSpacing(6)
        ac = c("accent").name(); mu = c("t_muted").name()
        lang_style = f"""QPushButton{{color:{mu};background:transparent;
            border:1px solid rgba(128,128,128,0.28);border-radius:3px;
            font-size:9px;padding:1px 12px;font-family:'Segoe UI';font-weight:600;}}
            QPushButton:checked{{color:{ac};border:1px solid {ac};background:rgba(128,128,128,0.10);}}"""
        for code, lkey in [("ko","lang_ko"),("en","lang_en")]:
            btn = QPushButton(self.T(lkey))
            btn.setCheckable(True); btn.setChecked(self.settings.get("lang","ko") == code)
            btn.setFixedHeight(22); btn.setStyleSheet(lang_style)
            btn.clicked.connect(lambda _, lc=code: self._set_lang(lc))
            ll.addWidget(btn)
        ll.addStretch(); cl.addWidget(lr); cl.addWidget(Divider())

        # Theme
        cl.addWidget(ql(self.T("theme_label"), 8, c("t_muted")))
        cur_theme = self.settings.get("theme", "dark")
        rows = [QWidget(), QWidget()]
        rls  = [QHBoxLayout(r) for r in rows]
        for rl in rls: rl.setContentsMargins(0,0,0,0); rl.setSpacing(6)
        for i, (tname, tkey) in enumerate(self.THEMES_ORDER):
            btn = self._theme_btn(self.T(tkey), THEMES[tname], tname == cur_theme)
            btn.clicked.connect(lambda _, tn=tname: self._set_theme(tn))
            rls[0 if i < 2 else 1].addWidget(btn, 1)
        for r in rows: cl.addWidget(r)
        cl.addWidget(Divider())

        # Visibility toggles — radio style (ON / OFF)
        cl.addWidget(ql(self.T("show_sections"), 8, c("t_muted")))
        for key, label_key in self.TOGGLES:
            cl.addWidget(self._switch_row(self.T(label_key), key, self.settings.get(key, True)))

        cl.addWidget(Divider())

        # Startup — radio style (Windows only)
        if sys.platform == "win32":
            cl.addWidget(self._switch_row(self.T("startup_boot"), "_startup",
                                        self._is_startup_registered()))
            cl.addWidget(Divider())

        cl.addWidget(ql(self.T("auto_saved"), 8, c("t_dim")))
        self._vl.addWidget(card); self._vl.addStretch()

    def _switch_row(self, label: str, key: str, enabled: bool) -> QWidget:
        """Return one row: label + toggle switch."""
        rw = QWidget(); rw.setAttribute(Qt.WA_TranslucentBackground)
        rl = QHBoxLayout(rw); rl.setContentsMargins(0, 2, 0, 2); rl.setSpacing(8)
        rl.addWidget(ql(label, 9, c("t_body")))
        rl.addStretch()
        sw = ToggleSwitch(checked=enabled)
        sw.toggled.connect(lambda val, k=key: self._on_switch(k, val))
        rl.addWidget(sw)
        return rw

    def _on_switch(self, key: str, value: bool):
        if key == "_startup":
            if value:
                exe = str(Path(sys.executable if getattr(sys,"frozen",False) else sys.argv[0]).resolve())
                register_startup(exe); log.info("startup registered: %s", exe)
            else:
                unregister_startup(); log.info("startup unregistered")
        else:
            self.settings[key] = value
            save_settings(self.settings)
            self.changed.emit()

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
        btn.setStyleSheet(f"""
            QPushButton{{color:{mu};background:{bg_hex};
            border:1px solid rgba(128,128,128,0.25);border-radius:5px;
            font-size:9px;font-family:'Segoe UI';font-weight:600;}}
            QPushButton:checked{{color:{ac_hex};border:2px solid {ac_hex};
            background:rgba({av[0]},{av[1]},{av[2]},25);}}
            QPushButton:hover:!checked{{border:1px solid rgba(128,128,128,0.50);}}
        """)
        return btn

    def _set_lang(self, code: str):
        self.settings["lang"] = code; save_settings(self.settings); self._build(); self.changed.emit()

    def _set_theme(self, name: str):
        self.settings["theme"] = name; save_settings(self.settings)
        apply_theme(name); self._build(); self.theme_changed.emit(name)




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

        self._clock_lbl = QLabel("—")
        self._clock_lbl.setStyleSheet(
            f"color:{c('t_muted').name()};font-size:9px;background:transparent;font-family:'Consolas';"
        )
        hl.addWidget(self._clock_lbl); hl.addStretch()

        self._cd_lbl = QLabel("")
        self._cd_lbl.setStyleSheet(
            f"color:{c('t_dim').name()};font-size:8px;background:transparent;font-family:'Segoe UI';"
        )
        hl.addWidget(self._cd_lbl)

        # Debug button (small, low emphasis)
        self._dbg_btn = QPushButton(S(settings, "debug_btn"))
        self._dbg_btn.setFixedSize(30, 22); self._dbg_btn.setCursor(Qt.PointingHandCursor)
        mu = c("t_dim").name()
        self._dbg_btn.setStyleSheet(f"""
            QPushButton{{color:{mu};background:transparent;
            border:1px solid rgba(128,128,128,0.18);border-radius:3px;font-size:8px;}}
            QPushButton:hover{{color:{c('t_muted').name()};border-color:rgba(128,128,128,0.40);}}
        """)
        self._dbg_btn.clicked.connect(self.debug_clicked); hl.addWidget(self._dbg_btn)

        # Refresh button
        self._rbtn = QPushButton(S(settings, "refresh_btn"))
        self._rbtn.setFixedSize(26, 22); self._rbtn.setCursor(Qt.PointingHandCursor)
        ac = c("accent").name()
        self._rbtn.setStyleSheet(f"""
            QPushButton{{color:{ac};background:rgba(128,128,128,0.08);
            border:1px solid rgba(128,128,128,0.25);border-radius:4px;font-size:12px;}}
            QPushButton:hover{{background:rgba(128,128,128,0.18);}}
        """)
        self._rbtn.clicked.connect(self.refresh_clicked); hl.addWidget(self._rbtn)

    def set_status(self, state: str):
        col_map = {"ok": c("c_green"), "loading": c("c_amber"), "error": c("c_red")}
        col = col_map.get(state, c("t_muted"))
        self._dot.setStyleSheet(
            f"color:rgba({col.red()},{col.green()},{col.blue()},255);"
            "font-size:8px;background:transparent;"
        )

    def set_clock(self, ts: str): self._clock_lbl.setText(ts)

    def set_countdown(self, secs: int):
        self._cd_lbl.setText(
            f"{S(self.settings,'next_refresh')} {secs}{S(self.settings,'seconds')}"
        )

    def refresh_labels(self):
        """Refresh labels when language changes."""
        self._dbg_btn.setText(S(self.settings, "debug_btn"))

    def refresh_theme(self):
        self._dot.setStyleSheet(f"color:{c('t_muted').name()};font-size:8px;background:transparent;")
        self._clock_lbl.setStyleSheet(
            f"color:{c('t_muted').name()};font-size:9px;background:transparent;font-family:'Consolas';"
        )
        self._cd_lbl.setStyleSheet(
            f"color:{c('t_dim').name()};font-size:8px;background:transparent;font-family:'Segoe UI';"
        )
        mu = c("t_dim").name()
        self._dbg_btn.setStyleSheet(f"""
            QPushButton{{color:{mu};background:transparent;
            border:1px solid rgba(128,128,128,0.18);border-radius:3px;font-size:8px;}}
            QPushButton:hover{{color:{c('t_muted').name()};border-color:rgba(128,128,128,0.40);}}
        """)
        ac = c("accent").name()
        self._rbtn.setStyleSheet(f"""
            QPushButton{{color:{ac};background:rgba(128,128,128,0.08);
            border:1px solid rgba(128,128,128,0.25);border-radius:4px;font-size:12px;}}
            QPushButton:hover{{background:rgba(128,128,128,0.18);}}
        """)


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
        btn.setStyleSheet(f"""
            QPushButton{{color:{mu};background:transparent;border:none;
            border-bottom:2px solid transparent;font-family:'Segoe UI';font-size:9px;
            font-weight:600;letter-spacing:0.5px;padding:0 4px;}}
            QPushButton:checked{{color:{ac};border-bottom:2px solid {ac};}}
            QPushButton:hover:!checked{{color:rgba(170,185,215,180);}}
        """)

    def set_active(self, idx: int):
        for i, btn in enumerate(self._btns): btn.setChecked(i == idx)

    def refresh_labels(self):
        for i, key in enumerate(self.TABS): self._btns[i].setText(S(self.settings, key))

    def refresh_theme(self):
        for btn in self._btns: self._apply_style(btn)


# ══════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════
class HUDWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cursor HUD")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos       = None
        self._fetcher        = None
        self._last_data      = None
        self._current_screen = None
        self._countdown      = REFRESH_MS // 1000
        self.settings        = load_settings()
        apply_theme(self.settings.get("theme", "dark"))
        self._apply_size(QApplication.primaryScreen())
        geo = QApplication.primaryScreen().availableGeometry()
        self.move(geo.right() - WIN_W - 20, geo.bottom() - WIN_H - 20)
        self._build_ui()
        self._setup_timers()
        self._fetch()

    def _apply_size(self, screen: QScreen):
        if screen == self._current_screen: return
        self._current_screen = screen
        self.setFixedSize(WIN_W, WIN_H)

    def _build_ui(self):
        root = QWidget(); root.setAttribute(Qt.WA_TranslucentBackground)
        self.setCentralWidget(root)
        vl = QVBoxLayout(root); vl.setContentsMargins(10,10,10,8); vl.setSpacing(0)

        # Title bar
        tbar = QWidget(); tbar.setAttribute(Qt.WA_TranslucentBackground); tbar.setFixedHeight(32)
        tl = QHBoxLayout(tbar); tl.setContentsMargins(10,0,6,0); tl.setSpacing(8)
        self._logo = QLabel("⬡")
        self._logo.setStyleSheet(f"color:{c('accent').name()};font-size:13px;background:transparent;")
        tl.addWidget(self._logo)
        self._title_lbl = QLabel("CURSOR  HUD")
        self._title_lbl.setStyleSheet(
            f"color:{c('t_bright').name()};font-family:'Segoe UI';font-size:10px;"
            "font-weight:700;letter-spacing:3px;background:transparent;"
        )
        tl.addWidget(self._title_lbl); tl.addStretch()
        self._win_btns: list[tuple[QPushButton, str | None]] = []
        for sym, slot, hc in [("─", self.showMinimized, None), ("✕", self.close, "#FF4660")]:
            btn = QPushButton(sym); btn.setFixedSize(22,22); btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(slot); mu = c("t_muted").name()
            btn.setStyleSheet(
                f"QPushButton{{color:{mu};background:transparent;border:none;font-size:11px;}}"
                f"QPushButton:hover{{color:{hc or c('t_bright').name()};}}"
            )
            tl.addWidget(btn)
            self._win_btns.append((btn, hc))
        vl.addWidget(tbar)

        self._nav = NavBar(self.settings)
        self._nav.tab_clicked.connect(self._switch_tab)
        vl.addWidget(self._nav); vl.addWidget(Divider())

        self._stack = QStackedWidget(); self._stack.setAttribute(Qt.WA_TranslucentBackground)
        self._pg_credits  = CreditsPage(self.settings)
        self._pg_profile  = ProfilePage(self.settings)
        self._pg_settings = SettingsPage(self.settings)
        self._pg_settings.changed.connect(self._on_settings_changed)
        self._pg_settings.theme_changed.connect(self._on_theme_changed)
        for pg in [self._pg_credits, self._pg_profile, self._pg_settings]:
            self._stack.addWidget(pg)
        vl.addWidget(self._stack, 1)

        vl.addWidget(Divider())
        self._status = StatusBar(self.settings)
        self._status.refresh_clicked.connect(self._fetch)
        self._status.debug_clicked.connect(self._show_debug)
        vl.addWidget(self._status)
        self._switch_tab(0)

    def _switch_tab(self, idx: int):
        self._stack.setCurrentIndex(idx); self._nav.set_active(idx)

    def _on_settings_changed(self):
        self._nav.refresh_labels()
        self._status.refresh_labels()
        self._pg_credits._rebuild_labels()
        self._pg_profile._rebuild_labels()
        if self._last_data:
            self._pg_credits.update_data(self._last_data)
            self._pg_profile.update_data(self._last_data)

    def _on_theme_changed(self, name: str):
        QApplication.instance().setStyleSheet(self._make_qss())
        # TitleBar
        self._logo.setStyleSheet(f"color:{c('accent').name()};font-size:13px;background:transparent;")
        self._title_lbl.setStyleSheet(
            f"color:{c('t_bright').name()};font-family:'Segoe UI';font-size:10px;"
            "font-weight:700;letter-spacing:3px;background:transparent;"
        )
        for btn, hc in self._win_btns:
            mu = c("t_muted").name()
            btn.setStyleSheet(
                f"QPushButton{{color:{mu};background:transparent;border:none;font-size:11px;}}"
                f"QPushButton:hover{{color:{hc or c('t_bright').name()};}}"
            )
        # Nav / StatusBar
        self._nav.refresh_theme(); self._status.refresh_theme()
        # Credits / Profile static colors
        self._pg_credits.refresh_theme()
        self._pg_profile.refresh_theme()
        self.update(); self.repaint()
        # Re-render data with new theme colors
        if self._last_data:
            self._pg_credits.update_data(self._last_data)
            self._pg_profile.update_data(self._last_data)

    def _make_qss(self) -> str:
        sb = TH()["scrollbar"]
        return f"""
            QScrollBar:vertical{{background:transparent;width:4px;margin:0;}}
            QScrollBar::handle:vertical{{background:{sb};border-radius:2px;min-height:20px;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}
            QToolTip{{background:#080A12;color:#E6F0FF;
            border:1px solid rgba(128,128,128,0.35);border-radius:4px;padding:4px;}}
        """

    def _setup_timers(self):
        t1 = QTimer(self); t1.timeout.connect(self._fetch); t1.start(REFRESH_MS)
        t2 = QTimer(self); t2.timeout.connect(self._tick);  t2.start(1000)
        # Show clock/countdown immediately (before first timer tick)
        self._status.set_clock(datetime.now().strftime("%H:%M:%S"))
        self._status.set_countdown(self._countdown)

    def _tick(self):
        self._countdown = max(0, self._countdown - 1)
        self._status.set_countdown(self._countdown)
        self._status.set_clock(datetime.now().strftime("%H:%M:%S"))

    def _fetch(self):
        if self._fetcher and self._fetcher.isRunning(): return
        if self._fetcher:
            try:
                self._fetcher.ready.disconnect(); self._fetcher.error.disconnect()
            except TypeError:
                pass
        self._countdown = REFRESH_MS // 1000
        self._status.set_countdown(self._countdown)
        self._status.set_status("loading")
        self._fetcher = DataFetcher()
        self._fetcher.ready.connect(self._on_data)
        self._fetcher.error.connect(self._on_error)
        self._fetcher.start()
        log.info("DataFetcher started")

    def _on_data(self, raw: dict):
        self._last_data = parse_data(raw)
        d = self._last_data
        self._pg_credits.update_data(d)
        self._pg_profile.update_data(d)
        self._pg_credits.set_error("")
        self._status.set_status("ok")
        log.info("data updated — budget %.1f%%", d["credit"]["budget_pct"])

    def _on_error(self, err: str):
        log.error("fetch error: %s", err)
        self._pg_credits.set_error(S(self.settings, "err_fetch"))
        self._status.set_status("error")

    def _show_debug(self):
        DebugDialog(self.settings, parent=self).exec_()

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

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self._drag_pos = e.globalPos() - self.pos()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, _): self._drag_pos = None

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
def main():
    if "--install-startup" in sys.argv:
        exe = str(Path(sys.executable if getattr(sys,"frozen",False) else sys.argv[0]).resolve())
        register_startup(exe); return
    if "--uninstall-startup" in sys.argv:
        unregister_startup(); return

    enable_dpi()
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps,    True)
    app = QApplication(sys.argv)
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
    if not db.exists():
        QMessageBox.critical(None, "CursorHUD",
            S(init_settings, "err_no_db") + str(db))
        sys.exit(1)

    win = HUDWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()