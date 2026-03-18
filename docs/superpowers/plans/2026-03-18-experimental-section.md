# Experimental Section Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an "Experimental" section at the bottom of the Settings tab that gates CSV-related UI (export button + Team ID field) behind a toggle, hidden by default.

**Architecture:** Single `show_experimental: bool` setting controls two visibility targets: `CreditsPage._csv_container` (CSV button) and `SettingsPage._experimental_detail` (Team ID label + input). Both widgets apply initial visibility from the `settings` dict at construction time; runtime changes flow through the existing `_on_switch` → `changed.emit()` → `HUDWindow._on_settings_changed` pipeline.

**Tech Stack:** Python 3.10+, PyQt5 — single file `cursor_hud.py` (~2900 lines)

**Spec:** `docs/superpowers/specs/2026-03-18-experimental-section-design.md`

---

## Chunk 1: Data model + CreditsPage container

### Task 1: Add STRINGS entries and DEFAULT_SETTINGS key

**Files:**
- Modify: `cursor_hud.py` (STRINGS dict ~line 267, DEFAULT_SETTINGS ~line 353)

- [ ] **Step 1: Add Korean STRINGS entries**

  Find the ko block ending around line 307. After `"csv_team_id_placeholder": "선택 사항 — 비워두면 개인 데이터",` and before the closing `},`, add:
  ```python
  "experimental_section": "실험적 기능",
  "experimental_toggle":  "실험적 기능 활성화",
  "experimental_hint":    "불안정하거나 변경될 수 있는 기능입니다",
  ```

- [ ] **Step 2: Add English STRINGS entries**

  Find the en block ending around line 349. After `"csv_team_id_placeholder": "optional — blank = personal data",` and before the closing `},`, add:
  ```python
  "experimental_section": "Experimental",
  "experimental_toggle":  "Enable experimental features",
  "experimental_hint":    "Features that may change or break",
  ```

- [ ] **Step 3: Add DEFAULT_SETTINGS key**

  Find `DEFAULT_SETTINGS` (~line 353). On the `"csv_team_id": ""` line, add `"show_experimental": False` on the next line:
  ```python
  "csv_team_id": "",        # override for CSV export teamId (empty = auto-detect)
  "show_experimental": False,  # gates all Experimental features
  ```

- [ ] **Step 4: Verify syntax**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 -c "import ast; ast.parse(open('cursor_hud.py').read()); print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 5: Commit**
  ```bash
  git add cursor_hud.py
  git commit -m "feat(experimental): add STRINGS keys and show_experimental setting"
  ```

---

### Task 2: Wrap CreditsPage CSV button in container

**Files:**
- Modify: `cursor_hud.py` (CreditsPage.__init__ ~line 1404, add method after _rebuild_labels)

**Context:** Currently lines 1404–1422 look like:
```python
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
self._csv_btn.setStyleSheet(...)
self._csv_btn.clicked.connect(self.export_csv_clicked)
exl.addWidget(self._csv_btn)
vl.addWidget(export_row)
```

- [ ] **Step 1: Wrap export_row in _csv_container**

  Replace the last line `vl.addWidget(export_row)` with:
  ```python
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
  ```
  Note: `self._csv_btn` is already a direct attribute — this doesn't change that.

- [ ] **Step 2: Add set_experimental_visible method**

  After the `_rebuild_labels` method (around line 1438), add:
  ```python
  def set_experimental_visible(self, visible: bool) -> None:
      """Show/hide CSV export controls (gated by Experimental toggle)."""
      self._csv_container.setVisible(visible)
  ```

