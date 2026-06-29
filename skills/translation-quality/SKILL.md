---
name: translation-quality
description: |
  Use this skill whenever the user asks for a non-trivial translation, transcript translation, financial/earnings-call translation, blog-ready translation, or review/revision of an existing Korean translation. It preserves source structure while producing natural Korean, applies the user's preferred speaker/paragraph formatting, and requires a full-document QA pass before delivery.
---

# Translation Quality

This skill defines the user's expected translation workflow and output standard. It applies even when the user does not ask for a blog-ready file. The goal is a deliverable that can be pasted or published with minimal cleanup.

## Core Standard

1. Translate meaning, not English syntax. Korean must read like polished Korean business prose, not a literal transcript.
2. Preserve the original document's information, order, speaker flow, emphasis, links, and explanatory context.
3. Do not treat the first draft as final. A full-document review and revision pass is mandatory.
4. Do not rely on the user to catch obvious translationese. Search for recurring weak phrases mechanically and revise them before delivery.
5. If a term needs explanation, place the note at the first occurrence of the term, not later.
6. If rich formatting matters, prefer HTML over plain text so bold, italics, links, and copy-paste line breaks survive.
7. The final standard is a reader-facing Korean transcript, not an annotated extraction dump. Do not expose internal extraction labels, duplicate metadata, interpreter placeholders, or source-cleanup artifacts unless the user explicitly asks for them.

## Portable Quality Contract

This skill must work from a fresh git install with no prior chat history, no remembered examples, and no local completed translations. Treat this `SKILL.md`, its bundled resources, the user's request, and the source document as the complete quality standard.

1. Do not rely on phrases such as "the previous translation" or "the last accepted result" as hidden requirements. Convert any such reference into explicit checks from this skill and its resources.
2. For long transcripts, earnings calls, blog-ready translations, or quality-sensitive revision work, read `references/quality_benchmark.md` during intake. Use it as the portable benchmark for what "good enough" means.
3. If the user references unavailable prior work, state that the prior artifact is unavailable and apply the benchmark criteria instead of pretending to know it.
4. Record in `work/qa_report.md` that the portable benchmark was used, and list any benchmark item that was intentionally not applicable.
5. Resolve bundled resources relative to the directory containing this `SKILL.md` first. If the skill is installed in the default location, `${CODEX_HOME:-$HOME/.codex}/skills/translation-quality` is the expected root.

## Reader Contract

Use these higher-level principles to decide what must be fixed. Mechanical bad-pattern checks are only a backstop.

1. The output is for a Korean reader trying to understand the event, not for an engineer trying to inspect extraction artifacts. Anything visible in the final document must help that reader.
2. Preserve the communicative role of each line. A handoff should read like a handoff, a disclaimer like a disclaimer, a financial comparison like a financial comparison, and a translator note like a translator note.
3. Speaker labels answer "who is speaking here?" rather than "what label did extraction produce?" Operator, company host, executive, analyst, and interpreter are different roles and must remain intelligible.
4. Korean honorifics imply hierarchy. Do not use polite nouns or verbs such as `말씀` merely because the English says "remarks" or "said"; choose register based on the relationship among speaker, listener, and document reader.
5. Financial units shape the reader's economic intuition. Currency codes, `billion`, `억`, dates, fiscal periods, percentages, and bp must be converted or displayed so a Korean reader will infer the same scale as the source.
6. Explanatory notes exist to prevent a likely misunderstanding, not to decorate the translation. A note is justified only when it clarifies a relationship, term, or event that the source alone would leave unclear for the target reader.
7. Repetition, greetings, self-identification, and call boilerplate may be shortened only when the information remains clear from speaker labels and flow. Do not erase substance; do remove ceremony that makes the Korean read like raw simultaneous interpretation.
8. If the user points out a phrase, infer the underlying class of failure and update the translation or skill at that level. Do not only add that exact phrase to a blacklist.
9. Period labels are part of financial meaning. If the call date and the period year differ, assume a fiscal-year issue may exist and preserve it explicitly, for example `2027 회계연도 1분기`, rather than silently converting it to a calendar-year phrase.
10. Domain terms must preserve business relationships. In platform transcripts, `merchant` is usually `판매자`, not `가맹상인`, unless the source is actually a franchise context. `first-party brand/business/model` is often `자체 브랜드` or `자체 브랜드 사업`, not `직영 브랜드`, unless the source is about directly operated retail stores.

