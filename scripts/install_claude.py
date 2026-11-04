#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from install_codex import (
    InstallError,
    InstallResult,
    discover_skills,
    ensure_dir,
    managed_skill_link,
    preflight_link,
    same_link,
)

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
RULE_NAME = "davis-agent-kit.md"


def expected_links(repo_root: Path, claude_home: Path, skills: tuple[str, ...]) -> tuple[tuple[Path, Path, str], ...]:
    links = [(claude_home / "rules" / RULE_NAME, repo_root / "AGENTS.md", "global rule")]
    links.extend(
        (claude_home / "skills" / name, repo_root / "skills" / name, f"skill {name}")
        for name in skills
    )
    return tuple(links)


def stale_skill_links(repo_root: Path, claude_home: Path, active: tuple[str, ...]) -> list[Path]:
    skills_home = claude_home / "skills"
    if not skills_home.is_dir():
        return []
    return [
        path
        for path in skills_home.iterdir()
        if path.name not in active and managed_skill_link(path, repo_root)
    ]


def check(repo_root: Path, claude_home: Path) -> list[str]:
    skills = discover_skills(repo_root)
    problems: list[str] = []
    for path, target, label in expected_links(repo_root, claude_home, skills):
        if not same_link(path, target):
            problems.append(f"{label} is not the expected symlink: {path}")
    for path in stale_skill_links(repo_root, claude_home, skills):
        problems.append(f"obsolete kit skill link: {path}")
    return problems


def install(repo_root: Path, claude_home: Path) -> InstallResult:
    skills = discover_skills(repo_root)
    if not (repo_root / "AGENTS.md").is_file():
        raise InstallError(f"missing normative source: {repo_root / 'AGENTS.md'}")
    links = expected_links(repo_root, claude_home, skills)
    stale = stale_skill_links(repo_root, claude_home, skills)
    result = InstallResult()
    to_create = []
    # All conflicts are checked before touching the user's Claude files.
    for path, target, label in links:
        if preflight_link(path, target, label):
            to_create.append((path, target))
        else:
            result.messages.append(f"KEEP {path}")
    try:
        for path, _ in to_create:
            ensure_dir(path.parent, result)
        for path in stale:
            previous_target = os.readlink(path)
            path.unlink()
            result.removed_symlinks.append((path, previous_target))
            result.messages.append(f"REMOVE obsolete kit skill {path}")
        for path, target in to_create:
            path.symlink_to(target, target_is_directory=target.is_dir())
            result.created_links.append(path)
            result.messages.append(f"LINK {path} -> {target}")
        problems = check(repo_root, claude_home)
        if problems:
            raise InstallError("; ".join(problems))
    except (OSError, RuntimeError, InstallError):
        result.rollback()
        raise
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Davis Agent Kit rules and skills for Claude Code.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--claude-home", type=Path, default=Path(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude"))
    parser.add_argument("--check", action="store_true", help="verify the installation without changing it")
    args = parser.parse_args()
    repo_root = args.root.expanduser().resolve()
    claude_home = args.claude_home.expanduser().resolve(strict=False)
    try:
        if args.check:
            problems = check(repo_root, claude_home)
            if problems:
                for problem in problems:
                    print(f"FAIL: {problem}")
                return 1
            print("PASS: Davis Agent Kit Claude Code installation is correct")
            return 0
        result = install(repo_root, claude_home)
    except (InstallError, OSError, RuntimeError) as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        return 1
    for message in result.messages:
        print(message)
    print("Claude Code rules and skills are ready. Start a new local session to load them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
