# Teamwork Loop Reference

Use when the parent skill selects Teamwork, including an explicit request for a separate orchestrator, dynamic team, multi-agent hackathon or `/teamwork-preview`. The purpose is to preserve the user-facing primary while a separate child manages changing workstreams.

## Ownership

```text
User <-> Primary session <-> separate Orchestrator child -> assigned specialists
```

- **Primary:** remains the user-facing session and owns intent, authority, meaningful contract revisions, status, steering, integration, final evidence and the response. The primary folds Sentinel duties into this role. It receives user updates promptly, distinguishes a status request from a scope change, and never treats an orchestrator summary as final proof.
- **Orchestrator:** a separate child accountable to the primary for this Teamwork run. It decomposes the goal, schedules ready work, delegates bounded implementation or discovery, supervises retries and coordinates authorized integration after writers stop. It may keep a concise coordination record, but it is not the primary, does not take over the user relationship, does not certify the final outcome and is not a permanent manager. Do not create a second orchestrator hierarchy without a concrete coordination need.
- **Specialists:** implementation workers, explorers and optional independent reviewers with bounded contracts. They run local checks and return evidence; an author does not final-certify its own work.

## Capability gate

Before dispatch, verify through current tool discovery or launcher behavior that the host supports a separate child, nested workers, delivery to running agents, a supported followup that wakes an idle agent, and enough capacity for the primary, orchestrator, active specialists and any review. Respect runtime, account and slot limits; never raise configuration to force Teamwork. If a capability or slot is unavailable, tell the primary/user and use ordinary bounded delegation or a serial fallback. Do not claim Teamwork exists when the host cannot provide it.

Use message semantics rather than an assumed command alias: a message to a running agent delivers information, while an idle agent wakes only through a host-supported followup. For example, a host may expose `collaboration.spawn_agent`, `send_message` and `followup_task`; verify the actual names and behavior, and never assume `send_message` wakes an idle agent.

## Adaptive scheduling

Choose team size and roles from the number of independent tracks, dependencies, evidence gaps and available capacity. There is no fixed worker count, round count, mandatory reviewer triangle or victory auditor. Count the primary, orchestrator and review roles against capacity; dispatch ready work rather than letting descendants wait indefinitely. Reuse an idle worker for related work when that preserves the contract. Release or interrupt work only through mechanisms the host supports; otherwise serialize the work or report that independence cannot be preserved. Do not cancel independent valid work merely to rebalance the team.

Choose model, reasoning effort, service tier and context per role and risk. The bounded implementation and CRA defaults in the parent skill do not automatically govern an orchestrator or other specialist. Use the current launcher and account capacity, and report an unavailable resource honestly.

## Handoffs and workspace ownership

Read `references/worker-delegation.md` for the handoff contract. Include the observable goal, scope and constraints, current contract revision, authority, pinned workspace/branch baseline and ownership, integration owner, acceptance evidence and the required return evidence. Send only the minimal history and artifacts needed to act.

A mutable worktree has one writer and stable readers. Parallel writing requires distinct worktrees; disjoint filenames alone are not enough. Pin the baseline, make the integration owner explicit, wait for writers before state-dependent validation, and serialize integration. The orchestrator may integrate authorized outputs after writers stop without becoming an implementation worker; the primary still inspects the integrated state.

## Steering, cancellation and state

Keep the primary available to the user while work runs, using event or followup notifications instead of polling or empty sleeps. Version meaningful user constraints and forward them to the orchestrator. The orchestrator acknowledges the revision, stops or drains affected obsolete work through supported mechanisms, then updates or redispatches the affected tasks. Results made under a superseded contract are unusable for final integration until revalidated against the latest revision.

A real cancellation stops descendants and related processes owned by the orchestrator to the extent the host supports; do not silently abandon workers when termination is unavailable. Replace an orchestrator when context degradation or unavailability requires it, rather than at every milestone: first reconcile live agents, workspaces, branches and artifacts, then transfer one owner. There must not be two active orchestrator owners.

Keep coordination state outside tracked product content only when a handoff needs it, and keep it concise: goal and contract revision; workspace/branch baseline; active agent/task ownership, dependencies and state; evidence, blockers and next action. Reuse an existing project task record. Do not add permanent ledgers, runtime databases, daemon state or one-file-per-agent scaffolds. Preserve critical evidence before cleaning temporary material.

## Verification and completion

Workers run local checks, but no worker or orchestrator self-certifies the final result. Select independent review or reproduction for concrete risks, reusing the native CRA commit-review loop when its criteria apply; do not duplicate review layers merely because they have different titles. Choose an acceptance oracle genuinely independent of the code under test. State numerical tolerances or stochastic criteria explicitly for the domain, using exact parity only where the domain requires it. Do not impose a fixed `$0` reconciliation, AST scan or zero-cache rerun on every task. Reject unsupported success claims and preserve the inputs, versions, commands, raw outputs and artifacts needed to reproduce the result.

The primary checks the actual integrated diff/state and completion evidence against the latest user contract. It reports unresolved gaps, uncertainty and skipped checks; no `VICTORY` ritual is required.

## Lifecycle and boundaries

Stop when the outcome is satisfied and no useful authorized action remains, progress stalls, or required evidence, authority or capability is unavailable. Bound retries to new evidence; do not run endless repair loops without it. This session workflow does not provide daemon or restart recovery and must not be described as a durable service. After interruption, reconcile live agents, workspaces and artifacts before resuming.

Children may not broaden product intent or perform push, deployment, migration, purchase or other external mutation without explicit authorization. Local commits are checkpoints, not permission for remote writes, and account, quota, provider and billing settings remain unchanged.
