---
name: experiment
description: Design and run falsifiable comparisons, sustained measured improvement, and blinded agent or prompt evaluations with reproducible evidence. Use only when explicitly selected.
disable-model-invocation: true
---

# Experiment

Use experiments to choose actions or improve a system, not to manufacture proof for a preferred answer. Work within existing resource and action authority.

1. Identify the real decision, causal hypothesis and plausible competing explanation. Select representative workloads, acceptance criteria, failure costs and a comparison baseline before changing the system. If the symptom cannot be reproduced, fix the measurement or investigate first.
2. Choose a measurement that reflects the user's outcome and guardrails that must not regress. Establish its sensitivity, noise and validity using the existing harness; read `references/measurement.md` for quantitative comparisons. Preserve the baseline, versions, environment, data and commands needed to rerun.
3. For comparing agent behavior, prompts or skills, read `references/agent-eval.md`. Judge actual artifacts and actions, not self-reported compliance.
4. For sustained improvement, test a causal hypothesis per interpretable iteration. Keep alternatives isolated, measure against the same baseline or the last verified accepted state, and run regression checks. Accept only meaningful improvement with acceptable costs and risks; discard or isolate unsuccessful variants. Record failed as well as accepted attempts and their evidence. Re-examine the premise or change hypothesis family after repeated failure. Interactions can justify a planned joint experiment.
5. Set a proportional resource budget and stopping condition based on the task, noise, value of information and risk. Do not mechanically require a minimum number of iterations, change success criteria to fit results, or stop at a lucky win. A measurement or model selection process must not leak held-out evidence into tuning.
6. Use the actual domain's constraints. In predictive or trading research, preserve time order and point-in-time inputs, realistic execution/costs and untouched out-of-sample evaluation; track selection across attempts, robustness and downside risk. Optimizing one historical metric is not evidence of future performance.

Keep raw logs and private data in authorized scratch storage, not the public kit. Report the baseline and candidate results, uncertainty, regressions, cost, evidence and recommended decision. If live comparisons cannot run, report what was designed or checked and mark behavioral improvement unproven. No automatic promotion, merge or deployment.
