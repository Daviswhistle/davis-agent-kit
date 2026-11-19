---
name: agent-improvement-loop
description: Improve an existing agent harness from observed execution traces and human/model feedback, using replayable regression cases and a bounded implementation handoff. Use only when explicitly selected.
---

# Agent Improvement Loop

Use this optional skill to make **observed failures** into **reusable evaluations** and verified harness changes. It does not instrument a model runtime, launch HALO, or autonomously modify production. Authority comes from the user and applicable `AGENTS.md`.

## Work from evidence, not a proposed prompt

1. **Capture:** Collect representative real run traces and final artifacts using the target agent's existing logging/trace system. Use the same task inputs for a baseline and proposed candidate. Record model/config/tool versions, environment and relevant cost/latency separately. Redact secrets, personal data and private source content; keep raw traces and reports outside this public kit.
2. **Review:** Keep human feedback separate from model-generated observations. Identify a concrete failure and the source/evidence that makes it a failure. Do not mistake a judge's preference or a trace summary for ground truth.
3. **Diagnose:** For each failure choose one primary cause: missing behavior contract, existing contract not followed, tool/data failure, routing/control-flow defect, artifact/validator defect, or inconclusive. Prefer a minimal targeted fix to another generic instruction.
4. **Make the regression:** Write one or more reviewed, observable assertions against the *actual output*, not only presence of a citation or a successful tool call. Use exact text or structured values for deterministic conditions; add a separately judged rubric or human check for semantic judgment. Use fresh holdout cases when asserting generalization.
5. **Implement and replay:** Give the coding agent a narrow change, exact failing examples, intended effect, tests, rollback and allowed paths. Compare baseline and candidate on the same cases. Run this skill's evaluator for mechanical assertions and use an independent reviewer where judgment is necessary. If no actual failure was observed, don't invent one or add speculative tests.
6. **Promote or reject:** Preserve the reviewed tests in the target project's regression suite **only when they protect real behavior**, check for new regressions, inspect runtime cost and failure modes, and require the project's existing review/merge gates. A deterministic pass does not establish improved reasoning or real-world reliability.

When the issue is a software defect, follow the existing `$software-engineering` workflow for implementation and its risk-based review; do not duplicate its code-review ceremony. Do not promote automatically, merge, deploy or update permissions without the authority required by the active project.

## Deterministic replay gate

The standard-library helper `scripts/evaluate.py` scores recorded outputs; it **does not execute agents**. Create an evaluation suite in a scratch directory (not this kit) and two run directories with one subdirectory per case ID:

```text
scratch/agent-loop/
  suite.json
  baseline/<case-id>/answer.md
  candidate/<case-id>/answer.md
  candidate/<case-id>/evidence.json
  source-data/finance.csv
```

Example `suite.json` (assertions may target any UTF-8 relative file within the corresponding case directory):

```json
{
  "version": 1,
  "cases": [{
    "id": "unvalidated-metric",
    "assertions": [
      {"type": "contains", "path": "answer.md", "value": "unvalidated"},
      {"type": "not_contains", "path": "answer.md", "value": "official NRR: 122%"},
      {"type": "json_equals", "path": "review.json", "pointer": "/validated", "value": false},
      {"type": "evidence_quotes", "path": "evidence.json"}
    ]
  }]
}
```

For `evidence_quotes`, the output file is a nonempty JSON array containing `{"claim":"...", "evidence":[{"file":"finance.csv", "quote":"exact source excerpt, at least 8 characters"}]}`. Each source file must be beneath `--sources`, and each quote must be an exact substring in that file. This blocks nonexistent citations and fabricated excerpts, **not** a real excerpt used to support the wrong conclusion; check entailment with a human/domain reviewer or a separate calibrated judge.

```bash
python3 skills/agent-improvement-loop/scripts/evaluate.py \
  --suite scratch/agent-loop/suite.json \
  --baseline scratch/agent-loop/baseline \
  --candidate scratch/agent-loop/candidate \
  --sources scratch/agent-loop/source-data \
  --output scratch/agent-loop/comparison.json
```

Exit code `0`: every candidate assertion passed. `1`: at least one candidate failure or regression. `2`: invalid suite. The report details improvements and regressions **per assertion**, so a new failure cannot be hidden by another improvement. Missing artifacts fail closed. Never copy raw case outputs, feedback, traces, or reports into a public repository without explicit authorization.

## Done means

Report the actual changed files/commit, which traces and checks were executed, baseline-versus-candidate results, separately assessed semantic quality, cost/latency changes if measured, remaining failures and approval boundaries. If there is no replayable runtime or no real traces, deliver the verified tooling and explicitly mark behavior improvement as **unproven**.
