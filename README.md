# AGENTS.md for Korean

한국어로 작업하는 AI 코딩 에이전트용 지시문 모음입니다.

- `AGENTS.md`: Codex CLI용
- `GEMINI.md`: Gemini CLI용

두 파일은 같은 작업 철학을 공유하지만, CLI별 지시문 로딩 방식과 리뷰 명령 방식이 달라 별도 파일로 관리합니다.

## 포함된 원칙

- 한국어로 대화합니다.
- 모호하거나 비현실적인 요청은 그대로 따르지 않고 먼저 지적합니다.
- 임시방편보다 근본 원인 해결을 우선합니다.
- 코드, 문서, 테스트, 설정의 정합성을 함께 확인합니다.
- 불확실한 외부 동작이나 환경 특성은 추정하지 않고 확인합니다.
- 대량 로그나 장문 파일은 필요한 범위만 읽습니다.
- CRA/TCA 루프를 통해 커밋 단위 리뷰와 검증을 수행할 수 있습니다.

## 설치

### Codex CLI

```bash
mkdir -p ~/.codex
cp AGENTS.md ~/.codex/AGENTS.md
```

프로젝트별로만 적용하려면 프로젝트 루트에 둡니다.

```bash
cp AGENTS.md /path/to/project/AGENTS.md
```

### Gemini CLI

```bash
mkdir -p ~/.gemini
cp GEMINI.md ~/.gemini/GEMINI.md
```

프로젝트별로만 적용하려면 프로젝트 루트에 둡니다.

```bash
cp GEMINI.md /path/to/project/GEMINI.md
```

Gemini CLI에서 로드된 지시문은 아래 명령으로 확인할 수 있습니다.

```text
/memory show
/memory list
```

수정 후에는 아래 명령으로 다시 로드합니다.

```text
/memory refresh
```

## Codex와 Gemini를 함께 쓸 때

Gemini용 파일은 Codex용 `AGENTS.md`에서 리뷰 예시만 바꾼 것이 아닙니다.

- Codex는 `codex review` 중심으로 CRA 루프를 구성합니다.
- Gemini는 `gemini -p`에 읽기 전용 리뷰 프롬프트를 넣는 방식으로 CRA 루프를 구성합니다.
- Gemini에서는 `/memory show`, `/memory list`, `/memory refresh`로 지시문 적용 상태를 확인하는 절차가 중요합니다.

## 라이선스

MIT License
