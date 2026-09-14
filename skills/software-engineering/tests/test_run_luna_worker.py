from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_luna_worker.py"
SPEC = importlib.util.spec_from_file_location("run_luna_worker", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class LunaWorkerLauncherTests(unittest.TestCase):
    def test_build_command_pins_worker_resources(self) -> None:
        command = MODULE.build_command("codex", Path("/repo"), False)
        self.assertEqual(command[:3], ["codex", "exec", "--strict-config"])
        self.assertIn("gpt-5.6-luna", command)
        self.assertIn("workspace-write", command)
        self.assertIn('model_reasoning_effort="max"', command)
        self.assertIn('service_tier="priority"', command)
        self.assertIn('approval_policy="never"', command)
        self.assertTrue(
            any(arg.startswith("developer_instructions=") for arg in command),
            command,
        )
        self.assertEqual(command[-1], "-")
        self.assertNotIn("--skip-git-repo-check", command)

    def test_build_command_can_allow_non_git_workspace(self) -> None:
        command = MODULE.build_command("codex", Path("/repo"), True)
        self.assertIn("--skip-git-repo-check", command)

    def test_toml_string_round_trips_worker_instructions(self) -> None:
        encoded = MODULE.toml_string(MODULE.WORKER_DEVELOPER_INSTRUCTIONS)
        self.assertEqual(json.loads(encoded), MODULE.WORKER_DEVELOPER_INSTRUCTIONS)

    def test_read_contract_rejects_empty_stdin(self) -> None:
        with mock.patch.object(sys, "stdin", io.StringIO("")):
            with self.assertRaisesRegex(ValueError, "empty"):
                MODULE.read_contract(None)

    def test_main_forwards_contract_and_exit_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            fake = cwd / "fake-codex"
            record = cwd / "record.json"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "Path(os.environ['RECORD']).write_text(json.dumps({'argv': sys.argv[1:], 'stdin': sys.stdin.read()}))\n"
                "raise SystemExit(7)\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            env = os.environ.copy()
            env["RECORD"] = str(record)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--codex-bin",
                    str(fake),
                    "--cwd",
                    str(cwd),
                    "Goal: change one file",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )
            self.assertEqual(completed.returncode, 7, completed.stderr)
            observed = json.loads(record.read_text(encoding="utf-8"))
            self.assertEqual(observed["stdin"], "Goal: change one file")
            self.assertEqual(observed["argv"][:2], ["exec", "--strict-config"])
            self.assertIn("gpt-5.6-luna", observed["argv"])
            self.assertIn('service_tier="priority"', observed["argv"])
            self.assertEqual(observed["argv"][-1], "-")


if __name__ == "__main__":
    unittest.main()
