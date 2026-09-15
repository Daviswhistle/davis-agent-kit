#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Sequence

REVIEW_MODEL = "gpt-6-astra"
REASONING_EFFORT = "high"
SERVICE_TIER = "default"
SANDBOX_MODE = "read-only"
DELEGATE_SCHEMA_VERSION = "1"
RULE_BATCH_SIZE = 50

SHADOW_DEVELOPER_INSTRUCTIONS = """You are an independent shadow code reviewer in an A/B experiment.

The target is one clean non-merge commit at repository HEAD. OpenCodeReview (OCR) is used only for deterministic file selection and rule resolution; you perform the actual review with your own reasoning and read-only repository tools.

Review every OCR-selected file against the target commit's parent. You may inspect excluded or unchanged files only as context, not as additional review targets. Do not edit files, amend commits, change configuration, or perform remote mutations.

Report only actionable defects introduced by the target change: correctness regressions, security or data-loss risks, concurrency/state errors, broken interfaces/contracts, or incorrect assumptions that can affect real behavior. Suppress style nits, preference-only suggestions, speculative future concerns, and pre-existing or out-of-scope problems.

For each finding use this shape:
[P0|P1|P2|P3] <short title> — <path>:<start>-<end>
<concise evidence and impact>

Use the narrowest useful line range. If there are no valid findings, output exactly: No findings.
"""


class ExperimentError(RuntimeError):
    pass


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def executable_available(value: str) -> bool:
    if os.path.sep in value or (os.path.altsep and os.path.altsep in value):
        return Path(value).is_file()
    return shutil.which(value) is not None


