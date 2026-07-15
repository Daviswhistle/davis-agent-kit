# Formal Report Profile

Use this profile for annual reports, audit reports, prospectuses, financial statements, governance reports, and other page/table-heavy formal documents. Read `references/core.md` first.

## Profile Contract

1. Preserve page and section hierarchy, table inventory, defined terms, bilingual names, statutory and legal labels, footnotes, signatures, audit blocks, and financial statement structure.
2. Create a page/section map and table inventory during intake. Record intentional source cleanup separately from reader-facing content.
3. Preserve exact table column parity and semantic alignment: descriptive text left, numeric and financial cells right, short codes centered.
4. Remove repeated extraction headers, footers, page markers, and raw Markdown without removing substantive report content.
5. Use `agents/korean_report_reviewer.md` for conceptual review and publication-risk inspection.

## Report Structure And Publication QA

Before final delivery, verify:

1. page-section count and order are plausible for the source
2. heading hierarchy and defined-term usage are consistent
3. table count, row count, header/data cell count, column parity, and table alignment classes match the source contract
4. footnotes, links, signatures, audit opinions, governance labels, and bilingual names remain intelligible
5. TOC and search behavior work when included
6. repeated corporate headers, footers, raw page labels, extraction placeholders, and Markdown artifacts are absent
7. title and fiscal/reporting period are exact
8. `agents/korean_report_reviewer.md` findings are recorded with reviewer mode, evidence, disposition, and remaining risk

Run the report QA profile so transcript-specific style patterns do not mask report structure:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/translation-quality/scripts/qa_html_translation.py" \
  --output outputs/<clear_document_name>_ko.html \
  --expect-title "<exact Korean title>" \
  --profile report \
  --strict-style
```

When comparing a generated report against an accepted reference, run:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/translation-quality/scripts/evaluate_report_equivalence.py" \
  --candidate outputs/<candidate>_ko.html \
  --reference /path/to/accepted_reference.html \
  --expect-title "<exact Korean title>" \
  --expect-pages <page-count> \
  --require-core-counts-match
```

## Equivalence Evidence Gate

When the task goal is to match an accepted reference translation, do not stop after updating prompts, rules, or helper tests. Produce or rerun a candidate output and prove that it reaches the reference bar.

1. Identify the accepted reference artifact, candidate artifact, source file, and the document type.
2. Identify which accepted reference axes apply. Use `examples/translation/good/reference-quality-suite.md` when available: Lululemon for transcript packaging and polished blog flow, PDD Holdings for interpreted-call/source-fidelity handling, and YesAsia for long formal-report publication structure.
3. Do not claim that structural metrics alone prove quality. Metrics prove shape and artifact cleanup; conceptual review, source fidelity, numeric checks, and reader-facing Korean prove translation quality.
4. For annual reports and formal financial reports, run `scripts/qa_html_translation.py --profile report --strict-style` on the candidate.
5. When a reference HTML exists, run `scripts/evaluate_report_equivalence.py` against candidate and reference. For report publication quality, require exact match for page, table, row, header-cell, and data-cell counts unless the QA explicitly explains a source-backed structural change.
6. For transcript or earnings-call references, use the transcript QA helper, source-unit numeric checks, and conceptual reviewer ledger. If no dedicated equivalence script exists yet, write a task-local evaluator before claiming equal quality.
7. Record the command, pass/fail result, metric table, reviewer/source-fidelity sampling, skipped checks, and residual risk in `work/qa_report.md` or an `examples/translation/good/*equivalence*.md` evidence note.
8. A passing unit-test suite proves the tools; it does not prove equivalent output quality. Equivalent quality requires a candidate artifact passing the relevant reference gates and the applicable exemplar axes.

## Report Final-File Checks

1. `<html lang="ko">`, `<meta charset="utf-8">`, `</body>`, and `</html>` are present
2. structural tags are balanced and every table has exact column parity
3. page sections, tables, rows, header cells, data cells, links, and footnotes are counted or the reason for skipping is recorded
4. left, right, and center table alignment classes reflect cell meaning
5. no raw source helper metadata appears in the reader-facing title block
6. reference-quality claims identify the applicable exemplar axes and include candidate-artifact evidence
7. no accepted report-review finding remains unresolved
