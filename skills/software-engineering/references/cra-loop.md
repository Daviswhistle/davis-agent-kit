# CRA Loop

CRA means Commit-Review-Amend. Use it after local validation when selected by the user, TCA or the software-engineering risk criteria. The reviewer uses Codex's native commit target, review rubric and output; do not add custom review packets, unit coverage or incremental review state to the review.

## Roles

CRA has exactly three roles. Each runs in its own session; no session holds two roles.

- **Author**: owns the task commit, sends it for review, decides and applies amendments, and reports the outcome.
- **Reviewer**: finds defects in the commit with the native review.
- **Verifier**: judges whether each finding is worth acting on and recommends a decision to the author.

Roles are independent of model vendor. A lead, supervisor or operator who receives the CRA report is outside the loop and does not adjudicate findings inside it.

Reviewers tend to treat any missing check as a defect, while the cost of a check that rejects normal real-world behavior is rarely raised. The verifier exists to weigh both directions before the author amends the code.

## Preconditions

Use one coherent, clean non-merge task commit with a fixed parent. Exclude unrelated changes, secrets and temporary review artifacts. The reviewer and verifier must not have authored the change; keep the checkout stable while they run.

Follow the user and applicable `AGENTS.md` for action permissions. A local commit, review or verification does not expand that authority.

## Native review

Default: `gpt-6.1-sol`, `max` reasoning, `default` (non-Fast) service tier and runtime default context. Do not enlarge context to fit a task; use coherent, independently reviewable task boundaries instead.

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
  -c 'developer_instructions="You are the assigned independent commit reviewer. Perform the requested native commit review directly using the native review rubric and output. Do not create a team, perform recursive CRA, or spawn or launch another reviewer. Use read-only inspection and non-destructive validation only; do not edit files, commit, or make remote writes. Return findings to the calling author."'
```

Set both model keys so an existing `review_model` setting cannot select a different reviewer. Read the completed review, not partial output. A zero process exit means the command completed, not that the findings are clean. If the review has no findings, skip verification for that round.

## Independent verification

Default: same model, reasoning and service tier as the reviewer, read-only sandbox, fresh session.

The author writes a verification packet and does not argue for or against findings in it:

- the commit SHA and parent;
- the complete review output, unedited;
- the acceptance criteria from the user, the task and applicable `AGENTS.md`, including the cost of a false stop or rejection, not only the cost of a missed defect;
- recorded real responses or behavior of the external systems the change touches, when the project keeps them;
- related incident records or prior rejected findings, when they exist.

Run in the foreground:

```bash
CRA_VERIFY_MODEL="${CRA_VERIFY_MODEL:-gpt-6.1-sol}"
CRA_VERIFY_EFFORT="${CRA_VERIFY_EFFORT:-max}"

codex exec --ephemeral -s read-only \
  -m "$CRA_VERIFY_MODEL" \
  -c "model_reasoning_effort=$CRA_VERIFY_EFFORT" \
  -c service_tier=default \
  -c features.fast_mode=false \
  -o "$VERDICT_FILE" - < "$VERIFY_PACKET_FILE"
```

The verifier instruction at the top of the packet:

> You are the independent CRA verifier. You did not write the commit or the review. For each finding, inspect the actual code and give one verdict: `accept`, `reject` or `narrow` (a smaller fix, such as a warning instead of a stop). For each verdict state: (1) the concrete harm the finding prevents, as trigger → wrong outcome, or that none is shown; (2) whether the finding or its fix would reject normal real-world behavior such as rounding, truncation, delay, missing optional fields or transient errors, citing the recorded behavior when given; (3) the failure scope of the fix and whether it can be smaller; (4) the recommended minimal action. A finding that adds strictness without a concrete harm is rejected. A defect that does cause concrete harm is accepted even if its fix is large. Do not edit files, commit, run destructive commands or make remote writes. Do not launch other agents.

### Rebuttal

When the verifier rejects or narrows a high-severity finding (P0 or P1), send the finding and verdict to a fresh read-only reviewer-role session with the same profile. It either gives a concrete trigger → harm path the verdict missed, or withdraws the finding. If a path is given, the verifier re-judges that finding once with it. One rebuttal round per finding.

## Amendments

1. The author decides each finding. Follow the verifier's recommendation unless current evidence shows it is wrong; record the reason for any deviation. Do not change code merely to appease the reviewer or the verifier.
2. Apply the smallest coherent fixes for accepted or narrowed findings, rerun affected local validation and amend the same task commit without changing its parent.
3. After any amendment, rerun the review with the new SHA against its parent, covering the complete amended commit, then verify its findings. Findings already rejected with unchanged evidence do not need verification again.

## Completion

Finish when applicable validation passes or limitations are disclosed, the latest full review completed successfully, the verifier accepted no unresolved finding in it, and HEAD, parent and worktree still match the reviewed state.

Report the final SHA, validation, review and verification outcomes, findings rejected or narrowed with their reasons, author deviations from recommendations, and remaining risk. Auth, quota, model availability, command support or transport failure of the reviewer or verifier is a CRA failure: report it rather than declaring the task reviewed or silently weakening the profile.
