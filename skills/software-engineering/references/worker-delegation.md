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
Resources: <role, model, reasoning effort, service tier, history propagation; brief selection reason>
Validation: <required checks/evidence>
Return: <changed files, effect, raw results, skipped checks, uncertainty, blockers>
```

Send minimal history and only the artifacts needed to act. Resolve missing product decisions in the primary session.

For coordinated or changing tasks, add the current contract revision, pinned workspace/branch baseline, writer or stable-reader ownership, integration owner and the point at which writers stop. Define domain-specific tolerances or stochastic criteria when needed for acceptance.

## Resource routing

Use the selection requirements and role defaults in [SKILL.md](../SKILL.md#resource-defaults). This reference supplies launcher details; [cra-loop.md](cra-loop.md) owns the exact CRA invocation.

### Luna + Fast routing

Current Codex native subagents inherit the root service tier, so a non-Fast primary cannot make only one native Luna child Fast. In that case launch the implementation worker as an independent root with `scripts/run_luna_worker.py`. The helper pins `gpt-5.6-luna`, Max reasoning, `service_tier=priority`, `workspace-write`, and `approval_policy=never`, injects the bounded worker instructions as developer instructions, and uses `--strict-config` so an installed CLI that does not recognize a pinned setting fails instead of silently downgrading it.

Pass the handoff contract on stdin so shell quoting does not become part of the task:

```bash
python3 "$HOME/.agents/skills/software-engineering/scripts/run_luna_worker.py" --cwd "$PWD" <<'CONTRACT'
Goal: ...
Scope: ...
Out of scope: ...
Constraints: ...
Authority: read/edit/test; no remote mutation
Resources: implementation worker; gpt-5.6-luna; Max; Fast; bounded contract only; precise implementation scope fits the first candidate
Validation: ...
Return: changed files, effect, raw results, skipped checks, uncertainty, blockers
CONTRACT
```

Wait for this writer to exit before the primary or another writer edits the same worktree. Inspect the actual diff and validation afterward. Because this is a nested `codex exec`, the outer shell execution must be allowed to reach the Codex backend; if its sandbox blocks network access, use an explicitly approved network-capable execution path or do not delegate rather than bypassing that boundary silently. If the root session is already Fast, native delegation remains acceptable when its other constraints fit.

### Dream-RSI mini replay experiment

For repeated, comparable search or delegation work, an opt-in offline experiment may use completed search trees to compare where a controller would have spent its budget. Read [dream-rsi-mini.md](dream-rsi-mini.md) before using `scripts/dream_rsi_replay.py`.

The replay helper is advisory only: it does not launch Codex, generate missing branches, edit a worktree, or grant live delegation authority. Keep the current controller as the baseline, separate training histories from whole-run holdouts, and treat any replay-selected policy as a shadow/recommendation candidate until held-out evidence and later live runs support promotion. Historical child outcomes that were not yet visited by the replay policy must remain hidden from that policy.

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

Require changed files, behavioral effect, commands actually run, exit status and useful raw output/artifact locations, skipped checks, uncertainty and blockers. Return available runtime model/effort/tier evidence or identify what could not be verified; an example config or requested setting is not runtime evidence.