def run_text(
    command: Sequence[str],
    *,
    cwd: Path,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            cwd=cwd,
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ExperimentError(f"executable not found: {command[0]}") from exc
    except OSError as exc:
        raise ExperimentError(f"failed to run {command[0]}: {exc}") from exc


def require_success(completed: subprocess.CompletedProcess[str], label: str) -> str:
    if completed.returncode == 0:
        return completed.stdout
    detail = completed.stderr.strip() or completed.stdout.strip() or "no output"
    raise ExperimentError(f"{label} failed with exit {completed.returncode}: {detail}")


def git_output(git_bin: str, cwd: Path, *args: str) -> str:
    completed = run_text([git_bin, *args], cwd=cwd)
    return require_success(completed, f"git {' '.join(args)}").strip()


def validate_target(git_bin: str, cwd: Path, commit: str) -> str:
    root = Path(git_output(git_bin, cwd, "rev-parse", "--show-toplevel")).resolve(strict=False)
    if root != cwd:
        raise ExperimentError(f"cwd must be the repository root: expected {root}, got {cwd}")

    resolved = git_output(git_bin, cwd, "rev-parse", "--verify", f"{commit}^{{commit}}")
    head = git_output(git_bin, cwd, "rev-parse", "HEAD")
    if resolved != head:
        raise ExperimentError(
            "shadow review requires the target commit to be the current HEAD so the reviewer "
            "cannot observe a different checkout"
        )

    parents = git_output(git_bin, cwd, "rev-list", "--parents", "-n", "1", resolved).split()
    if len(parents) != 2:
        raise ExperimentError("shadow review requires one non-merge commit with exactly one parent")

    status = git_output(git_bin, cwd, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise ExperimentError("shadow review requires a clean worktree")
    return resolved


def build_preview_command(ocr_bin: str, cwd: Path, commit: str) -> list[str]:
    return [
        ocr_bin,
        "delegate",
        "preview",
        "--repo",
        str(cwd),
        "--commit",
        commit,
        "--format",
        "json",
    ]


def build_rule_command(ocr_bin: str, cwd: Path, commit: str, paths: Sequence[str]) -> list[str]:
    return [
        ocr_bin,
        "delegate",
        "rule",
        "--repo",
        str(cwd),
        "--commit",
        commit,
        "--format",
        "json",
        *paths,
    ]


def build_codex_command(codex_bin: str, cwd: Path) -> list[str]:
    return [
        codex_bin,
        "exec",
        "--strict-config",
        "--model",
        REVIEW_MODEL,
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
        "features.fast_mode=false",
        "-c",
        f'developer_instructions={toml_string(SHADOW_DEVELOPER_INSTRUCTIONS)}',
        "-",
    ]


def parse_json_output(raw: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExperimentError(f"{label} returned invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ExperimentError(f"{label} returned a non-object JSON value")
    if value.get("schema_version") != DELEGATE_SCHEMA_VERSION:
        raise ExperimentError(
            f"{label} schema mismatch: expected {DELEGATE_SCHEMA_VERSION}, "
            f"got {value.get('schema_version')!r}"
        )
    return value


def load_preview(ocr_bin: str, cwd: Path, commit: str) -> dict[str, Any]:
    raw = require_success(
        run_text(build_preview_command(ocr_bin, cwd, commit), cwd=cwd),
        "ocr delegate preview",
    )
    preview = parse_json_output(raw, "ocr delegate preview")
    if preview.get("mode") != "commit":
        raise ExperimentError(f"ocr delegate preview returned unexpected mode: {preview.get('mode')!r}")
    reported_commit = preview.get("commit")
    if reported_commit not in (None, commit):
        raise ExperimentError(
            f"ocr delegate preview returned unexpected commit: {reported_commit!r}"
        )
    return preview


def batched(values: Sequence[str], size: int = RULE_BATCH_SIZE) -> list[list[str]]:
    if size < 1:
        raise ValueError("batch size must be positive")
    return [list(values[index:index + size]) for index in range(0, len(values), size)]


def load_rule_batches(
    ocr_bin: str,
    cwd: Path,
    commit: str,
    paths: Sequence[str],
) -> list[dict[str, Any]]:
    batches = []
    for path_batch in batched(paths):
        raw = require_success(
            run_text(build_rule_command(ocr_bin, cwd, commit, path_batch), cwd=cwd),
            "ocr delegate rule",
        )
        batches.append(parse_json_output(raw, "ocr delegate rule"))
    return batches


def reviewable_paths(preview: dict[str, Any]) -> list[str]:
    files = preview.get("reviewable_files")
    if not isinstance(files, list):
        raise ExperimentError("ocr delegate preview is missing reviewable_files")
    paths: list[str] = []
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ExperimentError("ocr delegate preview contains an invalid reviewable file entry")
        paths.append(entry["path"])
    return paths


def validate_rule_coverage(paths: Sequence[str], rule_batches: Sequence[dict[str, Any]]) -> None:
    covered: set[str] = set()
    for batch in rule_batches:
        groups = batch.get("groups")
        if not isinstance(groups, list):
            raise ExperimentError("ocr delegate rule is missing groups")
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("files"), list):
                raise ExperimentError("ocr delegate rule contains an invalid rule group")
            for path in group["files"]:
                if isinstance(path, str):
                    covered.add(path)
    missing = [path for path in paths if path not in covered]
    if missing:
        raise ExperimentError(f"ocr delegate rule did not resolve rules for: {', '.join(missing)}")


def build_prompt(commit: str, preview: dict[str, Any], rule_batches: Sequence[dict[str, Any]]) -> str:
    packet = {
        "target_commit": commit,
        "preview": preview,
        "rule_batches": list(rule_batches),
    }
    packet_json = json.dumps(packet, ensure_ascii=False, indent=2)
    return f"""Review the exact commit {commit} against its single parent.

Use read-only Git commands such as `git show` and `git diff {commit}^ {commit}` to inspect the exact patch and any necessary repository context. OCR's deterministic selection and resolved rules are supplied below. Treat the selected files as the review boundary and apply the matching rule content to each selected file.

OCR review packet:
```json
{packet_json}
```

Return only findings in the required shadow-review format, ordered by severity. If none are valid, output exactly `No findings.`
"""


def render_report(
    *,
    commit: str,
    preview: dict[str, Any],
    elapsed_seconds: float,
    review: str,
) -> str:
    selected = reviewable_paths(preview)
    excluded = preview.get("excluded_files")
    excluded_count = len(excluded) if isinstance(excluded, list) else preview.get("excluded_count", "?")
    selected_lines = "\n".join(f"- `{path}`" for path in selected) or "- none"
    if isinstance(excluded, list):
        excluded_lines = "\n".join(
            f"- `{entry.get('path', '?')}` — `{entry.get('exclude_reason', 'unknown')}`"
            for entry in excluded
            if isinstance(entry, dict)
        ) or "- none"
    else:
        excluded_lines = "- unavailable"
    body = review.strip() or "(reviewer returned no text)"
    return (
        "# OCR Shadow Review\n\n"
        f"- commit: `{commit}`\n"
        f"- reviewer: `{REVIEW_MODEL}` / `{REASONING_EFFORT}` / `{SERVICE_TIER}`\n"
        f"- OCR delegate schema: `{DELEGATE_SCHEMA_VERSION}`\n"
        f"- selected files: {len(selected)}\n"
        f"- excluded files: {excluded_count}\n"
        f"- wall time: {elapsed_seconds:.2f}s\n\n"
        "## Selected files\n\n"
        f"{selected_lines}\n\n"
        "## Excluded files\n\n"
        f"{excluded_lines}\n\n"
        "## Shadow findings\n\n"
        f"{body}\n"
    )


def resolve_output(output: Path | None, cwd: Path) -> Path | None:
    if output is None:
        return None
    resolved = output.expanduser().resolve(strict=False)
    try:
        resolved.relative_to(cwd)
    except ValueError:
        return resolved
    raise ExperimentError("output must be outside the repository so the experiment leaves the worktree unchanged")


def write_report(report: str, output: Path | None) -> None:
    if output is None:
        print(report, end="")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"OCR shadow review written to {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run an opt-in OpenCodeReview delegation shadow review without changing the native CRA workflow."
        )
    )
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument("--commit", default="HEAD", help="target commit (must resolve to current HEAD)")
    parser.add_argument("--git-bin", default=os.environ.get("GIT_BIN", "git"))
    parser.add_argument("--ocr-bin", default=os.environ.get("OCR_BIN", "ocr"))
    parser.add_argument("--codex-bin", default=os.environ.get("CODEX_BIN", "codex"))
    parser.add_argument("--output", type=Path, help="optional Markdown report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cwd = args.cwd.expanduser().resolve(strict=False)
    if not cwd.is_dir():
        print(f"OCR shadow review failed: cwd is not a directory: {cwd}", file=sys.stderr)
        return 2

    for label, executable in (("git", args.git_bin), ("ocr", args.ocr_bin), ("codex", args.codex_bin)):
        if not executable_available(executable):
            print(f"OCR shadow review failed: {label} executable not found: {executable}", file=sys.stderr)
            return 127

    try:
        output = resolve_output(args.output, cwd)
        commit = validate_target(args.git_bin, cwd, args.commit)
        started = time.monotonic()
        preview = load_preview(args.ocr_bin, cwd, commit)
        paths = reviewable_paths(preview)
        if not paths:
            elapsed = time.monotonic() - started
            report = render_report(
                commit=commit,
                preview=preview,
                elapsed_seconds=elapsed,
                review="Shadow reviewer not run: OCR selected no reviewable files.",
            )
            write_report(report, output)
            return 0

        rules = load_rule_batches(args.ocr_bin, cwd, commit, paths)
        validate_rule_coverage(paths, rules)
        prompt = build_prompt(commit, preview, rules)
        command = build_codex_command(args.codex_bin, cwd)
        completed = run_text(command, cwd=cwd, input_text=prompt)
        elapsed = time.monotonic() - started
        review = require_success(completed, "codex OCR shadow review")
        report = render_report(
            commit=commit,
            preview=preview,
            elapsed_seconds=elapsed,
            review=review,
        )
        write_report(report, output)
        return 0
    except ExperimentError as exc:
        print(f"OCR shadow review failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
