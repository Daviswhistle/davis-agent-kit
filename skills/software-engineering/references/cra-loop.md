# CRA Loop

CRA means Commit-Review-Amend. Use it after local validation when selected by the user, TCA or the software-engineering risk criteria. Use Codex's native commit target, review rubric and output; do not add custom review packets, unit coverage or incremental review state.

## Preconditions

Use one coherent, clean non-merge task commit with a fixed parent. Exclude unrelated changes, secrets and temporary review artifacts. The reviewer must run in a separate session that did not author the change; keep the checkout stable while it runs.

A local commit or review does not authorize push, deployment, migration or remote mutation.

## Native review

Default: `gpt-6.1-sol`, `max` reasoning, `default` (non-Fast) service tier and runtime default context. Do not enlarge context to fit a task; use coherent, independently reviewable task boundaries instead.

The calling primary leads the CRA loop and owns integration and final acceptance: it evaluates findings, applies authorized amendments and starts re-reviews. The session launched by `codex review` is the already-assigned independent reviewer, including when it runs as a separate CLI root; it reviews the requested commit directly and returns findings to the primary.

Run in the foreground against the current task SHA:

```bash
COMMIT_SHA="$(git rev-parse HEAD)"
CRA_REVIEW_MODEL="${CRA_REVIEW_MODEL:-gpt-6.1-sol}"
CRA_REVIEW_EFFORT="${CRA_REVIEW_EFFORT:-max}"

codex review --commit "$COMMIT_SHA" \
  -c "model=$CRA_REVIEW_MODEL" \
  -c "review_model=$CRA_REVIEW_MODEL" \
  -c "model_reasoning_effort=$CRA_REVIEW_EFFORT" \
  -c service_tier=default \
  -c features.fast_mode=false \
  -c 'developer_instructions="You are the assigned independent commit reviewer. Perform the requested native commit review directly using the native review rubric and output. Do not create a team, perform recursive CRA, or spawn or launch another reviewer. Use read-only inspection and non-destructive validation only; do not edit files, commit, or make remote writes. Return findings to the calling primary."'
```

Set both model keys so an existing `review_model` setting cannot select a different reviewer. Read the completed review, not partial output. A zero process exit means the command completed, not that the findings are clean.

## Findings and amendments

1. Verify each finding against the actual code and task intent. Reject incorrect, speculative, pre-existing or out-of-scope findings with a concise evidence-based reason; do not change code merely to appease the reviewer.
2. Apply the smallest coherent fixes for valid in-scope findings, rerun affected local validation and amend the same task commit without changing its parent.
3. After any amendment, rerun the command with the new SHA to review the complete amended commit against its parent, not only the fixes or amendment delta.

## Completion

Finish when applicable validation passes or limitations are disclosed, the latest full review completed successfully, no valid in-scope finding remains unresolved, and HEAD, parent and worktree still match the reviewed state. Findings rebutted with current evidence do not require another unchanged review.

Report the final SHA, validation and review outcome, material rejected findings and remaining risk. Auth, quota, model availability, command support or transport failure is a review failure: report it rather than declaring the task reviewed or silently weakening the profile.
