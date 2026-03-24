# Theme Fonts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 테마마다 개성 있는 폰트를 적용하고, Cursor 웹 대시보드 색상 기반의 `native` 테마를 추가한다.

**Architecture:** `THEMES` dict에 `"font"` 키를 추가하고, `apply_theme()` 호출 시 `_UI_FONT` 전역을 갱신한다. 폰트 파일은 `assets/fonts/`에 번들하며, PyInstaller `--add-data`로 frozen 바이너리에도 포함한다. 테마 전환 시 `HUDWindow._on_theme_changed()`에서 `_apply_scale()`을 추가 호출해 기존 QFont 객체에 새 폰트를 반영한다.

**Tech Stack:** Python 3.10+ · PyQt5 (`QFontDatabase`) · PyInstaller · Google Fonts (OFL)

---

## 변경 파일 요약

| 파일 | 변경 내용 |
|---|---|
| `assets/fonts/*.ttf` | 폰트 파일 10개 추가 (신규) |
| `.gitattributes` | `*.ttf binary` 추가 |
| `cursor_hud.py:240-248` | `_OS_DEFAULT_FONT` 분리 |
| `cursor_hud.py:110-157` | `THEMES` dict — font 키 + native 테마 추가 |
| `cursor_hud.py:185-189` | `_loaded_fonts`, `_load_bundled_fonts()` 추가 (THEME SYSTEM 섹션 끝, QSS HELPERS 배너 앞) |
| `cursor_hud.py:176-178` | `apply_theme()` — font 키 처리 |
| `cursor_hud.py:293-295` | STRINGS ko — `theme_native` 추가 |
| `cursor_hud.py:353-355` | STRINGS en — `theme_native` 추가 |
| `cursor_hud.py:1883-1886` | `SettingsPage.THEMES_ORDER` — native 추가 |
| `cursor_hud.py:1966` | 테마 버튼 2열 분배 로직 (`i < 2` → `i < 3`) |
| `cursor_hud.py:3689-3700` | `HUDWindow._apply_scale()` 미니모드 폰트 family 갱신 |
| `cursor_hud.py:3326-3348` | `HUDWindow._on_theme_changed()` — `_apply_scale()` 추가 |
| `cursor_hud.py:3928-3931` | `main()` — `_load_bundled_fonts()` 호출 추가 |
| `.github/workflows/release.yml` | 3개 플랫폼 `--add-data` 추가 |
| `.claude/rules/cursor-hud-code.md` | THEME SYSTEM 키 심볼 업데이트 |

---

## 검증 명령어 공통 사항

아래 Task들의 검증 단계에서 `--mock`은 실존하는 JSON 파일 경로가 필요하다.
`cursor_hud_settings.json`이 없으면 먼저 생성한다:

```bash
echo '{}' > cursor_hud_settings.json
```

이후 모든 검증:
```bash
python cursor_hud.py --mock cursor_hud_settings.json
```

---

## Task 1: 폰트 파일 준비 및 .gitattributes

**Files:**
- Create: `assets/fonts/` (디렉터리 + 10개 .ttf)
- Modify: `.gitattributes`

- [ ] **Step 1: Google Fonts에서 static 아카이브 다운로드**

  각 폰트의 **static** 아카이브를 다운로드한다 (variable font 아카이브 사용 금지).
  Google Fonts 검색 → Download family → `static/` 폴더 안의 파일 사용.

  | 폰트 | 파일명 (Regular / SemiBold) |
  |---|---|
  | Nunito | `Nunito-Regular.ttf` / `Nunito-SemiBold.ttf` |
  | Space Grotesk | `SpaceGrotesk-Regular.ttf` / `SpaceGrotesk-SemiBold.ttf` |
  | Raleway | `Raleway-Regular.ttf` / `Raleway-SemiBold.ttf` |
  | Fira Code | `FiraCode-Regular.ttf` / `FiraCode-SemiBold.ttf` |
  | Inter | `Inter-Regular.ttf` / `Inter-SemiBold.ttf` |

