# Davis Agent Kit

한국어로 작업하는 Codex가 사용자의 목적과 판단 기준을 일관되게 적용하도록 만드는 전역 지침 + reusable skills + custom pets 묶음입니다.

단순히 요청을 수행하는 데서 끝나지 않고, 실제 목적·근본 원인·완료 기준을 확인하며 필요한 경우 전문 workflow를 자동으로 불러오도록 구성되어 있습니다.

## 설치

저장소 루트에서 실행합니다.

```bash
./scripts/install_codex.sh
```

설치 후에는 새 Codex 세션을 시작하세요.

설치 상태만 확인하려면:

```bash
./scripts/install_codex.sh --check
```

다른 위치에서 시험하거나 격리하려면:

```bash
./scripts/install_codex.sh \
  --codex-home /tmp/codex-home \
  --skills-home /tmp/agents/skills
```

## 무엇이 설치되나

기본 설치 명령 하나로 다음 항목을 함께 설치합니다.

- **Global instructions** — `${CODEX_HOME:-$HOME/.codex}/AGENTS.md`
- **User skills** — `$HOME/.agents/skills/<skill-name>`
- **Custom pets** — `pets/` 아래에서 `pet.json`을 가진 모든 펫

새 skill이나 pet을 개별적으로 골라 설치할 필요는 없습니다. 이 kit가 관리하는 항목은 설치기가 자동으로 발견합니다.

## 사용

대부분의 기능은 별도 명령 없이 Codex가 작업에 맞는 skill을 선택해 사용합니다.

예를 들어 번역, 소프트웨어 구현, 장문 글쓰기처럼 품질 기준이 다른 작업은 각각 전용 skill의 절차와 검증 규칙을 사용합니다.

프로젝트의 확인된 맥락을 필요한 구간만 읽고 갱신하려면:

```text
$section-store 이 프로젝트의 확인된 지식을 PROJECT.md 하나로 관리하고 필요한 섹션만 읽게 해줘.
```

기존 `section-store` 원본이 있는 프로젝트에서는 색인으로 필요한 맥락을 찾는 것이 기본 경로입니다. 원본이 없는 프로젝트에 파일을 자동으로 만들지는 않습니다. 결정을 바꾸는 사실은 기록된 코드·문서·결과 근거의 현재 상태와 대조합니다.

## Skills

현재 포함된 주요 skill은 다음과 같습니다.

- `section-store` — 단일 Markdown 원본의 자동 색인, 안정적 ID 기반 부분 읽기·수정과 버전 충돌 검사
- `translation-quality` — 비단순 한국어 번역, transcript·재무보고서 번역, source/numeric/format QA
- `handoff-agent-builder` — Codex가 자동 발견하는 repo-local handoff skill 설계와 멀티턴 검증
- `software-engineering` — 소프트웨어 변경의 구현·검증과 위임 시의 자원 후보, 필요할 때 CRA/TCA
- `writing-quality` — 글쓰기 자체가 품질 병목인 원고·장문 분석·게시용 문서 작성과 편집

Codex는 먼저 skill metadata를 보고 필요한 skill을 선택한 뒤, 선택된 `SKILL.md`와 필요한 reference만 읽습니다. 전역 원칙은 `AGENTS.md`에, 조건부 workflow는 각 skill 내부에 둡니다.

위임과 팀 구성은 주 모델이 과업에 맞게 결정하며, 직무 분리와 최종 수락 책임은 전역 지침이 정합니다.

## Custom pets

기본 설치 명령이 `pets/` 아래의 모든 custom pet을 자동으로 설치합니다.

현재 제공되는 pet 목록과 새 pet 추가 방법은 [`pets/`](./pets/)를 참고하세요.

새 pet은 `pets/<id>/pet.json`과 sprite 파일을 추가하면 다음 설치부터 자동으로 포함됩니다. 루트 README나 설치 목록을 별도로 수정할 필요는 없습니다.

