import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate.py"
spec = importlib.util.spec_from_file_location("agent_loop_evaluate", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EvaluateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / "baseline"
        self.candidate = self.root / "candidate"
        self.sources = self.root / "sources"
        for run in [self.base, self.candidate]:
            (run / "nrr").mkdir(parents=True)
        self.sources.mkdir()

    def write(self, root, path, value):
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(value, encoding="utf-8")

    def suite(self, *rules):
        return {"version": 1, "cases": [{"id": "nrr", "assertions": list(rules)}]}

    def test_improvement_and_no_regressions(self):
        self.write(self.base, "nrr/answer.md", "NRR 122% is official")
        self.write(self.candidate, "nrr/answer.md", "NRR 122% is unvalidated")
        rules = self.suite(
            {"type": "contains", "path": "answer.md", "value": "unvalidated"},
            {"type": "not_contains", "path": "answer.md", "value": "official"},
        )
        report = module.compare(rules, self.base, self.candidate, None)
        self.assertTrue(report["summary"]["passed"])
        self.assertEqual(report["summary"]["improved_assertions"], 2)
        self.assertEqual(report["summary"]["candidate_failures"], 0)

    def test_regression_detected_even_when_other_rule_improves(self):
        self.write(self.base, "nrr/answer.md", "keep this")
        self.write(self.candidate, "nrr/answer.md", "new improvement")
        report = module.compare(self.suite(
            {"type": "contains", "path": "answer.md", "value": "new improvement"},
            {"type": "contains", "path": "answer.md", "value": "keep this"},
        ), self.base, self.candidate, None)
        self.assertEqual(report["summary"]["improved_assertions"], 1)
        self.assertEqual(report["summary"]["regressed_assertions"], 1)
        self.assertFalse(report["summary"]["passed"])

    def test_json_field_and_types(self):
        self.write(self.base, "nrr/metrics.json", '{"review": {"validated": 1}}')
        self.write(self.candidate, "nrr/metrics.json", '{"review": {"validated": true}}')
        report = module.compare(self.suite({"type": "json_equals", "path": "metrics.json",
                                                 "pointer": "/review/validated", "value": True}),
                                self.base, self.candidate, None)
        self.assertTrue(report["summary"]["passed"])
        self.assertEqual(report["summary"]["improved_assertions"], 1)

    def test_evidence_quote_must_match_actual_source(self):
        self.write(self.sources, "finance.csv", "metric,value\ncontrolled_arr,36.9\n")
        self.write(self.base, "nrr/evidence.json", json.dumps([
            {"claim": "ARR 43.0", "evidence": [{"file": "finance.csv", "quote": "controlled_arr,43.0"}]}
        ]))
        self.write(self.candidate, "nrr/evidence.json", json.dumps([
            {"claim": "ARR 36.9", "evidence": [{"file": "finance.csv", "quote": "controlled_arr,36.9"}]}
        ]))
        report = module.compare(self.suite({"type": "evidence_quotes", "path": "evidence.json"}),
                                self.base, self.candidate, self.sources)
        self.assertTrue(report["summary"]["passed"])
        self.assertEqual(report["summary"]["improved_assertions"], 1)

    def test_missing_artifact_is_failure_not_skip(self):
        self.write(self.base, "nrr/answer.md", "verified")
        report = module.compare(self.suite({"type": "contains", "path": "answer.md", "value": "verified"}),
                                self.base, self.candidate, None)
        self.assertFalse(report["summary"]["passed"])
        self.assertEqual(report["summary"]["regressed_assertions"], 1)

    def test_unsafe_paths_rejected(self):
        with self.assertRaises(module.SuiteError):
            module.compare(self.suite({"type": "contains", "path": "../../private", "value": "x"}),
                           self.base, self.candidate, None)
        with self.assertRaises(module.SuiteError):
            module.compare(self.suite({"type": "contains", "path": "/tmp/secret", "value": "x"}),
                           self.base, self.candidate, None)

    def test_symlink_escape_blocked_in_candidate(self):
        self.write(self.root, "outside.txt", "forbidden")
        (self.candidate / "nrr" / "answer.md").symlink_to(self.root / "outside.txt")
        report = module.compare(self.suite({"type": "contains", "path": "answer.md", "value": "forbidden"}),
                                self.base, self.candidate, None)
        self.assertFalse(report["summary"]["passed"])
        self.assertIn("escapes root", report["cases"][0]["candidate"][0]["reason"])

    def test_bad_suite_is_hard_error(self):
        with self.assertRaises(module.SuiteError):
            module.compare(self.suite({"type": "fictional", "path": "answer.md"}),
                           self.base, self.candidate, None)
        with self.assertRaises(module.SuiteError):
            module.compare({"version": 1, "cases": [{"id": "nrr", "assertions": []}]},
                           self.base, self.candidate, None)

    def test_cli_exit_codes_and_report(self):
        self.write(self.base, "nrr/answer.md", "official")
        self.write(self.candidate, "nrr/answer.md", "unvalidated")
        suite = self.root / "suite.json"
        suite.write_text(json.dumps(self.suite({"type": "contains", "path": "answer.md", "value": "unvalidated"})))
        output = self.root / "report.json"
        self.assertEqual(module.main(["--suite", str(suite), "--baseline", str(self.base),
                                      "--candidate", str(self.candidate), "--output", str(output)]), 0)
        self.assertTrue(json.loads(output.read_text())["summary"]["passed"])
        self.assertEqual(module.main(["--suite", str(suite), "--baseline", str(self.candidate),
                                      "--candidate", str(self.base)]), 1)


if __name__ == "__main__":
    unittest.main()
