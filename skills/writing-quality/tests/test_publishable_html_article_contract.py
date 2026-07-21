from __future__ import annotations

from pathlib import Path
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (SKILL_ROOT / path).read_text(encoding="utf-8")


class PublishableHtmlArticleContractTests(unittest.TestCase):
    def test_profile_is_bundled_and_linked(self) -> None:
        skill = read("SKILL.md")
        profile_path = "references/publishable-html-article.md"

        self.assertTrue((SKILL_ROOT / profile_path).is_file())
        self.assertIn(profile_path, skill)
        self.assertIn("publish-ready HTML/CSS article", skill)

    def test_profile_covers_repeated_failure_modes(self) -> None:
        profile = read("references/publishable-html-article.md")

        for concept in (
            "주장과 제목",
            "한국어 독해 비용",
            "대중 대상 수치 표현",
            "원자료의 의미 범위",
            "시각적 의미",
            "실제 게시 환경에서 렌더링하라",
            "피드백 이후 전수 회귀 검수",
            "이상",
            "초과",
            "실제 아티클 컨테이너 폭",
            "최종 HTML에서 미리보기를 다시 만든다",
        ):
            self.assertIn(concept, profile)

    def test_rubric_and_forward_matrix_cover_publishable_articles(self) -> None:
        rubric = read("references/review-rubric.md")
        matrix = read("references/test-matrix.md")

        self.assertIn("## 게시형 HTML 아티클 추가 검수", rubric)
        self.assertIn("실제 아티클 컨테이너", rubric)
        self.assertIn("최종 HTML, CMS용 코드, 미리보기", rubric)

        for case_type in (
            "분석 글 제목",
            "한국어 자료 재서술",
            "수치 카드",
            "게시형 HTML",
            "패턴 수정 회귀",
        ):
            self.assertIn(f"| {case_type} |", matrix)


if __name__ == "__main__":
    unittest.main()