## Work Discipline

This skill is not only a style guide. It is a workflow contract for producing and maintaining translation deliverables without relying on hidden memory or user cleanup.

1. State the task objective and completion conditions in one sentence before substantial work. For long or file-based jobs, record that sentence in `work/translation_progress.md` or `work/qa_report.md`.
2. Trace the source-to-output flow before editing: source extraction, source units, speaker map, chunk files, assembly script, final output, QA helper, and task-local evaluators. Do not patch only the visible symptom if the same failure can recur in another unit, chunk, or generated file.
3. Identify affected resources before changing the skill itself. If a rule changes, check whether `SKILL.md`, `agents/korean_translation_reviewer.md`, `references/quality_benchmark.md`, helper scripts, tests, and README need matching updates.
4. Keep scope tight. Do not rewrite unrelated sections, modify unrelated user files, or include generated logs/caches in the skill contract unless they are intentional deliverables.
5. User corrections are evidence of a failure class. Convert them into a principle, reviewer check, benchmark example, helper check, or test when that prevents recurrence. Do not only add the exact corrected phrase to a blacklist.
6. Separate verification from approval or publication. Before claiming readiness, list the commands or reviews run, checks skipped with reasons, and residual risks. A passing helper alone is not enough if conceptual review, source coverage, or a relevant local evaluator is missing.
7. If a check fails, decide whether the output, test, helper, or contract is wrong based on the reader contract and source evidence. Fix the root cause and rerun the closest relevant checks before moving on.
8. Check naming and visible labels as part of quality. File names, titles, speaker labels, `data-unit` IDs, note basis fields, test names, and helper option names should describe their current role rather than an earlier implementation detail.

## Initial Intake

Before translating or revising:

1. Identify the source file or pasted text and confirm whether it is a PDF, plain text, HTML, or another format.
2. Extract text with a structure-preserving method when possible. For PDFs, keep speaker names, question/answer sections, links, footnotes, and page-break artifacts separate.
3. Determine the intended output:
   - If the user asks for `.txt`, use plain text unless formatting requirements make that insufficient.
   - If the user needs bold speakers, italics, live links, or copy-paste-safe spacing, produce HTML.
   - If the user says blog-ready, produce copy-paste-safe HTML by default.
4. Create intermediate working files under the current workspace's `work/` directory and final user-facing files under `outputs/`.
5. Keep the original source and intermediate extraction available until the final QA is complete.
6. Separate reader-visible metadata from QA metadata. A filename date, call date, fiscal period, source title, and generated-output label may all be useful internally, but the output should usually show only the clean Korean title and the call date. Record the rest in `work/qa_report.md`.
7. Before translating, scan the current task directory for explicit local evaluation files or scripts such as `evaluation_*.md`, `rubric*.md`, `*_rubric.md`, `evaluate_*.py`, `check_*.py`, or `test_*.py`. Treat them as part of the acceptance criteria unless they conflict with the user request. Run applicable evaluators before claiming QA success.

## Large Document Execution Contract

For long transcripts, PDFs, earnings calls, interviews, or any source longer than roughly 3,000 words, do not attempt to translate the entire document in one uninterrupted model response. That often leads to stalls, omissions, or half-finished files. Use a chunked file-based workflow.

1. Build a source outline first:
   - title/date
   - speaker list
   - language/interpreter flow, if the call contains non-English remarks or interpreted answers
   - currency and large-number units
   - fiscal year versus calendar date relationships
   - domain-specific terms whose literal translation may change the business model
   - prepared remarks
   - Q&A turns
   - footnotes, disclaimers, links, and unusual terms
2. Normalize the source into numbered translation units under `work/`, preserving speaker changes and paragraph boundaries.
3. Translate in chunks that are small enough to review, usually 20-40 source paragraphs or one coherent Q&A section at a time.
4. Save every translated chunk immediately under `work/translation_chunks/` before moving to the next chunk.
5. Do not fake chunking by writing one giant translation dictionary or script for the entire document and only splitting it afterward. Each chunk must be translated, saved, and reviewable as its own artifact before the next chunk is authored.
6. Keep a progress ledger such as `work/translation_progress.md` with:
   - source range translated
   - chunk file path
   - unresolved terms
   - QA notes
