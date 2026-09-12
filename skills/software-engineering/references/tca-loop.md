# TCA Loop Reference

Use when the user explicitly requests TCA or `software-engineering` selects it because independently reviewable task commits improve correctness, recovery or reviewability. Do not split an ordinary multi-step change merely to create a workflow.

TCA means Task-Commit-Approve: complete one coherent task, validate and commit it, run CRA, then decide whether the next task remains necessary. `Approve` is a next-task gate, not user approval or permission for external writes.

## Task boundaries and queue

Record the entry source (`explicit-request` or `autonomous-structure`) and the concrete reason for separate task commits. A later user instruction to avoid commits or reviews overrides either source.

Each task needs one goal, scope, dependencies, closest practical validation, a clean commit boundary and a rollback/failure path. Keep directly connected code, tests, docs, configuration and generated contracts together. Never leave a task broken, misleading or materially incomplete just to create a boundary.

Maintain a small execution queue, not a fixed promise:

```text
Entry source and rationale:
[ ] Task: <goal and scope>
    Dependencies / failure path:
    Validation:
    Execution owner and resource-selection record, if delegated:
    Commit / CRA state / remaining risk:
```

Update, merge or remove tasks as facts change. Address blocking failures and prerequisites first, then choose the smallest coherent unit that reduces risk. Do not create a permanent queue artifact when a working record suffices.

## Per-task loop

1. Select the active task and its completion evidence. Delegate only that task when separation adds value, using the contract and resource selection in `references/worker-delegation.md`; otherwise implement directly.
2. Keep a mutable worktree single-writer/stable-reader. Wait for its writer before repository-state-dependent review, or give readers a separate worktree or fixed commit snapshot.
3. Inspect actual changes and state. Verify completion-critical results by rerunning them or inspecting independently accessible raw output, exit status and artifacts. A worker's prose summary is not evidence.
4. Check `git status --short` and the relevant diff. Commit only the active task; exclude unrelated changes, secrets, caches, logs, review output and temporary artifacts.
5. Run `references/cra-loop.md` on that commit. Process findings, amend the same task commit and revalidate affected behavior and connected contracts. Do not implement the next task while CRA is running or valid in-scope findings remain unresolved.
6. Record the final commit, validation evidence, skipped checks and CRA terminal state. Reassess the remaining queue before continuing.

If a review fix changes a test expectation, check the affected test first. Name/path changes require connected reference checks; configuration changes require runtime/environment checks. A changed goal or dependency requires re-bounding and reordering the queue before continuing.

## Next-task gate

Continue only when:

- the active task has one coherent commit whose actual diff and repository state the primary inspected;
- completion-critical validation is independently verified, with affected checks rerun after amendments and any skips explained;
- the latest CRA meets `references/cra-loop.md` completion criteria, with no unresolved valid critical, high-risk or in-scope medium finding;
- the queue reflects current evidence and the next task remains requested, necessary and independently coherent.

An unperformed required check or unavailable CRA is not a successful gate. Do not weaken validation to continue.

## Authority and stopping

Local commits and CRA do not authorize push, deployment, migration, production mutation, purchasing or other external writes. Existing configured resources and account usage may be used; billing, plan, quota, provider or account settings require explicit approval to change. Workers remain within their delegated authority.

Stop when the user cancels, the current boundary becomes unclear, unrelated changes cannot be separated, required evidence is unavailable, or a failure has no safe in-scope correction or direct-execution fallback. Resolve changed premises and dependencies before resuming. Obtain authorization for an unapproved external effect; do not repeatedly request authorization for the same already-approved scope. Stop or remove a planned task when it is no longer necessary or coherent.

## Final report

Summarize entry rationale, completed/merged/removed/deferred tasks, final commit hashes, execution owner and any delegated resource choices, verified evidence and skipped checks, CRA outcomes and material accepted/rejected findings, and remaining risks or unapproved external actions. Do not substitute a workflow report for the user's requested result.
