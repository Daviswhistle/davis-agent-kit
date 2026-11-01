from __future__ import annotations

import os
from pathlib import Path
import subprocess
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

    def test_copied_rule_is_backed_up_and_linked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules_home = Path(tmp) / "cli" / "rules"
            rules_home.mkdir(parents=True)
            source = ROOT / "providers" / "agy" / install_agy.RULE_NAME
            destination = rules_home / install_agy.RULE_NAME
            destination.write_bytes(source.read_bytes())

            self.assertTrue(install_agy.check(ROOT, rules_home))
            result = install_agy.install(ROOT, rules_home)

            backup = rules_home.parent / ".davis-agent-kit-backups" / "agy" / install_agy.RULE_NAME
            self.assertEqual(backup.read_bytes(), source.read_bytes())
            self.assertTrue(destination.is_symlink())
            self.assertTrue(any(item.startswith("BACKUP") for item in result.messages))
            self.assertEqual(install_agy.check(ROOT, rules_home), [])
            again = install_agy.install(ROOT, rules_home)
            self.assertFalse(again.created_links)
            self.assertEqual(len(list(backup.parent.iterdir())), 1)

    def test_modified_copy_keeps_edits_in_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules_home = Path(tmp) / "rules"
            rules_home.mkdir()
            destination = rules_home / install_agy.RULE_NAME
            edited = "# Davis Agent Kit — AGY verification rule\nLocal note: keep this.\n"
            destination.write_text(edited, encoding="utf-8")

            install_agy.install(ROOT, rules_home)

            backup = rules_home.parent / ".davis-agent-kit-backups" / "agy" / install_agy.RULE_NAME
            self.assertEqual(backup.read_text(encoding="utf-8"), edited)
            self.assertTrue(destination.is_symlink())

    def test_backup_name_does_not_overwrite_previous_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules_home = Path(tmp) / "rules"
            rules_home.mkdir()
            backup_dir = rules_home.parent / ".davis-agent-kit-backups" / "agy"
            backup_dir.mkdir(parents=True)
            previous = backup_dir / install_agy.RULE_NAME
            previous.write_text("previous backup", encoding="utf-8")
            destination = rules_home / install_agy.RULE_NAME
            destination.write_text("# Davis Agent Kit — AGY verification rule\nnew copy\n", encoding="utf-8")

            install_agy.install(ROOT, rules_home)

            self.assertEqual(previous.read_text(encoding="utf-8"), "previous backup")
            self.assertTrue((backup_dir / "davis-agent-kit-2.md").exists())

    def test_relinks_previous_checkout_without_deleting_source(self) -> None:
        for dangling in (False, True):
            with self.subTest(dangling=dangling), tempfile.TemporaryDirectory() as tmp:
                old_source = Path(tmp) / "old-clone" / "providers" / "agy" / install_agy.RULE_NAME
                if not dangling:
                    old_source.parent.mkdir(parents=True)
                    old_source.write_text("# Davis Agent Kit — AGY verification rule\nold\n", encoding="utf-8")
                rules_home = Path(tmp) / "cli" / "rules"
                rules_home.mkdir(parents=True)
                path = rules_home / install_agy.RULE_NAME
                path.symlink_to(old_source)

                result = install_agy.install(ROOT, rules_home)

                self.assertTrue(any(item.startswith("RELINK") for item in result.messages))
                self.assertEqual(path.resolve(strict=True), (ROOT / "providers" / "agy" / install_agy.RULE_NAME).resolve())
                self.assertEqual(install_agy.check(ROOT, rules_home), [])
                self.assertEqual(old_source.exists(), not dangling)

    def test_unrelated_file_and_symlink_are_not_overwritten(self) -> None:
        for kind in ("file", "symlink", "directory"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                rules_home = Path(tmp) / "rules"
                rules_home.mkdir()
                existing = rules_home / install_agy.RULE_NAME
                if kind == "file":
                    existing.write_text("keep my rule\n", encoding="utf-8")
                elif kind == "symlink":
                    other = Path(tmp) / "custom.md"
                    other.write_text("keep my rule\n", encoding="utf-8")
                    existing.symlink_to(other)
                else:
                    existing.mkdir()
                    (existing / "keep.txt").write_text("keep", encoding="utf-8")

                with self.assertRaises(install_agy.InstallError):
                    install_agy.install(ROOT, rules_home)

                self.assertTrue(install_agy.check(ROOT, rules_home))
                if kind == "file":
                    self.assertEqual(existing.read_text(encoding="utf-8"), "keep my rule\n")
                elif kind == "symlink":
                    self.assertEqual(existing.read_text(encoding="utf-8"), "keep my rule\n")
                else:
                    self.assertEqual((existing / "keep.txt").read_text(encoding="utf-8"), "keep")
                self.assertFalse((rules_home.parent / ".davis-agent-kit-backups").exists())

    def test_failed_upgrade_restores_original_copy_and_cleans_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules_home = Path(tmp) / "rules"
            rules_home.mkdir()
            destination = rules_home / install_agy.RULE_NAME
            text = "# Davis Agent Kit — AGY verification rule\nkeep edits\n"
            destination.write_text(text, encoding="utf-8")

            with mock.patch.object(Path, "symlink_to", side_effect=PermissionError("simulated")):
                with self.assertRaises(PermissionError):
                    install_agy.install(ROOT, rules_home)

            self.assertFalse(destination.is_symlink())
            self.assertEqual(destination.read_text(encoding="utf-8"), text)
            self.assertFalse((rules_home.parent / ".davis-agent-kit-backups").exists())

    def test_failed_relink_restores_original_relative_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules_home = Path(tmp) / "cli" / "rules"
            rules_home.mkdir(parents=True)
            original = Path("../old/providers/agy/davis-agent-kit.md")
            destination = rules_home / install_agy.RULE_NAME
            destination.symlink_to(original)
            original_link = os.readlink(destination)
            original_symlink_to = Path.symlink_to
            calls = 0

            def fail_first(path: Path, target: Path, target_is_directory: bool = False) -> None:
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise PermissionError("simulated")
                original_symlink_to(path, target, target_is_directory=target_is_directory)

            with mock.patch.object(Path, "symlink_to", new=fail_first):
                with self.assertRaises(PermissionError):
                    install_agy.install(ROOT, rules_home)

            self.assertTrue(destination.is_symlink())
            self.assertEqual(os.readlink(destination), original_link)

    def test_check_reports_stale_copy_but_does_not_modify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rules_home = Path(tmp) / "rules"
            rules_home.mkdir()
            rule = rules_home / install_agy.RULE_NAME
            content = "# Davis Agent Kit — AGY verification rule\nold copy\n"
            rule.write_text(content, encoding="utf-8")
            checked = subprocess.run(
                [sys.executable, str(SCRIPTS / "install_agy.py"),
                 "--root", str(ROOT), "--rules-home", str(rules_home), "--check"],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(checked.returncode, 1)
            self.assertIn(str(rule), checked.stdout)
            self.assertEqual(rule.read_text(encoding="utf-8"), content)

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
