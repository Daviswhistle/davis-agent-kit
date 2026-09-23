from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import install_agy  # noqa: E402


@unittest.skipIf(os.name == "nt", "symlink contract is POSIX-oriented")
class AgyInstallerTests(unittest.TestCase):
    def test_install_is_idempotent_and_checkable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules_home = Path(tmp) / ".gemini" / "antigravity-cli" / "rules"
            first = install_agy.install(ROOT, rules_home)
            second = install_agy.install(ROOT, rules_home)

            self.assertEqual(len(first.created_links), 1)
            self.assertFalse(second.created_links)
            self.assertEqual(
                (rules_home / install_agy.RULE_NAME).resolve(strict=True),
                (ROOT / "providers" / "agy" / install_agy.RULE_NAME).resolve(),
            )
            self.assertEqual(install_agy.check(ROOT, rules_home), [])

    def test_conflict_fails_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules_home = Path(tmp) / "rules"
            rules_home.mkdir()
            existing = rules_home / install_agy.RULE_NAME
            existing.write_text("keep my rule\n", encoding="utf-8")

            with self.assertRaises(install_agy.InstallError):
                install_agy.install(ROOT, rules_home)

            self.assertEqual(existing.read_text(encoding="utf-8"), "keep my rule\n")

    def test_partial_failure_rolls_back_created_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules_home = Path(tmp) / ".gemini" / "antigravity-cli" / "rules"
            with mock.patch.object(
                Path,
                "symlink_to",
                side_effect=PermissionError("simulated"),
            ):
                with self.assertRaises(PermissionError):
                    install_agy.install(ROOT, rules_home)

            self.assertFalse(rules_home.exists())


if __name__ == "__main__":
    unittest.main()
