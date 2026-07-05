#!/usr/bin/env python3
"""Mechanical QA checks for Korean transcript HTML deliverables."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import html
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from typing import Iterable


HARD_PATTERNS = (
    ("visible non-English source marker", re.compile(r"\[(?:Non-English content|비영어 발언)\]")),
    ("raw emphasis marker", re.compile(r"\[\[em:")),
    ("visible interpreter speaker label", re.compile(r"<strong>\s*통역\s*</strong>", re.IGNORECASE)),
    ("raw extracted speaker label as visible speaker", re.compile(r"data-speaker=(['\"])Speaker\s+\d+\1")),
    ("visible workflow metadata", re.compile(r"번역 품질 평가용|Financial period source|Title source|Date source")),
)

TRANSCRIPT_STYLE_PATTERNS = (
    ("literal high-level phrase", re.compile(r"높은 수준에서\s+말씀드리겠습니다")),
    ("literal operator question handoff", re.compile(r"에게서 나옵니다")),
    ("literal halo-effect phrase", re.compile(r"파급 효과를\s+만들어내지\s+못")),
    ("literal product/material phrase", re.compile(r"새로운\s+\S{1,20}원단")),
    ("literal current-expect phrase", re.compile(r"것으로 현재|현재 예상")),
    ("literal gateway factor", re.compile(r"관문 요인")),
    ("literal product-move phrase", re.compile(r"제품을 이동")),
    ("literal update-us wording", re.compile(r"업데이트해 주실 수")),
    ("literal analyst goodbye", re.compile(r"행운을 빕니다")),
    ("ambiguous proxy phrase", re.compile(r"위임장 변경")),
    ("literal prepared-remarks closing", re.compile(r"준비한 말씀|이상으로 준비한")),
    ("literal further-remarks transition", re.compile(r"추가 말씀")),
    ("awkward handoff phrase", re.compile(r"에게 넘겨")),
    ("awkward violation-handling phrase", re.compile(r"매장 위반 처리 시간")),
    ("raw RMB currency code", re.compile(r"\bRMB\b")),
    ("possible large-number currency-scale issue", re.compile(r"(?<!1,)100억(?:\(위안\))?\s*(?:규모|지원|투자|프로그램|계획|펀드)")),
)

STYLE_PATTERNS_BY_PROFILE = {
    "transcript": TRANSCRIPT_STYLE_PATTERNS,
    "report": (),
    "generic": (),
}

TAG_RE = re.compile(r"<(?P<tag>div|p)\b(?P<attrs>[^>]*)>", re.IGNORECASE | re.DOTALL)
CLASS_RE = re.compile(r"\bclass\s*=\s*(['\"])(?P<class>.*?)\1", re.IGNORECASE | re.DOTALL)
ALIGNMENT_CLASSES = {"left-cell", "right-cell", "center-cell"}
TRACKED_TAGS = {
    "a",
    "aside",
    "body",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "html",
    "li",
    "main",
    "ol",
    "p",
    "section",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}


@dataclass(frozen=True)
class Finding:
    severity: str
    path: Path
    line: int
    message: str


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Final HTML output path.")
    parser.add_argument(
        "--chunks",
        action="append",
        default=[],
        type=Path,
        help="Translation chunk file or directory. Can be repeated.",
    )
    parser.add_argument("--expect-title", help="Exact reader-facing Korean title expected in the output.")
    parser.add_argument("--expect-date", help="Exact reader-facing date expected in the output.")
    parser.add_argument(
        "--strict-style",
        action="store_true",
        help=(
            "Fail when exact recurring mistranslation templates remain, not only hard "
            "structural failures. Ordinary wording still requires conceptual review."
        ),
    )
    parser.add_argument(
        "--allow-visible-interpreter-label",
        action="store_true",
        help="Allow a visible <strong>통역</strong> speaker label when QA confirms the speaker is genuinely an interpreter.",
    )
    parser.add_argument(
        "--source-units",
        type=Path,
        help="Optional source_units.tsv. When provided, checks selected numeric range terms against final data-unit paragraphs.",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(STYLE_PATTERNS_BY_PROFILE),
        default="transcript",
        help=(
            "Style profile for lexical review. Use 'report' for annual reports and "
            "formal financial reports where transcript-specific wording checks are not applicable."
        ),
    )
    return parser.parse_args(argv)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def html_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.glob("*.html")))
        else:
            files.append(path)
    return files


def add_pattern_findings(
    findings: list[Finding],
    path: Path,
    text: str,
    patterns: Iterable[tuple[str, re.Pattern[str]]],
    severity: str,
) -> None:
    for label, pattern in patterns:
        for match in pattern.finditer(text):
            findings.append(Finding(severity, path, line_number(text, match.start()), label))


def has_utf8_meta(text: str) -> bool:
    return bool(re.search(r"<meta\b[^>]*charset\s*=\s*['\"]?utf-8", text, re.IGNORECASE))


def count_open(text: str, tag: str) -> int:
    return len(re.findall(rf"<{tag}\b", text, re.IGNORECASE))


def count_close(text: str, tag: str) -> int:
    return len(re.findall(rf"</{tag}\s*>", text, re.IGNORECASE))


def block_sequence(text: str) -> list[tuple[str, int]]:
    blocks: list[tuple[str, int]] = []
    for match in TAG_RE.finditer(text):
        class_match = CLASS_RE.search(match.group("attrs"))
        if not class_match:
            continue
        classes = set(class_match.group("class").split())
        for block_class in ("speaker", "para", "blank"):
            if block_class in classes:
                blocks.append((block_class, match.start()))
                break
    return blocks


class RobustTagAndTableParser(HTMLParser):
    def __init__(self, path: Path, findings: list[Finding]) -> None:
        super().__init__()
        self.path = path
        self.findings = findings
        self.stack: list[tuple[str, tuple[int, int]]] = []
        self.table_depth = 0
        self.current_table_headers_count: int | None = None
        self.current_table_row_count = 0
        self.current_row_cells_count = 0
        self.in_tr = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        attr_map = {name.lower(): value or "" for name, value in attrs}
        if tag_lower in TRACKED_TAGS:
            self.stack.append((tag_lower, self.getpos()))

        if tag_lower == 'table':
            self.table_depth += 1
            self.current_table_headers_count = None
            self.current_table_row_count = 0
        elif tag_lower == 'tr':
            self.in_tr = True
            self.current_row_cells_count = 0
            self.current_table_row_count += 1
        elif tag_lower in ('td', 'th'):
            if self.in_tr:
                colspan = 1
                try:
                    colspan = int(attr_map.get("colspan", "1"))
                except ValueError:
                    colspan = 1
                self.current_row_cells_count += colspan
                classes = set(attr_map.get("class", "").split())
                if self.table_depth and not classes.intersection(ALIGNMENT_CLASSES):
                    self.findings.append(
                        Finding(
                            "HARD",
                            self.path,
                            self.getpos()[0],
                            f"table cell <{tag_lower}> missing left-cell/right-cell/center-cell alignment class",
                        )
                    )

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in TRACKED_TAGS:
            if not self.stack:
                self.findings.append(Finding("HARD", self.path, self.getpos()[0], f"unexpected closing tag </{tag_lower}>"))
                return
            expected, pos = self.stack.pop()
            if expected != tag_lower:
                self.findings.append(Finding("HARD", self.path, self.getpos()[0], f"mismatched tag: closed </{tag_lower}> but expected </{expected}> (opened at line {pos[0]})"))

        if tag_lower == 'tr':
            self.in_tr = False
            if self.current_table_headers_count is None:
                self.current_table_headers_count = self.current_row_cells_count
            else:
                if self.current_row_cells_count != self.current_table_headers_count:
                    self.findings.append(Finding("HARD", self.path, self.getpos()[0], f"table row has {self.current_row_cells_count} columns, expected {self.current_table_headers_count}"))
        elif tag_lower == 'table':
            self.table_depth -= 1

    def handle_data(self, data: str) -> None:
        in_a = any(t == 'a' for t, _ in self.stack)
        if not in_a:
            url_match = re.search(r'\b(?:https?://|www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}[^\s<)]*', data)
            if url_match:
                self.findings.append(Finding("STYLE", self.path, self.getpos()[0], f"unlinked website URL: {url_match.group(0)}"))

            if '**' in data or '\\#' in data or '\\*' in data:
                self.findings.append(Finding("HARD", self.path, self.getpos()[0], "leftover raw markdown formatting markers"))

            duplicate_match = re.search(r'\(\s*([가-힣]{2,4})\s*,\s*\1\s*\)', data)
            if duplicate_match:
                self.findings.append(Finding("HARD", self.path, self.getpos()[0], f"duplicate name/phrase translation artifact: {duplicate_match.group(0)}"))


def add_html_structure_findings(findings: list[Finding], path: Path, text: str, args: argparse.Namespace) -> None:
    lower = text.lower()
    visible_text = html.unescape(text)

    if '<html lang="ko"' not in lower and "<html lang='ko'" not in lower:
        findings.append(Finding("HARD", path, 1, "missing <html lang=\"ko\">"))
    if not has_utf8_meta(text):
        findings.append(Finding("HARD", path, 1, "missing <meta charset=\"utf-8\">"))

    # Use HTMLParser subclass to check robust tag balance and table parity
    parser = RobustTagAndTableParser(path, findings)
    try:
        parser.feed(text)
    except Exception as e:
        findings.append(Finding("HARD", path, 1, f"HTML parsing error: {e}"))

    if parser.stack:
        for tag, pos in parser.stack:
            findings.append(Finding("HARD", path, pos[0], f"unclosed tag <{tag}>"))

    if "</body>" not in lower:
        findings.append(Finding("HARD", path, 1, "missing closing </body>"))
    if "</html>" not in lower:
        findings.append(Finding("HARD", path, 1, "missing closing </html>"))

    if args.expect_title and args.expect_title not in visible_text:
        findings.append(Finding("HARD", path, 1, f"missing expected title: {args.expect_title}"))
    if args.expect_date and args.expect_date not in visible_text:
        findings.append(Finding("HARD", path, 1, f"missing expected date: {args.expect_date}"))

    blocks = block_sequence(text)
    for index, (kind, position) in enumerate(blocks):
        if kind != "speaker":
            continue
        if index + 1 >= len(blocks):
            findings.append(Finding("HARD", path, line_number(text, position), "speaker block has no following paragraph"))
            continue
        next_kind, _ = blocks[index + 1]
        if next_kind != "para":
            findings.append(
                Finding(
                    "HARD",
                    path,
                    line_number(text, position),
                    f"speaker block is followed by .{next_kind}, not .para",
                )
            )


RANGE_EXPECTATIONS: tuple[tuple[str, re.Pattern[str], tuple[str, ...]], ...] = (
    (
        "mid-to-high teens range",
        re.compile(r"\bmid[- ]to[- ]high teens\b", re.IGNORECASE),
        ("10%대 중반에서 후반",),
    ),
    (
        "high-single-to-low-double range",
        re.compile(r"\bhigh single[- ](?:digit[s]?)?[- ]to[- ]low double[- ]digit[s]?\b", re.IGNORECASE),
        ("한 자릿수 후반에서 10%대 초반",),
    ),
    (
        "low-to-mid single digits range",
        re.compile(r"\blow[- ]to[- ]mid single digits\b", re.IGNORECASE),
        ("한 자릿수 초중반",),
    ),
    (
        "low double digits range",
        re.compile(r"\blow double[- ]digit[s]?\b", re.IGNORECASE),
        ("10%대 초반",),
    ),
    (
        "mid-teens range",
        re.compile(r"\bmid[- ]teens\b", re.IGNORECASE),
        ("10%대 중반",),
    ),
    (
        "high-teens range",
        re.compile(r"(?<!mid to )(?<!mid-to )\bhigh[- ]teens\b", re.IGNORECASE),
        ("10%대 후반",),
    ),
)

DATA_UNIT_RE = re.compile(
    r"<(?P<tag>div|p)\b(?P<attrs>[^>]*\bdata-unit\s*=\s*(['\"])(?P<unit>\d+)\3[^>]*)>"
    r"(?P<body>.*?)</(?P=tag)>",
    re.IGNORECASE | re.DOTALL,
)
SOURCE_COLUMN_CANDIDATES = ("source_text", "source", "text", "original")


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def unit_texts_from_html(text: str) -> dict[str, str]:
    unit_texts: dict[str, str] = {}
    for match in DATA_UNIT_RE.finditer(text):
        unit = match.group("unit").zfill(3)
        rendered = html.unescape(strip_tags(match.group("body")))
        rendered = re.sub(r"\s+", " ", rendered).strip()
        unit_texts[unit] = rendered
    return unit_texts


def add_source_unit_numeric_findings(
    findings: list[Finding],
    source_units_path: Path,
    output_path: Path,
    output_text: str,
) -> None:
    if not source_units_path.exists():
        findings.append(Finding("HARD", source_units_path, 1, "source_units.tsv path does not exist"))
        return

    unit_texts = unit_texts_from_html(output_text)
    with source_units_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row_number, row in enumerate(reader, start=2):
            unit = (row.get("unit") or row.get("id") or "").strip().zfill(3)
            source_text = ""
            for column in SOURCE_COLUMN_CANDIDATES:
                if row.get(column):
                    source_text = row[column]
                    break
            if not unit or not source_text:
                continue
            final_text = unit_texts.get(unit)
            for label, source_pattern, expected_phrases in RANGE_EXPECTATIONS:
                if not source_pattern.search(source_text):
                    continue
                if final_text is None:
                    findings.append(
                        Finding("HARD", output_path, 1, f"missing final data-unit {unit} for {label}")
                    )
                    continue
                if not any(phrase in final_text for phrase in expected_phrases):
                    findings.append(
                        Finding(
                            "HARD",
                            output_path,
                            line_number(output_text, output_text.find(f'data-unit="{unit}"')),
                            f"unit {unit} mistranslates {label}; expected one of: {', '.join(expected_phrases)}",
                        )
                    )


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    findings: list[Finding] = []

    if not args.output.exists():
        print(f"FAIL: output path does not exist: {args.output}", file=sys.stderr)
        return 2

    output_text = read_text(args.output)
    add_html_structure_findings(findings, args.output, output_text, args)
    if args.source_units:
        add_source_unit_numeric_findings(findings, args.source_units, args.output, output_text)

    paths = [args.output, *html_files(args.chunks)]
    seen: set[Path] = set()
    for path in paths:
        if path in seen or not path.exists():
            continue
        seen.add(path)
        text = read_text(path)
        hard_patterns = HARD_PATTERNS
        if args.allow_visible_interpreter_label:
            hard_patterns = tuple(
                item for item in HARD_PATTERNS if item[0] != "visible interpreter speaker label"
            )
        add_pattern_findings(findings, path, text, hard_patterns, "HARD")
        add_pattern_findings(findings, path, text, STYLE_PATTERNS_BY_PROFILE[args.profile], "STYLE")

    hard_count = sum(1 for finding in findings if finding.severity == "HARD")
    style_count = sum(1 for finding in findings if finding.severity == "STYLE")

    if not findings:
        print(f"PASS: {args.output}")
        return 0

    for finding in findings:
        print(f"[{finding.severity}] {finding.path}:{finding.line}: {finding.message}")

    if hard_count:
        print(f"FAIL: {hard_count} hard finding(s), {style_count} style finding(s)")
        return 1
    if args.strict_style and style_count:
        print(f"FAIL: {style_count} unresolved style finding(s)")
        return 1

    print(f"PASS WITH STYLE REVIEW: {style_count} style finding(s) require QA disposition")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