7. If interrupted, resume from the progress ledger. Do not restart from scratch unless the extraction itself was wrong.
8. After all chunks are translated, assemble the final output with a script or deterministic parser rather than manually pasting a huge document.
9. Run QA on the assembled file, then revise the source chunks or final assembly as needed.
10. Do not report completion until the final output file exists and the mandatory QA pass has run.

For long transcripts, `work/translation_progress.md`, `work/translation_chunks/`, and `work/qa_report.md` are required deliverables, not optional examples. If the source is long but chunk files are intentionally skipped because the user supplied an already-final translation to review, record the reason in `work/qa_report.md` and still provide a unit-to-output coverage check before final delivery.

When delegating to another Codex process or working non-interactively, make the prompt require this chunked workflow explicitly. A single monolithic "translate the whole PDF and write one HTML" instruction is not sufficient for long documents.

## Working File Pattern

Use this file pattern for non-trivial translations unless the user gives a stronger preference:

```
work/
  source_extracted.txt
  source_units.tsv
  translation_progress.md
  translation_chunks/
    001_prepared_remarks.html
    002_financial_guidance.html
    003_qna_01.html
    ...
  qa_report.md
outputs/
  <clear_document_name>_ko.html
```

Each source unit should include:

1. unit number
2. speaker, if any
3. source text
4. section marker
5. whether the speaker changed from the previous unit
6. visible speaker, if different from the extracted speaker
7. source speaker, if the visible speaker is inferred from an interpreter or anonymous speaker label

This makes it possible to verify speaker labels and omissions mechanically.

Before translation, scan every source unit for multiple speaker markers using a known speaker list. Any unit containing two or more speaker markers must be split into separate source units before translation. Record the number of split units and the affected source ranges in `work/qa_report.md`.

## Speaker And Paragraph Formatting

Use this format for transcripts unless the user explicitly requests otherwise:

1. Add a speaker label only when the speaker changes.
2. Put the speaker label on its own line.
3. Do not insert a blank line between the speaker label and that speaker's first paragraph.
4. Do not add a speaker label to every sentence.
5. Break by natural paragraphs, not sentence by sentence.
6. Do not cram the entire answer into one dense block. Separate distinct ideas, financial guidance, operational commentary, and Q&A turns into readable paragraphs.
7. For blog/copy-paste HTML, use actual blank-line elements such as `<div class="blank"><br></div>`, not CSS margins alone, because CSS-only spacing may disappear when pasted.
8. Speaker names in HTML should be bold, for example `<strong>Executive A</strong>`.
9. Keep call roles distinct. Translate the bridge `Operator` as `사회자`; translate the company IR host or moderator as `진행자` when the source uses an anonymous speaker label. Do not collapse both roles into the same Korean label.
10. For bilingual or interpreted calls, do not print `[Non-English content]`, `[비영어 발언]`, or equivalent markers in the final output when an interpreted version is present. Attribute the interpreted paragraph to the original speaker whenever the source flow makes that clear. Use internal attributes such as `data-source-speaker` or QA notes for traceability rather than showing `통역` as the reader-facing speaker.
11. If the interpreter owner is ambiguous, inspect the source around the skipped non-English unit, the Q&A question, and any self-identification in the interpreted answer. Use `통역` as a visible label only when the original speaker cannot be determined after that check, and record the ambiguity in QA.

## Korean Style Rules

Prefer concise, natural Korean equivalents over literal English patterns:

