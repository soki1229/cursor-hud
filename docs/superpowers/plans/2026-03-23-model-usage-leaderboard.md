# Model Usage & Leaderboard Tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace CSV-based Analytics with a JSON API fetcher, add a Leaderboard tab with Tab/Composer sub-toggle, and remove all CSV export code.

**Architecture:** All changes are in `cursor_hud.py` (single-file convention). Tasks flow top-to-bottom: delete dead code first, then replace the Analytics fetcher, then add Leaderboard, then wire nav/HUDWindow. Each task is independently testable by running `python cursor_hud.py --mock` and verifying UI.

**Tech Stack:** Python 3.10+, PyQt5, requests, single-file `cursor_hud.py` (~2800 lines)

---

## Pre-flight

- [ ] **Confirm app launches before touching anything**

  ```bash
  cd /Users/soki/dev/personal/cursor-hud
  python cursor_hud.py --mock
  ```
  Expected: window opens, Credits tab visible. Close it.

---

### Task 1: Remove CSV export from CreditsPage and HUDWindow

**Files:**
- Modify: `cursor_hud.py` — `CreditsPage` (~line 1591), `HUDWindow._build_ui` (~line 2919), `HUDWindow._on_export_csv` (~line 3155), `HUDWindow._on_csv_ready/error` (~line 3203)

- [ ] **Step 1: Remove `export_csv_clicked` signal and `_csv_container` block from `CreditsPage.__init__`**

  Delete lines 1591–1618 (the entire "CSV export row" block):
  ```python
  # DELETE this entire block:
  # CSV export row — small muted action link at the bottom of the scroll area
  export_row = QWidget()
  ...
  vl.addWidget(self._csv_container)
  ```
  Also delete `export_csv_clicked = pyqtSignal()` from the `CreditsPage` class-level signals (find it just above `__init__`).

- [ ] **Step 2: Remove `_csv_btn` reference from `CreditsPage._rebuild_labels`**

  Find and delete this line (~line 1633):
  ```python
  self._csv_btn.setText(self.T("csv_export"))
  ```

- [ ] **Step 3: Delete `CreditsPage.set_experimental_visible` method**

  Delete (~lines 1635–1637):
  ```python
  def set_experimental_visible(self, visible: bool) -> None:
      """Show/hide CSV export controls (gated by Experimental toggle)."""
      self._csv_container.setVisible(visible)
  ```

- [ ] **Step 4: Remove CSV wiring in `HUDWindow._build_ui`**

  Delete these two lines (~lines 2919–2920):
  ```python
  self._pg_credits.export_csv_clicked.connect(self._on_export_csv)
  self._csv_fetcher: CsvFetcher | None = None
  ```

- [ ] **Step 5: Delete `_on_export_csv`, `_on_csv_ready`, `_on_csv_error` from `HUDWindow`**

  Delete the three methods at ~lines 3155–3221 (everything from `def _on_export_csv` through `_on_csv_error`).

- [ ] **Step 6: Remove CSV call site in `HUDWindow._on_settings_changed`**

  Delete these two lines (~lines 3031–3032):
  ```python
  show_exp = cfg.get("show_experimental", False)
  self._pg_credits.set_experimental_visible(show_exp)
  ```
  Keep the `show_exp` variable — it is still needed for `set_analytics_visible` call below it. Replace the deleted pair with just:
  ```python
  show_exp = cfg.get("show_experimental", False)
  ```

- [ ] **Step 7: Verify the app still launches**

  ```bash
  python cursor_hud.py --mock
  ```
  Expected: Credits tab opens, no CSV button visible anywhere, no Python errors in terminal.

- [ ] **Step 8: Commit**

  ```bash
  git add cursor_hud.py
  git commit -m "refactor: remove CSV export feature from CreditsPage and HUDWindow"
  ```

---

### Task 2: Remove `CsvFetcher` and `AnalyticsFetcher` classes

**Files:**
- Modify: `cursor_hud.py` — lines ~660–792 (the two fetcher classes)

- [ ] **Step 1: Delete the `CsvFetcher` class**

  Delete lines ~671–712 (entire `class CsvFetcher(QThread):` including its `run` method).

- [ ] **Step 2: Delete the `AnalyticsFetcher` class**

  Delete lines ~715–792 (entire `class AnalyticsFetcher(QThread):` including its `run` method).

  Leave the `# ══ CSV FETCHER` banner and `_date_to_ms` helper above them intact — both are still needed.

- [ ] **Step 3: Verify no NameError at import time**

  ```bash
  python -c "import cursor_hud"
  ```
  Expected: no output (no errors). If you see `NameError: name 'CsvFetcher' is not defined` you missed a reference — grep for it.

- [ ] **Step 4: Commit**

  ```bash
  git add cursor_hud.py
  git commit -m "refactor: delete CsvFetcher and AnalyticsFetcher classes"
  ```

---

### Task 3: Remove CSV strings, settings key, and SettingsPage CSV field

**Files:**
- Modify: `cursor_hud.py` — `STRINGS` (~line 311), `DEFAULT_SETTINGS` (~line 394), `SettingsPage` (~line 2062)

