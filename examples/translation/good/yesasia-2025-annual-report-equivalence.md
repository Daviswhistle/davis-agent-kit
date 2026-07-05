# YesAsia 2025 Annual Report Equivalence Evidence

This records a local equivalence run for the YesAsia annual-report reference without storing the copyrighted source or full translated report in this repository.

## Portable Reference Inputs

- Public source PDF: <https://www.yesasiaholdings.com/pdf/e_2209_annualreport2025.pdf>
- Public IR page: <https://www.yesasiaholdings.com/investor-relations.html>
- Accepted reference HTML convention: `${TRANSLATION_REFERENCE_ROOT}/yesasia-2025-annual-report/YesAsia_2025_Annual_Report_KO.html`
- Accepted translated Markdown convention: `${TRANSLATION_REFERENCE_ROOT}/yesasia-2025-annual-report/YesAsia_2025_Annual_Report_KO.md`
- Accepted translated chunks convention: `${TRANSLATION_REFERENCE_ROOT}/yesasia-2025-annual-report/translated_chunks/`

The accepted translated artifacts are local benchmark artifacts and are not committed here. Each machine should set `TRANSLATION_REFERENCE_ROOT` to the directory that contains its local copy of those artifacts.

## Reproduction Command

```bash
: "${TRANSLATION_REFERENCE_ROOT:?set TRANSLATION_REFERENCE_ROOT to the local reference artifact directory}"
YESASIA_REF_DIR="$TRANSLATION_REFERENCE_ROOT/yesasia-2025-annual-report"
YESASIA_REF_MD="$YESASIA_REF_DIR/YesAsia_2025_Annual_Report_KO.md"
YESASIA_REF_HTML="$YESASIA_REF_DIR/YesAsia_2025_Annual_Report_KO.html"
tmpdir="$(mktemp -d)"

PYTHONDONTWRITEBYTECODE=1 python3 skills/translation-quality/scripts/md_to_html.py \
  --input "$YESASIA_REF_MD" \
  --output "$tmpdir/yesasia_regenerated.html" \
  --title "YesAsia Holdings Limited - 2025년도 연례 보고서" \
  --date "2026.03.27."

PYTHONDONTWRITEBYTECODE=1 python3 skills/translation-quality/scripts/qa_html_translation.py \
  --output "$tmpdir/yesasia_regenerated.html" \
  --expect-title "YesAsia Holdings Limited - 2025년도 연례 보고서" \
  --profile report \
  --strict-style

PYTHONDONTWRITEBYTECODE=1 python3 skills/translation-quality/scripts/evaluate_report_equivalence.py \
  --candidate "$tmpdir/yesasia_regenerated.html" \
  --reference "$YESASIA_REF_HTML" \
  --expect-title "YesAsia Holdings Limited - 2025년도 연례 보고서" \
  --expect-pages 167 \
  --require-core-counts-match
```

## Observed Result

Run date: 2026-07-05

Both checks passed:

- `qa_html_translation.py --profile report --strict-style`
- `evaluate_report_equivalence.py --require-core-counts-match`

| Metric | Reference HTML | Regenerated candidate |
| --- | ---: | ---: |
| Pages | 167 | 167 |
| Tables | 111 | 111 |
| Table rows (`tr`) | 1,154 | 1,154 |
| Header cells (`th`) | 468 | 468 |
| Data cells (`td`) | 4,726 | 4,726 |
| External links | 17 | 17 |
| Unique external links | 8 | 8 |
| Emphasis tags (`em`) | 31 | 31 |
| Strong tags (`strong`) | 1,471 | 1,471 |
| Raw markdown/source artifacts | 6 | 0 |

## Interpretation

This proves the repository workflow can reproduce the accepted YesAsia report's publication/report structure from the accepted translated Markdown, with stricter artifact cleanup than the reference HTML. It is structural/publication evidence, not a stand-alone proof of prose or source-fidelity quality.

For a new Codex, agy, or other runner translation to claim equivalent quality, its generated HTML must pass the same report QA and equivalence gate against the relevant accepted reference or reference-derived benchmark, plus source-fidelity/reviewer sampling and the applicable reference axes in `reference-quality-suite.md` recorded in QA.
