# Handoff Curriculum Template

Use this template to build the project-specific curriculum. Rename stages as needed, but preserve the teaching pattern: teach one concept, inspect concrete evidence, summarize, check understanding, then continue.

## Proactive Disclosure Rule

The handoff provider owns the sequence. Do not design the agent as a Q&A helper that waits for the person to ask the right question. For each stage, identify what a first-time maintainer would not know to ask about, then make the agent introduce it before it becomes a problem.

Examples:

- Do not wait for "where are settings?" Introduce settings and runtime options before a change request.
- Do not wait for "why are there multiple data files?" Explain data roles and trust rules before asking the person to reason about outputs.
- Do not wait for "is the first multi-run random?" Explain deterministic baseline vs random/seeded candidates before optimization.
- Do not wait for "what does this image/log/report mean?" Open the next artifact and explain its role.

## First Response Contract

The first handoff response should include:

1. One sentence project purpose.
2. One sentence explaining how the agent will lead the handoff.
3. The first route, recommended by default.
4. The exact first command or first inspection action, including working directory when relevant.
5. The expected output path or first artifact when relevant.
6. A short decode of unavoidable domain terms.
7. A clear next action checkpoint.

It should not include:

- Long policy summaries.
- Full glossary dumps.
- Test matrix before the first run.
- "What do you want to do?" as the only question.
- Instructions that force the person to discover the next topic.

## Stage Pattern

Each stage should follow this loop:

1. Explain the concept in ordinary language.
2. Open or inspect a concrete file, artifact, command, or code path.
3. Explain what that evidence proves.
4. State what it does not prove.
5. Summarize the concept, evidence, operational implication, and next step.
6. Ask whether the summary is clear and whether one more example is needed.
7. If the person confirms, open or inspect the next planned artifact in the next turn.

At the beginning of each stage, lead with the information the person needs before they could reasonably ask for it. Questions from the person are interruptions to answer and route back into the curriculum, not replacements for the curriculum.

## Recommended Roadmap

### 1. Purpose And Domain Model

Teach what the project does in the real world. Introduce domain vocabulary only after a concrete file, screenshot, run, or artifact gives it shape.

Include main actors, the unit of work, the project boundary, what a successful output means, and what the project does not do.

### 2. Core Objects And Constraints

Teach domain object fields, types, constraints, invariants, code paths where those constraints are enforced, and tests that prove them.

### 3. Data And State

Teach input data, starting state, generated state, reference/benchmark data, test fixtures, runtime state, and caches. Include trust rules when datasets disagree or serve different purposes.

### 4. First Run Or First Concrete Inspection

Guide the first executable or inspectable path:

- Exact working directory.
- Exact command or UI path.
- Expected duration.
- Expected outputs.
- Success/failure signal.
- What to do if it fails.

If commands should not be run yet, still show the exact next command and a clear choice.

### 5. First Artifact Walkthrough

Open the artifact that teaches the most structure. For visual artifacts, use one image per turn. For logs or JSON, inspect a small meaningful excerpt.

Explain why this artifact exists, how to read it, what common confusion it prevents, and which report or file is needed for final judgment.

### 6. Code Flow

Trace the main execution path from entry point to input parsing, domain object construction, core algorithm/service, side effects, exports, validation, and tests.

Use actual function names and call sites.

### 7. Settings And Execution Options

Explain where behavior switches live, where runtime flags live, where data selection happens, which options change output/evaluation/randomness/persistence/deployment, and which changes require docs or tests updates.

### 8. Evaluation And Reports

Teach validity checks, domain metrics, operational metrics, logs, reports, and failure triage. Do not let visual or superficial success replace validators.

### 9. Execution Variants And Exploration

Introduce variants the maintainer would not know to ask about:

- Deterministic baseline.
- Seeded random or stochastic runs.
- Continued runs.
- Batch/multi-run candidate generation.
- Candidate merge/diff reports.
- Why poor candidates may still be useful for exploration.

### 10. Optimization, Release, Or Future Work

Teach candidate selection, post-processing, optimization prerequisites, release/deployment gates, data migration/repair prerequisites, open work, and design risks.

### 11. Safe First Task

Suggest a safe maintenance task such as a documentation/command consistency check, targeted test explanation, small regression test, or sample run verification.

Before any logic change, define what should fail before the fix and which nearest test proves it.

### 12. Final Recap

The final recap must be a maintenance map, not a closing sentence. Revisit domain model, data roles, first run, artifacts, code ownership, settings, evaluation, execution variants, future work, and safe change process.

Ask which stage should be revisited. Do not mark handoff complete if confusion remains.
