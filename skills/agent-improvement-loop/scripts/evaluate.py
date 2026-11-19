#!/usr/bin/env python3
"""Compare recorded agent output against a reviewed, deterministic regression suite.

This tool does not run an agent or decide whether an answer is semantically correct.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
MAX_BYTES = 2_000_000
RULES = {"contains", "not_contains", "json_equals", "evidence_quotes"}


class SuiteError(ValueError):
    pass


def _relative_file(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise SuiteError(f"unsafe relative path: {name!r}")
    path = Path(name)
    if any(part in {"..", "."} for part in path.parts):
        raise SuiteError(f"unsafe relative path: {name!r}")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise SuiteError(f"path escapes root: {name!r}")
    return resolved


def _load_text(root: Path, name: str) -> str:
    file = _relative_file(root, name)
    if not file.is_file():
        raise SuiteError(f"missing file: {name}")
    if file.stat().st_size > MAX_BYTES:
        raise SuiteError(f"file exceeds {MAX_BYTES} bytes: {name}")
    try:
        return file.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise SuiteError(f"file is not UTF-8: {name}") from exc


def _load_json(root: Path, name: str):
    try:
        return json.loads(_load_text(root, name))
    except json.JSONDecodeError as exc:
        raise SuiteError(f"invalid JSON in {name}: {exc.msg}") from exc


def _json_pointer(document, pointer: str):
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise SuiteError("JSON pointer must be empty or begin with /")
    value = document
    for raw in pointer[1:].split("/"):
        segment = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and segment in value:
            value = value[segment]
        elif isinstance(value, list) and segment.isdigit() and int(segment) < len(value):
            value = value[int(segment)]
        else:
            raise SuiteError(f"JSON pointer does not resolve: {pointer}")
    return value


def _check_quotes(document, sources: Path | None):
    if sources is None:
        raise SuiteError("evidence_quotes requires --sources")
    if not isinstance(document, list) or not document:
        raise SuiteError("evidence document must be a nonempty list")
    for index, claim in enumerate(document):
        if not isinstance(claim, dict) or not isinstance(claim.get("claim"), str) or not claim["claim"].strip():
            raise SuiteError(f"evidence claim {index} has no claim text")
        evidence = claim.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise SuiteError(f"evidence claim {index} has no evidence")
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("file"), str):
                raise SuiteError(f"evidence claim {index} has invalid source entry")
            quote = item.get("quote")
            if not isinstance(quote, str) or len(quote.strip()) < 8:
                raise SuiteError(f"evidence claim {index} needs a nontrivial source quote")
            if quote not in _load_text(sources, item["file"]):
                raise SuiteError(f"evidence claim {index} cites a quote absent from its source")


def _validate_suite(suite):
    if not isinstance(suite, dict) or type(suite.get("version")) is not int or suite["version"] != 1:
        raise SuiteError("suite version must be 1")
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        raise SuiteError("suite requires nonempty cases")
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not ID.fullmatch(case["id"]) or case["id"] in {".", ".."}:
            raise SuiteError("case requires a safe id")
        if case["id"] in seen:
            raise SuiteError(f"duplicate case id: {case['id']}")
        seen.add(case["id"])
        rules = case.get("assertions")
        if not isinstance(rules, list) or not rules:
            raise SuiteError(f"case {case['id']} has no assertions")
        for rule in rules:
            if not isinstance(rule, dict) or rule.get("type") not in RULES:
                raise SuiteError(f"case {case['id']} has unknown assertion")
            _relative_file(Path("/validation-root"), rule.get("path"))
            if rule["type"] in {"contains", "not_contains"} and (not isinstance(rule.get("value"), str) or not rule["value"]):
                raise SuiteError("text assertion needs nonempty value")
            if rule["type"] == "json_equals" and ("value" not in rule or not isinstance(rule.get("pointer"), str)):
                raise SuiteError("json_equals needs a pointer and value")
    return cases


def _evaluate(run: Path, rule: dict, sources: Path | None) -> dict:
    try:
        path, kind = rule["path"], rule["type"]
        if kind in {"contains", "not_contains"}:
            present = rule["value"] in _load_text(run, path)
            passed = present if kind == "contains" else not present
            return {"passed": passed, "reason": "matched" if passed else "text condition failed"}
        data = _load_json(run, path)
        if kind == "json_equals":
            value = _json_pointer(data, rule["pointer"])
            expected = rule["value"]
            passed = type(value) is type(expected) and value == expected
            return {"passed": passed, "reason": "matched" if passed else "JSON value differed"}
        _check_quotes(data, sources)
        return {"passed": True, "reason": "source excerpts verified (not semantic entailment)"}
    except SuiteError as exc:
        return {"passed": False, "reason": str(exc)}


def compare(suite: dict, baseline: Path, candidate: Path, sources: Path | None) -> dict:
    cases = _validate_suite(suite)
    reports = []
    improvements = regressions = 0
    for case in cases:
        old_dir = _relative_file(baseline, case["id"])
        new_dir = _relative_file(candidate, case["id"])
        old = [_evaluate(old_dir, rule, sources) for rule in case["assertions"]]
        new = [_evaluate(new_dir, rule, sources) for rule in case["assertions"]]
        improved = [i for i, (b, c) in enumerate(zip(old, new)) if not b["passed"] and c["passed"]]
        regressed = [i for i, (b, c) in enumerate(zip(old, new)) if b["passed"] and not c["passed"]]
        improvements += len(improved)
        regressions += len(regressed)
        reports.append({"id": case["id"], "baseline": old, "candidate": new,
                        "improved_assertions": improved, "regressed_assertions": regressed})
    failures = sum(not item["passed"] for case in reports for item in case["candidate"])
    return {"summary": {"cases": len(cases), "assertions": sum(len(c["assertions"]) for c in cases),
                        "improved_assertions": improvements, "regressed_assertions": regressions,
                        "candidate_failures": failures, "passed": failures == 0 and regressions == 0},
            "cases": reports}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True, help="Reviewed JSON assertion suite")
    parser.add_argument("--baseline", type=Path, required=True, help="Baseline run directory")
    parser.add_argument("--candidate", type=Path, required=True, help="Candidate run directory")
    parser.add_argument("--sources", type=Path, help="Read-only source corpus for evidence_quotes")
    parser.add_argument("--output", type=Path, help="Optional JSON report (keep outside Git)")
    args = parser.parse_args(argv)
    try:
        report = compare(_load_json(args.suite.parent.resolve(), args.suite.name),
                         args.baseline.resolve(), args.candidate.resolve(),
                         args.sources.resolve() if args.sources else None)
    except SuiteError as exc:
        print(f"invalid suite: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["summary"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
