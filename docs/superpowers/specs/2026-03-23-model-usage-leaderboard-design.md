# Model Usage & Leaderboard Tabs — Design Spec

**Date:** 2026-03-23
**Status:** Approved

---

## Goal

Replace the CSV-based model usage pipeline with a proper JSON API, add a new Leaderboard tab, and remove the now-obsolete CSV export feature. Both new/updated tabs are gated behind the existing `show_experimental` toggle.

---

## Scope

**In scope:**
- Replace `CsvFetcher` + `AnalyticsFetcher` with `UsageEventsFetcher` using `POST /api/dashboard/get-filtered-usage-events`
- New `LeaderboardFetcher` + `LeaderboardPage` using `GET /api/v2/analytics/team/leaderboard`
- Remove CSV export button from Credits tab and all CSV-related code
- Remove `csv_team_id` settings field (teamId not required with session token)
- New Leaderboard nav tab (experimental, gated)

**Out of scope:**
- Date range picker (billing cycle dates used automatically)
- Pagination beyond `pageSize: 500` (confirmed sufficient for current usage volume)
- Profile picture display in Leaderboard

---

## API Contracts

### Usage Events (Analytics tab)

```
POST https://cursor.com/api/dashboard/get-filtered-usage-events
Cookie: WorkosCursorSessionToken=<token>
Content-Type: application/json
Origin: https://cursor.com

Body: {"startDate": <epoch_ms>, "endDate": <epoch_ms>, "pageSize": 500}
```

Response shape:
```json
{
  "totalUsageEventsCount": 351,
  "usageEventsDisplay": [
    {
      "timestamp": "1774259833170",
      "model": "premium:gpt-5.3-codex",
      "kind": "USAGE_EVENT_KIND_USAGE_BASED",
      "chargedCents": 28.77,
      "tokenUsage": {
        "inputTokens": 111161,
        "outputTokens": 938,
        "cacheReadTokens": 122368,
        "totalCents": 22.91
      },
      "owningUser": "313946729",
      "owningTeam": "14707113",
      "isChargeable": true
    }
  ]
}
```

Cost field priority: `chargedCents` → fallback to `tokenUsage.totalCents` → 0. Both fields are floats; accumulate as float throughout (no integer truncation until display).

### Leaderboard

```
GET https://cursor.com/api/v2/analytics/team/leaderboard
Cookie: WorkosCursorSessionToken=<token>
Content-Type: application/json
Origin: https://cursor.com

Body: {"startDate": <epoch_ms>, "endDate": <epoch_ms>}
```

Response shape:
```json
{
  "tab_leaderboard": {
    "data": [
      {
        "rank": 1,
        "display_name": "Taehyeong Gu",
        "email": "...",
        "user_id": 276154486,
        "total_tab_accepts": 128,
        "total_tab_lines_accepted": 279,
        "total_tab_lines_suggested": 1286,
        "tab_accept_ratio": 0.240,
        "favorite_model": "claude-4.6-sonnet-medium-thinking",
        "profile_picture_url": null
      }
    ],
    "total_users": 14
  },
  "composer_leaderboard": {
    "data": [
      {
        "rank": 1,
        "display_name": "Taehyeong Gu",
        "email": "...",
        "user_id": 276154486,
        "total_diff_accepts": 178,
        "total_composer_lines_accepted": 8041,
        "total_composer_lines_suggested": 5130,
        "composer_line_acceptance_ratio": 1.567,
        "favorite_model": "claude-4.6-sonnet-medium-thinking",
        "profile_picture_url": null
      }
    ],
    "total_users": 14
  }
}
```

---

## Architecture

### Removed

| Item | Reason |
|---|---|
| `CsvFetcher` class | CSV export feature removed entirely |
| `AnalyticsFetcher` class | Replaced by `UsageEventsFetcher` |
| CSV export button + handler in `CreditsPage` | Feature removed |
| `set_experimental_visible` in `CreditsPage` | Method becomes no-op after CSV button removal — delete it; remove call site in `HUDWindow._on_settings_changed` |
| `set_analytics_visible` in `NavBar` | Renamed to `set_experimental_visible`; covers both Analytics + Leaderboard tabs |
| `csv_team_id` input field + label in `SettingsPage` | teamId not required |
| `_on_team_id_edited` in `SettingsPage` | No longer needed |
| `export_csv_clicked` signal in `CreditsPage` | No longer needed |
| `_on_export_csv`, `_on_csv_ready`, `_on_csv_error` in `HUDWindow` | No longer needed |
| `_csv_fetcher` reference in `HUDWindow` | No longer needed |
| All `csv_*` STRINGS entries | No uses remain |
| `analytics_no_team_id` STRINGS entry | teamId no longer required |
| `csv_team_id` key in `DEFAULT_SETTINGS` | No longer needed |

