---
name: correct
description: Diagnose repeated agent or project mistakes and remove their causes with the least costly enforceable change. Use only when explicitly selected.
disable-model-invocation: true
---

# Correct

Turn observed failures into durable improvements, not an ever-growing instruction file. Authority comes from the user and applicable AGENTS.md.

1. Inspect the actual failure, recent relevant changes, authorized feedback and existing checks. Group recurring symptoms by causal mechanism; distinguish observed behavior from inferred causes. Distinguish a missing contract, a contract not followed, tool/data failure, routing/control-flow failure, and a faulty check or artifact; do not fix a rule when the mechanism lies elsewhere. A single costly failure can justify action. Do not search unrelated private sessions or publish raw traces.
2. Test the underlying premise before repeating a failed approach. Reproduce the old failure when practical; identify the first incorrect state or decision, the intended behavior and valid cases that must remain possible.
3. Prefer eliminating the error path through ownership, interfaces, data structures or a single source of truth. Otherwise use types, boundary validation, a focused lint/CI check, or a behavioral regression test as appropriate. Use a short instruction or skill only for judgment that cannot economically be enforced. Compare false rejection, maintenance burden and scope against the actual harm; do not add a guard merely because it is possible.
4. Make the smallest durable correction, removing redundant instructions or obsolete paths when safe. For code changes, use the software-engineering workflow and its risk-based review rather than duplicating it. Prove a new check catches a real failing case (or a deliberately broken variant) and preserves legitimate behavior; run affected existing checks. For agent judgment changes, use the experiment skill's paired evaluation when feasible.
5. Record the cause, evidence, change, enforcement or residual judgment, and remaining risk in the task report or PR. Keep permanent rules only where they still change behavior. Do not create a rule ledger, helper or test solely to preserve wording.

If the cause or effect remains uncertain, report the uncertainty and the smallest useful next check; do not claim recurrence has been eliminated. No new authority to inspect private data, merge, deploy or change production is granted.