## 기본 동작 원칙

목적 소유와 주인·파트너 관점은 별도 skill이 아니라 전역 `AGENTS.md`의 기본값입니다. 모델은 표면 과업보다 실제 결과를 보고, 잘못된 전제를 고치며, 근본 원인과 높은 레버리지의 개선을 찾습니다.

저장소 변경 작업은 검증·커밋·일반 push까지 마무리하는 것이 기본입니다. 행동별 권한과 별도 승인 기준은 전역 [`AGENTS.md`](./AGENTS.md)가 정합니다.

긴 작업에서 continuity가 실제 문제일 때만 작은 checkpoint를 남기고, 재개할 때 현재 저장소·산출물·검증과 다시 대조합니다.

## 설치 관리

### 기존 override

전역 위치의 `AGENTS.override.md`에 내용이 있으면 Codex는 일반 `AGENTS.md` 대신 override를 선택합니다.

설치기는 다른 지침을 담은 override를 감지하면 링크를 만들기 전에 중단합니다. 기존 override를 자동 삭제·덮어쓰기·병합하지 않습니다.

빈 파일·공백뿐인 파일이나 kit의 규범 원본 `AGENTS.md` 자체를 가리키는 링크는 허용합니다.

저장소 안의 프로젝트용 `AGENTS.override.md`는 전역 검사 대상이 아니며 설치하지 않습니다.

### 이전 설치에서 migration

이 kit의 과거 버전은 `${CODEX_HOME:-$HOME/.codex}/skills`를 사용했습니다. Codex가 이 위치를 호환 목적으로 읽을 수 있기 때문에, 과거 kit skill이 남아 있으면 중복 로딩을 막기 위해 설치를 중단합니다.

이 경우 메시지에 표시된 과거 링크를 확인해 제거한 뒤 다시 실행하세요.

배포에서 제거된 skill이 user skills 또는 과거 Codex skills 위치에 남아 있어도 설치와 `--check`가 실패합니다. 끊어진 링크도 검사합니다. 메시지에 표시된 경로가 이 kit의 과거 설치인지 확인한 뒤 해당 링크를 제거하세요. 설치기는 기존 파일이나 디렉터리를 자동 삭제하지 않습니다.

`--check`는 kit의 전역 `AGENTS.md`, user skill 링크, custom pet 설치 상태와 전역 override 우선순위를 검사합니다. 실제 Codex 세션의 전체 지침 로딩이나 프로젝트별 override까지 검증한다는 뜻은 아닙니다.

## Advanced

### 단일 파일 프로젝트 지식

프로젝트 지식·규칙·결정을 하나의 원본과 자동 색인으로 관리하려면:

```text
$section-store 이 프로젝트의 확인된 지식을 PROJECT.md 하나로 관리하고 필요한 섹션만 읽게 해줘.
```

기존 원본이 section-store 마커를 사용한다면 직접 실행할 수도 있습니다.

```bash
python3 ~/.agents/skills/section-store/scripts/store.py build --source PROJECT.md
python3 ~/.agents/skills/section-store/scripts/store.py list --source PROJECT.md --query "검증"
python3 ~/.agents/skills/section-store/scripts/store.py read --source PROJECT.md --id validation
```

`PROJECT.md.index.json`은 재생성 가능한 색인입니다. 원본의 의미·요약은 작성자가 명시하고, 줄·byte 범위와 해시는 코드가 계산합니다. helper를 통한 본문 수정은 색인도 갱신하며 직접 편집한 뒤에는 `build`가 필요합니다. 오래된 색인이나 버전 충돌은 거부합니다. 전체 파일을 모델에 전달하지 않지만 원본 버전 확인용 전체 파일 해시 I/O는 수행합니다.

