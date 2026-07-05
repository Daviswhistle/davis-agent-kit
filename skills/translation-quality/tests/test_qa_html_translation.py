from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qa_html_translation.py"


GOOD_HTML = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Example Company A 2026년 1분기 컨퍼런스콜</title>
</head>
<body>
<header><h1>Example Company A 2026년 1분기 컨퍼런스콜</h1><div class="date">2026.05.27.</div></header>
<div class="speaker"><strong>사회자</strong></div>
<p class="para">다음은 Analyst A입니다. 부탁드립니다.</p>
<div class="blank"><br></div>
<div class="speaker" data-speaker="Executive B" data-source-speaker="Interpreter 1"><strong>Executive B</strong></div>
<p class="para">초기 현금 투입액은 150억 위안이며, 향후 3년간 1,000억 위안을 투자할 계획입니다. <em>(같은 전략 맥락의 투자입니다.)</em></p>
</body>
</html>
"""


class QaHtmlTranslationTests(unittest.TestCase):
    def run_qa(self, html_text: str, *extra_args: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "out.html"
            output.write_text(html_text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(output), *extra_args],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def test_clean_html_passes_strict_style(self) -> None:
        result = self.run_qa(
            GOOD_HTML,
            "--expect-title",
            "Example Company A 2026년 1분기 컨퍼런스콜",
            "--expect-date",
            "2026.05.27.",
            "--strict-style",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_visible_interpreter_and_non_english_marker_fail_hard(self) -> None:
        bad_html = GOOD_HTML.replace("<strong>Executive B</strong>", "<strong>통역</strong>").replace(
            "초기 현금",
            "[Non-English content] 초기 현금",
        )
        result = self.run_qa(bad_html)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("visible interpreter speaker label", result.stdout)
        self.assertIn("visible non-English source marker", result.stdout)

    def test_blank_between_speaker_and_paragraph_fails(self) -> None:
        bad_html = GOOD_HTML.replace(
            '<div class="speaker"><strong>사회자</strong></div>\n<p class="para">',
            '<div class="speaker"><strong>사회자</strong></div>\n<div class="blank"><br></div>\n<p class="para">',
        )
        result = self.run_qa(bad_html)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("speaker block is followed by .blank, not .para", result.stdout)

    def test_context_sensitive_words_do_not_fail_without_context(self) -> None:
        html = GOOD_HTML.replace("부탁드립니다.", "말씀해 주십시오.")
        result = self.run_qa(html, "--strict-style")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_strict_style_fails_exact_literal_template(self) -> None:
        bad_html = GOOD_HTML.replace("부탁드립니다.", "이상으로 준비한 말씀을 마치겠습니다.")
        loose = self.run_qa(bad_html)
        strict = self.run_qa(bad_html, "--strict-style")

        self.assertEqual(loose.returncode, 0, loose.stdout + loose.stderr)
        self.assertIn("PASS WITH STYLE REVIEW", loose.stdout)
        self.assertNotEqual(strict.returncode, 0)
        self.assertIn("literal prepared-remarks closing", strict.stdout)

    def test_expected_title_and_date_are_checked(self) -> None:
        result = self.run_qa(GOOD_HTML, "--expect-title", "다른 제목", "--expect-date", "2026.06.04.")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing expected title", result.stdout)
        self.assertIn("missing expected date", result.stdout)

    def test_visible_workflow_metadata_fails_hard(self) -> None:
        bad_html = GOOD_HTML.replace(
            "Example Company A 2026년 1분기 컨퍼런스콜",
            "번역 품질 평가용 컨퍼런스콜 발췌 번역",
            1,
        )
        result = self.run_qa(bad_html)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("visible workflow metadata", result.stdout)

    def test_domain_terms_need_conceptual_review_not_mechanical_failure(self) -> None:
        html = GOOD_HTML.replace("사회자", "사회자 직영 브랜드 가맹상인", 1)

        strict = self.run_qa(html, "--strict-style")

        self.assertEqual(strict.returncode, 0, strict.stdout + strict.stderr)

    def test_raw_extracted_speaker_label_as_visible_speaker_fails_hard(self) -> None:
        bad_html = GOOD_HTML.replace('data-speaker="Executive B"', 'data-speaker="Speaker 12"')
        result = self.run_qa(bad_html)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("raw extracted speaker label as visible speaker", result.stdout)

    def test_source_unit_numeric_range_must_match_final_data_unit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            output = tmp / "out.html"
            source_units = tmp / "source_units.tsv"
            output.write_text(
                """<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><title>Example</title></head>
<body>
<div class="para" data-unit="048">중국 매출은 한 자릿수 후반에서 10%대 중반 증가할 것으로 봅니다.</div>
</body>
</html>
""",
                encoding="utf-8",
            )
            source_units.write_text(
                "unit\tspeaker\tsource_text\n"
                "048\tExecutive A\tChina revenue is expected to increase in the mid to high teens.\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output",
                    str(output),
                    "--source-units",
                    str(source_units),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unit 048 mistranslates mid-to-high teens range", result.stdout)

    def test_mismatched_table_columns_fail(self) -> None:
        bad_html = GOOD_HTML + "\n<table><tr><td>1</td><td>2</td></tr><tr><td>1</td></tr></table>"
        result = self.run_qa(bad_html)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("table row has 1 columns, expected 2", result.stdout)

    def test_table_cells_require_alignment_class(self) -> None:
        bad_html = GOOD_HTML + "\n<table><tr><th>구분</th><th>2025년</th></tr><tr><td>매출</td><td>1,000</td></tr></table>"
        result = self.run_qa(bad_html)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing left-cell/right-cell/center-cell alignment class", result.stdout)

    def test_aligned_table_passes(self) -> None:
        good_html = (
            GOOD_HTML
            + "\n<table><tr><th class=\"left-cell\">구분</th><th class=\"right-cell\">2025년</th></tr>"
            + "<tr><td class=\"left-cell\">매출</td><td class=\"right-cell\">1,000</td></tr></table>"
        )
        result = self.run_qa(good_html, "--strict-style")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_leftover_markdown_markers_fail(self) -> None:
        bad_html = GOOD_HTML.replace("Analyst A", "**Analyst A**")
        result = self.run_qa(bad_html)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("leftover raw markdown formatting markers", result.stdout)

    def test_duplicate_name_translation_fails(self) -> None:
        bad_html = GOOD_HTML.replace("Analyst A", "(홍길동, 홍길동)")
        result = self.run_qa(bad_html)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate name/phrase translation artifact", result.stdout)

    def test_unlinked_website_urls_flagged_style(self) -> None:
        bad_html = GOOD_HTML.replace("Analyst A", "www.example.com")
        result = self.run_qa(bad_html, "--strict-style")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unlinked website URL", result.stdout)

    def test_report_profile_skips_transcript_specific_style_patterns(self) -> None:
        report_html = GOOD_HTML.replace("Analyst A", "RMB 이니셔티브 관련 말씀", 1)

        transcript = self.run_qa(report_html, "--strict-style")
        report = self.run_qa(report_html, "--strict-style", "--profile", "report")

        self.assertNotEqual(transcript.returncode, 0)
        self.assertIn("raw RMB currency code", transcript.stdout)
        self.assertEqual(report.returncode, 0, report.stdout + report.stderr)


if __name__ == "__main__":
    unittest.main()
