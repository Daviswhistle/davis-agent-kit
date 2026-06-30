# Davis Agent Kit

한국어로 작업하는 에이전트가 사용자의 판단 기준과 작업 습관을 따라 사고하고 행동하도록 만드는 철학과 원칙 중심 운영 키트입니다.

최종 목적은 반복 작업에서 드러난 사고방식, 판단 기준, 우선순위, 품질 기준, 검증 습관을 새 환경에서도 재현 가능한 형태로 남기는 것입니다.

## 철학과 원칙

이 레포의 최상위 기준은 [PHILOSOPHY.md](PHILOSOPHY.md)입니다. 철학은 필요한 것을 잃지 않는 가장 단순한 형태를 찾는 사고방식입니다.

[PRINCIPLES.md](PRINCIPLES.md)는 철학을 작업에 적용하기 위한 변하지 않을 소수의 판단 기준입니다.

가이드라인, 스킬, 체크리스트, 템플릿, 테스트, 폴백 규칙은 원칙을 현재 환경에 적용하는 실행물입니다. 실행물은 실제 작업과 검증 결과에 따라 계속 수정합니다.

## 기본 구조

```text
davis-agent-kit/
  PHILOSOPHY.md # 에이전트가 따라야 할 최상위 사고방식
  PRINCIPLES.md # 변하지 않을 소수의 판단 기준
  AGENTS.md     # 전역 지침 원본
  GEMINI.md     # 전역 지침 원본
  guidelines/   # 원칙에서 내려온 적용 지침
  checklists/   # 완료 전 검수 기준
  templates/    # 글, 리서치, 리뷰 등 출력 형식 템플릿
  skills/       # 독립 Codex skill 원본
  examples/     # 좋은 결과물과 나쁜 결과물 예시
  user-model/   # 작업 재현성에 필요한 사용자 선호와 품질 기준
  decisions/    # 왜 이렇게 정했는지 남기는 결정 기록
  inbox/        # 아직 정리되지 않은 원칙, 피드백, 아이디어
  scratch/      # 임시 작업 공간, git 제외
  private/      # 토큰, 계정 정보, 비공개 원문 등 공개하면 안 되는 자료, git 제외
```

## 운영 방식

1. `PHILOSOPHY.md`에는 에이전트가 따라야 할 최상위 사고방식을 둡니다.
2. `PRINCIPLES.md`에는 변하지 않을 소수의 판단 기준만 둡니다.
3. 전역 지침 파일은 각 파일이 스스로 정의한 역할을 먼저 읽고 관리합니다.
4. 실제 Codex 스킬은 `skills/<skill-name>/SKILL.md` 형태로 독립 유지합니다.
5. 반복해서 지적된 문제는 먼저 철학, 원칙, 가이드라인, 실행물 중 어디에 속하는지 분류합니다.
6. 핵심 원칙으로 올릴 수 없는 항목은 `guidelines/`, `checklists/`, `skills/`, `templates/`, `inbox/` 중 맞는 곳에 둡니다.
7. 스킬은 실제 작업에 적용하고 실패 지점을 반영한 뒤 고정합니다.
8. 좋은 결과물만 저장하지 말고 반복 실수를 막는 나쁜 예시와 검수 기준도 함께 남깁니다.
9. 사용자와 작업하며 새로 파악한 선호와 품질 기준은 작업 재현성에 직접 도움이 될 때만 `user-model/`에 근거와 함께 기록합니다.
10. push, 배포, 원격 레포 rename처럼 외부 상태를 바꾸는 작업은 현재 적용 중인 전역 지침과 사용자의 명시 요청을 따릅니다.

## 검증

루트 문서 계층과 스킬 구조 계약은 아래 명령으로 검증합니다.

```bash
python3 -m unittest discover
```

스킬별 helper와 계약 테스트는 해당 스킬의 `tests/`에서 관리합니다.

## 수정 전 safe sync

에이전트가 이 레포를 수정하기 전에는 원격 변경을 먼저 확인합니다. 목표는 로컬 변경과 원격 변경을 모두 보존한 상태로 수정 가능한 기준점을 만드는 것입니다.

```bash
cd "$HOME/.codex/davis-agent-kit"

if [ -n "$(git status --porcelain)" ]; then
  git status --short
  printf '%s\n' "local changes exist; inspect and commit intended changes first"
else
  git fetch origin main
  git pull --ff-only origin main
fi
```

로컬 변경이 있으면 먼저 `git diff`와 `git diff --cached`로 내용을 확인합니다. 의도된 변경은 관련 파일만 stage해서 커밋 가능한 단위로 보호한 뒤 원격 변경을 가져옵니다.

```bash
git add <intended-files>
git commit -m "<message>"
git fetch origin main
git rebase origin/main
```

