from __future__ import annotations

import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import install_claude  # noqa: E402


@unittest.skipIf(os.name == "nt", "symlink contract is POSIX-oriented")
class ClaudeInstallerTests(unittest.TestCase):
    def test_install_is_idempotent_and_checkable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".claude"
            first = install_claude.install(ROOT, home)
            second = install_claude.install(ROOT, home)
            self.assertTrue(first.created_links)
            self.assertFalse(second.created_links)
            self.assertEqual((home / "rules" / install_claude.RULE_NAME).resolve(strict=True), (ROOT / "AGENTS.md").resolve())
            for name in install_claude.discover_skills(ROOT):
                self.assertEqual((home / "skills" / name).resolve(strict=True), (ROOT / "skills" / name).resolve())
            self.assertEqual(install_claude.check(ROOT, home), [])
            self.assertFalse((home / "CLAUDE.md").exists())

    def test_preserves_existing_claude_settings_and_unrelated_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".claude"
            (home / "rules").mkdir(parents=True)
            (home / "skills" / "personal").mkdir(parents=True)
            (home / "CLAUDE.md").write_text("Keep my notes", encoding="utf-8")
            (home / "settings.json").write_text('{"model": "sonnet"}', encoding="utf-8")
            (home / "rules" / "other.md").write_text("Other", encoding="utf-8")
            install_claude.install(ROOT, home)
            self.assertEqual((home / "CLAUDE.md").read_text(), "Keep my notes")
            self.assertEqual((home / "settings.json").read_text(), '{"model": "sonnet"}')
            self.assertTrue((home / "skills" / "personal").is_dir())
            self.assertEqual((home / "rules" / "other.md").read_text(), "Other")

    def test_conflict_blocks_without_partial_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".claude"
            (home / "rules").mkdir(parents=True)
            (home / "rules" / install_claude.RULE_NAME).write_text("Keep this", encoding="utf-8")
            with self.assertRaises(install_claude.InstallError):
                install_claude.install(ROOT, home)
            self.assertFalse((home / "skills").exists())
            self.assertEqual((home / "rules" / install_claude.RULE_NAME).read_text(), "Keep this")

    def test_skill_conflict_blocks_without_partial_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".claude"
            name = install_claude.discover_skills(ROOT)[0]
            (home / "skills" / name).mkdir(parents=True)
            with self.assertRaises(install_claude.InstallError):
                install_claude.install(ROOT, home)
            self.assertFalse((home / "rules").exists())

    def test_prunes_only_obsolete_kit_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".claude"
            install_claude.install(ROOT, home)
            old = ROOT / "skills" / "removed"
            (home / "skills" / "removed").symlink_to(old, target_is_directory=True)
            other = Path(tmp) / "other"
            other.mkdir()
            (home / "skills" / "unrelated").symlink_to(other, target_is_directory=True)
            self.assertTrue(install_claude.check(ROOT, home))
            result = install_claude.install(ROOT, home)
            self.assertFalse((home / "skills" / "removed").is_symlink())
            self.assertTrue((home / "skills" / "unrelated").is_symlink())
            self.assertTrue(any(line.startswith("REMOVE") for line in result.messages))
            self.assertEqual(install_claude.check(ROOT, home), [])

    def test_rollback_on_link_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".claude"
            orig_symlink_to = Path.symlink_to
            counter = 0

            def fail_second(path, target, target_is_directory=False):
                nonlocal counter
                counter += 1
                if counter == 2:
                    raise PermissionError("simulated error")
                return orig_symlink_to(path, target, target_is_directory=target_is_directory)

            with mock.patch.object(Path, "symlink_to", new=fail_second):
                with self.assertRaises(PermissionError):
                    install_claude.install(ROOT, home)
            self.assertFalse(home.exists())

    def test_check_cli_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".claude"
            command = [sys.executable, str(SCRIPTS / "install_claude.py"), "--root", str(ROOT), "--claude-home", str(home), "--check"]
            failed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(failed.returncode, 1)
            self.assertFalse(home.exists())
            install_claude.install(ROOT, home)
            passed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
