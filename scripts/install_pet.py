#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import sys

DEFAULT_ROOT = Path(__file__).resolve().parents[1]


class InstallError(RuntimeError):
    pass


@dataclass(frozen=True)
class Pet:
    pet_id: str
    display_name: str
    description: str
    source: Path


def _read_pet(directory: Path) -> Pet:
    metadata_path = directory / "pet.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InstallError(f"cannot read {metadata_path}: {exc}") from exc

    if not isinstance(metadata, dict):
        raise InstallError(f"{metadata_path}: metadata must be a JSON object")

    pet_id = metadata.get("id")
    display_name = metadata.get("displayName")
    description = metadata.get("description")
    spritesheet = metadata.get("spritesheetPath")

    if not isinstance(pet_id, str) or not pet_id:
        raise InstallError(f"{metadata_path}: missing non-empty id")
    if pet_id != directory.name:
        raise InstallError(
            f"{metadata_path}: id {pet_id!r} must match directory {directory.name!r}"
        )
    if not isinstance(display_name, str) or not display_name:
        raise InstallError(f"{metadata_path}: missing non-empty displayName")
    if not isinstance(description, str) or not description:
        raise InstallError(f"{metadata_path}: missing non-empty description")
    if not isinstance(spritesheet, str) or not spritesheet:
        raise InstallError(f"{metadata_path}: missing non-empty spritesheetPath")

    sprite_path = Path(spritesheet)
    if sprite_path.is_absolute() or ".." in sprite_path.parts:
        raise InstallError(f"{metadata_path}: unsafe spritesheetPath {spritesheet!r}")
    if not (directory / sprite_path).is_file():
        raise InstallError(f"{metadata_path}: missing spritesheet {spritesheet!r}")

    return Pet(pet_id, display_name, description, directory)


def discover_pets(repo_root: Path) -> list[Pet]:
    pets_root = repo_root / "pets"
    if not pets_root.is_dir():
        raise InstallError(f"missing pets directory: {pets_root}")

    pets = []
    for directory in sorted(path for path in pets_root.iterdir() if path.is_dir()):
        if (directory / "pet.json").is_file():
            pets.append(_read_pet(directory))

    if not pets:
        raise InstallError(f"no custom pets found in {pets_root}")
    return pets


def get_pet(repo_root: Path, pet_id: str) -> Pet:
    for pet in discover_pets(repo_root):
        if pet.pet_id == pet_id:
            return pet
    available = ", ".join(pet.pet_id for pet in discover_pets(repo_root))
    raise InstallError(f"unknown pet {pet_id!r}; available: {available}")


def _files(root: Path) -> dict[str, bytes]:
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def check(repo_root: Path, codex_home: Path, pet_id: str) -> list[str]:
    pet = get_pet(repo_root, pet_id)
    destination = codex_home / "pets" / pet.pet_id
    if not destination.is_dir():
        return [f"missing installed pet: {destination}"]
    if _files(destination) != _files(pet.source):
        return [f"installed pet differs from source: {destination}"]
    return []


def install(repo_root: Path, codex_home: Path, pet_id: str) -> Path:
    pet = get_pet(repo_root, pet_id)
    destination = codex_home / "pets" / pet.pet_id

    if destination.exists() or destination.is_symlink():
        problems = check(repo_root, codex_home, pet_id)
        if problems:
            raise InstallError(
                f"{destination} already exists and differs from the kit; "
                "remove or rename it before installing"
            )
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pet.source, destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List, install, or check Davis Agent Kit Codex custom pets."
    )
    parser.add_argument("pet_id", nargs="?", help="pet id, for example mochi")
    parser.add_argument("--list", action="store_true", help="list available pets")
    parser.add_argument("--check", action="store_true", help="check an installed pet")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
    )
    args = parser.parse_args()

    repo_root = args.root.expanduser().resolve()
    codex_home = args.codex_home.expanduser().resolve()

    try:
        if args.list:
            if args.pet_id or args.check:
                parser.error("--list cannot be combined with pet_id or --check")
            for pet in discover_pets(repo_root):
                print(f"{pet.pet_id}\t{pet.display_name}\t{pet.description}")
            return 0

        if not args.pet_id:
            parser.error("pet_id is required unless --list is used")

        if args.check:
            problems = check(repo_root, codex_home, args.pet_id)
            if problems:
                for problem in problems:
                    print(f"[FAIL] {problem}")
                return 1
            print(f"[PASS] {args.pet_id}")
            return 0

        destination = install(repo_root, codex_home, args.pet_id)
        print(f"Installed {args.pet_id} -> {destination}")
        return 0
    except InstallError as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