- [ ] **Step 1: Remove all `csv_*` and `analytics_no_team_id` keys from STRINGS**

  In the `"ko"` dict, delete these entries (lines ~311–315, 325):
  ```python
  "csv_export": "CSV 내보내기", "csv_save_title": "사용 이벤트 CSV 저장",
  "csv_err_no_team": "팀 ID를 찾을 수 없습니다. 설정에서 직접 입력해 주세요.",
  "csv_err_fetch": "CSV 다운로드 실패", "csv_saved": "저장 완료",
  "csv_team_id_label": "팀 ID (CSV 내보내기)",
  "csv_team_id_placeholder": "선택 사항 — 비워두면 개인 데이터",
  "analytics_no_team_id": "팀 ID 없음 — 설정에서 입력하세요",
  ```

  In the `"en"` dict, delete (~lines 367–371, 381):
  ```python
  "csv_export": "Export CSV", "csv_save_title": "Save Usage Events CSV",
  "csv_err_no_team": "Team ID not found. Enter it manually in Settings.",
  "csv_err_fetch": "CSV download failed", "csv_saved": "Saved",
  "csv_team_id_label": "Team ID (CSV export)",
  "csv_team_id_placeholder": "optional — blank = personal data",
  "analytics_no_team_id": "No team ID — enter in Settings",
  ```

- [ ] **Step 2: Remove `csv_team_id` from DEFAULT_SETTINGS**

  Delete line ~394:
  ```python
  "csv_team_id": "",        # override for CSV export teamId (empty = auto-detect)
  ```

- [ ] **Step 3: Remove `csv_team_id` field from SettingsPage**

  In `SettingsPage.__init__`, delete the entire block that creates `self._t["csv_team_id_label"]` and `self._team_id_input` (~lines 2062–2076):
  ```python
  # DELETE:
  self._t["csv_team_id_label"] = ql(self.T("csv_team_id_label"), 9, c("t_body"))
  _edl.addWidget(self._t["csv_team_id_label"])

  self._team_id_input = QLineEdit()
  ...
  self._team_id_input.editingFinished.connect(self._on_team_id_edited)
  _edl.addWidget(self._team_id_input)
  ```

  Also delete the `_on_team_id_edited` method (~lines 2131–2135):
  ```python
  def _on_team_id_edited(self):
      val = self._team_id_input.text().strip()
      self.settings["csv_team_id"] = val
      save_settings(self.settings)
      log.info("csv_team_id set to: %s", val or "(auto-detect)")
  ```

  Also delete the `refresh_theme` block that updates `_team_id_input` (~lines 2183–2190):
  ```python
  if hasattr(self, "_team_id_input"):
      self._team_id_input.setStyleSheet(...)
  ```

- [ ] **Step 4: Also remove `import csv as _csv` if no longer used**

  Grep for `_csv` usage:
  ```bash
  grep -n "_csv" cursor_hud.py | grep -v "^.*#"
  ```
  If only the now-deleted fetchers used it, delete line 22: `import csv as _csv`

  Also check `QLineEdit` in imports — if SettingsPage was its only use site, remove it from the PyQt5 import line. (Check with `grep -n "QLineEdit" cursor_hud.py`.)

- [ ] **Step 5: Verify**

  ```bash
  python cursor_hud.py --mock
  ```
  Expected: Settings tab → Experimental section has no "Team ID" field.

- [ ] **Step 6: Commit**

  ```bash
  git add cursor_hud.py
  git commit -m "refactor: remove csv_team_id setting, strings, and SettingsPage field"
  ```

---

### Task 4: Add `UsageEventsFetcher` (replaces `AnalyticsFetcher`)

**Files:**
- Modify: `cursor_hud.py` — after the `# ══ CSV FETCHER` banner (~line 660)

- [ ] **Step 1: Add `UsageEventsFetcher` class after `_date_to_ms`**

  Insert after `_date_to_ms` function (~line 668), before `# ══ HELPERS` banner:

  ```python
  class UsageEventsFetcher(QThread):
      """Fetch model usage via POST /api/dashboard/get-filtered-usage-events.

      Emits ready(dict) with keys:
        "model_usage"  : dict  — {model_name: {"count": int, "cost_cents": float}}
        "total_events" : int   — totalUsageEventsCount from response
      """
      ready = pyqtSignal(dict)
      error = pyqtSignal(str)

      def __init__(self, start_ms: int, end_ms: int):
          super().__init__()
          self._start_ms = start_ms
          self._end_ms   = end_ms

      def run(self):
          try:
              cookie, _ = read_cursor_token()
              if not cookie:
                  self.error.emit("No auth token found.")
                  return
              hdrs = api_headers(cookie)
              body = {
                  "startDate": self._start_ms,
                  "endDate":   self._end_ms,
                  "pageSize":  500,
              }
              r = requests.post(
                  f"{BASE_URL}/api/dashboard/get-filtered-usage-events",
                  json=body, headers=hdrs, timeout=30,
              )
              log.info("UsageEventsFetcher → HTTP %s", r.status_code)
              if not r.ok:
                  self.error.emit(f"HTTP {r.status_code}: {r.text[:120]}")
                  return
              data = r.json()
              events = data.get("usageEventsDisplay", [])
              total  = data.get("totalUsageEventsCount", len(events))
              model_agg: dict[str, dict] = {}
              for event in events:
                  model = event.get("model", "").strip()
                  if not model:
                      continue
                  cost = (
                      event.get("chargedCents")
                      or (event.get("tokenUsage") or {}).get("totalCents", 0)
                      or 0.0
                  )
                  entry = model_agg.setdefault(model, {"count": 0, "cost_cents": 0.0})
                  entry["count"]      += 1
                  entry["cost_cents"] += float(cost)
              log.info("UsageEventsFetcher done — %d models, %d events",
                       len(model_agg), total)
              self.ready.emit({"model_usage": model_agg, "total_events": total})
          except Exception:
              log.exception("UsageEventsFetcher.run")
              self.error.emit("Request failed — see log for details.")
  ```

