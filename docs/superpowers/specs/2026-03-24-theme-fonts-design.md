# Theme Fonts — Design Spec

**Date:** 2026-03-24
**Status:** Approved

---

## Overview

각 테마에 개성을 살리는 커스텀 폰트를 적용한다. 새 `native` 테마(Cursor 웹 대시보드 색상 스키마)를 추가하고, 기존 4개 테마에도 무드에 맞는 폰트를 부여한다. 모든 폰트는 OFL 라이선스로 앱에 번들된다.

---

## 1. 테마별 폰트 정의

| 테마 | 폰트 (`"font"` 키 값) | 무드 |
|---|---|---|
| light | `"Nunito"` | 둥글고 친근함, 따뜻한 라이트 UI |
| dark | `"Space Grotesk"` | 기하학적·테크, 시안/일렉트릭과 궁합 |
| midnight | `"Raleway"` | 얇고 우아함, 보라/핑크 무드에 드라마틱 |
| matrix | `"Fira Code"` | 고정폭 터미널 감성, 녹색 on 블랙에 완벽 |
| native | `"Inter"` | 정밀·미니멀, Cursor 웹 대시보드 자체 폰트 |

각 폰트는 **Regular (400)** 와 **SemiBold (600)** weight 2종만 번들한다.
번들 위치: `assets/fonts/<Family>-Regular.ttf`, `assets/fonts/<Family>-SemiBold.ttf`

> **주의:** Google Fonts에서 다운로드 시 반드시 **static** 아카이브를 사용한다.
> Variable font 아카이브(`SpaceGrotesk[wght].ttf` 형식)는 `QFontDatabase.applicationFontFamilies()`
> 반환 값이 Qt 버전에 따라 달라질 수 있어 family name 매칭이 실패할 수 있다.

> **구현 시 검증 필수:** 각 `.ttf` 로드 후 `applicationFontFamilies()` 반환값을 로그로 확인하여
> 위 `"font"` 키 값과 정확히 일치하는지 검증한다. 불일치 시 `_loaded_fonts`에 등록되지 않아
> 해당 테마가 OS 기본 폰트로 fallback된다.

---

## 2. native 테마 색상 팔레트

`cursor.com/settings` 기준으로 추출한 색상. 채도 없는 쿨 그레이 + near-black 배경.

```python
"native": {
    "name": "native",
    "font": "Inter",
    "bg_win":    (10, 10, 10),
    "bg_win2":   (4,  4,  4),    # bg_win과 6pt 차이로 시각적 구분 확보
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
}
```

---

## 3. 아키텍처 변경

### 3.1 THEMES dict — `"font"` 키 추가

각 테마 dict에 `"font": "<Family Name>"` 키를 추가한다. 이 키가 있고 폰트 로드에 성공했을 경우 해당 테마 선택 시 `_UI_FONT`가 갱신된다.

### 3.2 전역 상수 분리

기존 if/elif/else 블록에서 `_UI_FONT`를 설정하는 위치에 `_OS_DEFAULT_FONT`를 동시에 할당한다.

```python
# 기존
if sys.platform == "win32":
    _UI_FONT = "Segoe UI"
    ...

# 변경 후 — 두 변수를 동시에 설정
if sys.platform == "win32":
    _OS_DEFAULT_FONT = _UI_FONT = "Segoe UI"
elif sys.platform == "darwin":
    _OS_DEFAULT_FONT = _UI_FONT = "Helvetica Neue"
else:
    _OS_DEFAULT_FONT = _UI_FONT = "DejaVu Sans"
```

`_OS_DEFAULT_FONT`는 이후 절대 변경하지 않는다. `apply_theme()`에서 폰트 키가 없는 테마 전환 시 `_UI_FONT`를 `_OS_DEFAULT_FONT`로 복원한다.

### 3.3 폰트 사전 로드 — `_load_bundled_fonts(base: Path)`

```python
_loaded_fonts: set[str] = set()

def _load_bundled_fonts(base: Path) -> None:
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

`main()`의 `apply_theme()` 호출 **이전**에 실행한다.

**`base` 경로 결정:**

```python
if getattr(sys, "frozen", False):
    _load_bundled_fonts(Path(sys._MEIPASS))   # PyInstaller --add-data 압축 해제 위치
else:
    _load_bundled_fonts(_app_dir())            # 개발 시 소스 트리
```

> `_app_dir()`은 frozen 여부와 무관하게 EXE 옆 디렉터리를 반환한다.
> frozen 시 `--add-data`로 번들된 파일은 `sys._MEIPASS` 아래에 위치하므로
> 반드시 `sys._MEIPASS`를 사용해야 한다. `_app_dir()`을 frozen 상태에서 사용하면
> 폰트를 찾지 못해 모든 테마가 OS 기본 폰트로 fallback된다.
> (기존 아이콘 로드 코드 line ~3917의 `Path(sys._MEIPASS)` 패턴과 동일.)

### 3.4 `apply_theme()` 수정

```python
def apply_theme(name: str) -> None:
    global _THEME, _UI_FONT
    _THEME = THEMES.get(name, THEMES["light"])
    font_name = _THEME.get("font")
    if font_name and font_name in _loaded_fonts:
        _UI_FONT = font_name
    else:
        _UI_FONT = _OS_DEFAULT_FONT
