---
name: software-engineering
description: Use for software implementation, modification, debugging, refactoring, or code review. Use CRA or TCA when warranted.
---

# Software Engineering

This optional workflow covers software-specific implementation, validation, CRA/TCA and delegated resource candidates. Action permissions come from the user and applicable `AGENTS.md`.

## Selection

For software changes:

1. define one coherent task unit, authority and checkable completion criteria;
2. inspect the actual execution path before editing;
3. if delegating, choose from the software candidates below; read `references/implementation-worker-launch.md` only when that launcher fits the selected resources;
4. inspect the integrated diff/state and independently verify completion-critical evidence;
5. decide whether CRA is warranted after local validation;
6. use TCA only when multiple independently reviewable task commits materially improve correctness, recovery or reviewability.

Do not create workflow ceremony merely because a task is difficult or has many steps.

## Delegated software resource candidates

These candidates apply only after delegation is independently warranted; do not delegate just to use a candidate:

- bounded implementation worker: first candidate `gpt-6-luna`, Max reasoning, Fast tier
- independent CRA reviewer: `gpt-6.1-sol`, Max reasoning, default/non-Fast service tier
- explorer: cheapest available model that can answer the bounded discovery question reliably

## Local validation

Start with checks closest to the changed behavior and connected contracts. Expand for shared dependencies, broad changes, material uncertainty, safety risk or explicit project requirements.

Reuse a prior result only when the target, dependencies, configuration, environment and acceptance criteria are still applicable and the evidence remains available. Recheck affected results after amendments.

Passing static checks does not establish deployment readiness or model behavior.

## Repository ownership

For concurrent software edits, treat each mutable Git worktree and its index, dependencies, generated artifacts and test state as one writer boundary. Parallel writers require separate worktrees; disjoint filenames alone do not isolate this state. A writer summary is navigation, not proof.

## CRA

Use CRA when the user explicitly requests it or independent commit-level review materially improves confidence: authentication/authorization, secrets, billing/money, persisted data, migrations, concurrency/recovery, deployment/runtime configuration, agent authority, public contracts, broad multi-path changes or material uncertainty.

Usually skip CRA for narrow mechanical changes already established by focused validation.

When selected, read `references/cra-loop.md` for the native commit-review and amend loop.

## TCA

Use TCA when the user explicitly requests it or a large change has safe, dependency-ordered, independently verifiable commit boundaries whose per-task CRA materially improves recovery/reviewability. Do not manufacture task boundaries.

When selected, read `references/tca-loop.md`.

## Boundaries

- Workers may not broaden product intent or perform push, deployment, migration, purchases or remote mutation.
- Action permissions come from the user and applicable `AGENTS.md`; a local commit or review does not grant additional authority.
- Existing account usage may be used; billing, plan, quota, provider or account settings may not be changed without explicit approval.
- Do not weaken validation to obtain a pass.

Report material delegation/review evidence, skipped checks and remaining risk. Do not narrate skipped workflows when they do not affect confidence.
