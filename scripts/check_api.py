#!/usr/bin/env python3
"""
check_api.py — Cursor API endpoint explorer using local session token.

Usage:
    python3 scripts/check_api.py
"""

import base64
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERROR] requests not installed: pip install requests")
    sys.exit(1)

BASE_URL = "https://cursor.com"

# GET endpoints — full response body printed
GET_ENDPOINTS = [
    ("/api/usage-summary",               "Usage Summary"),
    ("/api/auth/me",                     "Auth / Profile"),
    ("/api/organizations",               "Organizations list"),
    ("/api/teams",                       "Teams list"),
    ("/api/team",                        "Team (singular)"),
    ("/api/user/teams",                  "User → Teams"),
    ("/api/dashboard/teams",             "Dashboard Teams"),
    ("/api/dashboard/get-organization",  "Dashboard Organization"),
    ("/api/settings",                    "Settings"),
    ("/api/subscription",                "Subscription"),
]

# POST endpoints — payload printed alongside response
POST_ENDPOINTS = [
    ("/api/dashboard/get-team-spend",
     "Team Spend (no teamId — auto?)",
     {"pageSize": 5, "sortBy": "name", "startDate": 0, "endDate": 9999999999999}),
]


# ── token helpers ─────────────────────────────────────────────────────────────

def _cursor_db_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", ""))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    return base / "Cursor" / "User" / "globalStorage" / "state.vscdb"


def _decode_jwt(token: str) -> dict:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}


def read_token() -> tuple[str, str]:
    """Return (cookie_value, email). cookie_value is '' if not found."""
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
        sub = _decode_jwt(token).get("sub", "")
        uid = sub.split("|")[-1] if "|" in sub else sub
        return f"{uid}%3A%3A{token}", email
    except Exception as exc:
        print(f"[ERROR] reading token: {exc}")
        return "", ""
    finally:
        tmp.unlink(missing_ok=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def _print_result(tag: str, method: str, path: str, label: str,
                  status: int, body_raw: str, ok: bool):
    try:
        body = json.loads(body_raw)
        body_str = json.dumps(body, indent=2, ensure_ascii=False)
    except Exception:
        body_str = body_raw

    status_tag = "OK " if ok else "ERR"
    print(f"  [{status_tag}] {method} {path}")
    print(f"         {label}  (HTTP {status})")
    # Indent body for readability
    for line in body_str.splitlines():
        print(f"         {line}")
    print()


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Cursor API explorer  →  {BASE_URL}\n")

    cookie, email = read_token()
    db_path = _cursor_db_path()
    print(f"  DB path  : {db_path}")
    print(f"  DB exists: {db_path.exists()}")
    print(f"  Email    : {email or '(none)'}")
    print(f"  Token    : {'[OK]' if cookie else '[MISSING]'}")
    print()

    if not cookie:
        print("[ERROR] No session token found. Open Cursor IDE and try again.")
        sys.exit(1)

    headers = {
        "Cookie":  f"WorkosCursorSessionToken={cookie}",
        "Accept":  "application/json",
        "Origin":  "https://cursor.com",
        "Referer": "https://cursor.com/dashboard",
    }

    # GET endpoints
    print("=" * 60)
    print("  GET ENDPOINTS")
    print("=" * 60)
    print()
    for path, label in GET_ENDPOINTS:
        url = BASE_URL + path
        try:
            r = requests.get(url, headers=headers, timeout=10,
                             allow_redirects=False)
            _print_result("GET", "GET", path, label,
                          r.status_code, r.text, r.ok)
        except requests.exceptions.ConnectionError:
            print(f"  [ERR] GET {path}  — connection failed\n")
        except requests.exceptions.Timeout:
            print(f"  [ERR] GET {path}  — timeout\n")

    # POST endpoints
    print("=" * 60)
    print("  POST ENDPOINTS")
    print("=" * 60)
    print()
    post_hdrs = dict(headers)
    post_hdrs["content-type"] = "application/json"
    post_hdrs["origin"]       = "https://cursor.com"
    post_hdrs["referer"]      = "https://cursor.com/dashboard"
    for path, label, body in POST_ENDPOINTS:
        url = BASE_URL + path
        print(f"  payload: {json.dumps(body)}")
        try:
            r = requests.post(url, json=body, headers=post_hdrs,
                              timeout=10, allow_redirects=False)
            _print_result("POST", "POST", path, label,
                          r.status_code, r.text, r.ok)
        except requests.exceptions.ConnectionError:
            print(f"  [ERR] POST {path}  — connection failed\n")
        except requests.exceptions.Timeout:
            print(f"  [ERR] POST {path}  — timeout\n")


if __name__ == "__main__":
    main()
