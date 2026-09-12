from __future__ import annotations

import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import install_codex  # noqa: E402


@unittest.skipIf(os.name == "nt", "symlink contract is POSIX-oriented")
class InstallerTests(unittest.TestCase):
    def homes(self, tmp: str) -> tuple[Path, Path]:
        root = Path(tmp)
        return root / ".codex", root / ".agents" / "skills"

    def test_install_is_idempotent_and_checkable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home, skills_home = self.homes(tmp)
            first = install_codex.install(ROOT, codex_home, skills_home)
            second = install_codex.install(ROOT, codex_home, skills_home)

            self.assertTrue(first.created_links)
            self.assertFalse(second.created_links)
            self.assertEqual(
                (codex_home / "AGENTS.md").resolve(strict=True),
                (ROOT / "AGENTS.md").resolve(),
            )
            for name in install_codex.discover_skills(ROOT):
                self.assertEqual(
                    (skills_home / name).resolve(strict=True),
                    (ROOT / "skills" / name).resolve(),
                )
            self.assertEqual(install_codex.check(ROOT, codex_home, skills_home), [])

    def test_conflict_fails_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home, skills_home = self.homes(tmp)
            codex_home.mkdir(parents=True)
            (codex_home / "AGENTS.md").write_text("keep\n", encoding="utf-8")

            with self.assertRaises(install_codex.InstallError):
                install_codex.install(ROOT, codex_home, skills_home)

            self.assertFalse(skills_home.exists())
            self.assertEqual((codex_home / "AGENTS.md").read_text(), "keep\n")

    def test_legacy_skill_blocks_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home, skills_home = self.homes(tmp)
            legacy = codex_home / "skills" / install_codex.discover_skills(ROOT)[0]
            legacy.mkdir(parents=True)

            with self.assertRaises(install_codex.InstallError) as raised:
                install_codex.install(ROOT, codex_home, skills_home)

            self.assertIn("legacy $CODEX_HOME/skills", str(raised.exception))
            self.assertFalse(skills_home.exists())

    def test_retired_skill_blocks_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home, skills_home = self.homes(tmp)
            retired = skills_home / install_codex.RETIRED_SKILLS[-1]
            retired.mkdir(parents=True)

            with self.assertRaises(install_codex.InstallError):
                install_codex.install(ROOT, codex_home, skills_home)

    def test_empty_global_override_does_not_shadow_instructions(self) -> None:
        for content in ("", " \n\t"):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as tmp:
                codex_home, skills_home = self.homes(tmp)
                codex_home.mkdir()
                override = codex_home / "AGENTS.override.md"
                override.write_text(content, encoding="utf-8")

                install_codex.install(ROOT, codex_home, skills_home)

                self.assertEqual(install_codex.check(ROOT, codex_home, skills_home), [])
                self.assertEqual(override.read_text(encoding="utf-8"), content)

    def test_shadowing_override_blocks_install_before_mutation(self) -> None:
        for linked in (False, True):
            with self.subTest(linked=linked), tempfile.TemporaryDirectory() as tmp:
                codex_home, skills_home = self.homes(tmp)
                codex_home.mkdir()
                override = codex_home / "AGENTS.override.md"
                source = Path(tmp) / "custom-instructions.md" if linked else override
                source.write_text("Keep my instructions.\n", encoding="utf-8")
                if linked:
                    override.symlink_to(source)

                with mock.patch.object(Path, "symlink_to") as create_link:
                    with self.assertRaises(install_codex.InstallError) as raised:
                        install_codex.install(ROOT, codex_home, skills_home)
                    create_link.assert_not_called()

                self.assertIn("shadowed", str(raised.exception))
                self.assertFalse(skills_home.exists())
                self.assertFalse((codex_home / "AGENTS.md").exists())
                self.assertEqual(override.read_text(), "Keep my instructions.\n")
                self.assertEqual(override.is_symlink(), linked)

    def test_added_override_fails_check_and_preserves_existing_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home, skills_home = self.homes(tmp)
            installed = install_codex.install(ROOT, codex_home, skills_home)
            override = codex_home / "AGENTS.override.md"
            override.write_text("Temporary instructions.\n", encoding="utf-8")

            problems = install_codex.check(ROOT, codex_home, skills_home)
            self.assertEqual(len(problems), 1)
            self.assertIn("shadowed", problems[0])
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / "install_codex.py"),
                 "--root", str(ROOT), "--codex-home", str(codex_home),
                 "--skills-home", str(skills_home), "--check"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn(str(override), completed.stdout)
            with self.assertRaises(install_codex.InstallError):
                install_codex.install(ROOT, codex_home, skills_home)
            for link in installed.created_links:
                self.assertTrue(link.is_symlink())
                self.assertTrue(link.exists())
            self.assertEqual(override.read_text(), "Temporary instructions.\n")

    def test_override_link_to_normative_source_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home, skills_home = self.homes(tmp)
            codex_home.mkdir()
            override = codex_home / "AGENTS.override.md"
            override.symlink_to(ROOT / "AGENTS.md")

            install_codex.install(ROOT, codex_home, skills_home)

            self.assertEqual(install_codex.check(ROOT, codex_home, skills_home), [])
            self.assertTrue(override.is_symlink())

    def test_uninspectable_override_fails_without_mutation(self) -> None:
        for kind in ("directory", "dangling-link", "invalid-utf8", "unreadable"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                codex_home, skills_home = self.homes(tmp)
                codex_home.mkdir()
                override = codex_home / "AGENTS.override.md"
                if kind == "directory":
                    override.mkdir()
                elif kind == "dangling-link":
                    override.symlink_to(Path(tmp) / "missing.md")
                else:
                    override.write_bytes(b"\xff" if kind == "invalid-utf8" else b"private")

                original_read = Path.read_text

                def read_text(path: Path, *args, **kwargs):
                    if kind == "unreadable" and path == override:
                        raise PermissionError("simulated")
                    return original_read(path, *args, **kwargs)

                with mock.patch.object(Path, "read_text", new=read_text):
                    with self.assertRaises(install_codex.InstallError) as raised:
                        install_codex.install(ROOT, codex_home, skills_home)
                    self.assertIn("cannot verify", str(raised.exception))
                    self.assertTrue(any("cannot verify" in problem for problem in
                                        install_codex.check(ROOT, codex_home, skills_home)))
                self.assertFalse(skills_home.exists())
                self.assertFalse((codex_home / "AGENTS.md").exists())
                self.assertTrue(install_codex.path_exists(override))

    def test_partial_link_failure_rolls_back_created_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home, skills_home = self.homes(tmp)
            original = Path.symlink_to
            calls = 0

            def fail_second(path: Path, target: Path, target_is_directory: bool = False) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise PermissionError("simulated")
                original(path, target, target_is_directory=target_is_directory)

            with mock.patch.object(Path, "symlink_to", new=fail_second):
                with self.assertRaises(PermissionError):
                    install_codex.install(ROOT, codex_home, skills_home)

            self.assertFalse((codex_home / "AGENTS.md").exists())
            self.assertFalse(any(skills_home.iterdir()) if skills_home.exists() else False)


if __name__ == "__main__":
    unittest.main()
