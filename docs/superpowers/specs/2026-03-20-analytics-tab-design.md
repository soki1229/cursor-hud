# Analytics Tab — Design Spec

**Date:** 2026-03-20
**Status:** Approved

---

## Goal

Add an **Analytics** tab to the HUD that surfaces team and personal usage data using session-token-accessible APIs. The tab is gated behind the existing `show_experimental` toggle.

---

## Scope

**In scope:**
- New `AnalyticsPage` widget with 2 flat sections (section header + list, consistent with Credits tab pattern)
- New `AnalyticsFetcher(QThread)` for on-demand fetching
- NavBar optional 4th tab, visible only when `show_experimental=True`
- Refresh button + billing cycle label in tab header

**Out of scope:**
- Admin/Analytics API (`api.cursor.com/analytics/*`) — requires separate Enterprise API key
- Per-event usage table — CSV used only for model cost aggregation (streamed, not stored)
- Date range picker — all data uses the current billing cycle automatically

---

## Data Sources

All accessible via `WorkosCursorSessionToken` cookie (session token from local Cursor DB).

| Section | Endpoint | HTTP | Notes |
|---|---|---|---|
| Team Spend | `cursor.com/api/dashboard/get-team-spend` | POST + JSON body | Requires `teamId`; uses `origin` + `referer` headers |
| Model Usage | `cursor.com/api/dashboard/export-usage-events-csv` | **GET + query params** (matches existing `CsvFetcher`) | Streamed line-by-line; aggregated into dict |

### get-team-spend request body
```json
{
  "teamId": 14707113,
  "pageSize": 5000,
  "sortBy": "name",
  "sortDirection": "asc",
  "page": 1
}
```
Required headers: `content-type: application/json`, `origin: https://cursor.com`, `referer: https://cursor.com/dashboard`.

### get-team-spend response shape
```json
{
  "teamMemberSpend": [
    {
      "userId": 313946729,
      "name": "Woosuk Kim",
      "email": "...",
      "role": "TEAM_ROLE_MEMBER",
      "spendCents": 7529,
      "includedSpendCents": 8034
    }
  ],
  "totalMembers": 17,
  "subscriptionCycleStart": "1772287928000",
  "nextCycleStart": "1774707128000"
}
```
Members without spend have no `spendCents` key (treat as 0).

### CSV GET query params (same as existing `CsvFetcher`)
```python
params = {
    "isEnterprise": "true" | "false",
    "startDate":    start_ms,   # epoch ms
    "endDate":      end_ms,     # epoch ms
    "strategy":     "tokens",
}
if team_id:
    params["teamId"] = team_id
```
CSV columns: `Date,User,Kind,Model,Max Mode,Input (w/ Cache Write),Input (w/o Cache Write),Cache Read,Output Tokens,Total Tokens,Cost`

---

## Architecture

### `AnalyticsFetcher(QThread)`

Dedicated thread. Triggered by:
1. User switches to the Analytics tab (if `_analytics_data` is `None`)
2. User clicks Refresh button (always re-fetches)

**Constructor:** `AnalyticsFetcher(team_id, start_ms, end_ms, is_enterprise)`

**Run sequence:**
1. `POST get-team-spend` → parse JSON
2. `GET export-usage-events-csv` with `stream=True` → iterate `response.iter_lines()` in a `with` block to ensure connection is closed; skip header row; accumulate `{model: {"count": int, "cost_cents": int}}`; never store full CSV text

**Signals:**
- `ready(dict)` — emits `{"team_spend": list[dict], "model_usage": dict}`
- `error(str)` — error message

**Billing cycle date source:**
Dates come from `d["cycle"]["start"]` and `d["cycle"]["end"]` (from `parse_data()`), converted via existing `_date_to_ms()`.

**Race condition guard:** If `DataFetcher` has not yet completed when the Analytics tab is first shown, `AnalyticsPage` displays a "Waiting for billing data…" message and defers the fetch until `HUDWindow._on_data()` fires and passes the billing dates.

**CSV streaming — connection safety:**
```python
with requests.get(url, params=params, headers=hdrs,
                  stream=True, timeout=30) as r:
    for line in r.iter_lines():
        ...  # aggregate only
# connection closed automatically on exit
```

### `AnalyticsPage(QWidget)`

Top-level page widget. Implements `refresh_theme()` and `refresh_labels()`.

Layout follows the same pattern as `CreditsPage` — `section_hdr()` labels followed by content rows, stacked in a `QVBoxLayout` inside a `QScrollArea`.

```
┌─ Analytics ─────────────────────── ↻ Refresh ─┐
│  Billing cycle: Feb 28 – Mar 28                │
├────────────────────────────────────────────────┤
│  TEAM SPEND                    17 · $156.70    │  ← section_hdr()
│  Woosuk Kim ──────────────────────── $75.28    │
│  Simon Balicki ────────────────────── $0.00    │
│  …                                             │
│                                                │
│  MODEL USAGE                                   │  ← section_hdr()
│  claude-3.5-sonnet  ████████░░  68%   $52.40  │
│  claude-3-opus      ███░░░░░░░  18%   $14.80  │
│  …                                             │
└────────────────────────────────────────────────┘
```

