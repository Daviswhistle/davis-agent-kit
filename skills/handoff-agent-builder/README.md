# Handoff Agent Builder Skill

프로젝트별 인수인계 에이전트를 만들기 위한 Codex 스킬입니다.

이 스킬은 Codex가 대상 저장소를 읽고, 그 저장소에 맞는 repo-local handoff agent를 설계하고, 첫 응답과 로드맵과 검증 루프를 만들도록 이끕니다.

핵심 원칙은 하나입니다. 인수인계를 받는 사람은 아직 무엇을 물어야 하는지 모를 수 있으므로, 에이전트가 중요한 주제와 다음 파일을 먼저 열어줘야 합니다.

## 이 스킬이 해결하는 문제

- 인수인계 문서가 파일 목록으로만 끝나는 문제
- 첫 응답이 "무엇을 도와드릴까요?"로 시작하는 문제
- 받는 사람이 모르는 개념을 먼저 질문해야만 설명이 나오는 문제
- 에이전트가 필수 주제를 먼저 알려주지 않고 질문을 기다리는 문제
- 실행 명령, 산출물, 설정, 데이터 역할, 평가 방법이 흩어져 있는 문제
- 에이전트가 실제 멀티턴 대화에서 다음 단계로 이끌지 못하는 문제
- 스킬 파일은 만들었지만 실제 대화 검증을 하지 않는 문제

## 설치

이 스킬은 `references/`를 사용하므로 폴더 전체를 복사하세요.

```bash
CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$CODEX_DIR/skills/handoff-agent-builder"
cp -R handoff-agent-builder/* "$CODEX_DIR/skills/handoff-agent-builder/"
```

복사한 뒤 Codex를 재시작하거나 새 세션을 시작해 스킬 목록이 다시 로드되도록 하세요.

## 사용 예시

```text
handoff-agent-builder 스킬을 사용해서 이 저장소를 새 담당자에게 인수인계할 repo-local agent를 만들어줘.
```

```text
이 프로젝트를 처음 맡는 사람이 첫 실행, 산출물, 설정, 평가, 향후 과제까지 이해하도록 인수인계 에이전트를 설계해줘.
```

## 기대 산출물

- `agents/<project>-handoff/SKILL.md`
- `agents/<project>-handoff/references/first-session.md`
- `agents/<project>-handoff/references/handoff-completion.md`
- `agents/<project>-handoff/references/maintainer-roadmap.md`
- 필요 시 `docs/handoff_agent.md`
- README/docs에서 handoff agent로 들어가는 링크
- 실제 멀티턴 forward-test 결과

## 품질 기준

통과 기준은 "에이전트가 실제로 사람을 이끌 수 있는가"입니다. 산출물에는 실제 대화를 다음 단계로 이끄는 힘이 있어야 합니다.

- 첫 응답이 compact하고 주도적이어야 합니다.
- 첫 실행 또는 첫 파일 확인이 명확해야 합니다.
- 한 파일/그림/개념씩 설명해야 합니다.
- 단계마다 에이전트가 먼저 요약하고 이해 여부를 확인해야 합니다.
- 설정, 데이터 역할, 평가, 실행 변형, 향후 과제를 먼저 열어줘야 합니다.
- 실제 서브에이전트나 격리 대화로 멀티턴 검증을 해야 합니다.