```

### 3.5 테마 전환 시 폰트 반영 — `refresh_theme()` + `apply_scale()`

`_UI_FONT` 변경은 **기존에 생성된 `QFont` 객체에 자동으로 반영되지 않는다.**
`QFont(_UI_FONT, size)` 로 생성된 위젯(예: `CreditsPage`의 `_hero_used`, `_hero_of`,
`_cycle_lbl`, KV 행 레이블 등)은 `apply_scale()` 호출 시 QFont를 재생성한다.

따라서 테마 전환 흐름 `_set_theme()` → `apply_theme()` → `theme_changed.emit()` →
`_on_theme_changed()` → 각 page의 `refresh_theme()` 에서,
**폰트 변경이 발생한 경우** `refresh_theme()`가 `apply_scale(current_scale)`을 추가 호출해야 한다.

구현 방법: `apply_theme()` 이전 `_UI_FONT`를 저장해두고, 변경 발생 시 flag를 반환하거나,
각 page의 `refresh_theme()`에서 `apply_scale()`을 무조건 호출한다 (비용이 작으므로 후자 권장).

```python
# CreditsPage.refresh_theme() 예시
def refresh_theme(self):
    # ... 기존 색상 갱신 ...
    self.apply_scale(self._current_scale)  # 폰트 변경 반영
```

`apply_scale()`을 가진 모든 page/widget에 동일하게 적용한다.

### 3.6 STRINGS 추가

```python
"ko": { ..., "theme_native": "네이티브" }
"en": { ..., "theme_native": "Native" }
```

### 3.7 SettingsPage.THEMES_ORDER 수정

```python
THEMES_ORDER = [
    ("light",    "theme_light"),
    ("dark",     "theme_dark"),
    ("midnight", "theme_midnight"),
    ("matrix",   "theme_matrix"),
    ("native",   "theme_native"),
]
```

---

## 4. 폰트 파일 구성

```
assets/fonts/
  Nunito-Regular.ttf
  Nunito-SemiBold.ttf
  SpaceGrotesk-Regular.ttf
  SpaceGrotesk-SemiBold.ttf
  Raleway-Regular.ttf
  Raleway-SemiBold.ttf
  FiraCode-Regular.ttf
  FiraCode-SemiBold.ttf
  Inter-Regular.ttf
  Inter-SemiBold.ttf
```

모두 Google Fonts **static** 아카이브에서 다운로드. 라이선스: SIL OFL 1.1.
`assets/fonts/` 디렉터리를 git에 커밋한다.

`.gitattributes`에 아래 줄을 추가하여 바이너리로 처리한다:

```
*.ttf binary
```

---

## 5. 빌드 변경 (release.yml)

| 플랫폼 | 추가 플래그 |
|---|---|
| Windows | `--add-data "assets/fonts;assets/fonts"` |
| macOS | `--add-data "assets/fonts:assets/fonts"` |
| Linux | `--add-data "assets/fonts:assets/fonts"` |

---

## 6. 개발 모드 동작

`frozen`이 False일 때 `_load_bundled_fonts(_app_dir())`를 호출한다.
`assets/fonts/`가 존재하지 않으면 조용히 skip — 기존 동작 유지.

---

## 7. 변경 파일 요약

| 파일 | 변경 내용 |
|---|---|
| `cursor_hud.py` | `THEMES` dict 확장 (font 키 + native 테마), `_OS_DEFAULT_FONT` 분리, `_loaded_fonts`, `_load_bundled_fonts()`, `apply_theme()` 수정, `refresh_theme()` apply_scale 호출 추가, STRINGS/THEMES_ORDER 추가 |
| `assets/fonts/*.ttf` | 폰트 파일 10개 추가 |
| `.gitattributes` | `*.ttf binary` 추가 |
| `.github/workflows/release.yml` | 3개 플랫폼 `--add-data` 추가 |

---

## 8. 비고

- `_MONO_FONT`는 변경하지 않는다 (OS 기본 모노 폰트 유지).
- Fira Code는 모노스페이스지만 10~12px UI 레이블에서도 충분히 가독성이 있다.
- 폰트 로드 실패 시 `_loaded_fonts`에 등록되지 않으므로 `apply_theme()`의 fallback 로직이 자동으로 동작한다.
- `_cycle_theme()` → `_set_theme()` → `apply_theme()` 체인은 별도 처리 불필요. `_set_theme()`이 `apply_theme()` 호출 후 `theme_changed`를 emit하므로 폰트 갱신이 자동으로 전파된다.
