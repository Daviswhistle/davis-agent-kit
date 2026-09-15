from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_ocr_shadow_review.py"
SPEC = importlib.util.spec_from_file_location("run_ocr_shadow_review", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

SHA = "a" * 40
PARENT = "b" * 40


class OCRShadowReviewTests(unittest.TestCase):
    def test_build_commands_pin_shadow_resources_and_json_delegate(self) -> None:
        cwd = Path("/repo")
        preview = MODULE.build_preview_command("ocr", cwd, SHA)
        self.assertEqual(preview[:3], ["ocr", "delegate", "preview"])
        self.assertIn("--format", preview)
        self.assertIn("json", preview)
        self.assertIn(SHA, preview)

        rule = MODULE.build_rule_command("ocr", cwd, SHA, ["src/a.py", "src/b.py"])
        self.assertEqual(rule[:3], ["ocr", "delegate", "rule"])
        self.assertEqual(rule[-2:], ["src/a.py", "src/b.py"])

        codex = MODULE.build_codex_command("codex", cwd)
        self.assertEqual(codex[:3], ["codex", "exec", "--strict-config"])
        self.assertIn("gpt-6-astra", codex)
        self.assertIn("read-only", codex)
        self.assertIn('model_reasoning_effort="high"', codex)
        self.assertIn('service_tier="default"', codex)
        self.assertIn("features.fast_mode=false", codex)
        self.assertIn('approval_policy="never"', codex)
        self.assertEqual(codex[-1], "-")

    def test_parse_json_rejects_schema_drift(self) -> None:
        with self.assertRaisesRegex(MODULE.ExperimentError, "schema mismatch"):
            MODULE.parse_json_output('{"schema_version":"2"}', "preview")

    def test_build_prompt_contains_exact_boundary_and_rules(self) -> None:
        preview = {
            "schema_version": "1",
            "mode": "commit",
            "reviewable_files": [{"path": "src/a.py"}],
            "excluded_files": [{"path": "tests/test_a.py", "exclude_reason": "default_path"}],
        }
        rules = [{"schema_version": "1", "groups": [{"files": ["src/a.py"], "rule": "check errors"}]}]
        prompt = MODULE.build_prompt(SHA, preview, rules)
        self.assertIn(SHA, prompt)
        self.assertIn("src/a.py", prompt)
        self.assertIn("check errors", prompt)
        self.assertIn("tests/test_a.py", prompt)
        self.assertIn("review boundary", prompt)

    def test_main_runs_ocr_then_codex_and_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd = root / "repo"
            cwd.mkdir()
            record = root / "codex-record.json"
            output = root / "shadow.md"
            fake_git = root / "fake-git"
            fake_ocr = root / "fake-ocr"
            fake_codex = root / "fake-codex"

            fake_git.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                f"sha={SHA!r}; parent={PARENT!r}\n"
                "args=sys.argv[1:]\n"
                "if args[:2] == ['rev-parse', '--show-toplevel']:\n"
                "    import os; print(os.getcwd())\n"
                "elif args[:2] == ['rev-parse', '--verify']:\n"
                "    print(sha)\n"
                "elif args == ['rev-parse', 'HEAD']:\n"
                "    print(sha)\n"
                "elif args[:3] == ['rev-list', '--parents', '-n']:\n"
                "    print(sha, parent)\n"
                "elif args[:2] == ['status', '--porcelain']:\n"
                "    pass\n"
                "else:\n"
                "    print('unexpected git args: '+repr(args), file=sys.stderr); raise SystemExit(9)\n",
                encoding="utf-8",
            )
            fake_ocr.write_text(
                "#!/usr/bin/env python3\n"
                "import json, sys\n"
                "args=sys.argv[1:]\n"
                "if args[:2] == ['delegate', 'preview']:\n"
                "    print(json.dumps({'schema_version':'1','mode':'commit','reviewable_count':1,'excluded_count':1,'reviewable_files':[{'path':'src/a.py','status':'M','insertions':2,'deletions':1}],'excluded_files':[{'path':'tests/test_a.py','status':'M','insertions':1,'deletions':1,'exclude_reason':'default_path'}]}))\n"
                "elif args[:2] == ['delegate', 'rule']:\n"
                "    print(json.dumps({'schema_version':'1','groups':[{'group_id':1,'source':'system','pattern':'**/*.py','files':['src/a.py'],'rule':'check Python correctness'}]}))\n"
                "else:\n"
                "    raise SystemExit(8)\n",
                encoding="utf-8",
            )
            fake_codex.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "Path(os.environ['RECORD']).write_text(json.dumps({'argv':sys.argv[1:],'stdin':sys.stdin.read()}), encoding='utf-8')\n"
                "print('No findings.')\n",
                encoding="utf-8",
            )
            for executable in (fake_git, fake_ocr, fake_codex):
                executable.chmod(0o755)

            env = os.environ.copy()
            env["RECORD"] = str(record)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--cwd",
                    str(cwd),
                    "--commit",
                    SHA,
                    "--git-bin",
                    str(fake_git),
                    "--ocr-bin",
                    str(fake_ocr),
                    "--codex-bin",
                    str(fake_codex),
                    "--output",
                    str(output),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            observed = json.loads(record.read_text(encoding="utf-8"))
            self.assertEqual(observed["argv"][:2], ["exec", "--strict-config"])
            self.assertIn("gpt-6-astra", observed["argv"])
            self.assertIn("read-only", observed["argv"])
            self.assertIn("src/a.py", observed["stdin"])
            self.assertIn("check Python correctness", observed["stdin"])
            report = output.read_text(encoding="utf-8")
            self.assertIn("# OCR Shadow Review", report)
            self.assertIn("No findings.", report)
            self.assertIn("selected files: 1", report)
            self.assertIn("excluded files: 1", report)
            self.assertIn("tests/test_a.py", report)
            self.assertIn("default_path", report)


if __name__ == "__main__":
    unittest.main()