- [ ] **Step 2: Update `HUDWindow` to use `UsageEventsFetcher`**

  In `HUDWindow._build_ui` (~line 2921), change:
  ```python
  self._analytics_fetcher: AnalyticsFetcher | None = None
  ```
  to:
  ```python
  self._analytics_fetcher: UsageEventsFetcher | None = None
  ```

  In `HUDWindow._trigger_analytics_fetch`, replace the entire body after `self._analytics_pending = False` with:
  ```python
  self._analytics_pending = False
  d = self._last_data
  cyc      = d["cycle"]
  start_ms = _date_to_ms(cyc["start"])
  end_ms   = _date_to_ms(cyc["end"])
  self._pg_analytics.set_cycle_label(cyc["start"], cyc["end"])

  if not force and self._analytics_data is not None:
      return
  if self._analytics_fetcher:
      self._analytics_fetcher.blockSignals(True)
      self._analytics_fetcher.quit()
      self._analytics_fetcher.wait(2000)
      self._analytics_fetcher.deleteLater()
      self._analytics_fetcher = None
  self._pg_analytics.show_loading()
  self._analytics_fetcher = UsageEventsFetcher(start_ms, end_ms)
  self._analytics_fetcher.ready.connect(self._on_analytics_data)
  self._analytics_fetcher.error.connect(self._on_analytics_error)
  self._analytics_fetcher.start()
  log.debug("UsageEventsFetcher started")
  ```

- [ ] **Step 3: Update `_on_analytics_data` log message**

  Change (~line 3014):
  ```python
  log.info("AnalyticsFetcher data received — %d models",
  ```
  to:
  ```python
  log.info("UsageEventsFetcher data received — %d models, %d events",
           len(data.get("model_usage", {})), data.get("total_events", 0))
  ```

- [ ] **Step 4: Update `AnalyticsPage.update_data` to display event count badge**

  In `AnalyticsPage`, the `update_data` method currently calls `_update_model_usage(data.get("model_usage", {}))`. Extend it to also show the total event count in the cycle label area.

  Add a helper method to `AnalyticsPage` (right after `update_data`):
  ```python
  def _update_events_badge(self, total_events: int):
      """Append event count to the cycle label."""
      if not total_events:
          return
      lang = self.settings.get("lang", "en")
      tmpl = STRINGS.get(lang, STRINGS["en"]).get(
          "analytics_events_badge", "{n} events")
      badge = tmpl.replace("{n}", str(total_events))
      existing = self._cycle_lbl.text()
      # Append badge only if not already appended
      if badge not in existing:
          self._cycle_lbl.setText(f"{existing}  ·  {badge}" if existing else badge)
  ```

  Then update `update_data`:
  ```python
  def update_data(self, data: dict):
      """Populate model usage section from UsageEventsFetcher ready() payload."""
      self._update_model_usage(data.get("model_usage", {}))
      self._update_events_badge(data.get("total_events", 0))
  ```

