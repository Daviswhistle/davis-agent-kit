from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_report_equivalence.py"


REPORT_HTML = """<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><title>테스트 연차보고서</title></head>
<body>
<h1>테스트 연차보고서</h1>
<section class="report-page" data-page="1">
<h2>요약</h2>
<p><strong>매출</strong>은 증가했습니다. <em>주석</em></p>
<a href="https://www.example.com">example</a>
<table>
<tr><th class="left-cell">구분</th><th class="right-cell">2025년</th></tr>
<tr><td class="left-cell">매출</td><td class="right-cell">1,000</td></tr>
</table>
</section>
<section class="report-page" data-page="2"><p>끝</p></section>
</body>
</html>
"""


class ReportEquivalenceTests(unittest.TestCase):
    def run_eval(self, candidate_text: str, reference_text: str = REPORT_HTML) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            candidate = tmp / "candidate.html"
            reference = tmp / "reference.html"
            candidate.write_text(candidate_text, encoding="utf-8")
            reference.write_text(reference_text, encoding="utf-8")
            return subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--candidate",
                    str(candidate),
                    "--reference",
                    str(reference),
                    "--expect-title",
                    "테스트 연차보고서",
                    "--expect-pages",
                    "2",
                    "--require-core-counts-match",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def test_matching_report_passes(self) -> None:
        result = self.run_eval(REPORT_HTML)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS: report equivalence gates satisfied", result.stdout)

    def test_missing_table_alignment_fails(self) -> None:
        bad = REPORT_HTML.replace(' class="right-cell"', "", 1)
        result = self.run_eval(bad)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("without alignment class", result.stdout)

    def test_core_count_drift_fails(self) -> None:
        bad = REPORT_HTML.replace("<table>", "<!-- missing table -->", 1).replace("</table>", "", 1)
        result = self.run_eval(bad)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("table_count mismatch", result.stdout)

    def test_raw_markdown_artifact_fails(self) -> None:
        bad = REPORT_HTML.replace("끝", r"\\* 끝")
        result = self.run_eval(bad)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("raw markdown/source artifact", result.stdout)


if __name__ == "__main__":
    unittest.main()
