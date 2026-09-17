#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import itertools
import json
from pathlib import Path
import statistics
import sys
from typing import Iterable, Sequence

SCHEMA_VERSION = 1
STRATEGIES = ("breadth", "depth", "best-parent")


@dataclass(frozen=True)
class Policy:
    strategy: str = "breadth"
    branch_limit: int = 2
    max_depth: int = 4
    patience: int = 8
    max_calls: int = 32

    def validate(self) -> None:
        if self.strategy not in STRATEGIES:
            raise ValueError(f"unsupported strategy: {self.strategy}")
        for name in ("branch_limit", "max_depth", "patience", "max_calls"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be >= 1")


@dataclass(frozen=True)
class Node:
    node_id: str
    parent_id: str | None
    children: tuple[str, ...]
    quality: float
    calls: int
    latency_ms: float
    terminal: bool = False


@dataclass(frozen=True)
class History:
    run_id: str
    root_id: str
    nodes: dict[str, Node]


@dataclass(frozen=True)
class ReplayResult:
    run_id: str
    policy: Policy
    best_quality: float
    calls: int
    latency_ms: float
    visited: tuple[str, ...]
    objective: float


@dataclass(frozen=True)
class AggregateResult:
    mean_objective: float
    mean_best_quality: float
    mean_calls: float
    mean_latency_ms: float


@dataclass(frozen=True)
class FrontierItem:
    node_id: str
    parent_id: str
    depth: int
    order: int


def _require_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    return float(value)


def load_history(path: Path) -> History:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"{path}: schema_version must be {SCHEMA_VERSION}, got {raw.get('schema_version')!r}"
        )
    run_id = raw.get("run_id")
    root_id = raw.get("root_id")
    raw_nodes = raw.get("nodes")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError(f"{path}: run_id must be a non-empty string")
    if not isinstance(root_id, str) or not root_id:
        raise ValueError(f"{path}: root_id must be a non-empty string")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ValueError(f"{path}: nodes must be a non-empty list")

    nodes: dict[str, Node] = {}
    for index, raw_node in enumerate(raw_nodes):
        if not isinstance(raw_node, dict):
            raise ValueError(f"{path}: nodes[{index}] must be an object")
        node_id = raw_node.get("id")
        parent_id = raw_node.get("parent_id")
        children = raw_node.get("children", [])
        if not isinstance(node_id, str) or not node_id:
            raise ValueError(f"{path}: nodes[{index}].id must be a non-empty string")
        if node_id in nodes:
            raise ValueError(f"{path}: duplicate node id: {node_id}")
        if parent_id is not None and not isinstance(parent_id, str):
            raise ValueError(f"{path}: node {node_id}: parent_id must be a string or null")
        if not isinstance(children, list) or not all(isinstance(item, str) for item in children):
            raise ValueError(f"{path}: node {node_id}: children must be a list of strings")

        calls = raw_node.get("calls", 1 if parent_id is not None else 0)
        if isinstance(calls, bool) or not isinstance(calls, int) or calls < 0:
            raise ValueError(f"{path}: node {node_id}: calls must be a non-negative integer")
        latency_ms = _require_number(raw_node.get("latency_ms", 0), f"{path}: node {node_id}: latency_ms")
        if latency_ms < 0:
            raise ValueError(f"{path}: node {node_id}: latency_ms must be >= 0")
        if "quality" not in raw_node:
            raise ValueError(f"{path}: node {node_id}: quality is required")
        quality = _require_number(raw_node["quality"], f"{path}: node {node_id}: quality")

        nodes[node_id] = Node(
            node_id=node_id,
            parent_id=parent_id,
            children=tuple(children),
            quality=quality,
            calls=calls,
            latency_ms=latency_ms,
            terminal=bool(raw_node.get("terminal", False)),
        )

    if root_id not in nodes:
        raise ValueError(f"{path}: root_id {root_id!r} is missing")
    if nodes[root_id].parent_id is not None:
        raise ValueError(f"{path}: root node must have parent_id=null")
    if nodes[root_id].calls != 0:
        raise ValueError(f"{path}: root node calls must be 0")
    if nodes[root_id].terminal and nodes[root_id].children:
        raise ValueError(f"{path}: terminal root node cannot declare children")
    for node in nodes.values():
        if node.node_id == root_id:
            continue
        if node.parent_id is None:
            raise ValueError(f"{path}: non-root node {node.node_id!r} must have a parent")
        if node.parent_id not in nodes:
            raise ValueError(
                f"{path}: node {node.node_id!r}: missing parent {node.parent_id!r}"
            )
        if node.terminal and node.children:
            raise ValueError(
                f"{path}: terminal node {node.node_id!r} cannot declare children"
            )

    referenced_as_child: set[str] = set()
    for node in nodes.values():
        for child_id in node.children:
            if child_id not in nodes:
                raise ValueError(f"{path}: node {node.node_id}: missing child {child_id!r}")
            child = nodes[child_id]
            if child.parent_id != node.node_id:
                raise ValueError(
                    f"{path}: node {child_id}: parent_id={child.parent_id!r}, "
                    f"expected {node.node_id!r}"
                )
            if child_id in referenced_as_child:
                raise ValueError(f"{path}: child {child_id!r} appears under multiple parents")
            referenced_as_child.add(child_id)

    expected_non_root = set(nodes) - {root_id}
    if referenced_as_child != expected_non_root:
        missing = sorted(expected_non_root - referenced_as_child)
        raise ValueError(f"{path}: disconnected nodes: {missing}")

    # A connected single-parent graph with n-1 edges is a tree; guard against a root cycle anyway.
    cursor_seen: set[str] = set()
    for node_id in nodes:
        cursor_seen.clear()
        cursor = node_id
        while cursor is not None:
            if cursor in cursor_seen:
                raise ValueError(f"{path}: cycle detected at {cursor!r}")
            cursor_seen.add(cursor)
            cursor = nodes[cursor].parent_id

    return History(run_id=run_id, root_id=root_id, nodes=nodes)


