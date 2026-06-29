# Repository Discovery Checklist

Use this checklist before writing a project-specific handoff agent. The goal is to discover the current repository's actual operating surface, not to infer it from filenames.

## 1. Local Rules And Boundaries

Inspect:

- `AGENTS.md`, `.agents/`, `.codex/`, or other local instruction files.
- `README.md`, docs indexes, contribution guides, testing docs, deployment docs.
- `.gitignore` and generated-output directories.
- Current git status. Do not revert unrelated or user-owned changes.

Record:

- Required language/tone.
- Commit, push, approval, sudo, network, and destructive-command rules.
- Standard test command, language runtime command, temp directory, and generated artifacts to avoid committing.
- Any repeated domain caveats or naming conventions.

## 2. Project Purpose And First Route

Find:

- One-sentence project purpose.
- Main user workflow or operational workflow.
- The first command, first UI screen, first notebook, first dataset, or first artifact that gives the fastest concrete understanding.
- The exact working directory and environment assumptions for that first action.

The first route must make the next action unambiguous. Avoid "read the README" as the only next step.

## 3. Data And State Roles

List every important input/state/output class:

- Configuration files.
- Domain data files.
- Seed/start state.
- Runtime state.
- Generated output.
- Benchmark/reference data.
- Test fixtures.
- Logs and reports.

For each, capture:

- Path pattern.
- What it represents.
- Whether it is source of truth, reference, sample, generated, or optional.
- What can go wrong if it is confused with another data role.
- Any trust rule: newer vs older, raw vs derived, live vs fixture, benchmark vs actual.

## 4. Artifact Teaching Order

Identify artifacts that teach the project visually or operationally:

- Screenshots, PNGs, PDFs, logs, JSON, CSV, database tables, dashboards, CLI output, traces.
- Which artifact should be opened first and why.
- Which artifacts must be explained one at a time.
- Which artifacts are optional or only produced by specific flags.

For every artifact, define:

- Why this file matters.
- What small part to inspect first.
- What project concept it demonstrates.
- What cannot be concluded from it alone.
- Which file or report must be used for final judgment.

## 5. Code Ownership Map

Trace the main flow from entry point to side effects:

- CLI, service entry point, web route, job runner, app screen, notebook, or script.
- Input parsing and validation.
- Core domain object creation.
- Main algorithm/service layer.
- Persistence/export/rendering.
- Evaluation/validation.
- Tests that exercise the path.

Use actual function and file names. Do not stop at high-level folders.

## 6. Settings And Options

Separate:

- Code constants and feature switches.
- Runtime CLI flags or environment variables.
- User-editable config.
- Data selection arguments.
- Deployment configuration.
- Test configuration.

Explain where a maintainer should change behavior, where they should only select a different input, and where they should not touch without a migration or operational plan.

## 7. Evaluation And Failure Diagnosis

Find:

- Closest smoke test.
- Full test command.
- Lint/type/build commands.
- Domain-specific validators.
- Runtime reports and logs.
- Known warning/error patterns.

Create a diagnosis route:

1. How to tell success vs failure.
2. Which log/report to open first.
3. How to split input problems, algorithm problems, export problems, and evaluation problems.
4. Which tests prove the current layer.

## 8. Advanced Workflows

Find workflows a new maintainer would not know to ask about:

- Continued runs.
- Random/seeded runs.
- Batch or multi-run exploration.
- Candidate selection.
- Optimization or post-processing.
- Deployment or release gates.
- Data repair or migration.

The handoff agent must introduce these proactively after the basics.