- [ ] **Step 2: assets/fonts/ 디렉터리에 파일 배치**

  ```bash
  ls assets/fonts/
  # 예상: 10개 .ttf 파일
  ```

- [ ] **Step 3: .gitattributes에 ttf binary 마크 추가 (idempotent)**

  ```bash
  grep -qF '*.ttf binary' .gitattributes 2>/dev/null || echo '*.ttf binary' >> .gitattributes
  ```

- [ ] **Step 4: 폰트 파일 family name 검증**

  아래 스크립트를 `verify_fonts.py`로 저장해 실행한다:

  ```python
  import sys
  from PyQt5.QtWidgets import QApplication
  from PyQt5.QtGui import QFontDatabase
  from pathlib import Path

  app = QApplication(sys.argv)
  fonts_dir = Path("assets/fonts")
  ok = True
  for ttf in sorted(fonts_dir.glob("*.ttf")):
      fid = QFontDatabase.addApplicationFont(str(ttf))
      if fid == -1:
          print(f"FAILED TO LOAD: {ttf.name}")
          ok = False
      else:
          families = QFontDatabase.applicationFontFamilies(fid)
          print(f"{ttf.name:42s} → {families}")
  sys.exit(0 if ok else 1)
  ```

  ```bash
  python verify_fonts.py
  ```

  예상 출력 (family name이 THEMES `"font"` 키 값과 정확히 일치해야 함):
  ```
  FiraCode-Regular.ttf                       → ['Fira Code']
  FiraCode-SemiBold.ttf                      → ['Fira Code']
  Inter-Regular.ttf                          → ['Inter']
  Inter-SemiBold.ttf                         → ['Inter']
  Nunito-Regular.ttf                         → ['Nunito']
  Nunito-SemiBold.ttf                        → ['Nunito']
  Raleway-Regular.ttf                        → ['Raleway']
  Raleway-SemiBold.ttf                       → ['Raleway']
  SpaceGrotesk-Regular.ttf                   → ['Space Grotesk']
  SpaceGrotesk-SemiBold.ttf                  → ['Space Grotesk']
  ```

  실제 출력이 다를 경우 Task 3의 `"font"` 키 값을 실제 출력에 맞게 조정한다.
  검증 후 `verify_fonts.py`를 삭제한다.

- [ ] **Step 5: 커밋**

  ```bash
  git add assets/fonts/ .gitattributes
  git commit -m "feat: add bundled fonts for per-theme typography (OFL)"
  ```

---

## Task 2: _OS_DEFAULT_FONT 분리 및 font 인프라 추가

**Files:**
- Modify: `cursor_hud.py:239-248` (font 상수), `cursor_hud.py:185-188` (THEME SYSTEM 끝)

> **주의:** `_load_bundled_fonts`는 모듈 레벨에 정의되지만 호출은 `main()`에서만 이루어진다.
> `main()`은 `QApplication(sys.argv)` 생성 후 이 함수를 호출하므로 `QFontDatabase` 사용이 안전하다.

- [ ] **Step 1: `_OS_DEFAULT_FONT` 분리**

  `cursor_hud.py` 라인 240-248을 아래로 교체한다:

  ```python
  # Platform-appropriate fonts — avoids Qt alias-lookup penalty for missing families
  if sys.platform == "win32":
      _OS_DEFAULT_FONT = _UI_FONT = "Segoe UI"
      _MONO_FONT = "Consolas"
  elif sys.platform == "darwin":
      _OS_DEFAULT_FONT = _UI_FONT = "Helvetica Neue"
      _MONO_FONT = "Menlo"
  else:
      _OS_DEFAULT_FONT = _UI_FONT = "DejaVu Sans"
      _MONO_FONT = "DejaVu Sans Mono"
  ```

