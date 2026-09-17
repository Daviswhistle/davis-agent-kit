# Dream-RSI Mini: Offline Delegation Replay

Use this only as an opt-in experiment for repeated, comparable agent-search or delegation work. It does not change the base model, launch agents, mutate a worktree, or replace the primary session's completion authority.

The experiment adapts the central idea from [Dream-RSI](https://arxiv.org/abs/2609.14858): treat completed search trees as replay environments, evaluate alternative exploration controllers without paying for new model calls, and carry only a controller policy into a later live run.

## What this experiment can answer

Given historical trees, `scripts/dream_rsi_replay.py` can compare policies for:

- breadth-first vs. depth-first vs. best-observed-parent exploration;
- how many recorded children to expose per visited node;
- maximum search depth;
- patience after non-improving attempts;
- a hard model/evaluator call budget.

The objective is:

```text
best observed quality
- call_penalty * recorded calls
- latency_penalty * recorded seconds
```

Quality must be a comparable numeric evaluator signal across the histories being compared. Do not mix unrelated scoring scales and interpret the resulting objective as meaningful.

## Trace format

One JSON file represents one completed historical tree:

```json
{
  "schema_version": 1,
  "run_id": "task-2026-09-17-a",
  "root_id": "root",
  "nodes": [
    {
      "id": "root",
      "parent_id": null,
      "children": ["plan-a", "plan-b"],
      "quality": 0.20,
      "calls": 0,
      "latency_ms": 0
    },
    {
      "id": "plan-a",
      "parent_id": "root",
      "children": ["plan-a-retry"],
      "quality": 0.55,
      "calls": 1,
      "latency_ms": 42000
    },
    {
      "id": "plan-b",
      "parent_id": "root",
      "children": [],
      "quality": 0.78,
      "calls": 1,
      "latency_ms": 39000,
      "terminal": true
    },
    {
      "id": "plan-a-retry",
      "parent_id": "plan-a",
      "children": [],
      "quality": 0.60,
      "calls": 1,
      "latency_ms": 41000,
      "terminal": true
    }
  ]
}
```

`children` order is part of the historical proposal order. A node's `quality` becomes observable only when that node is replayed. `calls` is treated as recorded cost metadata and may be used before visiting a node to test whether the action fits the hard call budget; `latency_ms` is charged after a node is visited. This cost-aware replay is valid for a live experiment only when an equivalent pre-action cost estimate is available; do not substitute post-hoc actual cost for an unavailable estimate. Unknown extra fields are preserved by the source trace but ignored by this v1 controller, so a recorder may attach provenance such as evaluator identity, failure class, workspace snapshot, ReasoningBank references, token usage, or artifact locations without changing replay semantics.

Each non-root node must have exactly one parent and must appear in that parent's `children` list. The helper rejects disconnected nodes, duplicate IDs, broken parent/child links, and cycles.

## Replay without hindsight leakage

The controller starts with only the root observed. Visiting a node reveals at most the first `branch_limit` children recorded for that node. It cannot rank children by their eventual quality before visiting them; recorded cost metadata is the explicit exception used for budget feasibility.

That boundary is deliberate. Reading every historical child score before choosing would turn replay into hindsight optimization rather than a simulation of what the controller could have known during the live run.

The replay is still not a full counterfactual world model: branches that were never generated in the original run do not exist in the simulator. Treat results as evidence about allocation among observed opportunities, not proof about unseen strategies.

## Commands

Replay one tree with an explicit policy:

```bash
python3 "$HOME/.agents/skills/software-engineering/scripts/dream_rsi_replay.py" replay history.json \
  --strategy breadth \
  --branch-limit 2 \
  --max-depth 4 \
  --patience 8 \
  --max-calls 32 \
  --call-penalty 0.01
```

Search a small deterministic policy grid on training histories and report a separate holdout comparison:

```bash
python3 "$HOME/.agents/skills/software-engineering/scripts/dream_rsi_replay.py" optimize \
  --train traces/train-1.json traces/train-2.json traces/train-3.json \
  --holdout traces/holdout-1.json traces/holdout-2.json \
  --strategy breadth \
  --branch-limit 2 \
  --max-depth 4 \
  --patience 8 \
  --max-calls 32 \
  --call-penalty 0.01 \
  --min-train-improvement 0.02
```

The explicit policy flags define the baseline. `optimize` searches only the controller grid; it does not generate new branches or run Codex. `--min-train-improvement` prevents a tiny training-only gain from replacing the baseline in the report.

## Promotion gate

Do not promote a replay-selected controller merely because training objective improved.

1. Keep complete live histories immutable.
2. Split by whole task/run, never by nodes from the same tree.
3. Select policy on training histories only.
4. Inspect holdout quality, calls, latency, failure modes and task comparability.
5. Reject a candidate that achieves its objective by materially lowering outcome quality unless that tradeoff was explicitly intended.
6. Run the candidate in shadow/recommendation mode before granting it authority to change live delegation.
7. Preserve the normal worker, CRA, TCA and primary-session safety boundaries.
8. Roll back to the baseline when evidence is sparse, stale, distribution-shifted or contradictory.

No policy produced by this helper authorizes extra model calls, parallel writers, broader product scope, remote mutation, deployment, purchases, or weaker validation.

## Relationship to reasoning memory

Reasoning memory and replay solve different problems:

- reasoning memory stores what was learned from an attempt;
- replay evaluates where a controller would have spent its next unit of search budget.

A future recorder can attach memory or ReasoningBank references to nodes, but this v1 experiment intentionally does not let those references alter replay decisions. That keeps the first A/B test about search allocation rather than mixing memory retrieval and controller changes in one experiment.