def _select_frontier(
    frontier: list[FrontierItem],
    policy: Policy,
    observed_quality: dict[str, float],
) -> int:
    if policy.strategy == "breadth":
        return min(range(len(frontier)), key=lambda i: frontier[i].order)
    if policy.strategy == "depth":
        return max(range(len(frontier)), key=lambda i: (frontier[i].depth, frontier[i].order))
    return max(
        range(len(frontier)),
        key=lambda i: (
            observed_quality[frontier[i].parent_id],
            -frontier[i].depth,
            -frontier[i].order,
        ),
    )


def replay(
    history: History,
    policy: Policy,
    *,
    call_penalty: float = 0.0,
    latency_penalty_per_second: float = 0.0,
) -> ReplayResult:
    policy.validate()
    if call_penalty < 0 or latency_penalty_per_second < 0:
        raise ValueError("penalties must be non-negative")

    root = history.nodes[history.root_id]
    best_quality = root.quality
    calls = root.calls
    latency_ms = root.latency_ms
    visited = [root.node_id]
    observed_quality = {root.node_id: root.quality}
    frontier: list[FrontierItem] = []
    next_order = 0
    no_improvement = 0

    def reveal_children(node: Node, depth: int) -> None:
        nonlocal next_order
        if node.terminal or depth >= policy.max_depth:
            return
        for child_id in node.children[: policy.branch_limit]:
            next_order += 1
            frontier.append(
                FrontierItem(
                    node_id=child_id,
                    parent_id=node.node_id,
                    depth=depth + 1,
                    order=next_order,
                )
            )

    reveal_children(root, 0)

    while frontier and calls < policy.max_calls and no_improvement < policy.patience:
        index = _select_frontier(frontier, policy, observed_quality)
        item = frontier.pop(index)
        node = history.nodes[item.node_id]
        if calls + node.calls > policy.max_calls:
            # This action cannot fit the remaining live-call budget. Other frontier
            # items may have a smaller recorded cost, so continue rather than stop.
            continue

        calls += node.calls
        latency_ms += node.latency_ms
        visited.append(node.node_id)
        observed_quality[node.node_id] = node.quality

        if node.quality > best_quality:
            best_quality = node.quality
            no_improvement = 0
        else:
            no_improvement += 1

        reveal_children(node, item.depth)

    objective = (
        best_quality
        - call_penalty * calls
        - latency_penalty_per_second * (latency_ms / 1000.0)
    )
    return ReplayResult(
        run_id=history.run_id,
        policy=policy,
        best_quality=best_quality,
        calls=calls,
        latency_ms=latency_ms,
        visited=tuple(visited),
        objective=objective,
    )


def aggregate(results: Sequence[ReplayResult]) -> AggregateResult:
    if not results:
        raise ValueError("at least one replay result is required")
    return AggregateResult(
        mean_objective=statistics.fmean(item.objective for item in results),
        mean_best_quality=statistics.fmean(item.best_quality for item in results),
        mean_calls=statistics.fmean(item.calls for item in results),
        mean_latency_ms=statistics.fmean(item.latency_ms for item in results),
    )


def evaluate(
    histories: Sequence[History],
    policy: Policy,
    *,
    call_penalty: float,
    latency_penalty_per_second: float,
) -> AggregateResult:
    return aggregate(
        [
            replay(
                history,
                policy,
                call_penalty=call_penalty,
                latency_penalty_per_second=latency_penalty_per_second,
            )
            for history in histories
        ]
    )


def candidate_policies(max_calls: int) -> Iterable[Policy]:
    branch_limits = (1, 2, 3, 4)
    max_depths = (2, 4, 8)
    patiences = (2, 4, 8, 16)
    for strategy, branch_limit, max_depth, patience in itertools.product(
        STRATEGIES, branch_limits, max_depths, patiences
    ):
        yield Policy(
            strategy=strategy,
            branch_limit=branch_limit,
            max_depth=max_depth,
            patience=patience,
            max_calls=max_calls,
        )


