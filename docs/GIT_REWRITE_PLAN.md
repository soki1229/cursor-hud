# Git 히스토리 정리 및 Force Push 플랜

## 실행된 결과: 베타 첫 버전 (v1.0.0-beta.1)

아래 전략에 따라 **전체 히스토리를 합친 뒤 계층화된 커밋으로 재구성**했고, 마지막 커밋에 **v1.0.0-beta.1** 태그를 붙였다.

- **스크립트**: `scripts/rewrite_history_to_beta.sh`  
- **백업 브랜치**: `backup-before-rewrite` (기존 master 상태)

**새 히스토리 (5 commits):**

| 순서 | 커밋 메시지 |
|------|-------------|
| 1 | chore: project scaffold (.gitignore, README, screenshots) |
| 2 | chore: add assets (screenshot images) |
| 3 | feat: Cursor HUD app (3-tab, themes, EXE-safe) |
| 4 | ci: add release workflow and CHANGELOG |
| 5 | fix, feat: robust parsing, theme/settings, i18n, UI (v1.0.1) |

- **태그**: `v1.0.0-beta.1` → 5번째 커밋 (현재 master tip)

**푸시:**  
`git push origin master --force-with-lease` 후  
원격에 기존 v1.0.0 / v1.0.1 태그가 있으면 제거·재푸시:  
`git push origin :refs/tags/v1.0.0` (필요 시), `git push origin v1.0.0-beta.1`

**5번 커밋을 더 세분화하려면:**  
`git rebase -i 6f51047` → 5번 커밋을 `edit`으로 두고,  
`git reset HEAD^` 후 `git add -p cursor_hud.py` 로 논리 단위로 나눠 커밋하면 된다.

---

## (참고) 이전 상태 요약

| 커밋 | 메시지 | 내용 |
|------|--------|------|
| `0ad9263` | Initial release: Cursor HUD v1.0.0 | 프로젝트 초기 (README, assets, cursor_hud.py 1541줄 등) |
| `4532543` | Add release workflow | `.github/workflows/release.yml`, CHANGELOG.md |
| `249578d` | temp commit for update | **cursor_hud.py 단일 파일 대규모 수정** (v1.0.1 픽스 + 사용성 개선이 한꺼번에 섞임) |

- **태그**: `v1.0.0`, `v1.0.1` (원격에 이미 푸시된 상태일 수 있음)
- **목표**: `249578d`를 논리 단위로 쪼개고, 정리된 히스토리를 `force push`로 원격에 반영

---

## 버전/태그 전략 (선택)

히스토리 정리 후 “어디를 정식 1.0으로 볼지”를 정하는 두 가지 방식이다.

### A. 새 v1.0.0으로 리셋

- **의미**: 기존 v1.0.0 / v1.0.1 태그는 “없었던 것”처럼 하고, **정리된 히스토리에서 “첫 안정 버전”**을 새로 `v1.0.0`으로 둔다.
- **방법**  
  - 리베이스로 커밋 세분화까지 끝낸 뒤, **첫 안정이라고 생각하는 커밋**(예: 파싱/데이터 모델 픽스까지 모두 반영된 시점)에 `v1.0.0` 태그를 붙인다.  
  - 기존 `v1.0.0`, `v1.0.1` 태그는 로컬/원격에서 제거하고, 필요하면 `v1.0.1`은 그 위 커밋에 다시 붙인다.
- **장점**: 깔끔한 출발. “v1.0.0 = 우리가 인정하는 첫 정식 릴리즈”가 명확해진다.
- **단점**: 이미 v1.0.0/v1.0.1을 받은 사람이 있다면, “같은 버전 번호가 다른 커밋을 가리키게 되었다”는 점을 릴리즈 노트 등에 한 줄 적어 두는 게 좋다.

### B. 베타 네이밍으로 “정식 아님” 드러내기

- **의미**: 과거에 붙인 태그를 “베타”로 재해석하고, **정식 1.0은 그 다음**에 둔다.
- **방법 예시**
  - **옵션 1**: 기존 v1.0.0 → `v1.0.0-beta.1`, 기존 v1.0.1 → `v1.0.0-beta.2`,  
    리베이스 후 “첫 안정” 커밋 → `v1.0.0` (또는 `v1.0.1`).
  - **옵션 2**: 초기 릴리즈를 `v0.9.0`으로 두고, 파싱/사용성 픽스 반영 후를 `v1.0.0`으로 둔다.  
    (히스토리 재작성 시 “Initial release” 커밋에 `v0.9.0`, 정리 후 첫 안정에 `v1.0.0`.)
