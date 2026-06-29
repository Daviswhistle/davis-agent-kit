# Validation Playbook

Use this playbook to prove that a project-specific handoff agent works at the level expected for serious handoff, not just that its files exist.

## Static Validation

Run the skill validator for the generated agent:

```bash
python3 /path/to/quick_validate.py agents/<project>-handoff
```

Run whitespace validation:

```bash
git diff --check
```

Search for unfinished markers:

```bash
rg -n "TODO|FIXME|\\[TODO\\]|PLACEHOLDER" agents/<project>-handoff docs README.md
```

Search for weak first-session patterns:

```bash
rg -n "무엇을 도와|뭘 도와|어떤 것을 알고|직접 해보|다음에 .*보면|초심자|인턴|후임|사용자가 금지|실행이 허용|명령 실행이 허용" agents/<project>-handoff docs
```

Adjust the banned phrases to the project's language. A match is not automatically a failure, but every match must be read.

## Required Behavior Tests

Use fresh subagents or isolated conversations. The validating agent should receive the skill and a natural user request, not your expected answer.

### Test 1. First Handoff Start

Prompt:

```text
Use $<project>-handoff at <path> for this repository. 인수인계 시작해줘
```

Pass criteria:

- Starts with project purpose and handoff route.
- Gives the exact first command or first inspection action.
- Includes working directory and expected output/artifact when relevant.
- Explains unavoidable terms.
- Does not start with a broad policy dump, test matrix, or "what do you want?"
- Does not use status labels for the listener.
- Ends with a clear next action checkpoint.

### Test 2. Run Or First Action

Prompt:

```text
실행해
```

or the equivalent for non-CLI projects.

Pass criteria:

- Runs only if the request and repo rules allow it.
- Reports success/failure from actual evidence.
- Opens or inspects the first planned artifact if success.
- Does not claim to have opened anything unless it actually did.
- Explains the artifact's role before jargon.
- Summarizes and checks understanding.

### Test 3. Continue After Confirmation

Prompt:

```text
이해됐어. 계속해줘.
```

Pass criteria:

- Continues to the next planned artifact/file/concept.
- Does not ask "what should we look at?"
- Inspects the next artifact when tooling allows.
- Uses one visual artifact per turn when visuals exist.
- Ends with a concrete summary and understanding check.

### Test 3.5. Proactive Topic Coverage

Prompt:

```text
좋아. 다음은 네가 알아서 이어가줘.
```

Pass criteria:

- Introduces the next required topic without waiting for a specific question.
- Names why the topic matters for safe maintenance.
- Opens or inspects the next concrete file/artifact when possible.
- Does not reduce the interaction to "궁금한 것을 물어보세요."

### Test 4. Domain Term Probe

Ask about a term that a first maintainer would not know:

```text
<domain term>가 뭔데?
```

Pass criteria:

- Explains in ordinary language before abbreviations.
- Connects the term to a concrete file/artifact/code path.
- Avoids condescension and quiz-like wording.
- Returns to the planned handoff flow after answering.

### Test 5. Settings And Data Probe

Prompt:

```text
설정 파일은 어디 있어? 데이터가 왜 여러 개야?
```

Pass criteria:

- Separates behavior settings, runtime options, environment, and data selection.
- Explains data roles and trust rules.
- Points to real paths.
- Does not treat sample, benchmark, generated output, and source-of-truth data as interchangeable.

### Test 6. Execution Variant Probe

Prompt:

```text
여러 번 돌리거나 랜덤 seed로 돌리는 흐름도 설명해줘.
```

Pass criteria:

- Explains deterministic baseline vs random/seeded candidates.
- Names the owning script/command/function when applicable.
- Explains why bad candidates may still be useful for exploration.
- Ends with a summary and understanding check.

## Acceptance Standard

The handoff agent passes only when:

1. Static validation passes.
2. First-session behavior passes.
3. At least one multi-turn continuation passes.
4. The agent proactively covers data roles, settings, artifacts, evaluation, execution variants, and future work.
5. The final recap requirement exists in the skill and is tested or manually inspected.
6. Observed failures are patched and retested.

If the agent only provides a good first answer but cannot continue through artifacts and code ownership, it is incomplete.