1. Avoid "높은 수준에서 말씀드리겠습니다." Use context-specific wording such as "큰 틀에서 보면" only if it sounds natural, or remove the filler if it adds no meaning.
2. Avoid "다음 질문은 X에게서 나옵니다." Use "다음은 X입니다. 부탁드립니다.", "첫 질문은 X입니다.", or another call-operator sentence depending on the flow.
3. Avoid "파급 효과를 만들어내지 못했습니다." Use the actual business meaning, such as "다른 제품군의 판매까지 끌어올리지는 못했습니다."
4. Avoid product/material literalism such as "새로운 [제품군] 원단" when the English means a material was applied to a product category. Use "새 소재를 적용한 [제품군] 제품" or a more specific product phrase.
5. Avoid "것으로 현재 예상합니다." Use "것으로 봅니다", "예상합니다", or a cleaner sentence structure.
6. Avoid overusing "측면에서", "관점에서", "관련해서는", "포지셔닝", "레버", "탄력", "기저 추세", and "이니셔티브" unless they are the clearest terms in context.
7. Translate financial guidance naturally:
   - "Gross margin is expected to decline by approximately 90 basis points year-over-year" -> "올해 전체 매출총이익률은 전년보다 약 90bp 낮아질 것으로 봅니다."
   - "Inventory dollar growth in the low-to-mid single digits and units down slightly" -> "재고는 금액 기준으로 한 자릿수 초중반 증가하고, 수량 기준으로는 소폭 감소할 것으로 봅니다."
   - Growth ranges must preserve the source scale every time they recur:
     - `mid-to-high teens` -> `10%대 중반에서 후반`
     - `high single digits to low double digits` -> `한 자릿수 후반에서 10%대 초반`
     - `low double digits` -> `10%대 초반`
     - `mid-teens` -> `10%대 중반`
     - `high teens` -> `10%대 후반`
8. In earnings calls, keep common finance terms accurate:
   - `basis points` -> `bp`
   - `gross margin` -> `매출총이익률`
   - `SG&A` -> `판관비` or `SG&A` depending on local consistency
   - `full year` -> `올해 전체` or `연간`, whichever reads better in context
   - `clearance` -> `할인 판매`, `재고 소진 할인`, or `시즌 상품 할인 판매` depending on context
   - Enablement words such as `unlock`, `opportunity`, `tailwind`, `can`, and `could` -> use a positive enablement phrase such as `가능해질 개선 여지`, `열릴 추가 개선 가능성`, or `기회`. Do not turn them into "풀어야 할 과제" unless the source frames the item as a constraint or problem.
9. Keep analyst pleasantries natural and brief. Do not translate every English politeness formula literally.
10. Treat `말씀` as an honorific, not a generic substitute for "remarks", "comments", "say", "discuss", or "talk through". In earnings-call translations, default to non-honorific business prose such as "설명하겠습니다", "언급했듯이", "발언", "순서를 넘기겠습니다", "부탁드립니다", or remove the filler. Use `말씀` only when the Korean honorific relationship is intentional and natural.
11. Avoid repetitive `비교됩니다` for "compared with" or "versus" in financial tables. Use varied and direct Korean such as "전년 동기는 ...였습니다", "...보다 늘었습니다", "...을 웃돌았습니다", "...을 밑돌았습니다", or restructure the sentence.
12. Remove ceremonial closing filler when it sounds like a literal transcript artifact, such as "이상으로 준비한 말씀을 마치겠습니다." Use a compact transition or omit it if the next section already signals the flow.
13. When "hand it over to X for further remarks" is a call transition, do not write "X에게 넘겨 추가 말씀을 듣겠습니다." Prefer "X에게 순서를 넘기겠습니다" or "이제 X가 설명하겠습니다" depending on who is speaking.
14. Translate compliance and operations phrases by the real object of work. For example, a phrase about handling violations on a platform, store network, or sales channel should become "플랫폼 내 위반 사항 처리 소요 시간", "입점 판매자 위반 사항 처리 소요 시간", or another domain-correct phrase, not a literal noun pileup such as "매장 위반 처리 시간" or an offline-store reading such as "입점 매장의 위반 사항" when the source is platform governance.
15. For platform business terminology, translate the role rather than the surface word:
   - `merchant` -> usually `판매자`; use `가맹상인` only if the source describes a franchise relationship.
   - `first-party brand`, `first-party brand business`, `first-party brand model` -> usually `자체 브랜드`, `자체 브랜드 사업`, `자체 브랜드 모델`; use `직영` only when the source means directly operated stores or retail locations.
   - `platform governance` -> `플랫폼 거버넌스` or `플랫폼 관리` depending on the document's terminology; keep one term consistent.
   - `compliance` -> `컴플라이언스` or `준법` consistently. In investor-facing transcripts, `컴플라이언스` is often clearer when the company uses it as a management function.
