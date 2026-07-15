from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class AgentKitContractTests(unittest.TestCase):
    def test_agents_is_the_single_normative_root(self) -> None:
        self.assertTrue((ROOT / "AGENTS.md").is_file())
        self.assertFalse((ROOT / "PHILOSOPHY.md").exists())
        self.assertFalse((ROOT / "PRINCIPLES.md").exists())
        self.assertTrue((ROOT / "guidelines").is_dir())
        self.assertFalse((ROOT / "STRATEGY.md").exists())
        self.assertFalse((ROOT / "principles").exists())

        agents = read("AGENTS.md")
        for heading in (
            "## 역할과 우선순위",
            "## 작동 철학",
            "## 핵심 원칙",
            "## 기본 동작",
            "## 스킬과 리소스 라우팅",
        ):
            self.assertIn(heading, agents)

        for statement in (
            "필요한 것을 잃지 않는 가장 단순한 형태를 찾는다.",
            "불필요한 것은 제거한다.",
            "필요한 것은 통합한다.",
            "확인하지 않은 사실을 단정하지 않는다.",
        ):
            self.assertIn(statement, agents)

        checked_paths = [
            path
            for path in ROOT.rglob("*.md")
            if ".git" not in path.parts
            and "scratch" not in path.parts
            and "private" not in path.parts
            and "user-model" not in path.parts
        ]
        stale_hits: dict[str, list[str]] = {}
        for path in checked_paths:
            text = path.read_text(encoding="utf-8")
            matches = [
                token
                for token in (
                    "PHILOSOPHY.md",
                    "PRINCIPLES.md",
                    "STRATEGY.md",
                    "principles/",
                )
                if token in text
            ]
            if matches:
                stale_hits[str(path.relative_to(ROOT))] = matches

        self.assertEqual(stale_hits, {})

    def test_software_engineering_skill_replaces_coding_workflow(self) -> None:
        self.assertTrue((ROOT / "skills" / "software-engineering" / "SKILL.md").is_file())
        self.assertFalse((ROOT / "skills" / "coding-workflow").exists())

        skill = read("skills/software-engineering/SKILL.md")
        metadata = read("skills/software-engineering/agents/openai.yaml")
        agents = read("AGENTS.md")
        skills_readme = read("skills/README.md")

        self.assertIn("name: software-engineering", skill)
        self.assertIn('display_name: "Software Engineering"', metadata)
        self.assertIn("$software-engineering", metadata)
        self.assertIn("`software-engineering` 스킬", agents)
        self.assertIn("`software-engineering`", skills_readme)
        self.assertNotIn("coding-workflow", agents)
        self.assertNotIn("coding-workflow", skills_readme)

    def test_software_engineering_references_are_bundled(self) -> None:
        skill_root = ROOT / "skills" / "software-engineering"
        reference_paths = [
            "references/cra-loop.md",
            "references/tca-loop.md",
            "references/naming-docs-consistency.md",
        ]

        skill = read("skills/software-engineering/SKILL.md")
        for rel_path in reference_paths:
            self.assertTrue((skill_root / rel_path).is_file())
            self.assertIn(rel_path, skill)

        reference_text = "\n".join(
            (skill_root / rel_path).read_text(encoding="utf-8")
            for rel_path in reference_paths
        )
        software_engineering_text = skill + "\n" + reference_text

        self.assertIn('-c model="gpt-5.6-sol"', software_engineering_text)
        self.assertNotIn("review_model=", software_engineering_text)
        self.assertIn("codex review --commit", reference_text)
        self.assertIn("Task-Commit-Approve", reference_text)
        self.assertIn("Names are maintenance interfaces", reference_text)

    def test_writing_quality_is_integrated_as_a_general_writing_skill(self) -> None:
        skill_root = ROOT / "skills" / "writing-quality"
        self.assertTrue((skill_root / "SKILL.md").is_file())
        self.assertTrue((skill_root / "agents" / "openai.yaml").is_file())

        skill = read("skills/writing-quality/SKILL.md")
        metadata = read("skills/writing-quality/agents/openai.yaml")
        agents = read("AGENTS.md")
        root_readme = read("README.md")
        skills_readme = read("skills/README.md")
        writing_guideline = read("guidelines/writing-style.md")

        self.assertIn("name: writing-quality", skill)
        self.assertIn("display_name: Writing Quality", metadata)
        self.assertIn("$writing-quality", metadata)
        self.assertIn("`writing-quality` 스킬", agents)
        self.assertIn("skills/writing-quality", root_readme)
        self.assertIn("`writing-quality`", skills_readme)
        self.assertIn("writing-quality", writing_guideline)

        references = [
            "references/genre-playbooks.md",
            "references/review-rubric.md",
            "references/recipient-centered-persuasion.md",
            "references/test-matrix.md",
        ]
        for rel_path in references:
            self.assertTrue((skill_root / rel_path).is_file())
            self.assertIn(rel_path, skill)

        playbooks = read("skills/writing-quality/references/genre-playbooks.md")
        core_and_playbooks = skill + playbooks
        self.assertNotIn("네이버웹툰", core_and_playbooks)
        for inherited_metaphor in ("시간선", "완충재", "유사 구독"):
            self.assertNotIn(inherited_metaphor, core_and_playbooks)


if __name__ == "__main__":
    unittest.main()