def optimize(
    train_histories: Sequence[History],
    *,
    baseline: Policy,
    call_penalty: float,
    latency_penalty_per_second: float,
    min_train_improvement: float = 0.0,
) -> tuple[Policy, AggregateResult, AggregateResult]:
    baseline.validate()
    baseline_result = evaluate(
        train_histories,
        baseline,
        call_penalty=call_penalty,
        latency_penalty_per_second=latency_penalty_per_second,
    )
    best_policy = baseline
    best_result = baseline_result

    for candidate in candidate_policies(baseline.max_calls):
        result = evaluate(
            train_histories,
            candidate,
            call_penalty=call_penalty,
            latency_penalty_per_second=latency_penalty_per_second,
        )
        # Prefer the objective first, then fewer calls, then a smaller controller.
        # The final strategy index makes exact ties deterministic.
        candidate_key = (
            result.mean_objective,
            -result.mean_calls,
            -candidate.branch_limit,
            -candidate.max_depth,
            -candidate.patience,
            -STRATEGIES.index(candidate.strategy),
        )
        best_key = (
            best_result.mean_objective,
            -best_result.mean_calls,
            -best_policy.branch_limit,
            -best_policy.max_depth,
            -best_policy.patience,
            -STRATEGIES.index(best_policy.strategy),
        )
        if candidate_key > best_key:
            best_policy = candidate
            best_result = result

    if best_result.mean_objective < baseline_result.mean_objective + min_train_improvement:
        return baseline, baseline_result, baseline_result
    return best_policy, best_result, baseline_result


def _load_many(paths: Sequence[str]) -> list[History]:
    return [load_history(Path(item)) for item in paths]


def ensure_disjoint_runs(train_histories: Sequence[History], holdout_histories: Sequence[History]) -> None:
    train_ids = {history.run_id for history in train_histories}
    holdout_ids = {history.run_id for history in holdout_histories}
    overlap = sorted(train_ids & holdout_ids)
    if overlap:
        raise ValueError(f"train and holdout run_id sets overlap: {overlap}")


def _policy_from_args(args: argparse.Namespace) -> Policy:
    return Policy(
        strategy=args.strategy,
        branch_limit=args.branch_limit,
        max_depth=args.max_depth,
        patience=args.patience,
        max_calls=args.max_calls,
    )


def _aggregate_json(result: AggregateResult) -> dict[str, float]:
    return asdict(result)


def cmd_replay(args: argparse.Namespace) -> int:
    history = load_history(Path(args.history))
    result = replay(
        history,
        _policy_from_args(args),
        call_penalty=args.call_penalty,
        latency_penalty_per_second=args.latency_penalty,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


def cmd_optimize(args: argparse.Namespace) -> int:
    train_histories = _load_many(args.train)
    holdout_histories = _load_many(args.holdout) if args.holdout else []
    ensure_disjoint_runs(train_histories, holdout_histories)
    if args.min_train_improvement < 0:
        raise ValueError("min_train_improvement must be non-negative")
    baseline = _policy_from_args(args)
    selected, train_result, baseline_train = optimize(
        train_histories,
        baseline=baseline,
        call_penalty=args.call_penalty,
        latency_penalty_per_second=args.latency_penalty,
        min_train_improvement=args.min_train_improvement,
    )

    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "mode": "offline-replay-only",
        "baseline_policy": asdict(baseline),
        "selected_policy": asdict(selected),
        "train": {
            "baseline": _aggregate_json(baseline_train),
            "selected": _aggregate_json(train_result),
        },
    }
    if holdout_histories:
        payload["holdout"] = {
            "baseline": _aggregate_json(
                evaluate(
                    holdout_histories,
                    baseline,
                    call_penalty=args.call_penalty,
                    latency_penalty_per_second=args.latency_penalty,
                )
            ),
            "selected": _aggregate_json(
                evaluate(
                    holdout_histories,
                    selected,
                    call_penalty=args.call_penalty,
                    latency_penalty_per_second=args.latency_penalty,
                )
            ),
        }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def add_policy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--strategy", choices=STRATEGIES, default="breadth")
    parser.add_argument("--branch-limit", type=int, default=2)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--max-calls", type=int, default=32)
    parser.add_argument(
        "--call-penalty",
        type=float,
        default=0.0,
        help="objective penalty per recorded model/evaluator call",
    )
    parser.add_argument(
        "--latency-penalty",
        type=float,
        default=0.0,
        help="objective penalty per recorded second of latency",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline Dream-RSI-style replay for historical delegation/search trees. "
            "This helper never launches agents or mutates a worktree."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    replay_parser = subparsers.add_parser("replay", help="replay one historical tree")
    replay_parser.add_argument("history")
    add_policy_args(replay_parser)
    replay_parser.set_defaults(func=cmd_replay)

    optimize_parser = subparsers.add_parser(
        "optimize",
        help="search a small controller grid on training histories and report optional holdout results",
    )
    optimize_parser.add_argument("--train", nargs="+", required=True)
    optimize_parser.add_argument("--holdout", nargs="*", default=[])
    add_policy_args(optimize_parser)
    optimize_parser.add_argument(
        "--min-train-improvement",
        type=float,
        default=0.0,
        help="keep the baseline unless the selected policy exceeds it by this objective margin",
    )
    optimize_parser.set_defaults(func=cmd_optimize)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Dream-RSI replay failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
