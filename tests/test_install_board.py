from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import install_claude
import install_codex


@unittest.skipIf(os.name == "nt", "symlink contract is POSIX-oriented")
class BoardInstallerTests(unittest.TestCase):
    def test_both_installers_share_a_writable_copy_and_preserve_edits(self):
        template = ROOT / "templates" / "BOARD.md"
        original = template.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            codex, claude = base / ".codex", base / ".claude"
            agents = base / ".agents"
            install_codex.install(ROOT, codex, agents / "skills")
            board = agents / "BOARD.md"
            self.assertFalse(board.is_symlink())
            self.assertEqual(board.read_bytes(), original)
            self.assertEqual(board.stat().st_mode & 0o777, 0o600)
            board.write_bytes(b"user-owned task state\n")
            install_claude.install(ROOT, claude)
            install_codex.install(ROOT, codex, agents / "skills")
            self.assertEqual(board.read_bytes(), b"user-owned task state\n")
            self.assertEqual(template.read_bytes(), original)
            self.assertEqual(install_codex.check(ROOT, codex, agents / "skills"), [])
            self.assertEqual(install_claude.check(ROOT, claude), [])

    def test_claude_can_initialize_board_first_and_use_custom_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home, agents = base / "client", base / "shared"
            install_claude.install(ROOT, home, agents)
            self.assertTrue((agents / "BOARD.md").is_file())
            self.assertFalse((base / ".agents").exists())
            self.assertEqual(install_claude.check(ROOT, home, agents), [])
            install_codex.install(ROOT, base / "other", base / "skills", agents)
            self.assertEqual(install_codex.check(ROOT, base / "other", base / "skills", agents), [])

    def test_missing_board_check_never_creates_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for installer in (install_codex, install_claude):
                with self.subTest(installer=installer.__name__):
                    if installer is install_codex:
                        problems = installer.check(ROOT, base / ".codex", base / ".agents" / "skills")
                    else:
                        problems = installer.check(ROOT, base / ".claude")
                    self.assertTrue(any("local board" in problem for problem in problems))
                    self.assertEqual(list(base.iterdir()), [])

    def test_directory_and_symlink_conflicts_precede_client_changes(self):
        for installer in (install_codex, install_claude):
            for kind in ("directory", "symlink", "dangling"):
                with self.subTest(installer=installer.__name__, kind=kind), tempfile.TemporaryDirectory() as tmp:
                    base = Path(tmp)
                    agents = base / ".agents"
                    agents.mkdir()
                    board = agents / "BOARD.md"
                    if kind == "directory":
                        board.mkdir()
                    else:
                        target = base / "target"
                        if kind == "symlink":
                            target.write_text("keep this")
                        board.symlink_to(target)
                    with self.assertRaises(install_codex.InstallError):
                        if installer is install_codex:
                            installer.install(ROOT, base / "client", agents / "skills")
                        else:
                            installer.install(ROOT, base / "client")
                    self.assertFalse((base / "client").exists())
                    self.assertFalse((agents / "skills").exists())
                    if kind == "symlink":
                        self.assertEqual(target.read_text(), "keep this")

    def test_concurrent_initialization_preserves_the_winning_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            agents = Path(tmp)
            original_open = os.open

            def raced_open(path, flags, mode):
                Path(path).write_bytes(b"other installer already wrote this")
                return original_open(path, flags, mode)

            result = install_codex.InstallResult()
            with mock.patch.object(install_codex.os, "open", side_effect=raced_open):
                install_codex.install_board(ROOT, agents, result)
            self.assertFalse(result.created_files)
            self.assertEqual((agents / "BOARD.md").read_bytes(), b"other installer already wrote this")

    def test_failure_after_board_creation_rolls_back_new_files(self):
        for installer in (install_codex, install_claude):
            with self.subTest(installer=installer.__name__), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                with mock.patch.object(installer, "check", return_value=["simulated failure"]):
                    with self.assertRaises(install_codex.InstallError):
                        if installer is install_codex:
                            installer.install(ROOT, base / ".codex", base / ".agents" / "skills")
                        else:
                            installer.install(ROOT, base / ".claude")
                self.assertEqual(list(base.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