- [ ] **Step 2: `_loaded_fonts` + `_load_bundled_fonts()` 추가**

  `track_bg()` 함수(라인 185-187) 이후, `# ══════ QSS HELPERS` 배너 **이전**에 삽입한다:

  ```python
  # ── Bundled font loader ──────────────────────────────────────
  _loaded_fonts: set[str] = set()

  def _load_bundled_fonts(base: Path) -> None:
      """Load all .ttf files from assets/fonts/ and register with Qt.
      Must be called after QApplication is created (QFontDatabase requires it).
      """
      fonts_dir = base / "assets" / "fonts"
      if not fonts_dir.exists():
          return
      for ttf in sorted(fonts_dir.glob("*.ttf")):
          fid = QFontDatabase.addApplicationFont(str(ttf))
          if fid != -1:
              families = QFontDatabase.applicationFontFamilies(fid)
              _loaded_fonts.update(families)
              log.debug("Font loaded: %s → %s", ttf.name, families)
  ```

- [ ] **Step 3: `apply_theme()` 수정**

  라인 176-178의 `apply_theme()`를 아래로 교체한다:

  ```python
  def apply_theme(name: str):
      global _THEME, _UI_FONT
      _THEME = THEMES.get(name, THEMES["light"])
      font_name = _THEME.get("font")
      if font_name and font_name in _loaded_fonts:
          _UI_FONT = font_name
      else:
          _UI_FONT = _OS_DEFAULT_FONT
  ```

- [ ] **Step 4: mock 모드로 실행해 시작 오류 없음 확인**

  ```bash
  python cursor_hud.py --mock cursor_hud_settings.json
  ```

  앱이 정상 실행되고 기존 테마가 올바르게 표시되면 OK.
  이 시점에서는 폰트 변경이 아직 적용되지 않는다 (THEMES dict 미수정).

- [ ] **Step 5: 커밋**

  ```bash
  git add cursor_hud.py
  git commit -m "feat: add _OS_DEFAULT_FONT, _load_bundled_fonts, update apply_theme for font key"
  ```

---

## Task 3: THEMES dict 업데이트 (font 키 + native 테마 + UI 조정)

**Files:**
- Modify: `cursor_hud.py:113-156` (THEMES dict), `cursor_hud.py:293-295`, `cursor_hud.py:353-355` (STRINGS), `cursor_hud.py:1883-1886` (THEMES_ORDER), `cursor_hud.py:1966` (버튼 레이아웃)

> **원자성 주의:** `THEMES` dict에 `native` 추가와 `THEMES_ORDER` 수정을 같은 커밋에 포함해야 한다.
> `THEMES_ORDER`에만 먼저 추가하면 라인 1964 `THEMES[tname]` 접근 시 `KeyError`가 발생한다.

- [ ] **Step 1: 기존 4개 테마에 `"font"` 키 추가**

  각 테마 dict `"name":` 줄 바로 다음에 삽입:

  ```python
  "dark":     { "name": "dark",     "font": "Space Grotesk", ... }
  "light":    { "name": "light",    "font": "Nunito",        ... }
  "midnight": { "name": "midnight", "font": "Raleway",       ... }
  "matrix":   { "name": "matrix",   "font": "Fira Code",     ... }
  ```

- [ ] **Step 2: `native` 테마 추가**

  `matrix` 테마 닫는 `},` 다음에 추가:

  ```python
  "native": {
      "name": "native",
      "font": "Inter",
      "bg_win":    (10, 10, 10),
      "bg_win2":   (4,  4,  4),
      "bg_card":   (20, 20, 20),
      "accent":    (220, 220, 225),
      "accent2":   (155, 155, 165),
      "c_green":   (0, 195, 105),
      "c_amber":   (215, 155, 40),
      "c_red":     (215, 58, 72),
      "t_bright":  (237, 237, 237),
      "t_body":    (148, 148, 155),
      "t_muted":   (78, 78, 84),
      "t_dim":     (38, 38, 44),
      "border_lo": (255, 255, 255, 11),
      "border_hi": (220, 220, 225, 38),
      "scrollbar": "rgba(255,255,255,0.11)",
      "hatch_alpha": 20,
      "track_bg":  (255, 255, 255, 16),
  },
  ```

