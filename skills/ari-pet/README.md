# 아리의 별정원 — Ari Pet

별꼬리를 흔드는 작은 흰 여우, 아리를 위한 선택형 Codex 동반자 스킬입니다. Codex 앱의 네이티브 펫은 `pets/ari/`에 따로 포함되어 있으며, 이 스킬은 별정원 브라우저 화면·터미널 카드·상호작용·경험치를 제공합니다.

## 설치

저장소 루트에서 기존 kit 설치 명령을 사용합니다.

```bash
./scripts/install_codex.sh
```

설치기는 `~/.agents/skills/ari-pet`에 스킬을, `${CODEX_HOME:-~/.codex}/pets/ari`에 네이티브 펫을 링크합니다. **설치만으로 Codex hooks나 설정 파일을 수정하지 않습니다.** Codex를 재시작하고 설정의 Pets에서 `아리 (Ari)`를 선택하면 네이티브 펫을 사용할 수 있습니다.

브라우저 별정원은 사용자가 원할 때만 실행합니다.

```bash
python3 ~/.agents/skills/ari-pet/ari.py serve --open
```

기본 주소는 `http://127.0.0.1:8765`이며 표준 라이브러리 기반 Python 3.9+ 외에 의존성이 없습니다. WSL에서 실행하면 Codex가 돌아가는 **WSL 환경**에 설치하고, Windows 브라우저에서 해당 로컬 주소를 엽니다(WSL localhost 전달이 가능한 환경).

Codex 채팅에서 `$ari-pet 보여줘`, `$ari-pet 쓰다듬어줘`라고 부르거나 다음 명령을 직접 실행할 수 있습니다.

```bash
python3 ~/.agents/skills/ari-pet/ari.py card
python3 ~/.agents/skills/ari-pet/ari.py pet
python3 ~/.agents/skills/ari-pet/ari.py feed
python3 ~/.agents/skills/ari-pet/ari.py play
python3 ~/.agents/skills/ari-pet/ari.py rest
```

## Codex 이벤트 연결 (옵트인)

브라우저 상태가 Codex 작업에 반응하도록 하려면 **사용자가 명시적으로** 이벤트 훅을 켭니다.

```bash
python3 ~/.agents/skills/ari-pet/install_hooks.py enable
```

Codex에서 `/hooks` 명령을 통해 훅 신뢰 확인을 요구할 수 있습니다. 기존 훅은 병합·보존되고 변경 직전 `hooks.json.ari-backup-*` 백업이 생성됩니다. SessionStart, UserPromptSubmit, PreToolUse, PermissionRequest, Stop, Interrupt 이벤트를 관찰합니다. 입력에서 작업 내용과 프롬프트를 저장하지 않고 종류와 해시된 턴 ID만 사용합니다. Codex 버전이나 실행 환경에 따라 이벤트 호출 가능 여부가 다를 수 있습니다.

훅만 해제하려면:

```bash
python3 ~/.agents/skills/ari-pet/install_hooks.py disable
```

이 명령은 kit가 설치한 스킬·네이티브 펫·기존 진행 상태를 삭제하지 않습니다. 훅을 쓰기 싫다면 Codex의 최상위 `notify` 설정에 `python3 /absolute/path/to/ari.py notify`를 연결하여 **턴 완료만** 관찰할 수도 있습니다. 기존 `notify` 설정은 덮어쓰지 마세요. `notify`와 훅의 Stop을 동시에 켜면 일부 Codex 버전에서 중복 XP가 발생할 수 있습니다.

## 동작과 데이터

- Codex 이벤트가 실제로 들어올 때마다 상태가 바뀝니다. 작업 완료 시 12XP를 얻으며 Lv.4에 별지기 여우, Lv.8에 성운 여우 칭호가 열립니다.
- 쓰다듬기·별사탕·놀이·휴식은 사용자의 명시적 조작에만 반응합니다. 돌보지 않아도 벌점이나 사망 기믹은 없습니다.
- 상태는 `~/.ari-pet/state.json` 또는 `ARI_PET_HOME`에 로컬 저장합니다. 프롬프트, 소스 코드, 명령, API 키, 원시 세션 ID는 저장하지 않습니다.
- 로컬 서버는 127.0.0.1에만 바인딩하며, API는 고정된 조작만 허용합니다. 외부 서비스나 추가 AI API를 호출하지 않습니다.
- Codex 앱의 네이티브 펫과 브라우저 별정원은 **별도 UI**입니다. 상태/XP는 브라우저 별정원의 기능이고 네이티브 Codex 아바타에 동기화되지는 않습니다.

## 검증

```bash
python3 -m unittest discover -s skills/ari-pet/tests -v
python3 scripts/validate_kit.py
```
