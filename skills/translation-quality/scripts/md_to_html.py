#!/usr/bin/env python3
"""Build reader-ready Korean report HTML from simple Markdown chunks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path


URL_RE = re.compile(r"\b(?:https?://|www\.)[A-Za-z0-9.-]+\.[A-Za-z]{2,6}[^\s<)]*")
PAGE_RE = re.compile(r"^###\s+Page\s+(\d+)\s*$", re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ORDERED_LIST_RE = re.compile(r"^\d+\.\s+")
TABLE_ALIGN_RE = re.compile(r"^:?-{3,}:?$")
SAFE_BR_RE = re.compile(r"&lt;br\s*/?&gt;", re.IGNORECASE)


@dataclass(frozen=True)
class TocEntry:
    target: str
    label: str
    page: str | None = None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert simple Markdown translation chunks to a deterministic Korean "
            "report HTML shell with page sections, TOC, search, links, and table alignment."
        )
    )
    parser.add_argument("--input", required=True, type=Path, help="Input Markdown file.")
    parser.add_argument("--output", required=True, type=Path, help="Output HTML file.")
    parser.add_argument("--title", default="연차보고서 번역본", help="Reader-facing document title.")
    parser.add_argument("--date", default="", help="Optional reader-facing document date.")
    parser.add_argument(
        "--replacements-json",
        type=Path,
        help="Optional JSON object of exact text replacements applied before rendering.",
    )
    parser.add_argument(
        "--footer-pattern",
        action="append",
        default=[],
        help="Regex for a line to strip before rendering. Can be repeated.",
    )
    parser.add_argument(
        "--strip-line-regex",
        action="append",
        default=[],
        help="Additional regex for a line to strip before rendering. Can be repeated.",
    )
    return parser.parse_args(argv)


def fail(message: str, code: int = 2) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return code


def load_replacements(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in data.items()
    ):
        raise ValueError("--replacements-json must contain a JSON object of string replacements")
    return data


def apply_replacements(text: str, replacements: dict[str, str]) -> str:
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def strip_matching_lines(text: str, patterns: list[str]) -> str:
    if not patterns:
        return text
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    kept: list[str] = []
    for line in text.splitlines():
        visible_line = re.sub(r"<[^>]+>", "", line).strip()
        if any(pattern.search(visible_line) for pattern in compiled):
            continue
        kept.append(line)
    return "\n".join(kept)


def split_table_row(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]

    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in body:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    cells.append("".join(current).strip())
    return cells


def is_table_separator(cells: list[str]) -> bool:
    return bool(cells) and all(TABLE_ALIGN_RE.match(cell.strip()) for cell in cells)


def alignment_from_separator(cell: str) -> str:
    value = cell.strip()
    if value.startswith(":") and value.endswith(":"):
        return "center"
    if value.endswith(":"):
        return "right"
    return "left"


def looks_numeric(value: str) -> bool:
    clean = re.sub(r"<[^>]+>", "", value)
    clean = clean.replace("&nbsp;", " ")
    clean = re.sub(r"[▲▼,$₩£€¥%*()\s]", "", clean)
    clean = re.sub(r"\b(?:US|HK|RMB|CNY|USD|HKD|KRW|JPY)\b", "", clean, flags=re.IGNORECASE)
    if not clean or clean in {"-", "–", "—"}:
        return True
    return bool(re.fullmatch(r"[0-9./+\-–—~]+", clean))


def infer_alignments(headers: list[str], rows: list[list[str]], separator: list[str] | None) -> list[str]:
    column_count = len(headers) if headers else max((len(row) for row in rows), default=0)
    hints = [alignment_from_separator(cell) for cell in separator] if separator else []
    alignments: list[str] = []
    for column_index in range(column_count):
        if column_index == 0:
            alignments.append("left")
            continue
        values = [row[column_index] for row in rows if column_index < len(row)]
        if values and sum(1 for value in values if looks_numeric(value)) / len(values) >= 0.5:
            alignments.append("right")
            continue
        if values and sum(1 for value in values if len(re.sub(r"\s+", "", value)) <= 4) / len(values) >= 0.5:
            alignments.append("center")
            continue
        if column_index < len(hints) and hints[column_index] in {"right", "center"}:
            alignments.append(hints[column_index])
            continue
        alignments.append("left")
    return alignments


def linkify_escaped_text(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        label = match.group(0)
        href = label if label.startswith("http") else f"https://{label}"
        return f'<a href="{escape(href, quote=True)}" target="_blank">{label}</a>'

    return URL_RE.sub(replace, text)


def inline_markdown(text: str) -> str:
    text = text.replace(r"\#", "#").replace(r"\*", "*")
    rendered = escape(text, quote=True)
    rendered = SAFE_BR_RE.sub("<br>", rendered)
    rendered = re.sub(r"\*\*([^*]+?)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", rendered)
    return linkify_escaped_text(rendered)


def slugify(value: str, used: set[str]) -> str:
    base = re.sub(r"[^0-9A-Za-z가-힣_-]+", "-", value).strip("-").lower()
    if not base:
        base = "section"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


class Renderer:
    def __init__(self) -> None:
        self.html: list[str] = []
        self.toc: list[TocEntry] = []
        self.used_ids: set[str] = set()
        self.in_list = False
        self.list_tag = ""
        self.in_page = False
        self.current_page: str | None = None
        self.table_headers: list[str] = []
        self.table_separator: list[str] | None = None
        self.table_rows: list[list[str]] = []

    def close_list(self) -> None:
        if self.in_list:
            self.html.append(f"</{self.list_tag}>")
            self.in_list = False
            self.list_tag = ""

    def close_page(self) -> None:
        self.close_table()
        self.close_list()
        if self.in_page:
            self.html.append("</section>")
            self.in_page = False

    def start_page(self, page: str) -> None:
        self.close_page()
        page_id = slugify(f"page-{page}", self.used_ids)
        self.current_page = page
        self.in_page = True
        self.toc.append(TocEntry(page_id, f"페이지 {page}", page))
        self.html.append(f'<section id="{page_id}" class="report-page" data-page="{escape(page, quote=True)}">')
        self.html.append(f'  <div class="page-header">페이지 {escape(page)}</div>')

    def close_table(self) -> None:
        if not self.table_headers and not self.table_rows:
            return

        expected = len(self.table_headers)
        rows = [self.table_headers, *self.table_rows]
        for row in rows:
            if len(row) != expected:
                raise ValueError(f"table row has {len(row)} columns, expected {expected}")

        alignments = infer_alignments(self.table_headers, self.table_rows, self.table_separator)
        self.html.append('<div class="table-container"><table>')
        self.html.append("<thead><tr>")
        for index, cell in enumerate(self.table_headers):
            align = alignments[index] if index < len(alignments) else "left"
            self.html.append(f'<th class="{align}-cell">{inline_markdown(cell)}</th>')
        self.html.append("</tr></thead>")
        self.html.append("<tbody>")
        for row in self.table_rows:
            self.html.append("<tr>")
            for index, cell in enumerate(row):
                align = alignments[index] if index < len(alignments) else "left"
                rendered = inline_markdown(cell)
                rendered = rendered.replace("▲", '<span class="up-trend">▲</span>')
                rendered = rendered.replace("▼", '<span class="down-trend">▼</span>')
                self.html.append(f'<td class="{align}-cell">{rendered}</td>')
            self.html.append("</tr>")
        self.html.append("</tbody></table></div>")
        self.table_headers = []
        self.table_separator = None
        self.table_rows = []

    def add_table_line(self, line: str) -> None:
        self.close_list()
        cells = split_table_row(line)
        if is_table_separator(cells):
            self.table_separator = cells
            return
        if not self.table_headers:
            self.table_headers = cells
            return
        self.table_rows.append(cells)

    def add_heading(self, marker: str, text: str) -> None:
        self.close_table()
        self.close_list()
        level = min(len(marker), 6)
        heading_id = slugify(text, self.used_ids)
        if level <= 3:
            self.toc.append(TocEntry(heading_id, text, self.current_page))
        self.html.append(f'<h{level} id="{heading_id}">{inline_markdown(text)}</h{level}>')

    def add_list_item(self, tag: str, text: str) -> None:
        self.close_table()
        if not self.in_list or self.list_tag != tag:
            self.close_list()
            self.in_list = True
            self.list_tag = tag
            self.html.append(f"<{tag}>")
        self.html.append(f"<li>{inline_markdown(text)}</li>")

    def add_paragraph(self, text: str) -> None:
        self.close_table()
        self.close_list()
        self.html.append(f"<p>{inline_markdown(text)}</p>")

    def render(self, markdown: str) -> str:
        for raw_line in markdown.splitlines():
            line = raw_line.strip()
            if not line:
                self.close_table()
                self.close_list()
                continue

            page_match = PAGE_RE.match(line)
            if page_match:
                self.start_page(page_match.group(1))
                continue

            if line.startswith("|") and line.endswith("|"):
                self.add_table_line(line)
                continue

            heading_match = HEADING_RE.match(line)
            if heading_match:
                self.add_heading(heading_match.group(1), heading_match.group(2))
                continue

            if line.startswith(("- ", "* ")):
                self.add_list_item("ul", line[2:].strip())
                continue

            if ORDERED_LIST_RE.match(line):
                self.add_list_item("ol", ORDERED_LIST_RE.sub("", line).strip())
                continue

            if line == "---":
                self.close_table()
                self.close_list()
                self.html.append("<hr>")
                continue

            self.add_paragraph(line)

        self.close_page()
        self.close_table()
        self.close_list()
        return "\n".join(self.html)


def build_html(title: str, date: str, body: str, toc: list[TocEntry]) -> str:
    safe_title = escape(title, quote=True)
    safe_date = escape(date, quote=True)
    toc_lines: list[str] = []
    for entry in toc:
        page_label = ""
        if entry.page:
            page_label = f' <span class="toc-page-num">p. {escape(entry.page)}</span>'
        toc_lines.append(
            f'<li><a href="#{entry.target}" data-target="{entry.target}">'
            f"{escape(entry.label)}{page_label}</a></li>"
        )
    toc_html = "\n".join(toc_lines)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
  <style>
    :root {{
      --bg-color: #f7f9fb;
      --panel-bg: #ffffff;
      --text-color: #1f2933;
      --muted-color: #66788a;
      --border-color: #d9e2ec;
      --primary-color: #0b3c5d;
      --primary-light: #2f80b7;
      --sidebar-width: 300px;
      --up-color: #1f9d55;
      --down-color: #d64545;
    }}
    [data-theme="dark"] {{
      --bg-color: #101722;
      --panel-bg: #182231;
      --text-color: #e6edf5;
      --muted-color: #9fb0c3;
      --border-color: #2b3a4d;
      --primary-color: #8ec7ee;
      --primary-light: #72b7e8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: flex;
      background: var(--bg-color);
      color: var(--text-color);
      font-family: -apple-system, BlinkMacSystemFont, "Noto Sans KR", "Segoe UI", sans-serif;
      line-height: 1.75;
    }}
    aside {{
      position: fixed;
      inset: 0 auto 0 0;
      width: var(--sidebar-width);
      background: #0b2239;
      color: #ffffff;
      overflow-y: auto;
      border-right: 1px solid var(--border-color);
    }}
    .sidebar-header {{ padding: 24px; border-bottom: 1px solid rgba(255,255,255,0.14); }}
    .sidebar-header h2 {{ margin: 0; font-size: 19px; line-height: 1.35; }}
    .sidebar-header p {{ margin: 6px 0 0; color: #b7c6d6; font-size: 13px; }}
    .search-container {{ padding: 16px 24px; }}
    #search-bar {{
      width: 100%;
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 7px;
      padding: 9px 11px;
      background: rgba(255,255,255,0.08);
      color: #ffffff;
      font-size: 14px;
    }}
    #search-bar::placeholder {{ color: #b7c6d6; }}
    .sidebar-menu {{ list-style: none; margin: 0; padding: 0 12px 24px; }}
    .sidebar-menu a {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 8px 10px;
      border-radius: 6px;
      color: #d7e2ee;
      text-decoration: none;
      font-size: 13px;
    }}
    .sidebar-menu a:hover, .sidebar-menu a.active {{ background: rgba(255,255,255,0.12); color: #ffffff; }}
    .toc-page-num {{ white-space: nowrap; color: #b7c6d6; }}
    main {{ margin-left: var(--sidebar-width); width: calc(100% - var(--sidebar-width)); min-width: 0; }}
    header {{
      position: sticky;
      top: 0;
      z-index: 10;
      min-height: 66px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 32px;
      background: var(--panel-bg);
      border-bottom: 1px solid var(--border-color);
    }}
    .header-title {{ font-weight: 700; }}
    button {{
      border: 1px solid var(--border-color);
      border-radius: 7px;
      background: transparent;
      color: var(--text-color);
      padding: 8px 12px;
      cursor: pointer;
    }}
    .content-container {{ max-width: 1060px; margin: 0 auto; padding: 36px 44px 64px; }}
    .report-page {{
      position: relative;
      margin: 0 0 34px;
      padding: 42px 44px 38px;
      background: var(--panel-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
    }}
    .page-header {{
      position: absolute;
      top: 14px;
      right: 18px;
      color: var(--muted-color);
      font-size: 12px;
      font-weight: 700;
    }}
    h1, h2, h3, h4, h5, h6 {{ color: var(--primary-color); line-height: 1.35; }}
    h1 {{ font-size: 28px; margin: 0 0 24px; }}
    h2 {{ font-size: 22px; margin: 32px 0 16px; }}
    h3 {{ font-size: 18px; margin: 28px 0 14px; }}
    p {{ margin: 0 0 18px; }}
    a {{ color: var(--primary-light); text-decoration: none; border-bottom: 1px solid currentColor; }}
    ul, ol {{ margin: 0 0 20px; padding-left: 24px; }}
    li {{ margin: 0 0 7px; }}
    .table-container {{ overflow-x: auto; margin: 26px 0; border: 1px solid var(--border-color); border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--border-color); vertical-align: top; }}
    th {{ background: rgba(11,60,93,0.08); font-weight: 700; }}
    tr:last-child td {{ border-bottom: 0; }}
    .left-cell {{ text-align: left; }}
    .right-cell {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .center-cell {{ text-align: center; }}
    .up-trend {{ color: var(--up-color); font-weight: 700; }}
    .down-trend {{ color: var(--down-color); font-weight: 700; }}
    .hidden-by-search {{ display: none; }}
    @media (max-width: 900px) {{
      body {{ display: block; }}
      aside {{ position: static; width: 100%; max-height: 300px; }}
      main {{ margin-left: 0; width: 100%; }}
      .content-container {{ padding: 24px 16px 48px; }}
      .report-page {{ padding: 38px 18px 26px; }}
    }}
  </style>
</head>
<body>
  <aside>
    <div class="sidebar-header">
      <h2>{safe_title}</h2>
      <p>{safe_date if safe_date else "한국어 번역본"}</p>
    </div>
    <div class="search-container"><input id="search-bar" type="search" placeholder="본문 검색"></div>
    <ul class="sidebar-menu">{toc_html}</ul>
  </aside>
  <main>
    <header>
      <div class="header-title">{safe_title}</div>
      <button id="theme-toggle" type="button">다크 모드</button>
    </header>
    <div class="content-container">
{body}
    </div>
  </main>
  <script>
    const root = document.documentElement;
    const themeToggle = document.getElementById('theme-toggle');
    const savedTheme = localStorage.getItem('translation-theme');
    if (savedTheme === 'dark') {{
      root.setAttribute('data-theme', 'dark');
      themeToggle.textContent = '라이트 모드';
    }}
    themeToggle.addEventListener('click', () => {{
      const dark = root.getAttribute('data-theme') === 'dark';
      if (dark) {{
        root.removeAttribute('data-theme');
        localStorage.setItem('translation-theme', 'light');
        themeToggle.textContent = '다크 모드';
      }} else {{
        root.setAttribute('data-theme', 'dark');
        localStorage.setItem('translation-theme', 'dark');
        themeToggle.textContent = '라이트 모드';
      }}
    }});

    const search = document.getElementById('search-bar');
    const pages = Array.from(document.querySelectorAll('.report-page'));
    search.addEventListener('input', () => {{
      const needle = search.value.trim().toLowerCase();
      pages.forEach((page) => {{
        page.classList.toggle('hidden-by-search', Boolean(needle) && !page.textContent.toLowerCase().includes(needle));
      }});
    }});

    const links = Array.from(document.querySelectorAll('.sidebar-menu a'));
    const byId = new Map(links.map((link) => [link.getAttribute('data-target'), link]));
    window.addEventListener('scroll', () => {{
      let current = null;
      pages.forEach((page) => {{
        if (window.scrollY >= page.offsetTop - 90) current = page.id;
      }});
      links.forEach((link) => link.classList.remove('active'));
      if (current && byId.has(current)) byId.get(current).classList.add('active');
    }});
  </script>
</body>
</html>
"""


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.input.exists():
        return fail(f"input file does not exist: {args.input}")

    try:
        text = args.input.read_text(encoding="utf-8")
        replacements = load_replacements(args.replacements_json)
        text = apply_replacements(text, replacements)
        text = strip_matching_lines(text, [*args.footer_pattern, *args.strip_line_regex])
        renderer = Renderer()
        body = renderer.render(text)
        output = build_html(args.title, args.date, body, renderer.toc)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return fail(str(exc))

    print(f"HTML generated: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
