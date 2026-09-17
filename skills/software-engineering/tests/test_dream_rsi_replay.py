from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import sys

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "dream_rsi_replay.py"
SPEC = importlib.util.spec_from_file_location("dream_rsi_replay", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def history_from_dict(raw: dict) -> object:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "history.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        return MODULE.load_history(path)


class DreamRSIReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.history = history_from_dict(
            {
                "schema_version": 1,
                "run_id": "r1",
                "root_id": "root",
                "nodes": [
                    {
                        "id": "root",
                        "parent_id": None,
                        "children": ["a", "b", "c"],
                        "quality": 0.10,
                        "calls": 0,
                    },
                    {
                        "id": "a",
                        "parent_id": "root",
                        "children": ["a1"],
                        "quality": 0.20,
                        "calls": 1,
                        "latency_ms": 100,
                    },
                    {
                        "id": "a1",
                        "parent_id": "a",
                        "children": [],
                        "quality": 0.21,
                        "calls": 1,
                        "latency_ms": 100,
                        "terminal": True,
                    },
                    {
                        "id": "b",
                        "parent_id": "root",
                        "children": [],
                        "quality": 0.90,
                        "calls": 1,
                        "latency_ms": 100,
                        "terminal": True,
                    },
                    {
                        "id": "c",
                        "parent_id": "root",
                        "children": [],
                        "quality": 0.95,
                        "calls": 1,
                        "latency_ms": 100,
                        "terminal": True,
                    },
                ],
            }
        )

    def test_branch_limit_cannot_peek_at_unrevealed_high_quality_child(self) -> None:
        result = MODULE.replay(
            self.history,
            MODULE.Policy(
                strategy="best-parent",
                branch_limit=1,
                max_depth=4,
                patience=8,
                max_calls=8,
            ),
        )
        self.assertNotIn("b", result.visited)
        self.assertNotIn("c", result.visited)
        self.assertEqual(result.best_quality, 0.21)

    def test_breadth_replay_observes_child_quality_only_after_visit(self) -> None:
        result = MODULE.replay(
            self.history,
            MODULE.Policy(
                strategy="breadth",
                branch_limit=3,
                max_depth=4,
                patience=8,
                max_calls=3,
            ),
        )
        self.assertEqual(result.visited, ("root", "a", "b", "c"))
        self.assertEqual(result.calls, 3)
        self.assertEqual(result.best_quality, 0.95)

    def test_call_budget_skips_unaffordable_node_and_can_continue(self) -> None:
        history = history_from_dict(
            {
                "schema_version": 1,
                "run_id": "budget",
                "root_id": "root",
                "nodes": [
                    {"id": "root", "parent_id": None, "children": ["expensive", "cheap"], "quality": 0, "calls": 0},
                    {"id": "expensive", "parent_id": "root", "children": [], "quality": 1.0, "calls": 3},
                    {"id": "cheap", "parent_id": "root", "children": [], "quality": 0.5, "calls": 1},
                ],
            }
        )
        result = MODULE.replay(
            history,
            MODULE.Policy(
                strategy="breadth",
                branch_limit=2,
                max_depth=2,
                patience=8,
                max_calls=1,
            ),
        )
        self.assertEqual(result.visited, ("root", "cheap"))
        self.assertEqual(result.calls, 1)
        self.assertEqual(result.best_quality, 0.5)

    def test_objective_charges_calls_and_latency(self) -> None:
        result = MODULE.replay(
            self.history,
            MODULE.Policy(
                strategy="breadth",
                branch_limit=1,
                max_depth=1,
                patience=8,
                max_calls=8,
            ),
            call_penalty=0.05,
            latency_penalty_per_second=0.5,
        )
        self.assertAlmostEqual(result.objective, 0.20 - 0.05 - 0.05)

    def test_optimizer_keeps_baseline_when_margin_not_met(self) -> None:
        baseline = MODULE.Policy(
            strategy="breadth",
            branch_limit=3,
            max_depth=4,
            patience=8,
            max_calls=3,
        )
        selected, selected_result, baseline_result = MODULE.optimize(
            [self.history],
            baseline=baseline,
            call_penalty=0,
            latency_penalty_per_second=0,
            min_train_improvement=0.5,
        )
        self.assertEqual(selected, baseline)
        self.assertEqual(selected_result, baseline_result)

    def test_loader_rejects_disconnected_node(self) -> None:
        raw = {
            "schema_version": 1,
            "run_id": "bad",
            "root_id": "root",
            "nodes": [
                {"id": "root", "parent_id": None, "children": [], "quality": 0},
                {"id": "orphan", "parent_id": "root", "children": [], "quality": 1},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "disconnected"):
                MODULE.load_history(path)

    def test_loader_rejects_missing_parent_cleanly(self) -> None:
        raw = {
            "schema_version": 1,
            "run_id": "bad-parent",
            "root_id": "root",
            "nodes": [
                {"id": "root", "parent_id": None, "children": [], "quality": 0},
                {"id": "orphan", "parent_id": "missing", "children": [], "quality": 1},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad-parent.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing parent"):
                MODULE.load_history(path)

    def test_train_holdout_overlap_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlap"):
            MODULE.ensure_disjoint_runs([self.history], [self.history])

    def test_loader_requires_quality(self) -> None:
        raw = {
            "schema_version": 1,
            "run_id": "missing-quality",
            "root_id": "root",
            "nodes": [
                {"id": "root", "parent_id": None, "children": [], "calls": 0},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing-quality.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "quality is required"):
                MODULE.load_history(path)

    def test_loader_rejects_nonfinite_metric(self) -> None:
        raw = {
            "schema_version": 1,
            "run_id": "nonfinite",
            "root_id": "root",
            "nodes": [
                {"id": "root", "parent_id": None, "children": [], "quality": float("nan")},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nonfinite.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "finite number"):
                MODULE.load_history(path)

    def test_loader_rejects_non_boolean_terminal(self) -> None:
        raw = {
            "schema_version": 1,
            "run_id": "bad-terminal",
            "root_id": "root",
            "nodes": [
                {
                    "id": "root",
                    "parent_id": None,
                    "children": [],
                    "quality": 0,
                    "terminal": "false",
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad-terminal.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "terminal must be a boolean"):
                MODULE.load_history(path)

    def test_loader_rejects_non_object_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "list.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "top-level JSON must be an object"):
                MODULE.load_history(path)

    def test_replay_rejects_nonfinite_penalty(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite number"):
            MODULE.replay(
                self.history,
                MODULE.Policy(max_calls=1),
                call_penalty=float("nan"),
            )


if __name__ == "__main__":
    unittest.main()
