# Custom pets

Davis Agent Kit에 포함된 선택형 Codex custom pet입니다. 펫은 kit의 동작과 무관하며 기본 설치기에 포함되지 않습니다.

## Available pets

| Pet | ID | Description |
| --- | --- | --- |
| Hwito | `hwito` | A tiny moon-bunny coding companion with a Go stone and a little laptop. |
| 모찌 | `mochi` | 분홍 귀와 동그란 흰 몸을 가진 사려 깊은 모찌 토끼 |

각 펫의 이름과 설명은 해당 디렉터리의 `pet.json`을 기준으로 합니다. 새 펫을 추가할 때 루트 README에 별도 설치 섹션을 추가할 필요는 없습니다.

## List

저장소 루트에서 현재 포함된 펫을 확인합니다.

```bash
python3 scripts/install_pet.py --list
```

## Install

원하는 펫의 ID를 지정합니다.

```bash
python3 scripts/install_pet.py mochi
```

기본 설치 위치는 `${CODEX_HOME:-$HOME/.codex}/pets/<pet-id>`입니다. 다른 Codex home에 설치하려면:

```bash
python3 scripts/install_pet.py mochi --codex-home /tmp/codex-home
```

기존 같은 ID의 펫이 kit와 동일하면 그대로 유지합니다. 내용이 다르면 덮어쓰지 않고 중단합니다.

Codex에서 custom pet 목록을 새로고침한 뒤 설치한 펫을 선택합니다.

## Check

설치된 펫이 현재 kit의 원본과 같은지 확인합니다.

```bash
python3 scripts/install_pet.py mochi --check
```

Custom pet은 선택 설치 항목이므로 `./scripts/install_codex.sh --check`의 검증 대상에는 포함되지 않습니다.
