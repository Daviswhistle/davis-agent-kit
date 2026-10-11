# Implementation Worker Launch

Use this only when the software resource choice requires a separate Codex root for the bounded implementation role.

Native Codex subagents inherit the root session's service tier. If the primary must stay on default/non-Fast while the bounded implementation worker uses the software candidate `gpt-6-luna`, Max reasoning and Fast/priority, launch that worker through `scripts/run_luna_worker.py` instead of relying on a child-level tier override. The helper pins `workspace-write`, `approval_policy=never`, and uses `--strict-config` so unsupported settings fail rather than silently downgrade.

Provide the bounded task, source baseline, writable worktree, excluded actions and required local checks. Require changed files, commands with exit statuses, artifact locations and blockers in the return. Pass this handoff on stdin so shell quoting does not alter it:

```bash
python3 "$HOME/.agents/skills/software-engineering/scripts/run_luna_worker.py" --cwd "$PWD" <<'CONTRACT'
<bounded implementation task, baseline, write boundary, authority and required checks>
CONTRACT
```

Wait for this writer to exit before another writer edits the same Git worktree. Inspect the actual diff and local evidence afterward. Because this is a nested `codex exec`, do not bypass a blocked network or sandbox boundary to force delegation. Report an unavailable launcher or context instead of claiming that the worker or requested settings ran.
