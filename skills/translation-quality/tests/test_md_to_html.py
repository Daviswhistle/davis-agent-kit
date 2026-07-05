from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "md_to_html.py"


class MdToHtmlTests(unittest.TestCase):
    def run_convert(self, markdown: str, *extra_args: str) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "input.md"
            output = tmp / "output.html"
            source.write_text(markdown, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--input",
                    str(source),
                    "--output",
                    str(output),
                    "--title",
                    "테스트 보고서",
                    *extra_args,
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            rendered = output.read_text(encoding="utf-8") if output.exists() else ""
        return result, rendered

    def test_escapes_raw_html_and_preserves_inline_markdown_and_links(self) -> None:
        result, rendered = self.run_convert(
            "### Page 1\n\n# 개요\n\n**굵게** <script>alert(1)</script> www.example.com"
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("<strong>굵게</strong>", rendered)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertIn('<a href="https://www.example.com" target="_blank">www.example.com</a>', rendered)

    def test_table_alignment_classes_are_generated(self) -> None:
        result, rendered = self.run_convert(
            "\n".join(
                [
                    "### Page 1",
                    "",
                    "| 구분 | 2025년 |",
                    "| --- | ---: |",
                    "| 매출 | 1,000 |",
                ]
            )
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('<th class="left-cell">구분</th>', rendered)
        self.assertIn('<th class="right-cell">2025년</th>', rendered)
        self.assertIn('<td class="right-cell">1,000</td>', rendered)

    def test_numeric_columns_override_centered_markdown_separator(self) -> None:
        result, rendered = self.run_convert(
            "\n".join(
                [
                    "### Page 1",
                    "",
                    "| 구분 | 2025년 | 2024년 |",
                    "| :---: | :---: | :---: |",
                    "| 매출 | 1,000 | 900 |",
                ]
            )
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('<th class="left-cell">구분</th>', rendered)
        self.assertIn('<th class="right-cell">2025년</th>', rendered)
        self.assertIn('<td class="right-cell">900</td>', rendered)

    def test_mismatched_table_columns_fail(self) -> None:
        result, rendered = self.run_convert(
            "\n".join(
                [
                    "### Page 1",
                    "",
                    "| 구분 | 2025년 |",
                    "| --- | ---: |",
                    "| 매출 |",
                ]
            )
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(rendered, "")
        self.assertIn("table row has 1 columns, expected 2", result.stderr)


if __name__ == "__main__":
    unittest.main()
