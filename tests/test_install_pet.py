from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import install_pet  # noqa: E402


class PetInstallerTests(unittest.TestCase):
    def make_repo(self, root: Path) -> Path:
        repo = root / "repo"
        pets = repo / "pets"
        for pet_id, name, description in (
            ("alpha", "Alpha", "First pet"),
            ("beta", "Beta", "Second pet"),
        ):
            directory = pets / pet_id
            directory.mkdir(parents=True)
            (directory / "sprite.webp").write_bytes(pet_id.encode())
            (directory / "pet.json").write_text(
                json.dumps(
                    {
                        "id": pet_id,
                        "displayName": name,
                        "description": description,
                        "spritesheetPath": "sprite.webp",
                    }
                ),
                encoding="utf-8",
            )
        return repo

    def test_discovers_pets_from_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make_repo(Path(tmp))
            pets = install_pet.discover_pets(repo)

            self.assertEqual([pet.pet_id for pet in pets], ["alpha", "beta"])
            self.assertEqual(pets[0].display_name, "Alpha")
            self.assertEqual(pets[1].description, "Second pet")

    def test_install_is_idempotent_and_checkable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.make_repo(root)
            codex_home = root / ".codex"

            first = install_pet.install(repo, codex_home, "alpha")
            second = install_pet.install(repo, codex_home, "alpha")

            self.assertEqual(first, second)
            self.assertEqual((first / "sprite.webp").read_bytes(), b"alpha")
            self.assertEqual(install_pet.check(repo, codex_home, "alpha"), [])

    def test_existing_different_pet_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.make_repo(root)
            codex_home = root / ".codex"
            destination = codex_home / "pets" / "alpha"
            destination.mkdir(parents=True)
            (destination / "keep.txt").write_text("keep", encoding="utf-8")

            with self.assertRaises(install_pet.InstallError):
                install_pet.install(repo, codex_home, "alpha")

            self.assertEqual((destination / "keep.txt").read_text(), "keep")

    def test_check_detects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.make_repo(root)
            codex_home = root / ".codex"
            destination = install_pet.install(repo, codex_home, "beta")
            (destination / "sprite.webp").write_bytes(b"changed")

            problems = install_pet.check(repo, codex_home, "beta")

            self.assertEqual(len(problems), 1)
            self.assertIn("differs from source", problems[0])

    def test_invalid_metadata_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.make_repo(root)
            metadata = repo / "pets" / "alpha" / "pet.json"
            data = json.loads(metadata.read_text(encoding="utf-8"))
            data["id"] = "wrong"
            metadata.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaises(install_pet.InstallError):
                install_pet.discover_pets(repo)


if __name__ == "__main__":
    unittest.main()