- [ ] **Step 3: Verify syntax**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 -c "import ast; ast.parse(open('cursor_hud.py').read()); print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 4: Smoke-test in mock mode — CSV button hidden by default**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 cursor_hud.py --mock &
  sleep 3
  ```
  Open app → go to Credits tab → CSV button should NOT be visible (show_experimental defaults to False).

- [ ] **Step 5: Commit**
  ```bash
  git add cursor_hud.py
  git commit -m "feat(experimental): wrap CSV button in _csv_container, add set_experimental_visible"
  ```

---

## Chunk 2: SettingsPage Experimental section

### Task 3: Restructure Settings bottom — Experimental section

**Files:**
- Modify: `cursor_hud.py` (SettingsPage.__init__ ~line 1820–1842, _on_switch ~line 1893, refresh_theme ~line 1936)

**Context — current bottom of SettingsPage.__init__:**
```python
cl.addWidget(Divider())       # line 1821

# Team ID override for CSV export
self._t["csv_team_id_label"] = ql(self.T("csv_team_id_label"), 9, c("t_body"))
cl.addWidget(self._t["csv_team_id_label"])
self._team_id_input = QLineEdit()
...
cl.addWidget(self._team_id_input)
cl.addWidget(Divider())       # line 1838

self._t["auto_saved"] = ql(self.T("auto_saved"), 8, c("t_dim"))
cl.addWidget(self._t["auto_saved"])
```

- [ ] **Step 1: Replace the Team ID block + auto_saved with the Experimental section**

  Remove lines 1821–1841 (the block from `cl.addWidget(Divider())` after startup through `cl.addWidget(self._t["auto_saved"])`).

  Replace with:
  ```python
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
  ```

- [ ] **Step 2: Handle show_experimental in _on_switch**

  In `_on_switch`, the current dispatch (~line 1893) is:
  ```python
  if key == "_startup":
      ...
  else:
      self.settings[key] = value
      save_settings(self.settings)
      self.changed.emit()
      if key == "pin_on_top":
          self.pin_changed.emit(value)
  ```

  Add an `elif` branch for `show_experimental` **inside the `else` block, after
  `self.changed.emit()`**:
  ```python
  else:
      self.settings[key] = value
      save_settings(self.settings)
      self.changed.emit()
      if key == "pin_on_top":
          self.pin_changed.emit(value)
      elif key == "show_experimental":
          self._experimental_detail.setVisible(value)
  ```

  `changed.emit()` fires before the `elif`, so `HUDWindow._on_settings_changed`
  (which updates `_csv_container` visibility on the Credits page) is triggered
  first, then the Settings page's own detail container is synced.

- [ ] **Step 3: Update refresh_theme for the experimental section**

  In `refresh_theme` (~line 1936), after the existing `if hasattr(self, "_team_id_input"):` block, add:
  ```python
  if hasattr(self, "_experimental_detail"):
      self._experimental_detail.setVisible(
          self.settings.get("show_experimental", False)
      )
  # Refresh experimental section header/hint label colors
  lbl = self._t.get("experimental_section")
  if lbl:
      set_lbl_color(lbl, c("t_muted"))
  lbl = self._t.get("experimental_hint")
  if lbl:
      set_lbl_color(lbl, c("t_dim"))
  ```

  This ensures `exp_hdr` and `exp_hint` colors update on theme switch, consistent
  with how `lang_label`, `theme_label`, and `auto_saved` are refreshed.

- [ ] **Step 4: Verify syntax**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 -c "import ast; ast.parse(open('cursor_hud.py').read()); print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 5: Smoke-test in mock mode**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 cursor_hud.py --mock
  ```
  Verify:
  - Settings tab shows "⚗ Experimental" section at the bottom
  - "Enable experimental features" toggle is OFF by default
  - Team ID input is NOT visible when toggle is OFF
  - Toggle ON → Team ID input appears
  - Toggle OFF → Team ID input disappears
  - Credits tab: CSV button hidden when toggle OFF, visible when toggle ON

- [ ] **Step 6: Commit**
  ```bash
  git add cursor_hud.py
  git commit -m "feat(experimental): add Experimental section to Settings with visibility toggle"
  ```

---

## Chunk 3: HUDWindow wiring + version bump

### Task 4: Wire HUDWindow._on_settings_changed