### New: `UsageEventsFetcher(QThread)`

Replaces `AnalyticsFetcher`. Same signal interface for zero UI changes.

```python
class UsageEventsFetcher(QThread):
    ready = pyqtSignal(dict)   # {"model_usage": dict, "total_events": int}
    error = pyqtSignal(str)

    def __init__(self, start_ms: int, end_ms: int):
        ...
```

**Run sequence:**
1. Read `WorkosCursorSessionToken` via `read_cursor_token()`
2. POST to `get-filtered-usage-events` with `{"startDate": start_ms, "endDate": end_ms, "pageSize": 500}`
3. Aggregate `usageEventsDisplay` by `model`:
   ```python
   cost = event.get("chargedCents") or (event.get("tokenUsage") or {}).get("totalCents", 0) or 0
   entry["count"] += 1
   entry["cost_cents"] += cost
   ```
4. Emit `ready({"model_usage": model_agg, "total_events": totalUsageEventsCount})`

No teamId parameter. Constructor signature drops `team_id` and `is_enterprise`.

### Updated: `AnalyticsPage`

- Replace "Loading…" with total events count in header badge: `"N events"`
- All other UI unchanged (pie chart, legend rows, refresh button, cycle label)

### New: `LeaderboardFetcher(QThread)`

```python
class LeaderboardFetcher(QThread):
    ready = pyqtSignal(dict)   # {"tab": list, "composer": list, "total_users": int}
    error = pyqtSignal(str)

    def __init__(self, start_ms: int, end_ms: int):
        ...
```

**Run sequence:**
1. Read `WorkosCursorSessionToken`
2. `requests.get(url, json={"startDate": ms, "endDate": ms}, headers=hdrs, timeout=30)` — note: GET with JSON body (confirmed working via curl test; `requests` sends it via `json=` kwarg which sets Content-Type and body correctly)
3. Parse `tab_leaderboard.data` and `composer_leaderboard.data`
4. `total_users` taken from `tab_leaderboard.total_users` (both sub-objects return the same value; if they differ, take `max`)
5. Emit `ready({"tab": [...], "composer": [...], "total_users": N})`

### New: `LeaderboardPage(QWidget)`

Implements `refresh_theme()` and `refresh_labels()`.

**Layout:**
```
┌─ Leaderboard ──────────────────── ↻ Refresh ─┐
│  Billing cycle: Feb 28 – Mar 28  · 14 members │
│                                               │
│  [  Tab  ] [  Composer  ]   ← toggle buttons  │
│                                               │
│  #  Name            Accepts  Ratio  Model     │
│  1  Taehyeong Gu     128     24%    claude…   │
│  2  Woosuk Kim       265     11%    gpt…      │
│  …  (0-activity members at 50% opacity)       │
└───────────────────────────────────────────────┘
```

**Toggle:** Two `QPushButton(checkable=True)` styled like nav tabs. Only one active at a time. Switching shows/hides the corresponding `QWidget` container (no re-fetch).

**Tab leaderboard columns:** rank · display_name · total_tab_accepts · tab_accept_ratio (%) · favorite_model

**Composer leaderboard columns:** rank · display_name · total_diff_accepts · composer_line_acceptance_ratio (%) · favorite_model

**States:** Loading → data rows | No data | Error (same pattern as `AnalyticsPage`)

**Zero-activity rows:** opacity 0.5. Threshold: `total_tab_accepts == 0` for Tab rows; `total_diff_accepts == 0` for Composer rows.

---

## Nav Structure

```
Credits(0) | Analytics(1) | Leaderboard(2) | Profile(3) | Settings(4)
```

`NavBar.TABS` updated to include `"nav_leaderboard"`. Both Analytics(1) and Leaderboard(2) hidden when `show_experimental=False`.

`NavBar` exposes `set_experimental_visible(bool)` (replaces `set_analytics_visible`): shows/hides both experimental tabs together.

If user disables experimental while on tab 1 or 2: switch to tab 0.

Keyboard shortcuts: Ctrl+1…Ctrl+5 for all five tabs.

---

## `HUDWindow` Wiring