- **장점**: “그때 건 베타였고, 지금이 진짜 1.0”이 버전 번호만 봐도 드러난다. 기존 사용자에게도 설명하기 쉽다.
- **단점**: 태그 이름을 바꾸거나 새로 붙이는 작업이 조금 더 필요하다.

### 권장

- **이미 v1.0.0/v1.0.1을 공개 배포했고**, “그건 준비가 덜 된 상태였다”는 걸 드러내고 싶다 → **B(베타 네이밍)** 가 더 자연스럽다.
- **배포 범위가 좁거나**, “지금부터가 진짜 1.0”이라고 단순하게 정리하고 싶다 → **A(새 v1.0.0)** 도 무방하다.

정한 전략에 맞춰 아래 Phase 4·5의 태그 생성/푸시 단계에서 `v1.0.0`, `v1.0.1`, `v1.0.0-beta.x` 등을 어떻게 붙일지만 조정하면 된다.

---

## Phase 0: 사전 준비 (백업·안전장치)

1. **원격 상태 확인**
   ```bash
   git fetch origin
   git log origin/master --oneline -5
   ```
   - 로컬과 원격이 같은지 확인 (다른 사람이 푸시했을 수 있음).

2. **백업 브랜치 생성**
   ```bash
   git branch backup-before-rewrite   # 현재 HEAD 보존
   git tag backup-tag-before-rewrite  # 태그로도 한 번 더 보존 (선택)
   ```

3. **협업자 여부**
   - `origin/master`를 쓰는 사람이 본인만이면 force push 가능.
   - 다른 사람이 있다면 사전 공지 후, 그들이 `git fetch && git reset --hard origin/master` 같은 방식으로 맞출 수 있도록 안내.

---

## Phase 1: 리베이스 시작 지점 정하기

- **유지할 커밋**: `0ad9263` (Initial release), `4532543` (Add release workflow)  
  → 이 두 개는 그대로 두고, **그 위에서** “temp commit” 하나를 여러 개로 쪼갠다.

**실제 작업**: `4532543`(Add release workflow)을 기준으로, 그 다음 커밋 하나(`249578d`)를 분해하는 **interactive rebase**를 한다.

```bash
git rebase -i 4532543
```

- 에디터에서 `249578d` 커밋 한 줄이 보일 것이다.
- 해당 줄을 `pick` → `edit`으로 바꾸고 저장하면, rebase가 그 커밋에서 멈춘다.

---

## Phase 2: “temp commit” 내용 분해 (커밋 세분화)

rebase가 `249578d`에서 멈춘 상태에서, **작업 디렉터리에는 v1.0.1 반영 후의 전체 변경이 들어 있다**.  
이걸 **되돌린 뒤**, 같은 내용을 여러 번에 나눠서 커밋한다.

### 2.1 현재 변경 전부 unstage

```bash
git reset HEAD^
```

- `249578d`가 취소되고, 변경 사항은 전부 working tree + index에 그대로 남는다.

### 2.2 논리 단위로 나눠서 커밋 (권장 순서)

아래 순서는 “의존성·가독성” 기준 제안이다. 실제로 diff를 보면서 **한 번에 하나의 주제만** 커밋하면 된다.

| 순서 | 커밋 메시지 (예시) | 포함할 변경 요약 |
|------|--------------------|------------------|
| 1 | `fix: robust JSON/API parsing and credit data model` | `_safe_int` / `_safe_float`, `parse_data` 수정 (summary/profile null, included/bonus/budget/remain, plan.limit/remaining, is_team), API 응답 타입 방어 |
| 2 | `fix: handle temp file and API log level` | `traceback` 제거, tempfile `fd` close 시 `OSError` 처리, GET 요청 로그를 `log.info` → `log.debug` |
| 3 | `feat: theme track_bg and window size constants` | `track_bg()` 추가, THEMES에 `track_bg`, WIN_W/WIN_W_MAX/WIN_H/ARC_MIN_W, `_preset_win_w` |
| 4 | `feat: settings for window position, size, pin-on-top, mini mode` | DEFAULT_SETTINGS에 `win_x`/`win_y`/`win_w`/`mini_mode`/`pin_on_top`, `show_team`/`show_od` → `show_personal`/`show_org` |
| 5 | `i18n: credit labels, status badges, and section strings` | STRINGS에 remain_label, bonus_saved, status_*, row_*, org_section, auto_pct, api_pct, show_personal/show_org, pin_top, free_plan_notice 짧게 등 |
| 6 | `feat: date and cycle helpers (fmt_date, days_left_text)` | `_MONTHS_EN`, `fmt_date`, `days_left_text` |
| 7 | `refactor: UI and credits display for new data model` | 크레딧/OD/팀 표시 로직, 새 데이터 모델에 맞춘 위젯·레이아웃 변경 (나머지 cursor_hud.py 변경) |
| 8 | `chore: comment and import cleanup (English)` | 주석 한글→영어, 사용하지 않는 import 정리 (QCheckBox 등), `qInstallMessageHandler` 등 |

