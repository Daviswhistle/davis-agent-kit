# Custom pets

Davis Agent Kit에 포함된 Codex custom pets입니다.

| Pet | ID | Description |
| --- | --- | --- |
| 아리 (Ari) | `ari` | 하늘빛 별꼬리를 가진 작은 흰 여우. Codex에서 기다리고 달리고 인사하며 함께해요. |
| Hwito | `hwito` | A tiny moon-bunny coding companion with a Go stone and a little laptop. |
| 모찌 | `mochi` | 분홍 귀와 동그란 흰 몸을 가진 사려 깊은 모찌 토끼 |

별도 설치 과정은 없습니다.

```bash
./scripts/install_codex.sh
```

위 기본 설치 명령이 `pets/` 아래에서 `pet.json`을 가진 모든 펫을 찾아 `${CODEX_HOME:-$HOME/.codex}/pets/`에 함께 설치합니다. 이미 같은 kit의 펫이 복사되어 있으면 그대로 인정하고, 다른 내용의 같은 ID 펫은 덮어쓰지 않습니다.

새 펫을 추가할 때는 `pets/<id>/` 아래에 `pet.json`과 해당 sprite 파일을 넣으면 됩니다. 루트 README나 설치 목록을 따로 수정할 필요는 없습니다.
