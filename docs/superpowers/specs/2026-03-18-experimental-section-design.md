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

The Team ID `QLineEdit`, its label, and any surrounding `Divider` widgets are
wrapped in a container widget (`_experimental_detail`) whose `setVisible()` is
toggled. The `csv_team_id_label` QLabel must still be registered as
`self._t["csv_team_id_label"]` so `_update_texts` continues to update it on
language/theme changes — the move into the container must not break this
registration.

---

## Credits Tab Changes

The CSV export button (`_csv_btn`) and its `export_row` container are wrapped in
a single `QWidget` container (`_csv_container`) inside `CreditsPage.__init__`.
No divider precedes the button in the current layout, so none is added to the
container. `CreditsPage` exposes:

```python
def set_experimental_visible(self, visible: bool) -> None:
    self._csv_container.setVisible(visible)
```

`CreditsPage.__init__` applies the initial visibility directly from the
`settings` dict passed in at construction:

```python
self._csv_container.setVisible(settings.get("show_experimental", False))
```

This mirrors the `SettingsPage.__init__` pattern and avoids relying on
`_on_settings_changed` being called at startup (it is only triggered by user
interaction). `HUDWindow._on_settings_changed` calls `set_experimental_visible`
for all subsequent runtime changes.

`self._csv_btn` retains its current attribute name and remains a direct
attribute of `CreditsPage` after being re-parented into `_csv_container`.
`HUDWindow` accesses `self._pg_credits._csv_btn` directly in four places
(`_on_export_csv`, `_on_csv_ready`, `_on_csv_error`) — those references must
continue to work unchanged.

---

## Wiring

### `_on_switch("show_experimental", value)` in `SettingsPage`

The existing `_on_switch` already emits `self.changed.emit()` (via HUDWindow's
`setting_changed` signal) after saving the setting. No new signal is needed.

`HUDWindow._on_settings_changed` is extended to handle this key — exactly as it
already handles `show_personal` / `show_org` / `show_official`:

```python
# in HUDWindow._on_settings_changed
self._pg_credits.set_experimental_visible(
    self.settings.get("show_experimental", False)
)
```

`SettingsPage` also syncs its own `_experimental_detail` container visibility
directly inside `_on_switch` when `key == "show_experimental"`:

```python
elif key == "show_experimental":
    self._experimental_detail.setVisible(value)
```

### Startup visibility

`SettingsPage.__init__` sets the initial state of `_experimental_detail` by
reading `settings.get("show_experimental", False)` immediately after the widget
is constructed — same pattern as the existing Team ID `QLineEdit` guard.

`CreditsPage.__init__` applies the initial `_csv_container` visibility the same
way (as specified in "Credits Tab Changes" above). `HUDWindow._on_settings_changed`
is **not** called automatically at startup — it is triggered only by user
interaction. All runtime changes (user toggles the setting) flow through
`_on_settings_changed`.

---

## Affected Symbols

| Symbol | Change |
|--------|--------|
| `DEFAULT_SETTINGS` | add `"show_experimental": False` |
| `STRINGS` | add 3 new keys (ko + en) |
| `SettingsPage.__init__` | add Experimental section; wrap Team ID widgets in `_experimental_detail` container; apply initial visibility |
| `SettingsPage._on_switch` | handle `"show_experimental"` key → set `_experimental_detail.setVisible(value)` |
| `CreditsPage.__init__` | wrap `export_row` + `_csv_btn` in `_csv_container` widget |
| `CreditsPage` | add `set_experimental_visible(bool)` method |
| `HUDWindow._on_settings_changed` | call `_pg_credits.set_experimental_visible(settings.get("show_experimental", False))` |

---

## Non-Goals

- No per-feature granularity within Experimental (single toggle for all)
- No visual indicator on the Credits tab when experimental is OFF ("CSV available in settings")
- No migration needed — `show_experimental` defaults to `False`, existing users
  who relied on CSV export must re-enable it once

---

## Version Bump

`1.0.0-beta.7` → `1.0.0-beta.8`
