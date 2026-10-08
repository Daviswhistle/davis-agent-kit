---
name: software-engineering
description: Use for software implementation, modification, debugging, refactoring, or code review. Assign only the needed specialist roles, keep the primary responsible for integration and final verification, and use CRA, TCA, or an optional coordinator when warranted.
---

# Software Engineering

For software execution, the primary is the dedicated team leader and owns user intent, priorities, authority, task boundaries, integration, final acceptance evidence and the response. It forms only the professional roles the task needs. Each specialist has one professional role and a separate context; reuse stays within that role. Specialists author their domain deliverables and run local checks; the primary integrates their work and performs final validation. Ordinary conversation, explanation and decisions stay with the primary without team ceremony.

## Selection

For software changes:

1. define one coherent task unit, authority and checkable completion criteria;
2. inspect the actual execution path before editing;
3. assign one specialist/context to each professional role needed, including one specialist for a single-role task; there is no fixed roster or headcount;
4. use the resource selection below and read `references/worker-delegation.md` before each handoff;
5. inspect the integrated diff/state and independently verify completion-critical evidence;
6. decide whether CRA is warranted after local validation;
7. use TCA only when multiple independently reviewable task commits materially improve correctness, recovery or reviewability;
8. read `references/teamwork-loop.md` when multiple roles need coordination; add a separate execution coordinator only when sustained coordination justifies one, with the primary remaining the default team leader.

Do not create workflow ceremony merely because a task is difficult or has many steps.

## Resource defaults

Before dispatch, and before reusing a specialist for materially changed same-role work, explicitly select the professional role, model, reasoning effort, service tier and history propagation. Record the selection and a brief reason in the handoff or existing task record. Never reuse a context for a different professional role. Convenience or context continuity alone does not justify retaining more expensive resources.

- bounded implementation worker: first candidate `gpt-6-luna`, Max reasoning, Fast tier
- independent CRA reviewer: `gpt-6.1-sol`, Max reasoning, default/non-Fast service tier
- explorer: cheapest available model that can answer the bounded discovery question reliably
- optional execution coordinator and non-implementation specialists: choose resources proportionate to the coordination, domain-work or verification risk using the current launcher and available account/runtime capacity; the implementation worker default does not automatically govern these roles
- every role: runtime default context; this kit does not raise context-window or auto-compaction limits

Escalate resources only for a concrete quality reason such as ambiguity, consequence of error, difficult reasoning or an insufficient result, and state that reason before dispatch. Verify that the launcher can express the selected settings; report any unavailable setting and the chosen fallback rather than silently inheriting defaults. Check actual model, effort and tier against runtime evidence when exposed; distinguish selected settings from unverified actual settings and do not claim cost optimization without supporting usage/cost evidence.

Current Codex native subagents share the root session's service tier. When the primary must remain default/non-Fast but the bounded implementation worker should use Luna + Max + Fast, run that worker as a separate root through `scripts/run_luna_worker.py` instead of relying on a role-level `service_tier` override. If a selected launcher is unavailable, use an available way to provide the same professional role and report the resource change. If the host cannot provide a separate context for a required role, report that capability blocker; do not transfer the specialist's work to the primary or claim Fast was applied when it was not.

## Local validation

Start with checks closest to the changed behavior and connected contracts. Expand for shared dependencies, broad changes, material uncertainty, safety risk or explicit project requirements.

Reuse a prior result only when the target, dependencies, configuration, environment and acceptance criteria are still applicable and the evidence remains available. Recheck affected results after amendments.

Passing static checks does not establish deployment readiness or model behavior.

## Role boundaries

Do not merge professional roles or move a specialist's deliverable to the primary because the task is small, a worker is idle, slots are scarce or delegation is unavailable. Queue or serialize distinct roles under capacity limits, using a separate context for each role. Worker, explorer and reviewer labels do not authorize unrelated professional work; state the specialist's role explicitly, including independent review when that is the assignment. If the host truly cannot provide a required specialist, report the narrow capability blocker.

Treat one mutable worktree as a single-writer/stable-reader boundary. A writer summary is navigation, not proof.

## CRA

Use CRA when the user explicitly requests it or independent commit-level review materially improves confidence: authentication/authorization, secrets, billing/money, persisted data, migrations, concurrency/recovery, deployment/runtime configuration, agent authority, public contracts, broad multi-path changes or material uncertainty.

Usually skip CRA for narrow mechanical changes already established by focused validation.

When selected, read `references/cra-loop.md` for the native commit-review and amend loop.

## TCA

Use TCA when the user explicitly requests it or a large change has safe, dependency-ordered, independently verifiable commit boundaries whose per-task CRA materially improves recovery/reviewability. Do not manufacture task boundaries.

When selected, read `references/tca-loop.md`.

## Coordination

The primary controls team creation and scheduling unless it explicitly delegates those duties to an execution coordinator. Specialists may coordinate directly with relevant peers through supported tools for bounded inputs, outputs, constraints and blockers; send shared-impact decisions to the primary and affected owners. Read `references/teamwork-loop.md` for messaging, capacity and coordinator boundaries. `/teamwork-preview` remains an intent phrase, but this kit does not install that slash command.

## Boundaries

- Workers may not broaden product intent or perform push, deployment, migration, purchases or remote mutation.
- Local commits are checkpoints, not permission for external writes.
- Existing account usage may be used; billing, plan, quota, provider or account settings may not be changed without explicit approval.
- Do not weaken validation to obtain a pass.

Report material delegation/review evidence, skipped checks and remaining risk. Do not narrate skipped workflows when they do not affect confidence.