**작업 방법 (각 주제마다)**:

- 해당 주제에 해당하는 파일/부분만 선택해서 스테이징:
  ```bash
  git add -p cursor_hud.py
  ```
  또는 에디터에서 해당 블록만 골라서 저장 후 `git add cursor_hud.py`.
- 한 번에 하나의 논리 커밋만:
  ```bash
  git commit -m "fix: robust JSON/API parsing and credit data model"
  ```
- 1~8번 순서대로 반복.

**실제로 쪼개기 어렵다면**:

- 최소한 **1번(파싱/데이터 모델)** 과 **나머지(UI/설정/문자열 등)** 2개로 나누는 것만 해도 히스토리가 크게 나아진다.

---

## Phase 3: CHANGELOG / 버전 태그 (선택)

- `CHANGELOG.md`에 v1.0.1 항목이 있다면, 위에서 만든 “fix/feat” 커밋들과 맞는지 한 번 확인.
- 필요하면 `docs/` 또는 프로젝트 루트에 “v1.0.1 내역”을 요약해 두면, 나중에 태그만 다시 붙이기 쉬워진다.

---

## Phase 4: Rebase 완료 및 태그 재정의

1. **Rebase 마무리**
   ```bash
  git rebase --continue
  ```
   - 더 이상 “edit”할 커밋이 없으면 rebase가 끝난다.

2. **태그 재정의**  
   위 **버전/태그 전략**에서 A/B 중 선택한 대로 적용.
   - **A(새 v1.0.0)**: 첫 안정 커밋에 `v1.0.0`, 그 위에 추가 픽스가 있으면 `v1.0.1`. 기존 v1.0.0/v1.0.1 태그는 제거 후 다시 붙인다.
   - **B(베타)**: 예) 첫 안정 커밋에 `v1.0.0` 하나만 붙이고, 필요 시 예전 포인트에 `v1.0.0-beta.1`, `v1.0.0-beta.2` 같은 태그를 남겨 둘 수 있다.
   ```bash
  git tag -d v1.0.1   # 로컬 기존 태그 삭제 (필요 시)
  git tag v1.0.0      # 선택한 “첫 안정” 커밋에서
  # 또는  git tag v1.0.1  (최신 HEAD가 v1.0.1인 경우)
  ```

---

## Phase 5: Force Push 및 원격 태그 정리

1. **원격 덮어쓰기**
   ```bash
  git push origin master --force-with-lease
  ```
   - `--force-with-lease`는 “원격이 내가 아는 상태일 때만” 덮어써서 실수를 줄인다.

2. **원격에 이미 v1.0.1 태그가 있었다면**
   ```bash
  git push origin :refs/tags/v1.0.1   # 원격 v1.0.1 삭제
  git push origin v1.0.1             # 새 v1.0.1 푸시
  ```

3. **확인**
   ```bash
  git log --oneline -10
  git log origin/master --oneline -10
  ```

---

## 롤백이 필요할 때

- 로컬만 되돌리기:
  ```bash
  git reset --hard backup-before-rewrite
  ```
- 원격을 예전 상태로 다시 덮어쓰려면 (백업 브랜치를 푸시):
  ```bash
  git push origin backup-before-rewrite:master --force-with-lease
  ```

---

## 요약 체크리스트

- [ ] Phase 0: `git fetch`, 백업 브랜치/태그 생성
- [ ] Phase 1: `git rebase -i 4532543`, `249578d`를 `edit`
- [ ] Phase 2: `git reset HEAD^` 후 1~8번 논리 커밋으로 분할
- [ ] Phase 3: CHANGELOG 확인 (선택)
- [ ] Phase 4: `git rebase --continue`, 필요 시 `v1.0.1` 태그 재생성
- [ ] Phase 5: `git push origin master --force-with-lease`, 원격 태그 정리

이 순서대로 진행하면 “temp commit”이 세분화된 커밋들로 정리되고, force push로 원격 히스토리를 깔끔하게 맞출 수 있다.