- [ ] **Step 4: Verify Analytics tab loads**

  ```bash
  python cursor_hud.py --mock
  ```
  Enable Experimental in Settings, click Analytics tab. Expected: shows "Loading…" then either data or a graceful error (since mock doesn't hit real API). No Python errors.

- [ ] **Step 5: Commit**

  ```bash
  git add cursor_hud.py
  git commit -m "feat: replace AnalyticsFetcher with UsageEventsFetcher (JSON API)"
  ```

---

### Task 5: Add leaderboard i18n strings

**Files:**
- Modify: `cursor_hud.py` — `STRINGS` dict (~line 319 for ko, ~line 375 for en)

- [ ] **Step 1: Add leaderboard strings to `"ko"` dict**

  After `"nav_analytics": "분석",` add:
  ```python
  "nav_leaderboard":        "리더보드",
  "leaderboard_refresh":    "새로고침",
  "leaderboard_loading":    "불러오는 중…",
  "leaderboard_waiting":    "데이터 대기 중…",
  "leaderboard_error":      "불러오기 실패",
  "leaderboard_no_data":    "데이터 없음",
  "leaderboard_tab":        "탭",
  "leaderboard_composer":   "컴포저",
  "leaderboard_members":    "명",
  "leaderboard_cycle_label":"청구 주기",
  "analytics_events_badge": "{n}건",
  ```

- [ ] **Step 2: Add leaderboard strings to `"en"` dict**

  After `"nav_analytics": "Analytics",` add:
  ```python
  "nav_leaderboard":        "Leaderboard",
  "leaderboard_refresh":    "Refresh",
  "leaderboard_loading":    "Loading…",
  "leaderboard_waiting":    "Waiting for data…",
  "leaderboard_error":      "Failed to load",
  "leaderboard_no_data":    "No data",
  "leaderboard_tab":        "Tab",
  "leaderboard_composer":   "Composer",
  "leaderboard_members":    "members",
  "leaderboard_cycle_label":"Billing cycle",
  "analytics_events_badge": "{n} events",
  ```

- [ ] **Step 3: Verify**

  ```bash
  python -c "from cursor_hud import STRINGS; print(STRINGS['en']['nav_leaderboard'])"
  ```
  Expected: `Leaderboard`

- [ ] **Step 4: Commit**

  ```bash
  git add cursor_hud.py
  git commit -m "feat: add leaderboard i18n strings"
  ```

---

### Task 6: Add `LeaderboardFetcher`

**Files:**
- Modify: `cursor_hud.py` — after `UsageEventsFetcher` class

- [ ] **Step 1: Add `LeaderboardFetcher` class**

  Insert directly after the `UsageEventsFetcher` class:

  ```python
  class LeaderboardFetcher(QThread):
      """Fetch team leaderboard via GET /api/v2/analytics/team/leaderboard.

      Emits ready(dict) with keys:
        "tab"         : list[dict]  — tab_leaderboard entries sorted by rank
        "composer"    : list[dict]  — composer_leaderboard entries sorted by rank
        "total_users" : int
      """
      ready = pyqtSignal(dict)
      error = pyqtSignal(str)

      def __init__(self, start_ms: int, end_ms: int):
          super().__init__()
          self._start_ms = start_ms
          self._end_ms   = end_ms

      def run(self):
          try:
              cookie, _ = read_cursor_token()
              if not cookie:
                  self.error.emit("No auth token found.")
                  return
              hdrs = api_headers(cookie)
              body = {"startDate": self._start_ms, "endDate": self._end_ms}
              r = requests.get(
                  f"{BASE_URL}/api/v2/analytics/team/leaderboard",
                  json=body, headers=hdrs, timeout=30,
              )
              log.info("LeaderboardFetcher → HTTP %s", r.status_code)
              if not r.ok:
                  self.error.emit(f"HTTP {r.status_code}: {r.text[:120]}")
                  return
              data = r.json()
              tab_block      = data.get("tab_leaderboard", {})
              composer_block = data.get("composer_leaderboard", {})
              tab_entries      = sorted(tab_block.get("data", []),
                                        key=lambda x: x.get("rank", 999))
              composer_entries = sorted(composer_block.get("data", []),
                                        key=lambda x: x.get("rank", 999))
              total_users = max(
                  tab_block.get("total_users", 0),
                  composer_block.get("total_users", 0),
              )
              log.info("LeaderboardFetcher done — %d users", total_users)
              self.ready.emit({
                  "tab":         tab_entries,
                  "composer":    composer_entries,
                  "total_users": total_users,
              })
          except Exception:
              log.exception("LeaderboardFetcher.run")
              self.error.emit("Request failed — see log for details.")
  ```

- [ ] **Step 2: Verify module imports cleanly**

  ```bash
  python -c "import cursor_hud; print('ok')"
  ```
  Expected: `ok`

- [ ] **Step 3: Commit**

  ```bash
  git add cursor_hud.py
  git commit -m "feat: add LeaderboardFetcher"
  ```

---

### Task 7: Add `LeaderboardPage` widget

**Files:**
- Modify: `cursor_hud.py` — after `AnalyticsPage` class (~line 2561), before `# ══ NAV BAR` banner

- [ ] **Step 1: Add `LeaderboardPage` class**

  Insert between `AnalyticsPage` and the `# ══ NAV BAR` banner:

  ```python
  # ══════════════════════════════════════════════════════════════
  #  PAGE: LEADERBOARD
  # ══════════════════════════════════════════════════════════════
  class LeaderboardPage(QWidget):
      """Leaderboard tab — Tab completion + Composer ranking.

      Layout:
        Header row: title + cycle label + refresh button
        Toggle row: [Tab] [Composer] sub-view selector
        Content: QStackedWidget — tab_view | composer_view
      """
      refresh_clicked = pyqtSignal()

      def __init__(self, settings: dict):
          super().__init__()
          self.setAttribute(Qt.WA_TranslucentBackground)
          self.settings = settings

          vl = QVBoxLayout(self)
          vl.setContentsMargins(12, 8, 12, 8)
          vl.setSpacing(6)

          # ── Main card ──────────────────────────────────────────
          self._card = Card("accent")
          cl = QVBoxLayout(self._card)
          cl.setContentsMargins(10, 8, 10, 10)
          cl.setSpacing(4)

          # ── Header row ─────────────────────────────────────────
          hdr_row = QWidget()
          hdr_row.setAttribute(Qt.WA_TranslucentBackground)
          hl = QHBoxLayout(hdr_row)
          hl.setContentsMargins(0, 0, 0, 0)
          hl.setSpacing(6)
          self._hdr_lbl = section_hdr(S(settings, "nav_leaderboard"), "accent")
          hl.addWidget(self._hdr_lbl, 1)
          self._cycle_lbl = ql("", 8, c("t_dim"))
          hl.addWidget(self._cycle_lbl, 0)
          self._refresh_btn = QPushButton(S(settings, "leaderboard_refresh"))
          self._refresh_btn.setFixedHeight(20)
          self._refresh_btn.setCursor(Qt.PointingHandCursor)
          self._refresh_btn.clicked.connect(self.refresh_clicked)
          hl.addWidget(self._refresh_btn, 0)
          cl.addWidget(hdr_row)

          # ── Status label (loading / error / no-data) ────────────
          self._status_lbl = ql(S(settings, "leaderboard_loading"), 9, c("t_dim"))
          cl.addWidget(self._status_lbl)

          # ── Content area (hidden until data arrives) ───────────
          self._content = QWidget()
          self._content.setAttribute(Qt.WA_TranslucentBackground)
          content_vl = QVBoxLayout(self._content)
          content_vl.setContentsMargins(0, 2, 0, 0)
          content_vl.setSpacing(4)

          # Toggle row
          toggle_row = QWidget()
          toggle_row.setAttribute(Qt.WA_TranslucentBackground)
          tl = QHBoxLayout(toggle_row)
          tl.setContentsMargins(0, 0, 0, 0)
          tl.setSpacing(4)
          self._tab_btn = QPushButton(S(settings, "leaderboard_tab"))
          self._tab_btn.setCheckable(True)
          self._tab_btn.setChecked(True)
          self._tab_btn.setFixedHeight(22)
          self._tab_btn.setCursor(Qt.PointingHandCursor)
          self._composer_btn = QPushButton(S(settings, "leaderboard_composer"))
          self._composer_btn.setCheckable(True)
          self._composer_btn.setFixedHeight(22)
          self._composer_btn.setCursor(Qt.PointingHandCursor)
          tl.addWidget(self._tab_btn)
          tl.addWidget(self._composer_btn)
          tl.addStretch()
          content_vl.addWidget(toggle_row)

          # Sub-views (stacked)
          self._sub_stack = QStackedWidget()
          self._sub_stack.setAttribute(Qt.WA_TranslucentBackground)
          self._tab_view      = QWidget()
          self._tab_view.setAttribute(Qt.WA_TranslucentBackground)
          self._tab_vbox      = QVBoxLayout(self._tab_view)
          self._tab_vbox.setContentsMargins(0, 0, 0, 0)
          self._tab_vbox.setSpacing(2)
          self._composer_view = QWidget()
          self._composer_view.setAttribute(Qt.WA_TranslucentBackground)
          self._composer_vbox = QVBoxLayout(self._composer_view)
          self._composer_vbox.setContentsMargins(0, 0, 0, 0)
          self._composer_vbox.setSpacing(2)
          self._sub_stack.addWidget(self._tab_view)       # index 0
          self._sub_stack.addWidget(self._composer_view)  # index 1
          content_vl.addWidget(self._sub_stack)

          self._tab_btn.clicked.connect(lambda: self._switch_sub(0))
          self._composer_btn.clicked.connect(lambda: self._switch_sub(1))

          self._content.hide()
          cl.addWidget(self._content)
          vl.addWidget(self._card)
          vl.addStretch()

          self._apply_styles()

      # ── Sub-view toggle ─────────────────────────────────────────

      def _switch_sub(self, idx: int):
          self._sub_stack.setCurrentIndex(idx)
          self._tab_btn.setChecked(idx == 0)
          self._composer_btn.setChecked(idx == 1)

      # ── Public API ──────────────────────────────────────────────

      def show_waiting(self):
          self._status_lbl.setText(S(self.settings, "leaderboard_waiting"))
          self._status_lbl.show()
          self._content.hide()
          self._cycle_lbl.setText("")

      def show_loading(self):
          self._status_lbl.setText(S(self.settings, "leaderboard_loading"))
          self._status_lbl.show()
          self._content.hide()

      def show_error(self, msg: str):
          self._status_lbl.setText(
              f"{S(self.settings, 'leaderboard_error')}: {msg}")
          self._status_lbl.show()
          self._content.hide()

      def set_cycle_label(self, start: str, end: str):
          self._cycle_start = start
          self._cycle_end   = end
          n_members = getattr(self, "_total_users", 0)
          members_str = S(self.settings, "leaderboard_members")
          badge = f"{n_members} {members_str}  ·  " if n_members else ""
          self._cycle_lbl.setText(
              f"{badge}{S(self.settings, 'leaderboard_cycle_label')}: {start} – {end}")

      def update_data(self, data: dict):
          self._total_users = data.get("total_users", 0)
          if hasattr(self, "_cycle_start"):
              self.set_cycle_label(self._cycle_start, self._cycle_end)
          self._populate_tab(data.get("tab", []))
          self._populate_composer(data.get("composer", []))
          if not data.get("tab") and not data.get("composer"):
              self._status_lbl.setText(S(self.settings, "leaderboard_no_data"))
              self._status_lbl.show()
              self._content.hide()
          else:
              self._status_lbl.hide()
              self._content.show()

      # ── Row builders ─────────────────────────────────────────────

      def _clear_layout(self, layout: QVBoxLayout):
          while layout.count():
              item = layout.takeAt(0)
              if item.widget():
                  item.widget().deleteLater()

      def _populate_tab(self, entries: list):
          self._clear_layout(self._tab_vbox)
          for entry in entries:
              row = self._make_tab_row(entry)
              self._tab_vbox.addWidget(row)

      def _populate_composer(self, entries: list):
          self._clear_layout(self._composer_vbox)
          for entry in entries:
              row = self._make_composer_row(entry)
              self._composer_vbox.addWidget(row)

      def _make_tab_row(self, entry: dict) -> QWidget:
          zero_activity = entry.get("total_tab_accepts", 0) == 0
          return self._make_row(
              rank=entry.get("rank", 0),
              name=entry.get("display_name", ""),
              accepts=entry.get("total_tab_accepts", 0),
              ratio=entry.get("tab_accept_ratio", 0.0),
              model=entry.get("favorite_model", ""),
              zero_activity=zero_activity,
          )

      def _make_composer_row(self, entry: dict) -> QWidget:
          zero_activity = entry.get("total_diff_accepts", 0) == 0
          return self._make_row(
              rank=entry.get("rank", 0),
              name=entry.get("display_name", ""),
              accepts=entry.get("total_diff_accepts", 0),
              ratio=entry.get("composer_line_acceptance_ratio", 0.0),
              model=entry.get("favorite_model", ""),
              zero_activity=zero_activity,
          )

      def _make_row(self, rank: int, name: str, accepts: int,
                    ratio: float, model: str, zero_activity: bool) -> QWidget:
          row = QWidget()
          row.setAttribute(Qt.WA_TranslucentBackground)
          rl = QHBoxLayout(row)
          rl.setContentsMargins(0, 1, 0, 1)
          rl.setSpacing(5)

          opacity = 0.5 if zero_activity else 1.0

          def dim(col: QColor) -> QColor:
              if zero_activity:
                  return QColor(col.red(), col.green(), col.blue(),
                                int(col.alpha() * opacity))
              return col

          rank_lbl = ql(f"#{rank}", 8, dim(c("t_dim")))
          rank_lbl.setFixedWidth(20)
          rank_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
          rl.addWidget(rank_lbl, 0)

          name_lbl = ql(name, 8, dim(c("t_body")))
          name_lbl.setMaximumWidth(100)
          rl.addWidget(name_lbl, 1)

          accepts_lbl = ql(str(accepts), 8, dim(c("accent")))
          accepts_lbl.setFixedWidth(30)
          accepts_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
          rl.addWidget(accepts_lbl, 0)

          pct = min(ratio * 100, 999.9)
          ratio_lbl = ql(f"{pct:.0f}%", 8, dim(c("t_dim")))
          ratio_lbl.setFixedWidth(32)
          ratio_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
          rl.addWidget(ratio_lbl, 0)

          # Truncate model name for display
          model_short = model.split(":")[-1][:18] if model else "—"
          model_lbl = ql(model_short, 7, dim(c("t_dim")))
          model_lbl.setMaximumWidth(90)
          rl.addWidget(model_lbl, 0)

          return row

      # ── Theme / labels ───────────────────────────────────────────

      def refresh_theme(self):
          self._apply_styles()
          set_lbl_color(self._cycle_lbl,  c("t_dim"))
          set_lbl_color(self._status_lbl, c("t_dim"))
          ac = c("accent").name()
          self._hdr_lbl.setStyleSheet(
              f"color:{ac};font-size:8px;font-weight:700;"
              f"font-family:{_UI_FONT};background:transparent;"
              "letter-spacing:1.5px;")

      def refresh_labels(self):
          self._refresh_btn.setText(S(self.settings, "leaderboard_refresh"))
          self._hdr_lbl.setText(S(self.settings, "nav_leaderboard").upper())
          self._tab_btn.setText(S(self.settings, "leaderboard_tab"))
          self._composer_btn.setText(S(self.settings, "leaderboard_composer"))
          if hasattr(self, "_cycle_start"):
              self.set_cycle_label(self._cycle_start, self._cycle_end)

      def _apply_styles(self):
          ac = c("accent").name()
          mu = c("t_muted").name()
          btn_qss = (
              f"QPushButton{{color:{mu};background:rgba(255,255,255,0.05);"
              f"border:1px solid rgba(255,255,255,0.1);border-radius:3px;"
              f"font-family:{_UI_FONT};font-size:8px;padding:2px 6px;}}"
              f"QPushButton:hover{{color:{ac};border-color:{ac};}}"
              f"QPushButton:checked{{color:{ac};border-color:{ac};"
              f"background:rgba(255,255,255,0.10);}}"
          )
          self._refresh_btn.setStyleSheet(btn_qss)
          self._tab_btn.setStyleSheet(btn_qss)
          self._composer_btn.setStyleSheet(btn_qss)
  ```

- [ ] **Step 2: Verify module imports cleanly**

  ```bash
  python -c "import cursor_hud; print('ok')"
  ```
  Expected: `ok`

- [ ] **Step 3: Commit**

  ```bash
  git add cursor_hud.py
  git commit -m "feat: add LeaderboardPage widget"
  ```

---

### Task 8: Update NavBar for 5-tab layout

**Files:**
- Modify: `cursor_hud.py` — `NavBar` class (~line 2565)

- [ ] **Step 1: Add `nav_leaderboard` to `TABS` and rename `set_analytics_visible`**

  Change:
  ```python
  TABS = ["nav_credit", "nav_analytics", "nav_profile", "nav_settings"]
  ANALYTICS_IDX = 1
  ```
  to:
  ```python
  TABS = ["nav_credit", "nav_analytics", "nav_leaderboard", "nav_profile", "nav_settings"]
  ANALYTICS_IDX    = 1
  LEADERBOARD_IDX  = 2
  ```

- [ ] **Step 2: Update `__init__` to hide both experimental tabs by default**

  Change the existing hidden-by-default block (currently only hides index 1):
  ```python
  # Analytics tab hidden by default (experimental)
  self._btns[self.ANALYTICS_IDX].setVisible(
      settings.get("show_experimental", False))
  ```
  to:
  ```python
  # Experimental tabs hidden by default
  _show_exp = settings.get("show_experimental", False)
  self._btns[self.ANALYTICS_IDX].setVisible(_show_exp)
  self._btns[self.LEADERBOARD_IDX].setVisible(_show_exp)
  ```

- [ ] **Step 3: Rename `set_analytics_visible` → `set_experimental_visible`**

  Replace the method:
  ```python
  def set_analytics_visible(self, visible: bool):
      self._btns[self.ANALYTICS_IDX].setVisible(visible)
  ```
  with:
  ```python
  def set_experimental_visible(self, visible: bool):
      self._btns[self.ANALYTICS_IDX].setVisible(visible)
      self._btns[self.LEADERBOARD_IDX].setVisible(visible)
  ```

- [ ] **Step 4: Verify nav renders 5 tabs when experimental is on**

  ```bash
  python cursor_hud.py --mock
  ```
  Enable Experimental in Settings. Expected: 5 nav tabs visible (Credits, Analytics, Leaderboard, Profile, Settings).

- [ ] **Step 5: Commit**

  ```bash
  git add cursor_hud.py
  git commit -m "feat: add Leaderboard tab to NavBar, rename set_experimental_visible"
  ```

---

### Task 9: Wire `LeaderboardPage` into `HUDWindow`

**Files:**
- Modify: `cursor_hud.py` — `HUDWindow._build_ui`, `_switch_tab`, `_on_settings_changed`, `_on_theme_changed`, `_setup_shortcuts`, `_on_data`

- [ ] **Step 1: Add `LeaderboardPage` to the stack in `_build_ui`**

  In `HUDWindow._build_ui`, find the page declarations and stack `addWidget` calls. The current order is:
  ```python
  self._pg_credits  = CreditsPage(self.settings)
  ...
  self._pg_profile  = ProfilePage(self.settings)
  self._pg_settings = SettingsPage(self.settings)
  ...
  self._pg_analytics = AnalyticsPage(self.settings)
  self._pg_analytics.refresh_clicked.connect(self._on_analytics_refresh)
  for pg in [self._pg_credits, self._pg_analytics,
             self._pg_profile, self._pg_settings]:
      self._stack.addWidget(pg)
  ```

  Add leaderboard state fields and page, then reorder the `addWidget` list:
  ```python
  self._analytics_fetcher: UsageEventsFetcher | None = None
  self._analytics_data: dict | None = None
  self._analytics_pending: bool = False
  self._leaderboard_fetcher: LeaderboardFetcher | None = None
  self._leaderboard_data: dict | None = None
  self._leaderboard_pending: bool = False
  self._pg_analytics = AnalyticsPage(self.settings)
  self._pg_analytics.refresh_clicked.connect(self._on_analytics_refresh)
  self._pg_leaderboard = LeaderboardPage(self.settings)
  self._pg_leaderboard.refresh_clicked.connect(self._on_leaderboard_refresh)
  for pg in [self._pg_credits, self._pg_analytics, self._pg_leaderboard,
             self._pg_profile, self._pg_settings]:
      self._stack.addWidget(pg)
  ```

- [ ] **Step 2: Update `_switch_tab` guard and Leaderboard trigger**

  Replace:
  ```python
  def _switch_tab(self, idx: int):
      if idx == 1 and not self.settings.get("show_experimental", False):
          return
      _metrics.inc(f"tab_{idx}")
      self._stack.setCurrentIndex(idx)
      self._nav.set_active(idx)
      self._adjust_height(delay_ms=0)
      if idx == 1:
          self._trigger_analytics_fetch(force=False)
  ```
  with:
  ```python
  def _switch_tab(self, idx: int):
      if idx in (1, 2) and not self.settings.get("show_experimental", False):
          return
      _metrics.inc(f"tab_{idx}")
      self._stack.setCurrentIndex(idx)
      self._nav.set_active(idx)
      self._adjust_height(delay_ms=0)
      if idx == 1:
          self._trigger_analytics_fetch(force=False)
      elif idx == 2:
          self._trigger_leaderboard_fetch(force=False)
  ```

- [ ] **Step 3: Add leaderboard fetcher methods**

  After `_on_analytics_error` method, add:
  ```python
  def _trigger_leaderboard_fetch(self, force: bool = False):
      """Start LeaderboardFetcher. Defers if _last_data not yet available."""
      if self._last_data is None:
          self._pg_leaderboard.show_waiting()
          self._leaderboard_pending = True
          return
      self._leaderboard_pending = False
      d = self._last_data
      cyc      = d["cycle"]
      start_ms = _date_to_ms(cyc["start"])
      end_ms   = _date_to_ms(cyc["end"])
      self._pg_leaderboard.set_cycle_label(cyc["start"], cyc["end"])

      if not force and self._leaderboard_data is not None:
          return
      if self._leaderboard_fetcher:
          self._leaderboard_fetcher.blockSignals(True)
          self._leaderboard_fetcher.quit()
          self._leaderboard_fetcher.wait(2000)
          self._leaderboard_fetcher.deleteLater()
          self._leaderboard_fetcher = None
      self._pg_leaderboard.show_loading()
      self._leaderboard_fetcher = LeaderboardFetcher(start_ms, end_ms)
      self._leaderboard_fetcher.ready.connect(self._on_leaderboard_data)
      self._leaderboard_fetcher.error.connect(self._on_leaderboard_error)
      self._leaderboard_fetcher.start()
      log.debug("LeaderboardFetcher started")

  def _on_leaderboard_refresh(self):
      """Force re-fetch triggered by Refresh button."""
      if self._last_data is None:
          return
      self._trigger_leaderboard_fetch(force=True)

  def _on_leaderboard_data(self, data: dict):
      self._leaderboard_data = data
      self._pg_leaderboard.update_data(data)
      self._adjust_height(delay_ms=60)
      log.info("LeaderboardFetcher data received — %d users",
               data.get("total_users", 0))

  def _on_leaderboard_error(self, msg: str):
      self._pg_leaderboard.show_error(msg)
      log.error("LeaderboardFetcher error: %s", msg)
  ```

- [ ] **Step 4: Update `_on_settings_changed`**

  a) Replace `self._nav.set_analytics_visible(show_exp)` with `self._nav.set_experimental_visible(show_exp)`.

  b) Add `self._pg_leaderboard.refresh_labels()` alongside other `refresh_labels()` calls at the top of the method.

  c) Extend the `if not show_exp:` block to also reset leaderboard state:
  ```python
  if not show_exp:
      self._analytics_pending = False
      self._analytics_data = None
      if self._analytics_fetcher:
          self._analytics_fetcher.blockSignals(True)
          self._analytics_fetcher.quit()
          self._analytics_fetcher.wait(2000)
          self._analytics_fetcher.deleteLater()
          self._analytics_fetcher = None
      self._leaderboard_pending = False
      self._leaderboard_data = None
      if self._leaderboard_fetcher:
          self._leaderboard_fetcher.blockSignals(True)
          self._leaderboard_fetcher.quit()
          self._leaderboard_fetcher.wait(2000)
          self._leaderboard_fetcher.deleteLater()
          self._leaderboard_fetcher = None
      if self._stack.currentIndex() in (1, 2):
          self._switch_tab(0)
  ```