16. For opaque initiative or program names, decide whether Korean readers need a Korean rendering. Do not leave every initiative in English by default. If the name has a transparent business meaning and no official Korean name is provided, use a concise Korean rendering and optionally keep the English in QA or at first occurrence. For example, a premium-produce initiative or a new-quality-supply initiative should not remain unexplained English if a Korean rendering would make the business meaning clearer.

## Currency And Large Numbers

For financial transcripts, convert currency and large-number units before finalizing:

1. `RMB` and `CNY` mean Chinese yuan/renminbi. In Korean financial prose, translate amounts as `위안`, not `원`.
2. Convert English `billion` to Korean `억` correctly: `1 billion` -> `10억`, `15 billion` -> `150억`, `100 billion` -> `1,000억`.
3. For a named program that embeds a large currency figure, include the unit at the first occurrence if Korean readers may otherwise assume won. Example: a hundred-billion-yuan supply-chain program -> `1,000억(위안) 규모의 공급망 프로그램` on first occurrence, then a shortened name only after the currency is established.
4. For ordinary financial amounts, keep the currency unit visible each time: `RMB 39.8 billion` -> `398억 위안`.
5. Add a currency conversion row to numeric QA for every non-USD large-number amount, especially RMB/CNY amounts in Chinese company calls.

## Notes And Explanations

1. Add explanatory notes only when a term would otherwise be unclear to a Korean reader.
2. Put the note at the first occurrence of the relevant term.
3. Do not repeat the same note at later occurrences.
4. If the user requests italic notes, italicize the entire note.
5. Keep notes concise but concrete. For example, for a proxy contest, explain that it is a shareholder vote fight over board seats and summarize the concrete event if relevant.
6. Do not use vague translations like "위임장 변경" for proxy-related events unless the source specifically says a proxy statement changed. Prefer "위임장 경쟁" or "주주 표 대결" depending on context.
7. If adding concrete background for governance events such as a proxy contest, verify the facts from a reliable source or the provided source material before writing the note.
8. Put the note immediately after the first Korean occurrence of the term.
9. Format the note as `<em>(...)</em>` when notes are italicized.
10. Do not repeat the note later.
11. Record the verification basis or source basis in QA.
12. Use short translator notes to prevent likely reader misinterpretation when two related source terms look like separate programs but external or source context shows they belong to the same strategic context. Verify the basis first, keep the note concise, and mark it visually, for example `<em>(같은 전략 맥락.)</em>`.
13. When a named program and a nearby investment plan share the same large monetary scale, explicitly decide whether the reader may confuse them. If the relationship is clear from source or verified context, the first note should clarify both currency scale and relationship/context, not only the currency unit. If the relationship is not clear, do not guess; record the uncertainty in QA.
14. Do not use notes to hide uncertainty. If the relationship is uncertain, state the uncertainty in QA or omit the note from the reader-facing output.
15. Do not let a note repeat the adjacent sentence. If the source sentence already states the relationship clearly, either translate it cleanly without a note or replace the adjacent explanation with a shorter note that adds only the missing reader context.
16. For every explanatory note, record a basis field in QA:
   - `source`: the source itself explains the relationship or term
   - `generic definition`: the note explains a standard business/finance term without adding event-specific claims
   - `externally verified`: the note adds event-specific background checked from a reliable source
   Do not add event-specific background under a generic-definition basis.

## HTML Deliverable Rules

When producing HTML for a translation:

1. Preserve the title and date at the top when provided or inferable.
   - For earnings calls, prefer a clean title like `<Company> <period> 컨퍼런스콜` or `<Company> <period> 실적 발표 컨퍼런스콜`, matching the document and user preference.
   - If the source says fiscal year or the call date makes the year ambiguous, preserve the fiscal-year relation explicitly: `2027 회계연도 1분기`, not `2027년 1분기`.
   - Show the call date in Korean numeric form such as `2026.05.27.` when that is the user's established preference.
   - Do not show raw helper labels or workflow titles such as `PDF filename date`, `Financial period`, `한국어 번역`, `원문 제목`, `evaluation`, `fixture`, `테스트`, or `번역 품질 평가용` in the reader-facing document unless requested.