**Stack insertion order** (must preserve indices):
```
addWidget(_pg_credits)     # index 0
addWidget(_pg_analytics)   # index 1
addWidget(_pg_leaderboard) # index 2  ← new, inserted here
addWidget(_pg_profile)     # index 3  (was 2)
addWidget(_pg_settings)    # index 4  (was 3)
```

**New state fields:**
- `_leaderboard_fetcher: LeaderboardFetcher | None = None`
- `_leaderboard_data: dict | None = None`
- `_leaderboard_pending: bool = False`

**`_switch_tab(idx)`:** guard for both experimental tabs:
```python
if idx in (1, 2) and not self.settings.get("show_experimental", False):
    return
```

**`_on_settings_changed()`:** when experimental toggled off, reset both tabs:
```python
if not value:  # show_experimental turned off
    if self._stack.currentIndex() in (1, 2):
        self._switch_tab(0)
    # analytics reset — use existing teardown pattern: blockSignals+quit+wait+deleteLater
    self._analytics_data = None
    self._analytics_pending = False
    if self._analytics_fetcher:
        self._analytics_fetcher.blockSignals(True)
        self._analytics_fetcher.quit()
        self._analytics_fetcher.wait(2000)
        self._analytics_fetcher.deleteLater()
        self._analytics_fetcher = None
    # leaderboard reset — same pattern
    self._leaderboard_data = None
    self._leaderboard_pending = False
    if self._leaderboard_fetcher:
        self._leaderboard_fetcher.blockSignals(True)
        self._leaderboard_fetcher.quit()
        self._leaderboard_fetcher.wait(2000)
        self._leaderboard_fetcher.deleteLater()
        self._leaderboard_fetcher = None
```
Also update the `self._nav.set_analytics_visible(show_exp)` call → `self._nav.set_experimental_visible(show_exp)` in this method.

**`_on_theme_changed()`:** add `self._pg_leaderboard.refresh_theme()`

**`_on_settings_changed()`:** add `self._pg_leaderboard.refresh_labels()` alongside other page refresh calls

**`_trigger_analytics_fetch()`:** remove the `team_id`/`is_enterprise` extraction block; `UsageEventsFetcher` takes only `start_ms, end_ms`.

**`_on_data()`:** if `_leaderboard_pending`, trigger leaderboard fetch

**Leaderboard refresh button** → `_trigger_leaderboard_fetch(force=True)`

**Keyboard shortcuts:** `_setup_shortcuts` gains `Ctrl+5` → `_switch_tab(4)` (Settings). Existing Ctrl+1–4 remain unchanged (Ctrl+3 now → Leaderboard(2), Ctrl+4 now → Profile(3)).

---

## i18n Strings

### Added
```python
# ko                                         # en
"nav_leaderboard":       "리더보드",          "Leaderboard"
"leaderboard_refresh":   "새로고침",           "Refresh"
"leaderboard_loading":   "불러오는 중…",       "Loading…"
"leaderboard_waiting":   "데이터 대기 중…",    "Waiting for data…"
"leaderboard_error":     "불러오기 실패",       "Failed to load"
"leaderboard_no_data":   "데이터 없음",        "No data"
"leaderboard_tab":       "탭",               "Tab"
"leaderboard_composer":  "컴포저",            "Composer"
"leaderboard_members":   "명",               "members"
"leaderboard_cycle_label": "청구 주기",        "Billing cycle"
"analytics_events_badge": "{n}건",           "{n} events"
```

### Removed
All `csv_*` keys + `analytics_no_team_id`

---

## Files Modified

- **`cursor_hud.py`** only (single-file convention)
  - `STRINGS`: add leaderboard entries, remove csv/team_id entries
  - `DEFAULT_SETTINGS`: remove `csv_team_id` key
  - Remove `CsvFetcher` class
  - Replace `AnalyticsFetcher` with `UsageEventsFetcher` (drop teamId/isEnterprise params)
  - Add `LeaderboardFetcher` class
  - `AnalyticsPage`: update event badge display
  - Add `LeaderboardPage` class
  - `CreditsPage`: remove CSV export button, signal, related controls
  - `SettingsPage`: remove `csv_team_id` input field; rename `set_analytics_visible` → `set_experimental_visible` to cover both tabs
  - `NavBar`: add `nav_leaderboard` tab; rename `set_analytics_visible` → `set_experimental_visible`
  - `HUDWindow`: wire `LeaderboardPage` + `LeaderboardFetcher`; remove all `_csv_*` references; Ctrl+5 shortcut
