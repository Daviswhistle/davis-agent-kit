#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from install_codex import InstallError, InstallResult, ensure_dir, preflight_link, same_link

DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def expected_link(repo_root: Path, gemini_home: Path) -> tuple[Path, Path]:
    return gemini_home / "GEMINI.md", repo_root / "providers" / "gemini" / "GEMINI.md"


def check(repo_root: Path, gemini_home: Path) -> list[str]:
    path, target = expected_link(repo_root, gemini_home)
    problems = []
    if not target.is_file():
        problems.append(f"missing Gemini guidance source: {target}")
    if not same_link(path, target):
        problems.append(f"global GEMINI.md is not the expected symlink: {path}")
    return problems


def install(repo_root: Path, gemini_home: Path) -> InstallResult:
    path, target = expected_link(repo_root, gemini_home)
    if not target.is_file():
        raise InstallError(f"missing Gemini guidance source: {target}")

    create = preflight_link(path, target, "global GEMINI.md")
    result = InstallResult()
    if not create:
        result.messages.append(f"KEEP {path}")
        return result

    try:
        ensure_dir(gemini_home, result)
        path.symlink_to(target)
        result.created_links.append(path)
        result.messages.append(f"LINK {path} -> {target}")
        problems = check(repo_root, gemini_home)
        if problems:
            raise InstallError("; ".join(problems))
    except (OSError, RuntimeError, InstallError):
        result.rollback()
        raise

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install Davis Agent Kit Gemini quality guidance."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--gemini-home",
        type=Path,
        default=Path(os.environ.get("GEMINI_HOME") or "~/.gemini"),
        help="Gemini CLI user home (default: GEMINI_HOME or ~/.gemini)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the global GEMINI.md link without changing it",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.root.expanduser().resolve()
    gemini_home = args.gemini_home.expanduser().resolve(strict=False)

    try:
        if args.check:
            problems = check(repo_root, gemini_home)
            if problems:
                for problem in problems:
                    print(f"FAIL: {problem}")
                return 1
            print("PASS: Davis Agent Kit Gemini guidance link is correct")
            return 0
        result = install(repo_root, gemini_home)
    except (InstallError, OSError, RuntimeError) as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        return 1

    for message in result.messages:
        print(message)
    print("Gemini guidance is ready.")
    print("Start a new Gemini CLI session or run /memory reload to load it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
