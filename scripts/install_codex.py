#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import sys

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
RETIRED_SKILLS = ("davis-operating-system", "coding-workflow", "outcome-owner")


class InstallError(RuntimeError):
    pass


def path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def same_link(path: Path, target: Path) -> bool:
    if not path.is_symlink():
        return False
    try:
        return path.resolve(strict=True).samefile(target.resolve(strict=True))
    except (OSError, RuntimeError):
        return False


def same_tree(path: Path, target: Path) -> bool:
    if path.is_symlink() or target.is_symlink() or not path.is_dir() or not target.is_dir():
        return False

    def files(root: Path) -> dict[str, bytes]:
        return {
            item.relative_to(root).as_posix(): item.read_bytes()
            for item in sorted(root.rglob("*"))
            if item.is_file() and not item.is_symlink()
        }

    try:
        return files(path) == files(target)
    except OSError:
        return False


def discover_skills(repo_root: Path) -> tuple[str, ...]:
    skills_root = repo_root / "skills"
    names = []
    for entrypoint in sorted(skills_root.glob("*/SKILL.md")):
        name = entrypoint.parent.name
        if name in RETIRED_SKILLS:
            raise InstallError(f"retired skill is present in source tree: {name}")
        names.append(name)
    if not names:
        raise InstallError(f"no skills found under {skills_root}")
    return tuple(names)


def discover_pets(repo_root: Path) -> tuple[str, ...]:
    pets_root = repo_root / "pets"
    if not pets_root.is_dir():
        return ()

    names = []
    for directory in sorted(path for path in pets_root.iterdir() if path.is_dir()):
        metadata_path = directory / "pet.json"
        if not metadata_path.is_file():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise InstallError(f"cannot read {metadata_path}: {exc}") from exc
        if not isinstance(metadata, dict):
            raise InstallError(f"{metadata_path}: metadata must be a JSON object")
        if metadata.get("id") != directory.name:
            raise InstallError(f"{metadata_path}: id must match directory name {directory.name!r}")
        spritesheet = metadata.get("spritesheetPath")
        if not isinstance(spritesheet, str) or not spritesheet:
            raise InstallError(f"{metadata_path}: missing non-empty spritesheetPath")
        sprite_path = Path(spritesheet)
        if sprite_path.is_absolute() or ".." in sprite_path.parts:
            raise InstallError(f"{metadata_path}: unsafe spritesheetPath {spritesheet!r}")
        if not (directory / sprite_path).is_file():
            raise InstallError(f"{metadata_path}: missing spritesheet {spritesheet!r}")
        names.append(directory.name)
    return tuple(names)


@dataclass
class InstallResult:
    messages: list[str] = field(default_factory=list)
    created_links: list[Path] = field(default_factory=list)
    created_dirs: list[Path] = field(default_factory=list)

    def rollback(self) -> None:
        for path in reversed(self.created_links):
            try:
                if path.is_symlink():
                    path.unlink()
            except OSError:
                pass
        for path in reversed(self.created_dirs):
            try:
                path.rmdir()
            except OSError:
                pass


def ensure_dir(path: Path, result: InstallResult) -> None:
    if path_exists(path):
        if not path.is_dir():
            raise InstallError(f"not a directory: {path}")
        return
    missing = []
    current = path
    while not path_exists(current):
        missing.append(current)
        if current.parent == current:
            break
        current = current.parent
    if path_exists(current) and not current.is_dir():
        raise InstallError(f"not a directory: {current}")
    for directory in reversed(missing):
        directory.mkdir()
        result.created_dirs.append(directory)


def preflight_link(path: Path, target: Path, label: str) -> bool:
    if not path_exists(path):
        return True
    if same_link(path, target):
        return False
    raise InstallError(f"{label} conflicts with existing path: {path}")


def preflight_pet(path: Path, target: Path, label: str) -> bool:
    if not path_exists(path):
        return True
    if same_link(path, target) or same_tree(path, target):
        return False
    raise InstallError(f"{label} conflicts with existing path: {path}")


def legacy_conflicts(codex_home: Path, names: tuple[str, ...]) -> list[Path]:
    legacy_root = codex_home / "skills"
    if not legacy_root.is_dir():
        return []
    conflicts = []
    for name in (*names, *RETIRED_SKILLS):
        path = legacy_root / name
        if path_exists(path):
            conflicts.append(path)
    return conflicts


def retired_conflicts(skills_home: Path) -> list[Path]:
    return [
        skills_home / name
        for name in RETIRED_SKILLS
        if path_exists(skills_home / name)
    ]


def expected_links(
    repo_root: Path,
    codex_home: Path,
    skills_home: Path,
    skills: tuple[str, ...],
) -> tuple[tuple[Path, Path, str], ...]:
    links = [
        (codex_home / "AGENTS.md", repo_root / "AGENTS.md", "global AGENTS.md"),
    ]
    links.extend(
        (skills_home / name, repo_root / "skills" / name, f"skill {name}")
        for name in skills
    )
    return tuple(links)


def expected_pets(
    repo_root: Path,
    codex_home: Path,
    pets: tuple[str, ...],
) -> tuple[tuple[Path, Path, str], ...]:
    return tuple(
        (codex_home / "pets" / name, repo_root / "pets" / name, f"pet {name}")
        for name in pets
    )