**States per section:** "Loading…" label while fetching → data rows | "No data" | error text

## Section Details

### ① Team Spend

**Header badge:** `"{N} {members_str} · ${total:.2f}"`

**Rows:** sorted by `spendCents` descending; zero-spend members shown at 50% opacity.

**Scroll:** `QScrollArea` inside body, max visible height ~160px (~8 rows).

**No-team edge case:** if `team_id` is empty AND auto-detect from `d["team_id"]` also fails, show inline message using `analytics_no_team_id` string instead of the member list. (Mirrors existing `csv_err_no_team` behavior.)

---

### ② Model Usage

**Aggregation (in `AnalyticsFetcher`):**
```python
model_agg: dict[str, dict] = {}
for line in r.iter_lines():
    if header_row: continue
    cols = line.decode().split(",")
    model = cols[3].strip()
    cost_str = cols[-1].strip().lstrip("$")
    cost_cents = int(round(float(cost_str or "0") * 100))
    entry = model_agg.setdefault(model, {"count": 0, "cost_cents": 0})
    entry["count"] += 1
    entry["cost_cents"] += cost_cents
```

**Display:** sorted by `cost_cents` descending.

Each row:
```
model_name    ████████░░░   68%   $52.40
```
- Progress bar: `cost_cents / max_cost_cents`; accent color
- Opacity by rank: rank 0 → 1.0, scaled linearly down to 0.4 for last item
- `XX%` ratio of total cost
- `$XX.XX` right-aligned

**Empty state:** show `analytics_no_data` string.

---

## NavBar Integration

`NavBar.TABS` remains `["nav_credit", "nav_profile", "nav_settings"]` for the always-visible tabs. The Analytics tab is a separate optional button appended/shown conditionally.

**Implementation approach:** add a 4th button `self._analytics_btn` in `NavBar.__init__()` using the same style as other tab buttons. Call `self._analytics_btn.setVisible(settings.get("show_experimental", False))` at init. Expose `set_analytics_visible(bool)` method.

**`HUDWindow` wiring:**
- `_build_ui`: add `AnalyticsPage` to the stacked layout at index 3
- `_switch_tab(3)`: show `AnalyticsPage`, trigger `AnalyticsFetcher` if needed
- `Ctrl+4` shortcut: same pattern as existing `Ctrl+1`–`Ctrl+3`
- `SettingsPage` `show_experimental` toggle: call `self._nav.set_analytics_visible(value)` and hide Analytics page if switching off while on tab 3

**`refresh_theme()`:** `HUDWindow.refresh_theme()` calls `self._pg_analytics.refresh_theme()`

---

## i18n Strings

```python
# ko                                    # en
"nav_analytics":        "분석",          "Analytics"
"analytics_refresh":    "새로고침",       "Refresh"
"analytics_loading":    "불러오는 중…",   "Loading…"
"analytics_waiting":    "데이터 대기 중…","Waiting for data…"
"analytics_error":      "불러오기 실패",  "Failed to load"
"analytics_no_data":    "데이터 없음",    "No data"
"analytics_no_team_id": "팀 ID 없음 — 설정에서 입력하세요",
                                         "No team ID — enter in Settings"
"analytics_team_spend": "팀 지출",        "Team Spend"
"analytics_model_usage":"모델 사용량",    "Model Usage"
"analytics_cycle_label":"청구 주기",      "Billing cycle"
"analytics_members":    "명",             "members"
```

---

## Experimental Gate

- `NavBar._analytics_btn` hidden when `show_experimental=False`
- `AnalyticsFetcher` not started when Analytics tab is not visible
- If user disables experimental while on tab 3: switch to tab 0 (Credits), then hide the Analytics button
- Consistent with existing `set_experimental_visible()` pattern in `CreditsPage`

---

## Files Modified

- **`cursor_hud.py`** only (single-file convention)
  - `STRINGS`: add i18n entries above
  - `AnalyticsFetcher`: new `QThread` after `CsvFetcher` (~line 686)
  - `AnalyticsPage`: new page class after `SettingsPage`
  - `NavBar`: add `_analytics_btn` + `set_analytics_visible()`
  - `HUDWindow._build_ui`: wire `AnalyticsPage` + index 3
  - `HUDWindow._switch_tab`: handle idx 3, trigger fetch
  - `HUDWindow._on_data`: pass billing dates to `AnalyticsPage` if deferred
  - `HUDWindow.refresh_theme`: add `self._pg_analytics.refresh_theme()`
  - `SettingsPage`: call `set_analytics_visible` on `show_experimental` toggle
  - `Ctrl+4` keyboard shortcut