원격과 로컬이 갈라져 fast-forward가 불가능하면 rebase로 로컬 커밋을 원격 최신 커밋 위에 다시 적용합니다. 충돌이 나면 양쪽 변경 의도를 확인해 해소하고, 검증한 뒤 `git rebase --continue`로 진행합니다. push는 명시 요청이 있을 때 수행합니다.

## 설치

권장 설치 방식은 레포 전체를 Codex 설정 디렉터리에 연결하는 것입니다. 이렇게 설치하면 `AGENTS.md`가 기준 원본의 `PHILOSOPHY.md`, `PRINCIPLES.md`, `guidelines/`, `checklists/`까지 참조할 수 있습니다.

기존 `~/.codex/AGENTS.md`나 같은 이름의 스킬 폴더를 보존해야 한다면 설치 전에 백업하세요.

```bash
KIT_DIR="$(pwd)"

mkdir -p "$HOME/.codex/skills"

if [ -e "$HOME/.codex/davis-agent-kit" ] && [ ! -L "$HOME/.codex/davis-agent-kit" ]; then
  printf '%s\n' "$HOME/.codex/davis-agent-kit exists and is not a symlink"
  exit 1
fi

rm -f "$HOME/.codex/davis-agent-kit"
rm -f "$HOME/.codex/AGENTS.md"
rm -rf "$HOME/.codex/skills/translation-quality"
rm -rf "$HOME/.codex/skills/handoff-agent-builder"
rm -rf "$HOME/.codex/skills/software-engineering"

ln -s "$KIT_DIR" "$HOME/.codex/davis-agent-kit"
ln -s "$HOME/.codex/davis-agent-kit/AGENTS.md" "$HOME/.codex/AGENTS.md"
ln -s "$HOME/.codex/davis-agent-kit/skills/translation-quality" "$HOME/.codex/skills/translation-quality"
ln -s "$HOME/.codex/davis-agent-kit/skills/handoff-agent-builder" "$HOME/.codex/skills/handoff-agent-builder"
ln -s "$HOME/.codex/davis-agent-kit/skills/software-engineering" "$HOME/.codex/skills/software-engineering"
```

이전 구조에서 쓰던 legacy 스킬이 남아 있는 기기에서는 아래 명령으로 정리합니다. 처음 설치하는 기기에서는 필요 없습니다.

```bash
rm -rf "$HOME/.codex/skills/davis-operating-system"
rm -rf "$HOME/.codex/skills/coding-workflow"
```

설치 후에는 Codex를 재시작하거나 새 세션을 시작해 전역 지침과 스킬 목록이 다시 로드되도록 합니다.

AGENTS.md만 복사하는 방식은 전역 기본 원칙 적용에 한정됩니다. 레포 전체 기준을 적용하려면 위 연결 설치를 사용합니다.

### 연결 상태 확인

연결 상태는 아래처럼 확인합니다.

```bash
readlink "$HOME/.codex/davis-agent-kit"
readlink "$HOME/.codex/AGENTS.md"
readlink "$HOME/.codex/skills/translation-quality"
readlink "$HOME/.codex/skills/handoff-agent-builder"
readlink "$HOME/.codex/skills/software-engineering"
```

## 현재 스킬

- [`translation-quality`](skills/translation-quality/) - 실적발표 컨퍼런스콜과 긴 비즈니스 문서를 자연스러운 한국어로 번역하고 개념 검수와 HTML QA까지 수행하기 위한 스킬
- [`handoff-agent-builder`](skills/handoff-agent-builder/) - 프로젝트별 인수인계 에이전트를 설계하고 멀티턴 검증까지 수행하기 위한 스킬
- [`software-engineering`](skills/software-engineering/) - 소프트웨어 변경, 리뷰, 검증, 런타임 경계, CRA/TCA 루프를 다루는 엔지니어링 판단 스킬

## 첫 번째 기준점

첫 기준점은 번역 작업입니다. `translation-quality` 스킬은 긴 실적발표 transcript 번역에서 요구되는 자연스러운 한국어, 화자/문단 형식, 주석, 링크, 이태릭체, 숫자 QA, 최종 검수를 절차화한 사례입니다.

이 사례에서 끌어낸 재현 가능한 품질 지침은 [재현 가능한 품질](guidelines/reproducible-quality.md)에 정리해 두었습니다.

## 공개/비공개 경계

이 저장소는 공개 가능한 작업 철학과 품질 기준을 관리합니다. 투자 판단 방식, 개인 선호, 작업 철학, 검수 기준도 공개해도 되는 내용만 남깁니다.

계정 정보, 토큰, 키, 비밀번호, 비공개 원문 전문, 저작권 문제가 있는 긴 발췌, 제3자 민감정보, 계약상 비공개 자료는 공개 대상에서 제외합니다.
