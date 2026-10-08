# Teamwork Loop Reference

Use for software execution when multiple specialist roles need coordination or a separate execution coordinator may help. The primary is the default team leader; ordinary conversation, explanation and decisions do not need team ceremony. A separate coordinator is optional and is added only when sustained coordination justifies it.

## Ownership

```text
User <-> Primary team leader -> role-specialized agents
Primary team leader -> optional execution coordinator -> assigned specialists
```

- **Primary:** remains the user-facing session and owns intent, priorities, authority, role assignment and scheduling by default, meaningful contract revisions, status, steering, integration responsibility, final acceptance evidence and the response. It may explicitly authorize a coordinator to integrate completed outputs after writers stop; the primary inspects the integrated state and accepts the result. It does not hand off specialist work to itself because a task is small, workers are idle or capacity is limited, and it never treats a specialist or coordinator summary as final proof.
- **Execution coordinator:** an optional child explicitly delegated team creation and scheduling when sustained coordination needs justify it. It remains accountable to the primary, follows the contract and capability limits, and may coordinate ready specialist assignments or integrate completed outputs after writers stop when the primary explicitly authorizes it. It does not replace the primary, take over the user relationship or accept or certify the final outcome. Specialists do not create their own subteams.
- **Specialists:** each has one professional role, such as frontend, backend, UX, research, operations, instruction authoring or independent reviewer. The role is stated in its contract and has a separate context; reuse is allowed only within that same role. Worker, explorer and reviewer labels do not authorize unrelated professional work; state the specialist's role explicitly. Specialists author their domain deliverables across the necessary same-role files, run local checks and return evidence; an author does not independently accept or final-certify its work.

## Capability gate

Before dispatch, verify through current tool discovery or launcher behavior that the host can provide a separate context for each required role and supports the messaging or followup needed for the planned coordination. An optional coordinator also requires a separate context and, if it assigns nested specialists, supported nested dispatch. Count the primary, coordinator, active specialists and review roles against available slots; respect runtime and account limits and never raise configuration to force capacity. Queue or serialize distinct roles when slots are limited. If the host truly cannot provide a required role/context, report that narrow capability blocker instead of merging roles or having the primary take over the work.

Use message semantics rather than an assumed command alias: a message to a running agent delivers information, while an idle agent wakes only through a host-supported followup. For example, a host may expose `collaboration.spawn_agent`, `send_message` and `followup_task`; verify the actual names and behavior, and never assume `send_message` wakes an idle agent. When supported, specialists may communicate directly with relevant peers about bounded inputs, outputs, constraints and blockers. Route decisions affecting shared scope, interfaces, architecture or acceptance to the primary and affected owners; peer messaging does not authorize scope expansion, peer reassignment, workspace mutation or subteam creation.

## Adaptive scheduling

Choose only the professional roles needed from the task, dependencies and evidence gaps; there is no fixed roster or headcount. Dispatch ready assignments and queue or serialize the rest under capacity limits. Never reuse an agent/context for a different professional role, even if it is idle; a new role gets a separate context. Do not cancel independent valid work merely to rebalance the team, and release or interrupt work only through supported mechanisms.

Choose model, reasoning effort, service tier and context per role and risk. The bounded implementation and CRA defaults in the parent skill do not automatically govern an execution coordinator or other specialist. Use the current launcher and account capacity, and report an unavailable resource honestly.

## Handoffs and workspace ownership

Read `references/worker-delegation.md` for the handoff contract. Include the professional role, responsibility and deliverable, peers and dependencies, scope and constraints, current contract revision, tools and authority, pinned workspace/branch baseline and ownership, primary as integration owner, acceptance evidence and required return evidence. Send only the minimal history and artifacts needed to act.

A mutable worktree has one writer and stable readers. Parallel writing requires distinct worktrees; disjoint filenames alone are not enough. Pin the baseline and name the primary as integration owner. The primary may explicitly authorize a coordinator to integrate completed outputs after writers stop; the primary then inspects the integrated state and performs final acceptance. The primary does not treat file ownership boundaries as professional-role boundaries: one specialist may change all necessary files for its assigned role.

## Steering, cancellation and state

Keep the primary available to the user while work runs, using event or followup notifications instead of polling or empty sleeps. Version meaningful user constraints and forward them to every affected specialist or explicitly delegated coordinator. The coordinator acknowledges revisions it manages; the primary stops or drains affected obsolete work through supported mechanisms and reschedules roles without changing their boundaries. Results made under a superseded contract are unusable for final integration until revalidated against the latest revision.

A cancellation by the primary covers all specialists and related processes owned for the task, including work scheduled through a coordinator. A coordinator also stops or drains its assigned work through supported mechanisms; do not silently abandon workers when termination is unavailable. If a coordinator becomes unavailable, the primary resumes scheduling after reconciling live agents, workspaces, branches and artifacts.

Keep coordination state outside tracked product content only when a handoff needs it, and keep it concise: goal and contract revision; workspace/branch baseline; active agent/task ownership, dependencies and state; evidence, blockers and next action. Reuse an existing project task record. Do not add permanent ledgers, runtime databases, daemon state or one-file-per-agent scaffolds. Preserve critical evidence before cleaning temporary material.

## Verification and completion

Specialists run role-local checks, but no specialist or coordinator self-certifies the final result. The primary integrates domain deliverables, runs completion-critical integrated validation and accepts the result. Select an independent reviewer or reproduction for concrete risks, reusing the native CRA commit-review loop when its criteria apply; do not duplicate review layers merely because they have different titles. Choose an acceptance oracle genuinely independent of the code under test. State numerical tolerances or stochastic criteria explicitly for the domain, using exact parity only where the domain requires it. Reject unsupported success claims and preserve the inputs, versions, commands, raw outputs and artifacts needed to reproduce the result.

The primary checks the actual integrated diff/state and completion evidence against the latest user contract. It reports unresolved gaps, uncertainty and skipped checks; no `VICTORY` ritual is required.

## Lifecycle and boundaries

Stop when the outcome is satisfied and no useful authorized action remains, progress stalls, or required evidence, authority or capability is unavailable. Bound retries to new evidence; do not run endless repair loops without it. This session workflow does not provide daemon or restart recovery and must not be described as a durable service. After interruption, reconcile live agents, workspaces and artifacts before resuming.

Children may not broaden product intent or perform push, deployment, migration, purchase or other external mutation without explicit authorization. Local commits are checkpoints, not permission for remote writes, and account, quota, provider and billing settings remain unchanged.