2. Use semantic enough structure for copy-paste:
   - title block
   - date block
   - speaker block
   - paragraph block
   - explicit blank-line block
3. Preserve live web links with `<a href="...">...</a>`.
4. Preserve italics for product names, campaign names, document names, acronyms, or user-requested notes when appropriate.
5. Escape text before injecting it into HTML.
6. Do not depend on visual CSS alone for blank lines.
7. After generation, open or inspect the HTML and verify that copy-paste-sensitive spacing is represented by real elements.
8. Keep HTML generation deterministic:
   - Store translated paragraphs as plain structured records or clean chunk HTML.
   - Use a small assembly script for repeated wrappers such as title, date, speaker, paragraph, blank-line block, links, and italics.
   - Do not hand-maintain hundreds of repeated HTML wrapper lines if a script can avoid formatting drift.

For blog HTML, verify these structural invariants mechanically before delivery:

1. Every `.speaker` block is immediately followed by a `.para` block.
2. No `.blank` block appears between a speaker and that speaker's first paragraph.
3. Paragraph-to-paragraph and paragraph-to-speaker spacing uses a real `.blank` element.
4. `<em>`, `<a>`, `<body>`, and `<html>` tags are balanced and closed.
5. The file starts with a valid Korean HTML shell, including `<html lang="ko">` and `<meta charset="utf-8">`.
6. The file ends with closing `</body>` and `</html>` tags.

Build a formatting inventory before assembly:

1. product names
2. campaign and event names
3. SEC form names
4. finance acronyms and metrics such as `GAAP`, `non-GAAP`, `EPS`, `SG&A`, `SKU`, `APAC`, and `EMEA`
5. source URLs
6. explanatory notes

After assembly, compare the inventory against output `<em>` and `<a href>` occurrences. Record intentional exceptions in the QA note.

## Conceptual Review Gate

Run a conceptual review before mechanical QA for long transcripts, earnings calls, blog-ready translations, or any revision where the user has already corrected tone, speaker labels, notes, or financial wording.

1. Use `agents/korean_translation_reviewer.md` as the reviewer prompt. If an actual sub-agent tool is available, give that prompt to a separate reviewer agent. If no sub-agent is available, run the same prompt yourself as a separate review pass and record that it was self-run.
2. Give the reviewer the source outline, speaker map, any translation units with source text, the assembled output, and known user preferences.
3. The reviewer must find principle violations, not just bad strings. Each finding must explain:
   - reader-facing problem
   - underlying principle violated
   - source/output location
   - concrete revision direction
4. Record conceptual review findings as a ledger in reviewer format or a table with equivalent fields, even when the finding is accepted and fixed. A bare statement such as "no unresolved P1/P2 findings" is not enough unless the QA also shows what was inspected and what evidence supports the conclusion.
5. The reviewer must explicitly inspect:
   - whether the document looks like a polished Korean publication or an extraction artifact
   - whether speaker labels match communicative roles
   - whether interpreted speech is attributed to the person whose words are being interpreted
   - whether Korean register and honorifics imply unintended hierarchy
   - whether financial units and large numbers create the right scale in Korean
   - whether fiscal-year labels remain distinguishable from calendar dates
   - whether domain terms preserve the source business relationship
   - whether positive enablement language has been turned into constraint/problem language
   - whether notes prevent real misunderstanding and appear at the first relevant occurrence
   - whether repeated boilerplate should be preserved, compressed, or removed
6. Add a `Conceptual Review` section to `work/qa_report.md` with:
   - reviewer mode: sub-agent or self-run
   - findings accepted and fixed
   - findings rejected and why
   - evidence that no accepted P1/P2 finding remains unresolved
   - systemic rules added or adjusted because of the findings
7. Do not proceed to final delivery while any accepted conceptual finding remains unresolved.

## Mandatory QA Pass

Before final delivery, run a full-document QA pass:

