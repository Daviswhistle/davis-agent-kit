from __future__ import annotations

from pathlib import Path
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (SKILL_ROOT / path).read_text(encoding="utf-8")


class PublishableHtmlArticleContractTests(unittest.TestCase):
    def test_profile_and_reader_first_examples_are_bundled_and_linked(self) -> None:
        skill = read("SKILL.md")
        profile_path = "references/publishable-html-article.md"
        examples_path = "references/reader-first-information-design-examples.md"

        self.assertTrue((SKILL_ROOT / profile_path).is_file())
        self.assertTrue((SKILL_ROOT / examples_path).is_file())
        self.assertIn(profile_path, skill)
        self.assertIn(examples_path, skill)
        self.assertIn("publish-ready HTML/CSS article", skill)
        self.assertIn("짧게 압축한 화면 문구", skill)
        self.assertIn("실제 산출물을 먼저 수정해 보여라", skill)

    def test_profile_covers_repeated_failure_modes(self) -> None:
        profile = read("references/publishable-html-article.md")

        for concept in (
            "주장과 제목",
            "한국어 독해 비용",
            "한국어 원문",
            "대중 대상 수치 표현",
            "원자료의 의미 범위",
            "독자의 조립 비용",
            "비교 대상·기준점·방향·결과",
            "관계에 맞는 형식",
            "가림 테스트",
            "콜드 리드",
            "실제 게시 환경에서 렌더링하라",
            "피드백 이후 전수 회귀 검수",
            "이상",
            "초과",
            "실제 아티클 컨테이너 폭",
            "최종 HTML에서 미리보기를 다시 만든다",
            "수정된 산출물을 먼저 제시",
        ):
            self.assertIn(concept, profile)

    def test_rubric_and_forward_matrix_cover_reader_assembly_cost(self) -> None:
        rubric = read("references/review-rubric.md")
        matrix = read("references/test-matrix.md")

        self.assertIn("## 게시형 HTML 아티클 추가 검수", rubric)
        self.assertIn("본문 한국어가 원자료의 문장 구조를 옮기지 않고", rubric)
        self.assertIn("한국어 원문을 화면 문구로 압축", rubric)
        self.assertIn("작은 보조 문구", rubric)
        self.assertIn("배지·버튼·탭처럼 보이는 모양", rubric)
        self.assertIn("가림 테스트나 콜드 리드", rubric)
        self.assertIn("실제 아티클 컨테이너", rubric)
        self.assertIn("최종 HTML, CMS용 코드, 미리보기", rubric)
        self.assertIn("실제 수정 결과", rubric)
        self.assertIn("`해당 없음`으로 기록하고 점수와 분모에서 제외", rubric)

        for case_type in (
            "분석 글 제목",
            "한국어 자료 재서술",
            "한국어 화면 문구 압축",
            "비교축·행위자",
            "수치 카드",
            "시각적 위계",
            "관계 시각화",
            "게시형 HTML",
            "패턴 수정 회귀",
            "수정 결과 제시",
        ):
            self.assertIn(f"| {case_type} |", matrix)

    def test_examples_explain_principles_not_phrase_bans(self) -> None:
        examples = read("references/reader-first-information-design-examples.md")

        for concept in (
            "한국어 원문도 압축 과정에서 망가질 수 있다",
            "같은 종류의 대상끼리 비교한다",
            "결론이 숫자보다 먼저다",
            "관계를 독자가 조립하게 하지 않는다",
            "수정 요청에는 결과부터 보여 준다",
        ):
            self.assertIn(concept, examples)

        self.assertIn("특정 문구를 금칙어로 외우지 않는다", examples)


if __name__ == "__main__":
    unittest.main()