def global_guidance_problem(repo_root: Path, codex_home: Path) -> str | None:
    """Check global override precedence without modifying the user's override."""
    override = codex_home / "AGENTS.override.md"
    try:
        if not path_exists(override):
            return None
        if not override.is_file():
            return f"cannot verify global instruction selection: not a readable file: {override}"
        if not override.read_text(encoding="utf-8").strip():
            return None
        if override.samefile(repo_root / "AGENTS.md"):
            return None
    except (OSError, UnicodeError, RuntimeError) as exc:
        return f"cannot verify global instruction selection at {override}: {exc}"
    return (
        f"global AGENTS.md is shadowed by non-empty override: {override}; "
        "Codex selects that file instead of the kit's global instructions. "
        "Review the override and move or merge it manually before retrying; "
        "the installer leaves it unchanged."
    )


def check(repo_root: Path, codex_home: Path, skills_home: Path) -> list[str]:
    skills = discover_skills(repo_root)
    pets = discover_pets(repo_root)
    problems = []
    if not (repo_root / "AGENTS.md").is_file():
        problems.append(f"missing normative source: {repo_root / 'AGENTS.md'}")
    for path in legacy_conflicts(codex_home, skills):
        problems.append(f"legacy Codex skill still installed: {path}")
    for path in retired_conflicts(skills_home):
        problems.append(f"retired skill still installed: {path}")
    for path, target, label in expected_links(repo_root, codex_home, skills_home, skills):
        if not same_link(path, target):
            problems.append(f"{label} is not the expected symlink: {path}")
    for path, target, label in expected_pets(repo_root, codex_home, pets):
        if not (same_link(path, target) or same_tree(path, target)):
            problems.append(f"{label} is not installed from this kit: {path}")
    guidance_problem = global_guidance_problem(repo_root, codex_home)
    if guidance_problem:
        problems.append(guidance_problem)
    return problems


def install(repo_root: Path, codex_home: Path, skills_home: Path) -> InstallResult:
    skills = discover_skills(repo_root)
    pets = discover_pets(repo_root)
    if not (repo_root / "AGENTS.md").is_file():
        raise InstallError(f"missing normative source: {repo_root / 'AGENTS.md'}")

    guidance_problem = global_guidance_problem(repo_root, codex_home)
    if guidance_problem:
        raise InstallError(guidance_problem)

    legacy = legacy_conflicts(codex_home, skills)
    if legacy:
        joined = ", ".join(str(path) for path in legacy)
        raise InstallError(
            "legacy $CODEX_HOME/skills entries still load in Codex; "
            f"remove these old kit links before migration: {joined}"
        )

    retired = retired_conflicts(skills_home)
    if retired:
        joined = ", ".join(str(path) for path in retired)
        raise InstallError(f"retired skill still installed: {joined}")

    links = expected_links(repo_root, codex_home, skills_home, skills)
    pet_links = expected_pets(repo_root, codex_home, pets)
    to_create = []
    result = InstallResult()
    for path, target, label in links:
        if preflight_link(path, target, label):
            to_create.append((path, target))
        else:
            result.messages.append(f"KEEP {path}")
    for path, target, label in pet_links:
        if preflight_pet(path, target, label):
            to_create.append((path, target))
        else:
            result.messages.append(f"KEEP {path}")

    try:
        ensure_dir(codex_home, result)
        ensure_dir(skills_home, result)
        if pets:
            ensure_dir(codex_home / "pets", result)
        for path, target in to_create:
            path.symlink_to(target, target_is_directory=target.is_dir())
            result.created_links.append(path)
            result.messages.append(f"LINK {path} -> {target}")
        problems = check(repo_root, codex_home, skills_home)
        if problems:
            raise InstallError("; ".join(problems))
    except (OSError, RuntimeError, InstallError):
        result.rollback()
        raise

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install Davis Agent Kit global instructions, user skills, and custom pets."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME") or "~/.codex"),
        help="global AGENTS/config/pets home (default: CODEX_HOME or ~/.codex)",
    )
    parser.add_argument(
        "--skills-home",
        type=Path,
        default=Path("~/.agents/skills"),
        help="Codex user skills root (default: ~/.agents/skills)",
    )
    parser.add_argument("--check", action="store_true", help="verify the installed kit without changing it")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.root.expanduser().resolve()
    codex_home = args.codex_home.expanduser().resolve(strict=False)
    skills_home = args.skills_home.expanduser().resolve(strict=False)

    try:
        if args.check:
            problems = check(repo_root, codex_home, skills_home)
            if problems:
                for problem in problems:
                    print(f"FAIL: {problem}")
                return 1
            print("PASS: Davis Agent Kit installation is correct")
            print("PASS: kit global instructions are not shadowed by an override")
            return 0

        result = install(repo_root, codex_home, skills_home)
    except (InstallError, OSError, RuntimeError) as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        return 1

    for message in result.messages:
        print(message)
    print("Codex instructions, skills, and pets are ready.")
    print("Restart Codex or start a new session to load the changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
