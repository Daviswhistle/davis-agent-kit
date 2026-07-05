#!/usr/bin/env python3
"""Compare a generated report HTML against a reference-quality report HTML."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys


ALIGNMENT_CLASSES = {"left-cell", "right-cell", "center-cell"}
RAW_ARTIFACT_PATTERNS = {
    "raw_bold_marker": re.compile(r"\*\*"),
    "raw_escaped_heading": re.compile(r"\\#"),
    "raw_escaped_asterisk": re.compile(r"\\\*"),
    "raw_em_marker": re.compile(r"\[\[em:"),
    "non_english_marker": re.compile(r"\[(?:Non-English content|비영어 발언)\]"),
}


@dataclass
class HtmlMetrics:
    path: str
    line_count: int
    page_count: int
    first_page: str
    last_page: str
    contiguous_pages: bool
    table_count: int
    tr_count: int
    th_count: int
    td_count: int
    table_column_mismatches: int
    table_cells_missing_alignment: int
    external_link_count: int
    unique_external_link_count: int
    em_count: int
    strong_count: int
    raw_artifact_count: int


class ReportMetricParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.counts: dict[str, int] = {}
        self.pages: list[str] = []
        self.links: list[str] = []
        self.classes: dict[str, int] = {}
        self.table_depth = 0
        self.in_row = False
        self.current_row_cells = 0
        self.current_table_rows: list[int] = []
        self.table_column_mismatches = 0
        self.table_cells_missing_alignment = 0
        self.visible_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self.counts[tag] = self.counts.get(tag, 0) + 1
        attr_map = {name.lower(): value or "" for name, value in attrs}

        if "class" in attr_map:
            for klass in attr_map["class"].split():
                self.classes[klass] = self.classes.get(klass, 0) + 1

        if tag == "section" and attr_map.get("data-page"):
            self.pages.append(attr_map["data-page"])
        elif tag == "a":
            self.links.append(attr_map.get("href", ""))
        elif tag == "table":
            self.table_depth += 1
            self.current_table_rows = []
        elif tag == "tr" and self.table_depth:
            self.in_row = True
            self.current_row_cells = 0
        elif tag in {"td", "th"} and self.table_depth and self.in_row:
            try:
                colspan = int(attr_map.get("colspan", "1"))
            except ValueError:
                colspan = 1
            self.current_row_cells += colspan
            classes = set(attr_map.get("class", "").split())
            if not classes.intersection(ALIGNMENT_CLASSES):
                self.table_cells_missing_alignment += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "tr" and self.table_depth and self.in_row:
            self.current_table_rows.append(self.current_row_cells)
            self.in_row = False
        elif tag == "table" and self.table_depth:
            if len(set(self.current_table_rows)) > 1:
                self.table_column_mismatches += 1
            self.table_depth -= 1

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.visible_chunks.append(data)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path, help="Generated candidate HTML.")
    parser.add_argument("--reference", type=Path, help="Reference-quality HTML to compare against.")
    parser.add_argument("--expect-title", help="Exact visible title expected in the candidate.")
    parser.add_argument("--expect-pages", type=int, help="Exact candidate page count.")
    parser.add_argument(
        "--require-core-counts-match",
        action="store_true",
        help="Require candidate page/table/tr/th/td counts to match the reference exactly.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path to write metrics and findings as JSON.",
    )
    return parser.parse_args(argv)


def external_links(links: list[str]) -> list[str]:
    return [link for link in links if link and not link.startswith("#")]


def contiguous_pages(pages: list[str]) -> bool:
    try:
        numbers = [int(page) for page in pages]
    except ValueError:
        return False
    return numbers == list(range(1, len(numbers) + 1))


def collect_metrics(path: Path) -> tuple[HtmlMetrics, str]:
    text = path.read_text(encoding="utf-8")
    parser = ReportMetricParser()
    parser.feed(text)
    ext_links = external_links(parser.links)
    raw_artifact_count = sum(len(pattern.findall(text)) for pattern in RAW_ARTIFACT_PATTERNS.values())
    metrics = HtmlMetrics(
        path=str(path),
        line_count=text.count("\n") + 1,
        page_count=len(parser.pages),
        first_page=parser.pages[0] if parser.pages else "",
        last_page=parser.pages[-1] if parser.pages else "",
        contiguous_pages=contiguous_pages(parser.pages),
        table_count=parser.counts.get("table", 0),
        tr_count=parser.counts.get("tr", 0),
        th_count=parser.counts.get("th", 0),
        td_count=parser.counts.get("td", 0),
        table_column_mismatches=parser.table_column_mismatches,
        table_cells_missing_alignment=parser.table_cells_missing_alignment,
        external_link_count=len(ext_links),
        unique_external_link_count=len(set(ext_links)),
        em_count=parser.counts.get("em", 0),
        strong_count=parser.counts.get("strong", 0),
        raw_artifact_count=raw_artifact_count,
    )
    return metrics, "\n".join(parser.visible_chunks)


def add_candidate_findings(findings: list[str], metrics: HtmlMetrics, visible_text: str, args: argparse.Namespace) -> None:
    if args.expect_title and args.expect_title not in visible_text:
        findings.append(f"candidate missing expected title: {args.expect_title}")
    if args.expect_pages is not None and metrics.page_count != args.expect_pages:
        findings.append(f"candidate page_count={metrics.page_count}, expected {args.expect_pages}")
    if not metrics.contiguous_pages:
        findings.append("candidate page sections are not contiguous from 1..N")
    if metrics.table_column_mismatches:
        findings.append(f"candidate has {metrics.table_column_mismatches} table(s) with mismatched row column counts")
    if metrics.table_cells_missing_alignment:
        findings.append(f"candidate has {metrics.table_cells_missing_alignment} table cell(s) without alignment class")
    if metrics.raw_artifact_count:
        findings.append(f"candidate has {metrics.raw_artifact_count} raw markdown/source artifact(s)")


def add_reference_findings(findings: list[str], candidate: HtmlMetrics, reference: HtmlMetrics, strict_counts: bool) -> None:
    if strict_counts:
        for field in ("page_count", "table_count", "tr_count", "th_count", "td_count"):
            candidate_value = getattr(candidate, field)
            reference_value = getattr(reference, field)
            if candidate_value != reference_value:
                findings.append(f"{field} mismatch: candidate={candidate_value}, reference={reference_value}")

    if candidate.unique_external_link_count < reference.unique_external_link_count:
        findings.append(
            "candidate unique external links below reference: "
            f"candidate={candidate.unique_external_link_count}, reference={reference.unique_external_link_count}"
        )
    if candidate.external_link_count < reference.external_link_count:
        findings.append(
            "candidate external link count below reference: "
            f"candidate={candidate.external_link_count}, reference={reference.external_link_count}"
        )
    if candidate.strong_count < int(reference.strong_count * 0.95):
        findings.append(
            "candidate strong tag count below 95% of reference: "
            f"candidate={candidate.strong_count}, reference={reference.strong_count}"
        )
    if candidate.em_count < reference.em_count:
        findings.append(f"candidate em tag count below reference: candidate={candidate.em_count}, reference={reference.em_count}")


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.candidate.exists():
        print(f"FAIL: candidate does not exist: {args.candidate}", file=sys.stderr)
        return 2
    if args.reference and not args.reference.exists():
        print(f"FAIL: reference does not exist: {args.reference}", file=sys.stderr)
        return 2

    findings: list[str] = []
    candidate_metrics, candidate_visible = collect_metrics(args.candidate)
    add_candidate_findings(findings, candidate_metrics, candidate_visible, args)

    reference_metrics = None
    if args.reference:
        reference_metrics, _ = collect_metrics(args.reference)
        add_reference_findings(findings, candidate_metrics, reference_metrics, args.require_core_counts_match)

    payload = {
        "status": "fail" if findings else "pass",
        "candidate": asdict(candidate_metrics),
        "reference": asdict(reference_metrics) if reference_metrics else None,
        "findings": findings,
    }

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if findings:
        for finding in findings:
            print(f"FAIL: {finding}")
        return 1

    print("PASS: report equivalence gates satisfied")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
