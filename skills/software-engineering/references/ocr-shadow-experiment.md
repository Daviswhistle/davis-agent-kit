# OpenCodeReview Shadow Experiment

Use this only when the user explicitly asks to evaluate OpenCodeReview (OCR) against the native CRA reviewer. It is an experiment, not a replacement review path.

## Invariants

- Native `codex review --commit` remains the CRA completion authority.
- Compare both reviewers on the same fixed, clean, non-merge HEAD commit before any amendment.
- Keep the reviewer resource profile aligned with CRA: `gpt-6-astra`, High reasoning, default/non-Fast tier.
- OCR delegation supplies deterministic file selection and rule resolution only. It does not call a separate LLM endpoint.
- Shadow findings are untrusted until checked against the actual code and task intent. Do not change code merely to satisfy OCR.
- The shadow run must not mutate the repository. Write any report outside the worktree.

## Prerequisites

`ocr`, `codex`, and Git must be available. OCR delegation mode currently exposes schema version 1; `scripts/run_ocr_shadow_review.py` rejects schema drift instead of guessing.

Install OCR when needed:

```bash
npm install -g @alibaba-group/open-code-review
```

Delegation mode does not require an OCR-side model or API key.

## Per-commit experiment

After local validation and after creating the coherent task commit:

1. Freeze `COMMIT_SHA="$(git rev-parse HEAD)"` and keep the checkout unchanged.
2. Run the normal native CRA review against that SHA, but do not amend yet.
3. Run the OCR shadow reviewer against the same SHA:

```bash
python skills/software-engineering/scripts/run_ocr_shadow_review.py \
  --commit "$COMMIT_SHA" \
  --output "/tmp/ocr-shadow-${COMMIT_SHA}.md"
```

The helper requires the target to equal clean repository `HEAD`, asks OCR for `delegate preview --format json` and `delegate rule --format json`, verifies full rule coverage, then launches a separate read-only Codex root pinned to the CRA reviewer profile. The report records selected files, OCR-excluded files and reasons, wall time, and the shadow findings.

4. Adjudicate the union of native and shadow findings against the code and task intent. For each finding, record whether it is a valid in-scope defect, a false positive, or pre-existing/out-of-scope, and whether it was native-only, shadow-only, or overlapping.
5. Apply the smallest fixes for all valid in-scope findings, rerun affected local validation, and amend the same task commit.
6. The normal CRA rule still applies after amendment: rerun native `codex review` on the complete amended commit. Rerun the shadow reviewer too only when continuing the experiment on that amended sample.

If OCR excludes a changed file and the native reviewer finds a valid defect there, count that as a shadow recall miss caused by selection rather than hiding it as an out-of-scope difference.

## Evaluation

Use representative commits rather than cherry-picked examples. An initial 10–20 commit sample is usually enough to decide whether a longer trial is justified. Compare at least:

- valid findings and unique valid findings per reviewer;
- false positives / precision;
- missed P0/P1 findings or other materially costly misses;
- exclusion-caused misses;
- wall time and operational friction.

Do not promote OCR to the default merely because it produces fewer comments. Consider replacement only if the shadow path materially reduces false positives or cost without a meaningful loss of important defect detection. Until that evidence exists, keep native CRA unchanged.
