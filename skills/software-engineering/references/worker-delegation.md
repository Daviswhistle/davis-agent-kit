# Worker Delegation

Use for every software specialist handoff, including implementation, bounded discovery, independent review and an optional execution coordinator. A handoff assigns professional work to a specialist; it does not transfer the primary's leadership or final responsibility.

## Roles

- primary/team leader: user intent, priorities, authority, user-facing status and steering, role assignment and scheduling by default, integration responsibility, final acceptance validation and response; may explicitly authorize a coordinator to integrate after writers stop
- optional execution coordinator: a separate child explicitly delegated team creation and scheduling only when sustained coordination justifies it; it may integrate completed outputs after writers stop when explicitly authorized, but does not replace the primary or accept the result
- specialist: one defined professional role and its domain deliverable; it may work across all necessary files within that role and runs role-local checks
- independent reviewer: a specialist role that must not author the change it reviews

Worker, explorer and reviewer labels do not authorize one context to perform unrelated professional work; state the specialist's professional role explicitly, including independent review when that is the assignment. Only the primary or a coordinator explicitly delegated team creation/scheduling may create or schedule agents. Specialists may coordinate with relevant peers through supported tools within their contracts, but may not reassign peers, expand scope, mutate another owner's workspace or create subteams.

## Handoff contract

Send only what the delegate needs:

```text
Professional role: <one defined specialty>
Goal and deliverable: <observable outcome and expected output>
Scope: <included components; may span necessary files for this same-role deliverable>
Peers and dependencies: <counterpart role plus current address/task identity; required inputs, expected outputs and dependency order; none if solo>
Out of scope: <nearby work to leave alone>
Constraints: <project, safety, compatibility, user choices>
Tools and authority: <allowed tools/actions, read/edit/test/commit permission and forbidden effects>
Resources: <model, reasoning effort, service tier, history propagation; brief selection reason>
Validation and evidence: <required checks, evidence and acceptance criteria>
Return: <changed files, effect, raw results, skipped checks, uncertainty, blockers>
```

Send minimal history and only the artifacts needed to act. Resolve missing product decisions in the primary session.

For coordinated or changing tasks, add the current contract revision, pinned workspace/branch baseline, writer or stable-reader ownership, the primary as integration owner, any explicitly authorized coordinator integration, and the point at which writers stop. Define domain-specific tolerances or stochastic criteria when needed for acceptance. State the role boundary and deliverable in terms of responsibility; do not restrict a specialist to one filename when the same-role work needs more files.

## Resource routing

Use the selection requirements and role defaults in [SKILL.md](../SKILL.md#resource-defaults). This reference supplies launcher details; [cra-loop.md](cra-loop.md) owns the exact CRA invocation.

### Luna + Fast routing

Current Codex native subagents inherit the root service tier, so a non-Fast primary cannot make only one native Luna child Fast. In that case launch the implementation worker as an independent root with `scripts/run_luna_worker.py`. The helper pins `gpt-6-luna`, Max reasoning, `service_tier=priority`, `workspace-write`, and `approval_policy=never`, injects the bounded worker instructions as developer instructions, and uses `--strict-config` so an installed CLI that does not recognize a pinned setting fails instead of silently downgrading it.

Pass the handoff contract on stdin so shell quoting does not become part of the task:

```bash
python3 "$HOME/.agents/skills/software-engineering/scripts/run_luna_worker.py" --cwd "$PWD" <<'CONTRACT'
Professional role: <the required implementation specialty>
Goal and deliverable: ...
Scope: ...
Out of scope: ...
Constraints: ...
Tools and authority: read/edit/test; no remote mutation
Resources: gpt-6-luna; Max; Fast; bounded contract only; precise implementation scope fits the first candidate
Validation and evidence: ...
Return: changed files, effect, raw results, skipped checks, uncertainty, blockers
CONTRACT
```

Wait for this writer to exit before the primary or another writer edits the same worktree. Inspect the actual diff and validation afterward. Because this is a nested `codex exec`, the outer shell execution must be allowed to reach the Codex backend; if its sandbox blocks network access, use an explicitly approved network-capable execution path or do not delegate rather than bypassing that boundary silently. If the root session is already Fast, native delegation remains acceptable when its other constraints fit.

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

1. Use one write-capable specialist/context for each professional role. A specialist may handle a coherent deliverable across multiple files when all work stays in its role.
2. Treat one mutable worktree as a single-writer/stable-reader boundary. Parallel writing requires distinct worktrees; disjoint filenames alone are not sufficient. Serialize state-dependent readers until the writer exits, or give them a fixed commit snapshot.
3. Pin the baseline and name the primary as integration owner before dispatch. The primary may explicitly authorize a coordinator to integrate completed outputs after active writers stop; the primary inspects the integrated state and owns final acceptance.
4. Dispatch only ready role assignments whose dependencies and slots are available. Reuse a specialist only within the same professional role; never repurpose an idle context for a different role. Queue or serialize distinct roles under capacity limits. Do not move specialist work to the primary because delegation is inconvenient or temporarily unavailable; if the host cannot provide a required separate context, report that capability blocker.
5. A worker does not final-certify or CRA-review its own implementation. Workers run local checks and return raw evidence for independent inspection.
6. Inspect actual changes, repository state and completion-critical evidence after the delegate returns.
7. If the delegate finds a contradiction or materially larger scope, it stops and returns evidence instead of expanding silently.

## Return evidence

Require the role's deliverable, changed files, behavioral effect, commands actually run, exit status and useful raw output/artifact locations, skipped checks, uncertainty and blockers. Return available runtime model/effort/tier evidence or identify what could not be verified; an example config or requested setting is not runtime evidence.
