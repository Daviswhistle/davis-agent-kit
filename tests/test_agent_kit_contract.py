from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def numbered_items(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError as exc:
        raise AssertionError(f"Missing heading: {heading}") from exc

    items: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        stripped = line.strip()
        if stripped and stripped[0].isdigit() and ". " in stripped:
            items.append(stripped.split(". ", 1)[1])
    return items


class AgentKitContractTests(unittest.TestCase):
    def test_root_layers_use_philosophy_principles_guidelines(self) -> None:
        self.assertTrue((ROOT / "PHILOSOPHY.md").is_file())
        self.assertTrue((ROOT / "PRINCIPLES.md").is_file())
        self.assertTrue((ROOT / "guidelines").is_dir())
        self.assertFalse((ROOT / "STRATEGY.md").exists())
        self.assertFalse((ROOT / "principles").exists())

        checked_paths = [
            path
            for path in ROOT.rglob("*.md")
            if ".git" not in path.parts
            and "scratch" not in path.parts
            and "private" not in path.parts
        ]
        stale_hits: dict[str, list[str]] = {}
        for path in checked_paths:
            text = path.read_text(encoding="utf-8")
            matches = [
                token
                for token in ("STRATEGY.md", "principles/")
                if token in text
            ]
            if matches:
                stale_hits[str(path.relative_to(ROOT))] = matches

        self.assertEqual(stale_hits, {})

    def test_philosophy_stays_high_level(self) -> None:
        expected = [
            "모든 것은 더 이상 단순화할 수 없을 만큼 단순해야 한다.",
            "단순함은 정보 삭제가 아니라 본질만 남기는 압축이다.",
            "좋은 구조는 더 적은 기준으로 더 많은 상황을 설명한다.",
        ]

        self.assertEqual(numbered_items(read("PHILOSOPHY.md"), "## 핵심 명제"), expected)
        self.assertEqual(numbered_items(read("AGENTS.md"), "## 작동 철학"), [
            "필요한 것을 잃지 않는 가장 단순한 형태를 찾는다.",
            expected[1],
            expected[2],
        ])
        self.assertEqual(numbered_items(read("GEMINI.md"), "## 작동 철학"), [
            "필요한 것을 잃지 않는 가장 단순한 형태를 찾는다.",
            expected[1],
            expected[2],
        ])

        philosophy_surface = "\n".join(
            numbered_items(read("PHILOSOPHY.md"), "## 핵심 명제")
        )
        operational_phrases = [
            "구체 사례",
            "실제 동작",
            "실행 진입점",
            "검증 경로",
            "역할을 판단",
            "확인한다",
        ]
        hits = [phrase for phrase in operational_phrases if phrase in philosophy_surface]
        self.assertEqual(hits, [])

    def test_principles_and_final_review_preserve_simplification_guardrails(self) -> None:
        self.assertEqual(
            numbered_items(read("PRINCIPLES.md"), "## 핵심 원칙"),
            [
                "불필요한 것은 제거한다.",
                "필요한 것은 통합한다.",
                "복잡하지만 필요한 것은 숨기거나 단계화한다.",
                "남기는 것은 이름, 위치, 형식이 역할을 드러내게 한다.",
                "제거하거나 통합한 뒤에도 정확성, 안전성, 맥락, 신뢰가 유지되는지 검증한다.",
            ],
        )

        checklist = read("checklists/final-review.md")
        required_questions = [
            "초보자가 이해하는가",
            "전문가가 봐도 틀리지 않는가",
            "예외 상황에서도 무너지지 않는가",
            "핵심 목적이 더 빨리 달성되는가",
            "설명은 짧아졌지만 판단은 더 쉬워졌는가",
        ]
        missing = [question for question in required_questions if question not in checklist]
        self.assertEqual(missing, [])

    def test_software_engineering_skill_replaces_coding_workflow(self) -> None:
        self.assertTrue((ROOT / "skills" / "software-engineering" / "SKILL.md").is_file())
        self.assertFalse((ROOT / "skills" / "coding-workflow").exists())

        skill = read("skills/software-engineering/SKILL.md")
        metadata = read("skills/software-engineering/agents/openai.yaml")
        agents = read("AGENTS.md")
        gemini = read("GEMINI.md")
        skills_readme = read("skills/README.md")

        self.assertIn("name: software-engineering", skill)
        self.assertIn("display_name: \"Software Engineering\"", metadata)
        self.assertIn("$software-engineering", metadata)
        self.assertIn("`software-engineering` 스킬", agents)
        self.assertIn("`software-engineering` 기준", gemini)
        self.assertIn("`software-engineering`", skills_readme)
        self.assertNotIn("coding-workflow", agents)
        self.assertNotIn("coding-workflow", gemini)
        self.assertNotIn("coding-workflow", skills_readme)


if __name__ == "__main__":
    unittest.main()