**Files:**
- Modify: `cursor_hud.py` (HUDWindow._on_settings_changed ~line 2463)

**Context — current _on_settings_changed:**
```python
def _on_settings_changed(self):
    self._nav.refresh_labels()
    self._status.refresh_labels()
    self._pg_credits._rebuild_labels()
    self._pg_profile._rebuild_labels()
    cfg = self.settings
    self._pg_credits._personal_card.setVisible(cfg.get("show_personal", True))
    self._pg_credits._org_card.setVisible(cfg.get("show_org", True))
    self._pg_credits._rate_card.setVisible(cfg.get("show_official", True))
    if self._last_data:
        ...
```

- [ ] **Step 1: Add set_experimental_visible call**

  After `self._pg_credits._rate_card.setVisible(cfg.get("show_official", True))`, add:
  ```python
  self._pg_credits.set_experimental_visible(
      cfg.get("show_experimental", False)
  )
  ```

- [ ] **Step 2: Verify syntax**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 -c "import ast; ast.parse(open('cursor_hud.py').read()); print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 3: Commit**
  ```bash
  git add cursor_hud.py
  git commit -m "feat(experimental): wire HUDWindow._on_settings_changed for CSV visibility"
  ```

---

### Task 5: Version bump + docs update

**Files:**
- Modify: `cursor_hud.py` (VERSION ~line 237)
- Modify: `CHANGELOG.md`
- Modify: `.claude/rules/cursor-hud-code.md` (settings keys table)

- [ ] **Step 1: Bump VERSION**

  Change:
  ```python
  VERSION   = "1.0.0-beta.7"
  ```
  To:
  ```python
  VERSION   = "1.0.0-beta.8"
  ```

- [ ] **Step 2: Update CHANGELOG**

  Prepend a new entry at the top of CHANGELOG.md:
  ```markdown
  ## v1.0.0-beta.8 — 2026-03-18

  ### Features
  - **Experimental section**: Settings tab now has an "Experimental" section at
    the bottom (disabled by default). Enable it to reveal CSV export controls.
    - Toggle OFF (default): CSV export button and Team ID field are hidden.
    - Toggle ON: CSV export button appears in Credits tab; Team ID input appears
      in Settings tab.
  - `show_experimental` setting added to `DEFAULT_SETTINGS` (default: `False`).
    Existing users who used CSV export will need to re-enable this once.

  ---
  ```

- [ ] **Step 3: Update .claude/rules/cursor-hud-code.md**

  **3a.** In the "Settings keys" section at the bottom, add `show_experimental`:
  ```
  `lang`, `theme`, `show_personal`, `show_org`, `show_official`, `pin_on_top`,
  `win_x`, `win_y`, `win_w`, `mini_mode`, `csv_team_id`, `show_experimental`.
  ```

  **3b.** In the section map table, update the `PAGE: CREDITS` row to include
  `set_experimental_visible` in the Key symbols cell:
  ```
  | `PAGE: CREDITS` | `CreditsPage` — hero card, arc gauge, seg bars, OD display, `set_experimental_visible()` |
  ```

- [ ] **Step 4: Final smoke-test**
  ```bash
  /opt/homebrew/opt/python@3.11/bin/python3.11 cursor_hud.py --mock
  ```
  Full verification checklist:
  - [ ] App starts without errors
  - [ ] Credits tab: CSV button hidden on first launch (fresh settings)
  - [ ] Settings tab: Experimental section visible at bottom
  - [ ] Experimental toggle OFF → Team ID hidden, CSV button hidden
  - [ ] Experimental toggle ON → Team ID visible, CSV button visible
  - [ ] Theme switch: visibility preserved correctly
  - [ ] Language switch (ko↔en): "실험적 기능" / "Experimental" section header updates

- [ ] **Step 5: Commit all**
  ```bash
  git add cursor_hud.py CHANGELOG.md .claude/rules/cursor-hud-code.md
  git commit -m "feat: Experimental section gates CSV export UI (v1.0.0-beta.8)"
  ```
