# Experimental Section — Design Spec

**Date:** 2026-03-18
**Status:** Approved

---

## Overview

Add an "Experimental" section at the bottom of the Settings tab that gates all
CSV-related UI behind a toggle. When the toggle is OFF (default), the CSV export
button and the Team ID input field are completely hidden. When ON, they appear
exactly as they do today.

---

## Motivation

CSV export is a power-user feature that:
- Requires knowing an undocumented Cursor API endpoint
- Optionally requires a manually-entered Team ID with no auto-detection path
- Is subject to change as the Cursor API evolves

Hiding it by default reduces noise for regular users while keeping it accessible
for those who want it.

---

## Data Model

### `DEFAULT_SETTINGS` addition

```python
"show_experimental": False   # gates all Experimental/Labs features
```

### New STRINGS entries (ko + en)

| key | ko | en |
|-----|----|----|
| `experimental_section` | 실험적 기능 | Experimental |
| `experimental_toggle` | 실험적 기능 활성화 | Enable experimental features |
| `experimental_hint` | 불안정하거나 변경될 수 있는 기능입니다 | Features that may change or break |

---

## Settings Tab Layout

Append to the bottom of the Settings scroll area:

```
─────────────────────────────────────
  ⚗ Experimental
  불안정하거나 변경될 수 있는 기능입니다
─────────────────────────────────────
  Enable experimental features   [toggle]

  ← shown only when toggle is ON →

  Team ID (CSV export)
  [________________________________]
  (placeholder: "optional — blank = personal data")
```

The section header uses the same muted-color `ql()` label style as other section
labels. The hint line uses `c("t_dim")`. The toggle uses the existing
`_switch_row()` helper with key `"show_experimental"`.

The Team ID `QLineEdit` and its label are wrapped in a container widget whose
`setVisible()` is toggled — this avoids having to show/hide multiple sibling
widgets individually.

---

## Credits Tab Changes

The CSV export button (`_csv_btn`) and its preceding `Divider` are wrapped in a
single container widget. `CreditsPage` exposes:

```python
def set_experimental_visible(self, visible: bool) -> None:
    self._csv_container.setVisible(visible)
```

`HUDWindow._on_data()` and `SettingsPage` both call this method when the
`show_experimental` value changes.

---

## Wiring

### `_on_switch("show_experimental", value)` in `SettingsPage`

Handled by the existing `_on_switch` dispatch:

```python
# new branch in _on_switch
elif key == "show_experimental":
    self._experimental_detail.setVisible(value)
    # notify HUDWindow to update Credits tab
    self.experimental_changed.emit(value)  # new pyqtSignal
```

`HUDWindow` connects `SettingsPage.experimental_changed` →
`_pg_credits.set_experimental_visible`.

### Startup / `refresh_theme()`

Both `SettingsPage.__init__` and `refresh_theme()` read
`settings.get("show_experimental", False)` and apply `setVisible()` to the
relevant widgets — same pattern as the existing Team ID QLineEdit visibility
guard.

---

## Affected Symbols

| Symbol | Change |
|--------|--------|
| `DEFAULT_SETTINGS` | add `"show_experimental": False` |
| `STRINGS` | add 3 new keys (ko + en) |
| `SettingsPage.__init__` | add Experimental section, wrap Team ID in container |
| `SettingsPage._on_switch` | handle `show_experimental` key |
| `SettingsPage.refresh_theme` | apply visibility from settings |
| `SettingsPage` | add `experimental_changed = pyqtSignal(bool)` |
| `CreditsPage._rebuild_labels` | wrap `_csv_btn` + divider in `_csv_container` |
| `CreditsPage` | add `set_experimental_visible(bool)` method |
| `HUDWindow.__init__` | connect `experimental_changed` signal |
| `HUDWindow._on_data` | call `set_experimental_visible` on data load |

---

## Non-Goals

- No per-feature granularity within Experimental (single toggle for all)
- No visual indicator on the Credits tab when experimental is OFF ("CSV available in settings")
- No migration needed — `show_experimental` defaults to `False`, existing users
  who relied on CSV export must re-enable it once

---

## Version Bump

`1.0.0-beta.7` → `1.0.0-beta.8`
