from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
SKILL = ROOT / "SKILL.md"
REVIEWER = ROOT / "agents" / "korean_translation_reviewer.md"
REPORT_REVIEWER = ROOT / "agents" / "korean_report_reviewer.md"
BENCHMARK = ROOT / "references" / "quality_benchmark.md"
REFERENCE_SUITE = REPO_ROOT / "examples" / "translation" / "good" / "reference-quality-suite.md"


class SkillContractTests(unittest.TestCase):
    def test_skill_contains_reader_contract_and_conceptual_review_gate(self) -> None:
        text = SKILL.read_text(encoding="utf-8")

        required_phrases = [
            "## Reader Contract",
            "## Conceptual Review Gate",
            "agents/korean_translation_reviewer.md",
            "underlying principle",
            "Korean honorifics imply hierarchy",
            "Financial units shape the reader's economic intuition",
            "If the user points out a phrase, infer the underlying class of failure",
            "Mechanical QA guards objective defects",
            "apparent source/extraction/transcript error",
            "ordinary Korean words as forbidden",
            "Visual emphasis is semantic",
            "ordinary finance acronyms such as `GAAP`, `SG&A`, `EPS`, `SKU`, `APAC`, and `EMEA` usually should remain plain body text",
            "Separate translator notes from source emphasis",
            "2027 회계연도 1분기",
            "Domain terms must preserve business relationships",
            "Before translating, scan the current task directory for explicit local evaluation files",
            "Do not report \"mechanical QA pass\" while a relevant local evaluator is failing",
            "positive enablement phrase",
            "Record conceptual review findings as a ledger",
            "For every explanatory note, record a basis field in QA",
            "`source correction`",
            "Do not let a note repeat the adjacent sentence",
            "## Portable Quality Contract",
            "fresh git install",
            "references/quality_benchmark.md",
            "${CODEX_HOME:-$HOME/.codex}/skills/translation-quality",
            "python3 \"${CODEX_HOME:-$HOME/.codex}/skills/translation-quality/scripts/qa_html_translation.py\"",
            "Do not fake chunking by writing one giant translation dictionary",
            "Growth ranges must preserve the source scale every time they recur",
            "`mid-to-high teens` -> `10%대 중반에서 후반`",
            "compare each numeric source unit against the matching final HTML paragraph",
            "Repeated numeric guidance is not covered by checking one representative occurrence",
            "플랫폼 내 위반 사항 처리 소요 시간",
            "For opaque initiative or program names",
            "When a named program and a nearby investment plan share the same large monetary scale",
            "## Work Discipline",
            "## Review Fanout For Long Documents",
            "## Equivalence Evidence Gate",
            "agents/korean_report_reviewer.md",
            "reviewer mode for each pass",
            "scripts/evaluate_report_equivalence.py",
            "--profile report",
            "reference-quality-suite.md",
            "Metrics prove shape and artifact cleanup",
            "applicable exemplar axes",
            "State the task objective and completion conditions in one sentence",
            "Trace the source-to-output flow before editing",
            "Identify affected resources before changing the skill itself",
            "Separate verification from approval or publication",
            "A passing helper alone is not enough",
            "Check naming and visible labels as part of quality",
            "table alignment classes",
        ]
        missing = [phrase for phrase in required_phrases if phrase not in text]
        self.assertEqual(missing, [])

    def test_conceptual_reviewer_prompt_targets_purpose_not_blacklist(self) -> None:
        text = REVIEWER.read_text(encoding="utf-8")

        required_phrases = [
            "not to search for forbidden strings",
            "reader-facing purpose",
            "Communicative role",
            "Speaker truth",
            "Register and hierarchy",
            "Financial scale",
            "Visual emphasis semantics",
            "Source correction transparency",
            "Systemic learning",
            "Evidence discipline",
            "Domain relationship",
            "fiscal-year wording",
            "Verification evidence",
            "Polarity and modality",
            "Enablement language",
            "Conceptual QA evidence",
            "Do not flag a word only because it appears in a blacklist",
            "inspect every material occurrence in the final output",
            "matching final paragraph",
            "`mid-to-high teens` is `10%대 중반에서 후반`",
            "Source-to-output flow",
            "Readiness evidence",
            "Workflow coverage",
            "Naming and label fit",
        ]
        missing = [phrase for phrase in required_phrases if phrase not in text]
        self.assertEqual(missing, [])

    def test_quality_benchmark_is_self_contained(self) -> None:
        text = BENCHMARK.read_text(encoding="utf-8")

        required_phrases = [
            "replaces any hidden assumption",
            "Acceptance Bar",
            "Bad-To-Target Examples",
            "Interpreted Speech",
            "Currency And Program Scale",
            "1,000억(위안) 규모의 공급망 프로그램",
            "150억 위안",
            "Honorific And Handoff",
            "2027 회계연도 1분기",
            "positive enablement language",
            "Conceptual Review Ledger",
            "Notes do not duplicate adjacent prose",
            "Reader-visible source corrections are transparent",
            "Numeric QA checks every material occurrence in the final assembled output",
            "Long-document chunking is real",
            "Numeric Range QA",
            "mid-to-high teens",
            "10%대 중반에서 후반",
            "Platform Governance Terms",
            "플랫폼 내 위반 사항 처리 소요 시간",
            "task objective and completion conditions are explicit",
            "source-to-output flow is inspectable",
            "Skill updates are consistent",
            "Verification Ledger",
            "Do not collapse verification, approval, and publication readiness",
            "Annual Report Structure",
            "Review Fanout",
            "Equivalence Evidence",
            "Reference-quality claims require reference evidence",
            "Reference quality is multi-axis",
            "Lexical checks are not a blacklist",
            "Visual emphasis has meaning",
            "Lululemon represents transcript packaging",
            "PDD Holdings represents interpreted-call",
            "YesAsia represents long formal-report publication",
            "evaluate_report_equivalence.py --require-core-counts-match",
            "report QA profile",
            "table alignment classes",
        ]
        missing = [phrase for phrase in required_phrases if phrase not in text]
        self.assertEqual(missing, [])

    def test_reference_quality_suite_records_three_reference_axes(self) -> None:
        text = REFERENCE_SUITE.read_text(encoding="utf-8")

        required_phrases = [
            "Mechanical metrics are only one gate",
            "Lululemon earnings-call transcript",
            "Blog-ready transcript flow",
            "PDD Holdings earnings-call transcript",
            "Interpreted-call fidelity",
            "YesAsia annual report",
            "Long formal-report publication",
            "Observed result: `PASS`",
            "do not by themselves prove natural Korean",
            "candidate must not inherit them silently",
            "Known stricter-rule caveat",
            "distinguish translator notes from source terms",
        ]
        missing = [phrase for phrase in required_phrases if phrase not in text]
        self.assertEqual(missing, [])

    def test_report_reviewer_prompt_targets_formal_report_risks(self) -> None:
        text = REPORT_REVIEWER.read_text(encoding="utf-8")

        required_phrases = [
            "annual reports",
            "financial statements",
            "Table fidelity",
            "Legal and governance labels",
            "Bilingual naming",
            "Extraction cleanup",
            "Publication usability",
            "page and section map",
            "table inventory",
            "table alignment",
            "Do not flag a formal legal/reporting phrase",
        ]
        missing = [phrase for phrase in required_phrases if phrase not in text]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
