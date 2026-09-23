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

import install_gemini  # noqa: E402


@unittest.skipIf(os.name == "nt", "symlink contract is POSIX-oriented")
class GeminiInstallerTests(unittest.TestCase):
    def test_default_home_follows_gemini_cli_home(self) -> None:
        with mock.patch.dict(os.environ, {"GEMINI_CLI_HOME": "/tmp/gemini-user"}):
            self.assertEqual(
                install_gemini.default_gemini_home(),
                Path("/tmp/gemini-user/.gemini"),
            )

    def test_install_is_idempotent_and_checkable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gemini_home = Path(tmp) / ".gemini"
            first = install_gemini.install(ROOT, gemini_home)
            second = install_gemini.install(ROOT, gemini_home)

            self.assertEqual(len(first.created_links), 1)
            self.assertFalse(second.created_links)
            self.assertEqual(
                (gemini_home / "GEMINI.md").resolve(strict=True),
                (ROOT / "providers" / "gemini" / "GEMINI.md").resolve(),
            )
            self.assertEqual(install_gemini.check(ROOT, gemini_home), [])

    def test_conflict_fails_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gemini_home = Path(tmp) / ".gemini"
            gemini_home.mkdir()
            existing = gemini_home / "GEMINI.md"
            existing.write_text("keep my guidance\n", encoding="utf-8")

            with self.assertRaises(install_gemini.InstallError):
                install_gemini.install(ROOT, gemini_home)

            self.assertEqual(
                existing.read_text(encoding="utf-8"),
                "keep my guidance\n",
            )

    def test_partial_failure_rolls_back_created_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gemini_home = Path(tmp) / ".gemini"
            with mock.patch.object(
                Path,
                "symlink_to",
                side_effect=PermissionError("simulated"),
            ):
                with self.assertRaises(PermissionError):
                    install_gemini.install(ROOT, gemini_home)

            self.assertFalse(gemini_home.exists())


if __name__ == "__main__":
    unittest.main()
