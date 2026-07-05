# Reference Translation Quality Suite

This records the accepted local translation references used to define "reference-quality" output without storing copyrighted source text or full translated artifacts in this repository.

## Purpose

These references are not answer keys to memorize. They define the quality axes that a new Codex, agy, or other runner output must prove before claiming equivalent quality.

Mechanical metrics are only one gate. They prove structure, formatting, and artifact cleanup. They do not by themselves prove natural Korean, source fidelity, domain judgement, or reader usefulness.

## Portable Reference Locators

Accepted translations are local reference artifacts, but this repository should not hard-code one user's machine path or store full copyrighted translated outputs. Put local reference artifacts under a machine-specific `TRANSLATION_REFERENCE_ROOT`, and use the public source locators below to recover the original source context.

| Reference | Public source locator | Reference artifact convention | Primary quality axis |
| --- | --- | --- |
| Lululemon earnings-call transcript | Official event page: <https://corporate.lululemon.com/investors/news-and-events/events-and-presentations/2026/lululemon-athletica-q1-2026-results>; official results release: <https://corporate.lululemon.com/media/press-releases/2026/06-04-2026-210523775> | `${TRANSLATION_REFERENCE_ROOT}/lululemon/lululemon_athletica_inc_2027_q1_transcript_ko_blog.html` | Blog-ready transcript flow: speaker-change-only labels, paragraph rhythm, real blank-line elements, fiscal-year title, live links, product/campaign/finance wording, and OCR/PDF cleanup. |
| PDD Holdings earnings-call transcript | Official event page: <https://investor.pddholdings.com/events/event-details/pdd-holdings-1q-2026-earnings-conference-call/> | `${TRANSLATION_REFERENCE_ROOT}/pdd/PDD_Holdings_Inc_2026-05-27_transcript_ko.html` | Interpreted-call fidelity: operator/facilitator/executive/analyst roles, original-speaker attribution, `data-unit` traceability, RMB/billion conversion, platform-domain terminology, and explanatory notes. |
| YesAsia annual report | Official annual report PDF: <https://www.yesasiaholdings.com/pdf/e_2209_annualreport2025.pdf>; IR page: <https://www.yesasiaholdings.com/investor-relations.html> | `${TRANSLATION_REFERENCE_ROOT}/yesasia-2025-annual-report/YesAsia_2025_Annual_Report_KO.html` | Long formal-report publication: page/section structure, table inventory, table alignment, links, defined names, legal/governance labels, and multi-pass review fanout. |

Reference-root setup example:

```bash
export TRANSLATION_REFERENCE_ROOT="/path/to/local/translation-reference-artifacts"
```

## Observed Local Checks

Run date: 2026-07-05

### Lululemon

Command:

```bash
: "${TRANSLATION_REFERENCE_ROOT:?set TRANSLATION_REFERENCE_ROOT to the local reference artifact directory}"
LULULEMON_REF="$TRANSLATION_REFERENCE_ROOT/lululemon/lululemon_athletica_inc_2027_q1_transcript_ko_blog.html"

PYTHONDONTWRITEBYTECODE=1 python3 skills/translation-quality/scripts/qa_html_translation.py \
  --output "$LULULEMON_REF" \
  --expect-title "lululemon athletica inc. 2027 회계연도 1분기 실적 발표 컨퍼런스콜" \
  --expect-date "2026.06.04." \
  --strict-style
```

Observed result: `PASS`.

Interpretation: the helper now treats the Lululemon artifact's HTML structure, title/date, and exact recurring template checks as passing. That does not mean every wording choice is automatically ideal; ordinary words such as `말씀`, `측면에서`, or `비교됩니다` require conceptual review against source role, register, and sentence purpose rather than blacklist-style mechanical failure.

Do not treat the legacy Lululemon artifact as a string-perfect target. Treat it as the positive reference for transcript packaging, speaker flow, paragraphing, rich HTML, fiscal-year title handling, link preservation, product/finance term review, and PDF cleanup. New outputs should keep those strengths while satisfying the conceptual-review rules now captured in the skill.

Known stricter-rule caveat: the legacy artifact uses `<em>` broadly for notes, product/campaign names, SEC form names, and common finance acronyms. That was acceptable for the original artifact, but new outputs should not copy the broad-emphasis habit mechanically. The QA record should distinguish translator notes from source terms and should justify any emphasized ordinary acronym.

### PDD Holdings

Command:

```bash
: "${TRANSLATION_REFERENCE_ROOT:?set TRANSLATION_REFERENCE_ROOT to the local reference artifact directory}"
PDD_REF="$TRANSLATION_REFERENCE_ROOT/pdd/PDD_Holdings_Inc_2026-05-27_transcript_ko.html"

PYTHONDONTWRITEBYTECODE=1 python3 skills/translation-quality/scripts/qa_html_translation.py \
  --output "$PDD_REF" \
  --expect-title "PDD Holdings Inc. 2026년 1분기 컨퍼런스콜" \
  --expect-date "2026.05.27." \
  --strict-style
```

Observed result: `PASS`.

Interpretation: PDD is the strict transcript regression reference for interpreted-call handling, unit-level traceability, platform terminology, RMB/billion scale, and source-visible explanatory notes.

### YesAsia

Command:

```bash
: "${TRANSLATION_REFERENCE_ROOT:?set TRANSLATION_REFERENCE_ROOT to the local reference artifact directory}"
YESASIA_REF="$TRANSLATION_REFERENCE_ROOT/yesasia-2025-annual-report/YesAsia_2025_Annual_Report_KO.html"

PYTHONDONTWRITEBYTECODE=1 python3 skills/translation-quality/scripts/qa_html_translation.py \
  --output "$YESASIA_REF" \
  --expect-title "YesAsia Holdings Limited - 2025년도 연례 보고서" \
  --profile report \
  --strict-style
```

Observed result: the accepted reference HTML has six hard raw-markdown artifact findings. The regenerated candidate recorded in `yesasia-2025-annual-report-equivalence.md` passes report QA and matches the accepted reference on core report structure while reducing raw artifacts to zero.

Interpretation: YesAsia is the formal-report structure and review-fanout reference. New report outputs must preserve that structure and should improve artifact cleanup, not reproduce known raw-markdown residue.

## Future Equivalence Claim

A future output can claim equivalent quality only when its QA record includes all applicable evidence:

1. Candidate artifact path and source locator, using a web URL when available and a configurable local reference root when the accepted artifact cannot be committed.
2. Which reference axes apply: Lululemon transcript packaging, PDD interpreted-call/source-fidelity handling, YesAsia report publication structure, or another documented local reference.
3. Conceptual review ledger with finding-level evidence, not only "looks good."
4. Source-unit or page/chunk coverage evidence.
5. Numeric/source-fidelity checks for every material repeated figure or range in the final artifact.
6. HTML/publication checks for links, emphasis, speaker/paragraph spacing, table parity, or report navigation as applicable.
7. Task-local evaluator output. For formal reports, include `evaluate_report_equivalence.py`; for transcripts, include `qa_html_translation.py` plus source-unit checks and reviewer findings.
8. Explicit residual risk. If any legacy reference has known weaknesses, the candidate must not inherit them silently.