- [ ] **Step 3: STRINGS에 `theme_native` 추가**

  `ko` dict의 `"theme_matrix": "매트릭스"` 뒤:
  ```python
  "theme_native": "네이티브",
  ```

  `en` dict의 `"theme_matrix": "Matrix"` 뒤:
  ```python
  "theme_native": "Native",
  ```

- [ ] **Step 4: `SettingsPage.THEMES_ORDER`에 native 추가**

  ```python
  THEMES_ORDER = [
      ("light",    "theme_light"),
      ("dark",     "theme_dark"),
      ("midnight", "theme_midnight"),
      ("matrix",   "theme_matrix"),
      ("native",   "theme_native"),
  ]
  ```

- [ ] **Step 5: 테마 버튼 2열 분배 로직 수정**

  라인 1966: `rls[0 if i < 2 else 1]` → `rls[0 if i < 3 else 1]`

  현재 4개 테마는 2+2로 균등 분배. 5개가 되면 `i < 2` 기준으로 2+3이 되어 비대칭.
  `i < 3`으로 바꾸면 3+2로 분배된다 (row0: light/dark/midnight, row1: matrix/native).

  ```python
  rls[0 if i < 3 else 1].addWidget(btn, 1)
  ```

- [ ] **Step 6: mock 모드로 실행, 설정 페이지에서 테마 버튼 5개 확인**

  ```bash
  python cursor_hud.py --mock cursor_hud_settings.json
  ```

  - 설정 탭 → 테마 행: 버튼 5개, 2열 (3+2) 배치 확인
  - "Native" / "네이티브" 버튼 클릭 시 near-black 배경으로 전환 확인

- [ ] **Step 7: 커밋**

  ```bash
  git add cursor_hud.py
  git commit -m "feat: add font key to all themes, native theme, fix 5-theme button layout"
  ```

---

## Task 4: 테마 전환 시 폰트 즉시 반영

**Files:**
- Modify: `cursor_hud.py:3689-3700` (`_apply_scale` 미니모드 블록), `cursor_hud.py:3326-3348` (`_on_theme_changed`)

**Context:** `_UI_FONT` 변경은 기존 `QFont` 객체에 자동 반영되지 않는다. 두 곳을 수정한다:
1. `_apply_scale()` 미니모드 블록 — 현재 `f.setPointSize()`만 호출해 family를 변경하지 않음
2. `_on_theme_changed()` — `_apply_scale()` 재호출을 추가

`_on_theme_changed()`의 `_apply_scale()` 호출은 `if self._last_data:` **이전**에 위치해야 한다.
`update_data()` 내부에서 위젯 텍스트를 갱신하지만 `apply_scale()`을 재호출하지 않으므로
font 재적용 → data update 순서가 안전하다.

- [ ] **Step 1a: `CreditsPage.apply_scale()` 섹션 헤더에 `setFamily` 추가**

  라인 1646-1650의 섹션 헤더 블록을 아래로 교체한다:

  ```python
  sec_px = max(7, int(8 * scale))
  for hdr in [self._hdr_personal, self._hdr_org, self._hdr_rates]:
      f = hdr.font()
      f.setFamily(_UI_FONT)   # ← 추가
      f.setPointSize(sec_px)
      hdr.setFont(f)
  ```

- [ ] **Step 1b: `_apply_scale()` 미니모드 블록에 `setFamily` 추가**

  라인 3689-3700의 `_mini_groups` 처리 블록을 아래로 교체한다:

  ```python
  if hasattr(self, "_mini_groups"):
      mini_px = max(8, int(9 * scale))
      hdr_px  = max(7, int(8 * scale))
      for label_lbl, amount_lbl in self._mini_groups:
          if amount_lbl is not None:
              f = amount_lbl.font()
              f.setFamily(_UI_FONT)   # ← 추가
              f.setPointSize(mini_px)
              amount_lbl.setFont(f)
          if label_lbl is not None:
              f2 = label_lbl.font()
              f2.setFamily(_UI_FONT)  # ← 추가
              f2.setPointSize(hdr_px)
              label_lbl.setFont(f2)
  ```

