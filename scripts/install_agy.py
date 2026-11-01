#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from install_codex import (
    InstallError,
    InstallResult,
    ensure_dir,
    path_exists,
    same_link,
)

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_HOME = Path("~/.gemini/antigravity-cli/rules")
RULE_NAME = "davis-agent-kit.md"
RULE_HEADING = "# Davis Agent Kit"


def expected_link(repo_root: Path, rules_home: Path) -> tuple[Path, Path]:
    return rules_home / RULE_NAME, repo_root / "providers" / "agy" / RULE_NAME


def is_kit_rule_copy(path: Path) -> bool:
    """Recognize a copied kit rule while leaving unrelated user rules alone."""
    if path.is_symlink() or not path.is_file():
        return False
    try:
        heading = path.open(encoding="utf-8").readline().strip()
    except (OSError, UnicodeError):
        return False
    return heading.startswith(RULE_HEADING) and ("AGY" in heading or "Antigravity" in heading)


def is_previous_kit_link(path: Path) -> bool:
    """Re-link rules pointing into another/removed checkout of this kit."""
    if not path.is_symlink():
        return False
    try:
        target = (path.parent / os.readlink(path)).resolve(strict=False)
    except (OSError, RuntimeError):
        return False
    return (
        target.name == RULE_NAME
        and target.parent.name == "agy"
        and target.parent.parent.name == "providers"
    )


def install_action(path: Path, target: Path) -> str:
    if not path_exists(path):
        return "create"
    if same_link(path, target):
        return "keep"
    if is_previous_kit_link(path):
        return "relink"
    if is_kit_rule_copy(path):
        return "backup-copy"
    raise InstallError(
        f"AGY global rule conflicts with an unmanaged existing path: {path}. "
        "Review it manually; the installer will not overwrite it."
    )


def backup_path(rules_home: Path) -> Path:
    """Keep old rules outside AGY's active rules directory."""
    backup_root = rules_home.parent / ".davis-agent-kit-backups" / "agy"
    candidate = backup_root / RULE_NAME
    number = 2
    while path_exists(candidate):
        candidate = backup_root / f"davis-agent-kit-{number}.md"
        number += 1
    return candidate


def check(repo_root: Path, rules_home: Path) -> list[str]:
    path, target = expected_link(repo_root, rules_home)
    problems = []
    if not target.is_file():
        problems.append(f"missing AGY guidance source: {target}")
    if not same_link(path, target):
        problems.append(f"AGY global rule is not the expected symlink: {path}")
    return problems


def install(repo_root: Path, rules_home: Path) -> InstallResult:
    path, target = expected_link(repo_root, rules_home)
    if not target.is_file():
        raise InstallError(f"missing AGY guidance source: {target}")

    action = install_action(path, target)
    result = InstallResult()
    if action == "keep":
        result.messages.append(f"KEEP {path}")
        return result

    try:
        ensure_dir(rules_home, result)
        if action == "backup-copy":
            backup = backup_path(rules_home)
            ensure_dir(backup.parent, result)
            path.rename(backup)
            # InstallResult's path-move rollback works for files as well.
            result.moved_directories.append((path, backup))
            result.messages.append(f"BACKUP old AGY rule {path} -> {backup}")
        elif action == "relink":
            previous_target = os.readlink(path)
            path.unlink()
            result.removed_symlinks.append((path, previous_target))
            result.messages.append(f"RELINK outdated AGY rule {path}")

        path.symlink_to(target)
        result.created_links.append(path)
        result.messages.append(f"LINK {path} -> {target}")
        problems = check(repo_root, rules_home)
        if problems:
            raise InstallError("; ".join(problems))
    except (OSError, RuntimeError, InstallError):
        result.rollback()
        raise

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install or update Davis Agent Kit quality guidance for Antigravity CLI (agy)."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--rules-home",
        type=Path,
        default=DEFAULT_RULES_HOME,
        help="AGY global rules directory (default: ~/.gemini/antigravity-cli/rules)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the AGY global rule link without changing it",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.root.expanduser().resolve()
    rules_home = args.rules_home.expanduser().resolve(strict=False)

    try:
        if args.check:
            problems = check(repo_root, rules_home)
            if problems:
                for problem in problems:
                    print(f"FAIL: {problem}")
                return 1
            print("PASS: Davis Agent Kit AGY rule link is correct")
            return 0
        result = install(repo_root, rules_home)
    except (InstallError, OSError, RuntimeError) as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        return 1

    for message in result.messages:
        print(message)
    print("AGY guidance is ready.")
    print("Start a new agy session to load the rule.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
