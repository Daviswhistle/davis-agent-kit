# Worker Delegation

Use when a software task is delegated to an implementation worker, explorer, independent reviewer or separate orchestrator. Delegation moves bounded work and noisy output; it does not transfer the primary's final responsibility.

## Roles

- primary: user intent, authority, user-facing status/steering, integration, completion-critical validation and final response
- orchestrator: a separate child accountable to the primary; decomposes, schedules, delegates and supervises bounded work and retries. It may maintain concise coordination state and integrate authorized outputs after writers stop, but it delegates implementation and does not replace the primary or certify the final outcome
- implementation worker: assigned implementation and local validation only
- explorer: read-only bounded discovery
- independent reviewer: must not be the author of the change it reviews

## Handoff contract

Send only what the delegate needs:

```text
Goal: <observable outcome>
Scope: <included files/components/behavior>
Out of scope: <nearby work to leave alone>
Constraints: <project, safety, compatibility, user choices>
Authority: <read/edit/test/commit permission>
Validation: <required checks/evidence>
Return: <changed files, effect, raw results, skipped checks, uncertainty, blockers>
```

Send minimal history and only the artifacts needed to act. Resolve missing product decisions in the primary session.

For coordinated or changing tasks, add the current contract revision, pinned workspace/branch baseline, writer or stable-reader ownership, integration owner and the point at which writers stop. Define domain-specific tolerances or stochastic criteria when needed for acceptance.

## Resource defaults

Choose role first, then model, reasoning effort, service tier and history propagation.

1. bounded implementation worker: `gpt-5.6-luna` + Max + Fast when available and sufficient;
2. CRA reviewer: `gpt-6-astra` + High + default/non-Fast tier; `references/cra-loop.md` owns the exact invocation;
3. explorer: cheapest available model that can answer the bounded discovery question reliably;
4. orchestrator and other specialists: choose a role-appropriate resource using the current launcher and available capacity; do not inherit the implementation worker default automatically.

Verify the launcher can express the selected settings when this matters. An example config is not runtime evidence.

## Context

Use the runtime default context for every role. Do not increase `model_context_window` or `model_auto_compact_token_limit`.

If a handoff does not fit:

1. remove duplicated instructions and irrelevant history;
2. bound recursive/generated tool output;
3. provide exact paths, diffs and evidence rather than making the delegate rediscover them;
4. split the work into coherent units;
5. use TCA only when those units are independently reviewable.

Prefer a self-contained handoff with no history or the smallest useful history subset.

## Execution rules

1. Use one write-capable worker for one coherent change.
2. Treat one mutable worktree as a single-writer/stable-reader boundary. Parallel writing requires distinct worktrees; disjoint filenames alone are not sufficient. Serialize state-dependent readers until the writer exits, or give them a fixed commit snapshot.
3. Pin the baseline and name an integration owner before dispatch. Serialize integration and state-dependent validation; an orchestrator may perform authorized integration after active writers stop.
4. Under TCA, delegate only the active task unit. Under Teamwork, dispatch only ready units whose dependencies and slots are available; reuse idle workers where useful and report when independence cannot be preserved.
5. A worker does not final-certify or CRA-review its own implementation. Workers run local checks and return raw evidence for independent inspection.
6. Inspect actual changes, repository state and completion-critical evidence after the delegate returns.
7. If the delegate finds a contradiction or materially larger scope, it stops and returns evidence instead of expanding silently.

## Return evidence

Require changed files, behavioral effect, commands actually run, exit status and useful raw output/artifact locations, skipped checks, uncertainty and blockers. Record model/effort/tier only when it matters to reproducibility.