- [ ] **Step 2: `_on_theme_changed()` 끝에 `_apply_scale()` 추가**

  라인 3344 `self.repaint()` 다음, `if self._last_data:` 이전에 삽입:

  ```python
  self._apply_scale()   # re-apply QFont objects with updated _UI_FONT
  ```

- [ ] **Step 3: mock 모드로 테마 전환 시 폰트 변경 확인**

  ```bash
  python cursor_hud.py --mock cursor_hud_settings.json
  ```

  - Credits 페이지 큰 숫자 + KV 행: 테마 클릭 즉시 폰트 변경 확인
  - 미니 모드(Ctrl+M): 미니 모드에서도 테마 전환 시 폰트 변경 확인
  - 창 리사이즈 없이 버튼 클릭만으로 변경되면 OK

- [ ] **Step 4: 커밋**

  ```bash
  git add cursor_hud.py
  git commit -m "fix: propagate _UI_FONT on theme change (mini-mode + apply_scale in _on_theme_changed)"
  ```

---

## Task 5: main()에 _load_bundled_fonts 연결

**Files:**
- Modify: `cursor_hud.py:3928-3931` (`main()` 내 apply_theme 호출 전)

- [ ] **Step 1: `apply_theme()` 호출 이전에 font 로드 삽입**

  라인 3930 `init_settings = load_settings()` 이후, `apply_theme(...)` 이전:

  ```python
  init_settings = load_settings()

  # Load bundled fonts before apply_theme so _UI_FONT can be set correctly.
  # frozen: fonts extracted to sys._MEIPASS by PyInstaller --add-data
  # dev:    fonts at assets/fonts/ relative to source tree
  if getattr(sys, "frozen", False):
      _load_bundled_fonts(Path(sys._MEIPASS))
  else:
      _load_bundled_fonts(_app_dir())

  apply_theme(init_settings.get("theme", "light"))
  ```

- [ ] **Step 2: mock 모드로 실행, 로그에서 폰트 로드 확인**

  ```bash
  python cursor_hud.py --mock cursor_hud_settings.json
  ```

  - 앱 시작 시 로그 버튼 클릭 → DEBUG 탭에서 `Font loaded:` 로그 10줄 확인
  - `light` 테마 기본 실행 시 Credits 페이지 텍스트가 Nunito(둥근 획)로 표시 확인

- [ ] **Step 3: 커밋**

  ```bash
  git add cursor_hud.py
  git commit -m "feat: load bundled fonts at startup before apply_theme"
  ```

---

## Task 6: CI 빌드 업데이트 (release.yml)

**Files:**
- Modify: `.github/workflows/release.yml`

> Windows는 `--add-data` 구분자가 `;`, macOS/Linux는 `:` 임에 주의.

- [ ] **Step 1: Windows 빌드에 `--add-data` 추가**

  현재:
  ```yaml
  run: python -m PyInstaller --onefile --windowed --name CursorHUD --icon=assets/icon.ico --add-data "assets/icon.ico;assets" cursor_hud.py
  ```
  변경 후:
  ```yaml
  run: python -m PyInstaller --onefile --windowed --name CursorHUD --icon=assets/icon.ico --add-data "assets/icon.ico;assets" --add-data "assets/fonts;assets/fonts" cursor_hud.py
  ```

- [ ] **Step 2: macOS 빌드에 `--add-data` 추가**

  현재:
  ```yaml
  run: python -m PyInstaller --windowed --name CursorHUD --icon=assets/icon.icns cursor_hud.py
  ```
  변경 후:
  ```yaml
  run: python -m PyInstaller --windowed --name CursorHUD --icon=assets/icon.icns --add-data "assets/fonts:assets/fonts" cursor_hud.py
  ```

