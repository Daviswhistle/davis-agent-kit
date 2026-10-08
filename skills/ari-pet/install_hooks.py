#!/usr/bin/env python3
"""Opt-in observational Codex hooks for the Ari pet skill.

The Davis Agent Kit installer owns skill installation. This program ONLY
merges/removes Ari's hook commands; it never installs or deletes the skill.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

EVENTS = {
    "SessionStart": "session",
    "UserPromptSubmit": "prompt",
    "PreToolUse": "tool",
    "PermissionRequest": "wait",
    "Stop": "stop",
    "Interrupt": "interrupt",
}


def default_hooks_path() -> Path:
    return Path(os.environ.get("CODEX_HOME") or "~/.codex").expanduser() / "hooks.json"


def quote(argv: list[str]) -> str:
    return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)


def command(skill_root: Path, action: str) -> str:
    return quote([sys.executable, str(skill_root / "ari.py"), "hook", action])


def is_ari_handler(value: object, skill_root: Path) -> bool:
    return (
        isinstance(value, dict)
        and value.get("type") == "command"
        and value.get("command") in {command(skill_root, action) for action in EVENTS.values()}
    )


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".ari-hooks-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(data, out, indent=2, ensure_ascii=False)
            out.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def merge_hooks(path: Path, skill_root: Path, uninstall: bool = False) -> int:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(existing, dict) or not isinstance(existing.get("hooks", {}), dict):
            raise ValueError("Unexpected hooks.json structure; file left unchanged")
    else:
        if uninstall:
            return 0
        existing = {}

    hooks = existing.setdefault("hooks", {})
    changed = 0
    for event, action in EVENTS.items():
        groups = hooks.get(event, [])
        if not isinstance(groups, list):
            raise ValueError(f"Unexpected hooks.json {event} structure; file left unchanged")
        result = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks", []), list):
                raise ValueError(f"Unexpected hooks.json {event} entry; file left unchanged")
            before = group.get("hooks", [])
            after = [item for item in before if not is_ari_handler(item, skill_root)]
            changed += len(before) - len(after)
            if after:
                result.append({**group, "hooks": after} if len(before) != len(after) else group)
            elif not before:
                result.append(group)
        if not uninstall:
            result.append({"hooks": [{"type": "command", "command": command(skill_root, action), "timeout": 10}]})
            changed += 1
        if result:
            hooks[event] = result
        else:
            hooks.pop(event, None)

    if not changed:
        return 0
    if path.exists():
        backup = path.with_name(f"hooks.json.ari-backup-{datetime.now():%Y%m%d-%H%M%S-%f}")
        shutil.copy2(path, backup)
        print(f"Backup: {backup}")
    atomic_json(path, existing)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enable/disable optional, passive Codex hooks for Ari")
    parser.add_argument("mode", choices=("enable", "disable"))
    parser.add_argument("--hooks-path", type=Path, default=default_hooks_path())
    parser.add_argument("--skill-root", type=Path, default=Path(__file__).absolute().parent)
    args = parser.parse_args(argv)
    root = args.skill_root.expanduser().absolute()
    if args.mode == "enable" and not (root / "ari.py").is_file():
        parser.error(f"ari.py not found: {root}")
    updated = merge_hooks(args.hooks_path.expanduser(), root, uninstall=args.mode == "disable")
    print(f"Ari hook entries {'enabled' if args.mode == 'enable' else 'removed'}: {updated}")
    print("Codex may request review/trust via /hooks; restart Codex to apply.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ari hooks: {exc}", file=sys.stderr)
        raise SystemExit(1)