1. Compare the final translation against the source or extracted source for omissions, duplicated blocks, speaker-order errors, and mistranslated numeric guidance.
2. Numeric QA must check the final assembled output, not only the draft chunks or a manually written summary. When source units have `unit` IDs and HTML paragraphs have `data-unit`, compare each numeric source unit against the matching final HTML paragraph.
3. Repeated numeric guidance is not covered by checking one representative occurrence. If a range such as `mid-to-high teens`, `high single digits`, bp guidance, EPS, margin, inventory growth, store count, or currency amount appears multiple times, record or script-check every occurrence and every final rendering.
4. Search the output for known bad patterns and revise every real issue:
   - `높은 수준`
   - `에게서 나옵니다`
   - `파급 효과`
   - literal product/material phrases such as `새로운 [제품군] 원단`
   - `것으로 현재`
   - `현재 예상`
   - `관문 요인`
   - `제품을 이동`
   - `기저 추세`
   - `순차적 개선`
   - `업데이트해 주실 수`
   - `부정적 영향`
   - `긍정적 영향`
   - `측면에서`
   - `관점에서`
   - `관련해서는`
   - `포지셔닝`
   - `이니셔티브`
   - `레버`
   - `탄력`
   - `도움이 됩니다`
   - `행운을 빕니다`
   - `말씀`
   - `비교됩니다`
   - `준비한 말씀`
   - `이상으로 준비한`
   - `추가 말씀`
   - `에게 넘겨`
   - `매장 위반 처리 시간`
   - `[Non-English content]`
   - `[비영어 발언]`
   - `[[em:`
   - visible speaker labels such as `<strong>통역</strong>` unless the speaker is genuinely an interpreter
   - raw extracted speaker labels such as `Speaker <number>` in reader-facing speaker labels
   - `RMB` in the final Korean body unless the user explicitly wants source currency codes retained
   - `100억 규모...`, `100억 지원...`, or similar phrases when the source means `RMB 100 billion` or another hundred-billion-yuan amount
5. Do not blindly replace every match. Read the surrounding context and keep a phrase only if it is genuinely the best Korean.
6. Verify transcript mechanics:
   - speaker labels appear only on speaker changes
   - speaker labels are bold in HTML
   - no blank line between speaker and first paragraph
   - paragraphs are readable and not one-sentence-per-line
   - copied blank lines survive because they are real elements
7. Verify rich formatting:
   - links remain live
   - italics remain where required
   - explanatory notes are in the right location
   - repeated notes have not been duplicated
8. Verify title/date/file naming:
   - requested title is exact
   - requested date is exact
   - fiscal year and calendar date are not collapsed into the wrong period label
   - output filename reflects the document clearly
9. Re-run the mechanical search after revisions.
10. Run task-local evaluators discovered during intake. If an evaluator fails, either fix the output and rerun it or record a concrete, defensible reason why that evaluator is not applicable. Do not report "mechanical QA pass" while a relevant local evaluator is failing or has not been run.

For long transcripts, create `work/qa_report.md` or an equivalent QA note containing:

1. source unit count and translated unit/chunk count
2. speaker count or speaker-transition sanity check
3. title/date check
4. link count and target check
5. italics/emphasis check
6. explanatory note count and first-occurrence placement check
7. bad-pattern search command and remaining matches with disposition
8. numeric guidance unit checks, especially revenue, margin, EPS, inventory, tariff, store count, and percentage guidance
9. any sections that were manually re-read after mechanical checks

For earnings calls, create a numeric QA table for all guidance and financial metric paragraphs:

1. source unit
2. source number and unit
3. Korean rendering
4. pass/fail
5. correction made, if any

Include revenue, margin, bp, EPS, inventory, store count, tariff, markdown, growth-rate ranges, and year/quarter references. Do not rely only on a small spot check when the document contains formal guidance.
When the source and final output have unit IDs, each table row should identify the final `data-unit` paragraph checked. A QA row that says a range was preserved is not acceptable if the exact unit's final paragraph was not read.

Use mechanical checks like these when applicable:

```bash
rg -n "높은 수준|에게서 나옵니다|파급 효과|새로운 .{1,20}원단|것으로 현재|현재 예상|관문 요인|제품을 이동|기저 추세|순차적 개선|업데이트해 주실 수|부정적 영향|긍정적 영향|측면에서|관점에서|관련해서는|포지셔닝|이니셔티브|레버|탄력|도움이 됩니다|행운을 빕니다|위임장 변경|말씀|비교됩니다|준비한 말씀|이상으로 준비한|추가 말씀|에게 넘겨|매장 위반 처리 시간|\\[Non-English content\\]|\\[비영어 발언\\]|\\[\\[em:|RMB|100억(\\(위안\\))?\\s*(규모|지원|투자|프로그램|계획|펀드)" outputs/*.html work/translation_chunks
```