- [ ] **Step 3: Linux 빌드에 `--add-data` 추가**

  현재:
  ```yaml
  run: python -m PyInstaller --onefile --windowed --name CursorHUD --icon=assets/icon_256.png cursor_hud.py
  ```
  변경 후:
  ```yaml
  run: python -m PyInstaller --onefile --windowed --name CursorHUD --icon=assets/icon_256.png --add-data "assets/fonts:assets/fonts" cursor_hud.py
  ```

- [ ] **Step 4: 커밋**

  ```bash
  git add .github/workflows/release.yml
  git commit -m "build: bundle fonts in all platform PyInstaller builds"
  ```

---

## Task 7: cursor-hud-code.md 섹션 맵 업데이트

**Files:**
- Modify: `.claude/rules/cursor-hud-code.md`

- [ ] **Step 1: THEME SYSTEM 행 키 심볼 업데이트**

  `cursor-hud-code.md`의 THEME SYSTEM 행을 찾아 key symbols 컬럼에 추가:

  현재:
  ```
  | `THEME SYSTEM` | `THEMES`, `c()`, `apply_theme()`, `TH()`, `track_bg()` |
  ```
  변경 후:
  ```
  | `THEME SYSTEM` | `THEMES`, `c()`, `apply_theme()`, `TH()`, `track_bg()`, `_OS_DEFAULT_FONT`, `_UI_FONT`, `_loaded_fonts`, `_load_bundled_fonts()` |
  ```

- [ ] **Step 2: 커밋**

  ```bash
  git add .claude/rules/cursor-hud-code.md
  git commit -m "docs: update THEME SYSTEM section map for font infrastructure"
  ```

---

## Task 8: 최종 검증

- [ ] **Step 1: 전체 테마 순환 테스트**

  ```bash
  python cursor_hud.py --mock cursor_hud_settings.json
  ```

  각 테마를 순서대로 선택하며 확인:

  | 테마 | 폰트 | 확인 항목 |
  |---|---|---|
  | light | Nunito | 둥근 획, 밝은 배경 |
  | dark | Space Grotesk | 기하학적 획, 시안 강조색 |
  | midnight | Raleway | 얇고 우아한 획, 보라 배경 |
  | matrix | Fira Code | 고정폭, 녹색 텍스트 |
  | native | Inter | 정밀 산세리프, near-black 배경 |

  Credits 큰 숫자, KV 행, 타이틀바 텍스트 모두 폰트 변경 확인.

- [ ] **Step 2: 미니 모드 폰트 확인**

  Ctrl+M으로 미니 모드 진입 후 각 테마 전환 시 레이블 폰트도 변경되는지 확인.

- [ ] **Step 3: 창 리사이즈 후 폰트 유지 확인**

  테마 전환 후 창 리사이즈 시 폰트가 유지되는지 (리사이즈로 초기화되지 않는지) 확인.

- [ ] **Step 4: 폰트 로드 실패 fallback 확인 (선택)**

  `assets/fonts/` 디렉터리를 임시 이름으로 바꾼 후 실행 → OS 기본 폰트로 정상 동작 확인.
  확인 후 원래 이름으로 복원.

- [ ] **Step 5: verify_fonts.py 및 임시 파일 정리**

  ```bash
  rm -f verify_fonts.py
  ```

---

## 구현 순서 요약

```
Task 1 (폰트 파일) → Task 2 (인프라 코드) → Task 3 (테마 데이터 + UI)
→ Task 4 (폰트 전파) → Task 5 (main 연결) → Task 6 (CI) → Task 7 (docs) → Task 8 (검증)
```

Task 2~5는 단일 파일(`cursor_hud.py`) 수정으로 순서대로 진행한다.
Task 3의 THEMES + THEMES_ORDER 변경은 반드시 같은 커밋에 포함한다.
