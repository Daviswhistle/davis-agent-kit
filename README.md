# Davis Agent Kit

한국어로 작업하는 에이전트를 위한 전역 지침, 작업 철학, 체크리스트, 템플릿, Codex 스킬 원본을 한곳에서 관리하는 공개 레포입니다.

목표는 특정 대화를 기억하는 것이 아니라, 반복 작업에서 드러난 판단 기준과 품질 기준을 새 환경에서도 재현 가능한 파일 구조로 남기는 것입니다.

## 기본 구조

```text
davis-agent-kit/
  AGENTS.md     # Codex 전역 지침 원본
  GEMINI.md     # AGY/Gemini 전역 지침 원본
  principles/   # 모든 작업에 공통으로 적용되는 원칙
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

1. `AGENTS.md`와 `GEMINI.md`는 전역 지침의 원본으로 관리합니다.
2. 실제 Codex 스킬은 `skills/<skill-name>/SKILL.md` 형태로 독립 유지합니다.
3. 반복해서 지적된 문제는 `inbox/`에 먼저 적고, 재발 방지 절차가 보이면 `principles/`, `checklists/`, `skills/`, `templates/` 중 맞는 곳으로 승격합니다.
4. 스킬은 실제 작업에 적용하고 실패 지점을 반영한 뒤 고정합니다.
5. 좋은 결과물만 저장하지 말고 반복 실수를 막는 나쁜 예시와 검수 기준도 함께 남깁니다.
6. 사용자와 작업하며 새로 파악한 선호와 품질 기준은 작업 재현성에 직접 도움이 될 때만 `user-model/`에 근거와 함께 기록합니다.
7. commit, push, 원격 레포 rename처럼 상태를 바꾸는 작업은 현재 적용 중인 전역 지침과 사용자의 명시 요청을 따릅니다.

## 설치

이 레포를 받은 뒤 필요한 파일을 Codex 설정 디렉터리에 직접 복사합니다. macOS, Linux, WSL에서는 아래 명령을 사용합니다.

```bash
mkdir -p "$HOME/.codex/skills"
cp AGENTS.md "$HOME/.codex/AGENTS.md"
rsync -a --delete skills/translation-quality/ "$HOME/.codex/skills/translation-quality/"
rsync -a --delete skills/handoff-agent-builder/ "$HOME/.codex/skills/handoff-agent-builder/"
```

이전 구조에서 쓰던 legacy 스킬이 남아 있는 기기에서는 아래 명령으로 정리합니다. 처음 설치하는 기기에서는 필요 없습니다.

```bash
rm -rf "$HOME/.codex/skills/davis-operating-system"
```

설치 후에는 Codex를 재시작하거나 새 세션을 시작해 스킬 목록이 다시 로드되도록 합니다.

### 관리용 연결 설치

이 레포를 직접 관리하면서 여러 기기에서 같은 기준을 유지하려면 복사 대신 심링크로 연결할 수 있습니다. 이렇게 설치하면 `~/.codex`에서 보이는 전역 지침과 스킬이 이 레포의 파일을 직접 가리키므로, 에이전트가 내용을 수정했을 때 git 변경으로 바로 잡힙니다.

기존 `~/.codex/AGENTS.md`나 같은 이름의 스킬 폴더를 보존해야 한다면 먼저 백업하세요.

```bash
KIT_DIR="$(pwd)"

mkdir -p "$HOME/.codex/skills"
rm -f "$HOME/.codex/AGENTS.md"
rm -rf "$HOME/.codex/skills/translation-quality"
rm -rf "$HOME/.codex/skills/handoff-agent-builder"

ln -s "$KIT_DIR/AGENTS.md" "$HOME/.codex/AGENTS.md"
ln -s "$KIT_DIR/skills/translation-quality" "$HOME/.codex/skills/translation-quality"
ln -s "$KIT_DIR/skills/handoff-agent-builder" "$HOME/.codex/skills/handoff-agent-builder"
```

연결 상태는 아래처럼 확인합니다.

```bash
readlink "$HOME/.codex/AGENTS.md"
readlink "$HOME/.codex/skills/translation-quality"
readlink "$HOME/.codex/skills/handoff-agent-builder"
```

## 현재 스킬

- [`translation-quality`](skills/translation-quality/) - 실적발표 컨퍼런스콜과 긴 비즈니스 문서를 자연스러운 한국어로 번역하고 개념 검수와 HTML QA까지 수행하기 위한 스킬
- [`handoff-agent-builder`](skills/handoff-agent-builder/) - 프로젝트별 인수인계 에이전트를 설계하고 멀티턴 검증까지 수행하기 위한 스킬

## 첫 번째 기준점

첫 기준점은 번역 작업입니다. `translation-quality` 스킬은 긴 실적발표 transcript 번역에서 요구되는 자연스러운 한국어, 화자/문단 형식, 주석, 링크, 이태릭체, 숫자 QA, 최종 검수를 절차화한 사례입니다.

이 사례에서 끌어낸 상위 철학은 [재현 가능한 품질](principles/reproducible-quality.md)에 정리해 두었습니다.

## 공개/비공개 경계

이 저장소는 공개 가능한 작업 철학과 품질 기준을 관리합니다. 투자 판단 방식, 개인 선호, 작업 철학, 검수 기준도 공개해도 되는 내용만 남깁니다.

계정 정보, 토큰, 키, 비밀번호, 비공개 원문 전문, 저작권 문제가 있는 긴 발췌, 제3자 민감정보, 계약상 비공개 자료는 공개 대상에서 제외합니다.