- [ ] **Step 5: Update `_on_theme_changed`**

  Add after `self._pg_analytics.refresh_theme()`:
  ```python
  self._pg_leaderboard.refresh_theme()
  ```

- [ ] **Step 6: Update `_on_data` to trigger deferred leaderboard fetch**

  After the existing `if self._analytics_pending:` block, add:
  ```python
  if self._leaderboard_pending:
      self._trigger_leaderboard_fetch(force=False)
  ```

- [ ] **Step 7: Update `_setup_shortcuts` for 5 tabs**

  Change Ctrl+3/4 comments and add Ctrl+5:
  ```python
  QShortcut(QKeySequence("Ctrl+1"), self, lambda: self._switch_tab(0))  # Credits
  QShortcut(QKeySequence("Ctrl+2"), self, lambda: self._switch_tab(1))  # Analytics
  QShortcut(QKeySequence("Ctrl+3"), self, lambda: self._switch_tab(2))  # Leaderboard
  QShortcut(QKeySequence("Ctrl+4"), self, lambda: self._switch_tab(3))  # Profile
  QShortcut(QKeySequence("Ctrl+5"), self, lambda: self._switch_tab(4))  # Settings
  ```

- [ ] **Step 8: Full integration test**

  ```bash
  python cursor_hud.py --mock
  ```
  Verify:
  - 4 tabs when Experimental OFF (Credits, Profile, Settings + Analytics/Leaderboard hidden)
  - Enable Experimental → 5 tabs appear
  - Click Leaderboard → page loads (shows Loading... or error without real token)
  - Toggle Tab / Composer buttons → sub-view switches without re-fetching
  - Disable Experimental → switches back to Credits, both experimental tabs hidden
  - Ctrl+1 through Ctrl+5 all work
  - Theme change → Leaderboard page repaints correctly