색인 검증은 문서 내용과 코드·운영 상태의 일치를 보증하지 않습니다. 핵심 사실에 근거 위치·확인 버전 또는 결과 시점·적용 범위를 기록하고, 관련 근거가 바뀌면 본문과 검색 메타데이터도 갱신합니다.

원본 형식, 생성·수정 명령과 복구 경계는 [`section-store`](./skills/section-store/SKILL.md)를 참고하세요. 기존 코드나 전역 지침을 자동으로 하나의 파일로 합치지는 않습니다.

### 모델 운용 범위

- `software-engineering`의 직무별 자원 후보와 launcher 설정은 위임이 별도로 타당할 때만 적용합니다. 후보를 쓰기 위해 worker를 만들지 않습니다.

### AGY 품질 보정

Antigravity CLI(`agy`)에도 이 kit의 보정 지침을 전역으로 적용하려면:

```bash
python3 scripts/install_agy.py
```

설치 상태만 확인하려면:

```bash
python3 scripts/install_agy.py --check
```

설치기는 AGY의 전역 rules 디렉터리인 `~/.gemini/antigravity-cli/rules/`에 `davis-agent-kit.md` 심링크를 만듭니다. 같은 이름의 기존 rule이 있으면 덮어쓰지 않고 중단합니다.

이 rule은 Codex용 skill routing이나 모델 선택 규칙을 AGY에 복제하지 않습니다. Gemini 계열 모델이 상위 수준의 그럴듯한 답에서 멈추지 않도록 전제·실패 모드·실제 control/data flow·downstream 효과·필수 검증을 끝까지 확인하게 보정합니다.

적용 뒤에는 새 AGY 세션을 시작하세요.

## 검증

```bash
python3 scripts/validate_kit.py
```

CI도 같은 진입점을 사용합니다.

검증 대상은 skill frontmatter/resource 경로, installer 계약, 실제 helper와 실행 코드의 tests입니다. 특정 Markdown 문구나 모델 판단 품질을 정적 테스트로 고정하지 않습니다.

## Repository structure

```text
davis-agent-kit/
├── AGENTS.md
├── AGENTS.override.md
├── providers/
│   └── agy/
│       └── davis-agent-kit.md
├── skills/
│   ├── section-store/
│   ├── translation-quality/
│   ├── handoff-agent-builder/
│   ├── software-engineering/
│   └── writing-quality/
├── pets/
├── scripts/
├── tests/
└── .github/
```

- `AGENTS.md` — 모든 작업의 기본 자세, 권한, 완료 기준과 skill routing
- `AGENTS.override.md` — 이 저장소 자체를 수정할 때의 관리 규칙
- `providers/agy/davis-agent-kit.md` — AGY에서 Gemini 계열 모델의 누락·검증 부족을 보정하는 선택형 전역 rule
- `skills/` — 반복 workflow와 그 workflow에만 필요한 references, agents, scripts, tests
- `pets/` — Codex custom pets
- `scripts/install_codex.py` — 전역 AGENTS, user skills, custom pets 설치
- `scripts/validate_kit.py` — active skill 계약과 실행 가능한 tests/helpers 검증

Codex의 자동 지침 로딩 계약에 맞춰 성격·말투·상호작용 원칙도 전역 `AGENTS.md`에 둡니다. 별도 `SOUL.md`를 추가해 자동 로딩되지 않는 문서를 만들지 않습니다.

과거 의사결정 기록, raw model trace, 수동 평가 archive 같은 유지보수용 기록은 제품 트리에 두지 않고 Git history와 PR에서 관리합니다.

## 수정 원칙

1. 현재 행동을 바꾸는 최소 규범 원본과 직접 연결된 실행물만 수정합니다.
2. 실제 실패보다 큰 방어 시스템을 만들지 않습니다.
3. helper가 필요 없어진다면 helper를 지키기 위한 테스트도 함께 없앱니다.
4. 행동 품질 변화는 필요할 때 대표 작업으로 비교하고 결과는 PR에 요약합니다.
