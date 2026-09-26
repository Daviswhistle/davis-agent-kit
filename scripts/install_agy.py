#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from install_codex import InstallError, InstallResult, ensure_dir, preflight_link, same_link

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_HOME = Path("~/.gemini/antigravity-cli/rules")
RULE_NAME = "davis-agent-kit.md"


def expected_link(repo_root: Path, rules_home: Path) -> tuple[Path, Path]:
    return rules_home / RULE_NAME, repo_root / "providers" / "agy" / RULE_NAME


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

    create = preflight_link(path, target, "AGY global rule")
    result = InstallResult()
    if not create:
        result.messages.append(f"KEEP {path}")
        return result

    try:
        ensure_dir(rules_home, result)
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
        description="Install Davis Agent Kit quality guidance for Antigravity CLI (agy)."
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