- [ ] **Step 9: Commit**

  ```bash
  git add cursor_hud.py
  git commit -m "feat: wire LeaderboardPage into HUDWindow navigation"
  ```

---

### Task 10: Update `.claude/rules/cursor-hud-code.md` section map

**Files:**
- Modify: `.claude/rules/cursor-hud-code.md`

- [ ] **Step 1: Update the section map**

  Update the `PAGE: CREDITS` row (remove `set_experimental_visible()` reference):
  ```
  | `PAGE: CREDITS`      | `CreditsPage` — hero card, arc gauge, seg bars, OD display |
  ```

  Update the `PAGE: ANALYTICS` row:
  ```
  | `PAGE: ANALYTICS`    | `AnalyticsPage` — Model Usage donut chart + legend; `refresh_clicked` signal |
  ```

  Add new rows after `PAGE: ANALYTICS`:
  ```
  | `PAGE: LEADERBOARD`  | `LeaderboardPage` — Tab / Composer sub-toggle; `refresh_clicked` signal |
  ```

  Update the `NAV BAR` row:
  ```
  | `NAV BAR`            | `NavBar` — Credits / Analytics / Leaderboard / Profile / Settings tabs; `ANALYTICS_IDX=1`, `LEADERBOARD_IDX=2`; `set_experimental_visible()` |
  ```

  Update `CSV FETCHER` banner description (no more CsvFetcher/AnalyticsFetcher):
  ```
  | `CSV FETCHER`        | `_date_to_ms()`, `UsageEventsFetcher(QThread)`, `LeaderboardFetcher(QThread)` |
  ```

  Update Settings keys (remove `csv_team_id`):
  ```
  `lang`, `theme`, `show_personal`, `show_org`, `show_official`, `pin_on_top`,
  `win_x`, `win_y`, `win_w`, `mini_mode`, `show_experimental`.
  ```

- [ ] **Step 2: Commit**

  ```bash
  git add .claude/rules/cursor-hud-code.md
  git commit -m "docs: update cursor-hud-code.md section map for leaderboard feature"
  ```

---

## Done

Run the full app one final time with `--mock` and verify:
- [ ] No Python errors or warnings in terminal
- [ ] Credits tab shows correctly (no CSV button)
- [ ] Settings → Experimental section: no Team ID field
- [ ] Experimental ON → 5 nav tabs visible
- [ ] Analytics tab → Leaderboard tab → sub-toggle between Tab/Composer works
- [ ] Theme cycling → all pages repaint correctly
- [ ] Experimental OFF → returns to Credits, both experimental tabs hidden
