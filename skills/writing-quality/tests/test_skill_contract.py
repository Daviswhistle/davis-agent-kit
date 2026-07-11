from __future__ import annotations

from pathlib import Path
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (SKILL_ROOT / path).read_text(encoding="utf-8")


class WritingQualitySkillContractTests(unittest.TestCase):
    def test_skill_metadata_and_interface(self) -> None:
        skill = read("SKILL.md")
        metadata = read("agents/openai.yaml")

        frontmatter = skill.split("---", 2)[1]
        keys = {
            line.split(":", 1)[0].strip()
            for line in frontmatter.splitlines()
            if ":" in line
        }
        self.assertEqual(keys, {"name", "description"})
        self.assertIn("name: writing-quality", frontmatter)
        self.assertIn("display_name:", metadata)
        self.assertIn("Writing Quality", metadata)
        self.assertIn("$writing-quality", metadata)

    def test_references_are_bundled_and_linked(self) -> None:
        skill = read("SKILL.md")
        references = [
            "references/genre-playbooks.md",
            "references/review-rubric.md",
            "references/test-matrix.md",
        ]
        for rel_path in references:
            self.assertTrue((SKILL_ROOT / rel_path).is_file())
            self.assertIn(rel_path, skill)

    def test_playbooks_cover_distinct_writing_jobs(self) -> None:
        skill = read("SKILL.md")
        playbooks = read("references/genre-playbooks.md")
        for heading in (
            "## 메커니즘·비즈니스 모델 분석",
            "## 기업·투자 리서치",
            "## 시장·정책 인과 분석",
            "## 기술 설명",
            "## 논증·비평",
            "## 업무 메시지",
            "## 프롬프트·지침 문서",
            "## 에세이·문학적 산문",
            "## 기존 글 편집",
        ):
            self.assertIn(heading, playbooks)

        core_and_playbooks = skill + playbooks
        self.assertNotIn("네이버웹툰", core_and_playbooks)
        for inherited_metaphor in ("시간선", "완충재", "유사 구독"):
            self.assertNotIn(inherited_metaphor, core_and_playbooks)

        self.assertIn("실화·자전적 글에서는", skill)
        self.assertIn("약속의 내용이 주어지지 않았으면", playbooks)
        self.assertIn("실화·자전적 산문에서는", playbooks)

    def test_forward_matrix_covers_generality_and_overfitting(self) -> None:
        matrix = read("references/test-matrix.md")
        for case_type in (
            "개념 설명",
            "기술 분석",
            "시장 인과",
            "기업·투자",
            "논증",
            "메커니즘",
            "업무 메시지",
            "프롬프트",
            "편집",
            "에세이",
        ):
            self.assertIn(f"| {case_type} |", matrix)

        self.assertIn("과최적화", read("references/review-rubric.md"))
        self.assertIn("과제와 무관하게 반복되지 않는다", matrix)


if __name__ == "__main__":
    unittest.main()
