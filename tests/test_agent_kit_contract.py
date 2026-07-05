from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


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

    def test_software_engineering_skill_replaces_coding_workflow(self) -> None:
        self.assertTrue((ROOT / "skills" / "software-engineering" / "SKILL.md").is_file())
        self.assertFalse((ROOT / "skills" / "coding-workflow").exists())

        skill = read("skills/software-engineering/SKILL.md")
        metadata = read("skills/software-engineering/agents/openai.yaml")
        agents = read("AGENTS.md")
        skills_readme = read("skills/README.md")

        self.assertIn("name: software-engineering", skill)
        self.assertIn("display_name: \"Software Engineering\"", metadata)
        self.assertIn("$software-engineering", metadata)
        self.assertIn("`software-engineering` 스킬", agents)
        self.assertIn("`software-engineering`", skills_readme)
        self.assertNotIn("coding-workflow", agents)
        self.assertNotIn("coding-workflow", skills_readme)


if __name__ == "__main__":
    unittest.main()