For HTML deliverables, also run the bundled QA helper when possible:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/translation-quality/scripts/qa_html_translation.py" \
  --output outputs/<clear_document_name>_ko.html \
  --chunks work/translation_chunks \
  --source-units work/source_units.tsv \
  --expect-title "<exact Korean title>" \
  --expect-date "YYYY.MM.DD." \
  --strict-style
```

If a style match is intentionally acceptable, rerun without `--strict-style` only after recording the context and disposition in `work/qa_report.md`. Hard structural failures, visible non-English markers, raw `[[em:` markers, and incorrect visible interpreter labels must be fixed rather than waived.

Use `--allow-visible-interpreter-label` only when the visible speaker really is an interpreter and the QA report records why the answer could not be attributed to an original speaker. Do not use it for anonymous interpreted executive or analyst answers.

Remaining matches are not automatically failures, but every match must be read in context and either revised or explicitly marked acceptable in the QA note.

Before the final response, run a final file sanity check and summarize it in QA:

1. output path exists
2. line count is plausible for the source length
3. exact title and exact date are present
4. `<html lang="ko">` and `<meta charset="utf-8">` are present for HTML deliverables
5. `<em>` tag count is balanced
6. `<a href>` tags are present for source URLs and point to the right target
7. speaker, paragraph, and blank-line block counts are plausible
8. every speaker block is followed by a paragraph block
9. closing `</body>` and `</html>` tags are present
10. no visible `[Non-English content]`, `[비영어 발언]`, raw `[[em:` markers, or anonymous interpreter speaker labels remain in the reader-facing output
11. no raw source helper metadata appears in the reader-facing title block
12. applicable task-local evaluator scripts have been run and their results are recorded

## Earnings Call Specific Checklist

For earnings-call transcripts, perform these additional checks:

1. Operator lines should sound like a call operator, not like a literal written document:
   - Prefer "다음은 X입니다. 부탁드립니다."
   - Prefer "마지막은 X입니다. 부탁드립니다."
   - Avoid "다음 질문은 X에게서 나옵니다."
2. Prepared remarks and Q&A should not collapse separate speakers into one paragraph. Source extraction often joins lines like `Executive A: ... Executive B: ...`; split these manually.
3. Guidance language should be natural and compact:
   - "we now expect" does not need to become "현재 예상합니다" every time.
   - Use "봅니다", "예상합니다", "가이던스에는 ... 반영했습니다", or sentence restructuring according to context.
4. Product/campaign names should be preserved consistently and italicized in HTML when useful.
5. Analyst pleasantries should be readable Korean, not literal ceremony.
6. Proxy contests, shareholder actions, board-seat fights, or other governance events should be explained at first occurrence if a Korean reader may not understand the context.
7. For Chinese-company calls or any call with interpretation, verify:
   - non-English source markers are not visible when interpretation exists
   - interpreted answers are attributed to the original executive or analyst, not to `통역`
   - `Operator` and company host/moderator labels are distinct
   - RMB/CNY and billion-to-억 conversions are correct
   - program names with large monetary figures are introduced once with the currency unit if needed
8. Re-read all passages involving:
   - markdowns and clearance
   - full-price sales
   - inventory dollars versus units
   - tariffs and offsets
   - gross margin and operating margin
   - store openings and optimizations
   - product launch performance and halo effects
   - enablement, upside, calendar or process compression, sourcing flexibility, go-to-market timing, and whether they are opportunities, constraints, or tradeoffs in the source
   - supply-chain investment programs and their relationship to adjacent initiatives
   - fiscal-year titles when the period year differs from the call date
   - platform terminology such as merchants, sellers, first-party brand models, marketplace, direct retail, franchise, and self-operated stores

## Final Response

When the translation or revision is complete:

1. State what was delivered and where.
2. Mention the concrete QA checks performed.
3. If a browser file is already open, tell the user to refresh the existing tab.
4. Do not overclaim perfection. If any verification was not possible, say so directly.
