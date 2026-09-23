#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

MODEL = "gpt-6-luna"
REASONING_EFFORT = "max"
SERVICE_TIER = "priority"
SANDBOX_MODE = "workspace-write"

WORKER_DEVELOPER_INSTRUCTIONS = """You are a bounded implementation worker delegated by a primary Codex session.

Follow the supplied implementation contract exactly. Preserve the user's intended outcome, scope, constraints, and completion evidence.

For each assignment:
1. Read the applicable AGENTS.md files and project instructions.
2. Inspect the actual execution path before editing.
3. Make the smallest complete and defensible change inside the assigned scope.
4. Preserve unrelated user or coworker changes and do not perform unrelated cleanup.
5. Run the most relevant available tests, linters, type checks, builds, or reproductions.
6. Inspect repository status and the relevant diff for accidental or unrelated changes.
7. Do not broaden product intent, select a different workflow, push, deploy, migrate, purchase, or mutate remote state.
8. Do not create or amend commits unless the implementation contract explicitly authorizes it.
9. Do not spawn or delegate to additional agents. Return to the primary when the bounded task is complete or blocked.
10. Stop and report evidence when a contradiction, hidden dependency, or materially larger scope prevents safe completion.

Return the behavioral result, changed files and rationale, validation commands and exit status, skipped validation and reasons, repository-state or diff concerns, remaining uncertainty, and blockers or contradictions.
"""


def toml_string(value: str) -> str:
    """Encode a Python string as a TOML-compatible basic string."""
    return json.dumps(value, ensure_ascii=False)


def build_command(codex_bin: str, cwd: Path, skip_git_repo_check: bool) -> list[str]:
    command = [
        codex_bin,
        "exec",
        "--strict-config",
        "--model",
        MODEL,
        "--sandbox",
        SANDBOX_MODE,
        "--cd",
        str(cwd),
        "-c",
        f'model_reasoning_effort={toml_string(REASONING_EFFORT)}',
        "-c",
        f'service_tier={toml_string(SERVICE_TIER)}',
        "-c",
        'approval_policy="never"',
        "-c",
        f'developer_instructions={toml_string(WORKER_DEVELOPER_INSTRUCTIONS)}',
    ]
    if skip_git_repo_check:
        command.append("--skip-git-repo-check")
    command.append("-")
    return command


def read_contract(positional: str | None) -> str:
    if positional not in (None, "-"):
        return positional
    if sys.stdin.isatty():
        raise ValueError("no delegation contract supplied; pass it as an argument or pipe it on stdin")
    contract = sys.stdin.read()
    if not contract.strip():
        raise ValueError("delegation contract is empty")
    return contract


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a bounded implementation worker in a separate Codex root session pinned to "
            "GPT-5.6 Luna, Max reasoning, Fast/priority tier, and workspace-write sandbox."
        )
    )
    parser.add_argument(
        "contract",
        nargs="?",
        help="delegation contract; use '-' or omit to read from stdin",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="worker repository root (default: current directory)",
    )
    parser.add_argument(
        "--codex-bin",
        default=os.environ.get("CODEX_BIN", "codex"),
        help="Codex executable (default: CODEX_BIN or 'codex')",
    )
    parser.add_argument(
        "--skip-git-repo-check",
        action="store_true",
        help="allow running outside a Git repository",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the exact argv as JSON and do not launch Codex",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cwd = args.cwd.expanduser().resolve(strict=False)
    if not cwd.is_dir():
        print(f"Worker launch failed: cwd is not a directory: {cwd}", file=sys.stderr)
        return 2

    try:
        contract = read_contract(args.contract)
    except ValueError as exc:
        print(f"Worker launch failed: {exc}", file=sys.stderr)
        return 2

    command = build_command(args.codex_bin, cwd, args.skip_git_repo_check)
    if args.dry_run:
        print(json.dumps(command, ensure_ascii=False))
        return 0

    if os.path.sep not in args.codex_bin and shutil.which(args.codex_bin) is None:
        print(f"Worker launch failed: Codex executable not found: {args.codex_bin}", file=sys.stderr)
        return 127

    try:
        completed = subprocess.run(
            command,
            input=contract,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print(f"Worker launch failed: Codex executable not found: {args.codex_bin}", file=sys.stderr)
        return 127
    except OSError as exc:
        print(f"Worker launch failed: {exc}", file=sys.stderr)
        return 1

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
