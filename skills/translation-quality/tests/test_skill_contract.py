from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
REVIEWER = ROOT / "agents" / "korean_translation_reviewer.md"
BENCHMARK = ROOT / "references" / "quality_benchmark.md"


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
            "2027 회계연도 1분기",
            "Domain terms must preserve business relationships",
            "Before translating, scan the current task directory for explicit local evaluation files",
            "Do not report \"mechanical QA pass\" while a relevant local evaluator is failing",
            "positive enablement phrase",
            "Record conceptual review findings as a ledger",
            "For every explanatory note, record a basis field in QA",
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
            "State the task objective and completion conditions in one sentence",
            "Trace the source-to-output flow before editing",
            "Identify affected resources before changing the skill itself",
            "Separate verification from approval or publication",
            "A passing helper alone is not enough",
            "Check naming and visible labels as part of quality",
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
        ]
        missing = [phrase for phrase in required_phrases if phrase not in text]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
