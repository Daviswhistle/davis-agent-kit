#!/usr/bin/env python3
"""One UTF-8 Markdown source, a disposable index, and bounded section access."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Any, BinaryIO, Iterator

ID = re.compile(r"[A-Za-z][A-Za-z0-9._-]{0,127}\Z")
MARKER = re.compile(r"<!-- section: (\{.*\}) -->[ \t]*\Z")
FENCE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)\Z")
META_KEYS = {"id", "title", "summary", "tags", "related"}


class StoreError(ValueError):
    """A rejected operation; CLI callers receive exit code 2."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - META_KEYS:
        raise StoreError("marker must contain only id, title, summary, tags, related")
    result = dict(value)
    for key in ("id", "title", "summary"):
        if not isinstance(result.get(key), str) or not result[key].strip():
            raise StoreError(f"marker requires a non-empty {key}")
    if not ID.fullmatch(result["id"]):
        raise StoreError("id must be a stable ASCII identifier (letters, digits, . _ -)")
    for key in ("tags", "related"):
        items = result.setdefault(key, [])
        if not isinstance(items, list) or any(not isinstance(x, str) or not x.strip() for x in items):
            raise StoreError(f"{key} must be a list of non-empty strings")
        if len(items) != len(set(items)):
            raise StoreError(f"duplicate {key}")
    if any(not ID.fullmatch(x) for x in result["related"]):
        raise StoreError("related must contain section IDs")
    return result


def make_index(data: bytes) -> dict[str, Any]:
    data.decode("utf-8")  # Strict decoding; offsets always refer to original bytes.
    lines = data.splitlines(keepends=True)
    entries: list[dict[str, Any]] = []
    offset = 0
    seen: set[str] = set()
    fence: str | None = None
    for number, raw in enumerate(lines, 1):
        line = raw.decode("utf-8").rstrip("\r\n")
        if number == 1:
            line = line.removeprefix("\ufeff")
        if not entries and line.strip() and not line.startswith("<!-- section:"):
            raise StoreError("put all content under a section marker; no unindexed preamble")
        if fence:
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*", line):
                fence = None
        else:
            match = FENCE.fullmatch(line)
            if match and (match[1][0] == "~" or "`" not in match[2]):
                fence = match[1]
            elif line.lstrip().startswith("<!-- section:"):
                marker = MARKER.fullmatch(line)
                if not marker:
                    raise StoreError(f"line {number}: malformed marker; use a single column-zero JSON marker")
                entry = metadata(json.loads(marker[1]))
                if entry["id"] in seen:
                    raise StoreError(f"duplicate section ID: {entry['id']}")
                seen.add(entry["id"])
                if entries:
                    entries[-1].update(end_line=number - 1, end_byte=offset)
                entries.append(dict(entry, start_line=number, body_start_line=number + 1,
                                    start_byte=offset, body_start_byte=offset + len(raw)))
            elif not entries and line.strip():
                raise StoreError("put all content under a section marker; no unindexed preamble")
        offset += len(raw)
    if fence:
        raise StoreError("unclosed fenced code block; refusing to hide later section markers")
    if not entries:
        raise StoreError("no section markers found")
    entries[-1].update(end_line=len(lines), end_byte=len(data))
    ids = {entry["id"] for entry in entries}
    for entry in entries:
        missing = set(entry["related"]) - ids
        if missing:
            raise StoreError(f"{entry['id']}: unknown related IDs: {', '.join(sorted(missing))}")
        entry["sha256"] = digest(data[entry["start_byte"]:entry["end_byte"]])
    result = dict(version=1, source_sha256=digest(data), source_bytes=len(data), sections=entries)
    result["index_sha256"] = digest(encoded(result))
    return result


def index_path(source: Path) -> Path:
    return source.with_name(source.name + ".index.json")


def file_digest(stream: BinaryIO) -> str:
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        value.update(block)
    return value.hexdigest()


def load_index(source: Path) -> dict[str, Any]:
    path = index_path(source)
    if path.is_symlink():
        raise StoreError("index must not be a symlink")
    try:
        index = json.loads(path.read_bytes())
        checksum = index.pop("index_sha256")
        if checksum != digest(encoded(index)) or index["version"] != 1:
            raise StoreError("index checksum/version mismatch; run build")
        index["index_sha256"] = checksum
        if (type(index["source_bytes"]) is not int or index["source_bytes"] < 0 or
                not isinstance(index["source_sha256"], str) or
                not re.fullmatch(r"[0-9a-f]{64}", index["source_sha256"])):
            raise StoreError("invalid source identity in index; run build")
        if not isinstance(index["sections"], list) or not index["sections"]:
            raise StoreError("invalid index sections; run build")
        previous_end = 0
        ids: set[str] = set()
        for entry in index["sections"]:
            metadata({key: entry[key] for key in META_KEYS})
            bounds = [entry[key] for key in ("start_byte", "body_start_byte", "end_byte")]
            if (any(type(x) is not int for x in bounds) or
                    not previous_end <= bounds[0] <= bounds[1] <= bounds[2] <= index["source_bytes"] or
                    entry["id"] in ids):
                raise StoreError("invalid index ranges/IDs; run build")
            line_bounds = [entry[key] for key in ("start_line", "body_start_line", "end_line")]
            if (any(type(x) is not int for x in line_bounds) or
                    not 1 <= line_bounds[0] <= line_bounds[2] or line_bounds[1] != line_bounds[0] + 1 or
                    not isinstance(entry["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])):
                raise StoreError("invalid section metadata in index; run build")
            ids.add(entry["id"])
            previous_end = bounds[2]
    except (OSError, UnicodeError, KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise StoreError(f"index missing or invalid; run build: {exc}") from exc
    return index


@contextmanager
def snapshot(source: Path) -> Iterator[tuple[dict[str, Any], BinaryIO]]:
    # Readers never repair caches or require write access. A mid-commit pair fails closed.
    index = load_index(source)
    with source.open("rb") as stream:
        if file_digest(stream) != index["source_sha256"]:
            raise StoreError("stale index: source changed; run build, then retry")
        yield index, stream


def catalog(source: Path, query: str = "", offset: int = 0, limit: int = 50) -> dict[str, Any]:
    if offset < 0 or limit < 1:
        raise StoreError("offset must be >= 0 and limit must be >= 1")
    with snapshot(source) as (index, _):
        words = query.casefold().split()
        matches = [entry for entry in index["sections"] if all(
            word in " ".join([entry["id"], entry["title"], entry["summary"], *entry["tags"]]).casefold()
            for word in words)]
        return dict(source_sha256=index["source_sha256"], total_sections=len(index["sections"]),
                    matches=len(matches), offset=offset,
                    next_offset=offset + limit if offset + limit < len(matches) else None,
                    sections=matches[offset:offset + limit])


def read_sections(source: Path, ids: list[str], related: bool = False,
                  max_bytes: int = 65536) -> dict[str, Any]:
    if not ids or max_bytes < 1:
        raise StoreError("request at least one ID and a positive max-bytes")
    with snapshot(source) as (index, stream):
        by_id = {entry["id"]: entry for entry in index["sections"]}
        selected = list(dict.fromkeys(ids))
        if any(key not in by_id for key in selected):
            raise StoreError("unknown section ID")
        if related:
            selected = list(dict.fromkeys(selected + [ref for key in selected for ref in by_id[key]["related"]]))
        if any(key not in by_id for key in selected):
            raise StoreError("invalid related ID in index; run build")
        if sum(by_id[key]["end_byte"] - by_id[key]["start_byte"] for key in selected) > max_bytes:
            raise StoreError("selection exceeds max-bytes; choose fewer/smaller sections or raise the explicit limit")
        result = []
        for key in selected:
            entry = by_id[key]
            stream.seek(entry["start_byte"])
            raw = stream.read(entry["end_byte"] - entry["start_byte"])
            if digest(raw) != entry["sha256"]:
                raise StoreError("section changed during read or index is corrupt; rebuild and retry")
            body = raw[entry["body_start_byte"] - entry["start_byte"]:].decode("utf-8")
            result.append(dict(entry, body=body))
        return dict(source_sha256=index["source_sha256"], sections=result)


@contextmanager
def writer(source: Path) -> Iterator[None]:
    lock = source.with_name(source.name + ".lock")
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise StoreError(f"writer lock exists: {lock}; check the owner before removing a stale lock") from exc
    try:
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(f"pid={os.getpid()}\n")
        cache = index_path(source)
        if cache.is_symlink() or (cache.exists() and not cache.is_file()):
            raise StoreError("index destination must be a regular file or absent")
        yield
    finally:
        lock.unlink()


def atomic_write(path: Path, data: bytes, create: bool = False) -> None:
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    temp = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            temp.chmod(stat.S_IMODE(path.stat().st_mode))
        if create:
            os.link(temp, path)  # No-clobber publication; never overwrite a racing creator.
        else:
            os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def build(source: Path) -> dict[str, Any]:
    with writer(source):
        data = source.read_bytes()
        index = make_index(data)
        if source.read_bytes() != data:
            raise StoreError("source changed during build; retry after the other writer finishes")
        atomic_write(index_path(source), encoded(index))
        return dict(source_sha256=index["source_sha256"], sections=len(index["sections"]), index=str(index_path(source)))


def commit_source(source: Path, data: bytes, index: dict[str, Any], create: bool = False) -> dict[str, Any]:
    atomic_write(source, data, create=create)
    try:
        atomic_write(index_path(source), encoded(index))
    except OSError as exc:
        raise StoreError(f"SOURCE SAVED but index update failed; run build before reading: {exc}") from exc
    return dict(source_sha256=index["source_sha256"], sections=len(index["sections"]), index=str(index_path(source)))


def section_bytes(meta: dict[str, Any], body: bytes) -> bytes:
    meta = metadata(meta)
    body.decode("utf-8")
    marker = "<!-- section: " + json.dumps(meta, ensure_ascii=False) + " -->\n"
    return marker.encode("utf-8") + body


def create_store(source: Path, meta: dict[str, Any], body: bytes) -> dict[str, Any]:
    data = section_bytes(meta, body)
    index = make_index(data)
    if len(index["sections"]) != 1:
        raise StoreError("body must not introduce section markers outside code fences")
    with writer(source):
        return commit_source(source, data, index, create=True)


def change(source: Path, section_id: str, body: bytes, expected: str,
           new_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    body.decode("utf-8")
    with writer(source):
        old = source.read_bytes()
        if digest(old) != expected:
            raise StoreError("source version conflict; read the current section and reconcile before retrying")
        before = make_index(old)
        ids = [entry["id"] for entry in before["sections"]]
        if new_meta is not None:
            if section_id in ids or new_meta.get("id") != section_id:
                raise StoreError("append requires a new, matching section ID")
            data = old + (b"\n" if not old.endswith(b"\n") else b"") + section_bytes(new_meta, body)
            expected_ids = ids + [section_id]
        else:
            entries = [entry for entry in before["sections"] if entry["id"] == section_id]
            if not entries:
                raise StoreError("unknown section ID")
            entry = entries[0]
            if entry["end_byte"] < len(old) and body and not body.endswith(b"\n"):
                body += b"\r\n" if old[entry["body_start_byte"] - 2:entry["body_start_byte"]] == b"\r\n" else b"\n"
            prefix = old[:entry["body_start_byte"]]
            if body and not prefix.endswith(b"\n"):
                prefix += b"\n"
            data = prefix + body + old[entry["end_byte"]:]
            expected_ids = ids
        after = make_index(data)
        if [entry["id"] for entry in after["sections"]] != expected_ids:
            raise StoreError("body must not introduce or hide section markers")
        if source.read_bytes() != old:
            raise StoreError("source changed outside the writer lock; reconcile before retrying")
        return commit_source(source, data, after)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "build", "check", "list", "read", "replace", "append"):
        command = commands.add_parser(name)
        command.add_argument("--source", type=Path, default=Path("PROJECT.md"))
        if name in ("init", "append"):
            command.add_argument("--id", required=True)
            command.add_argument("--title", required=True)
            command.add_argument("--summary", required=True)
            command.add_argument("--tag", action="append", default=[])
            command.add_argument("--related", action="append", default=[])
        if name in ("init", "replace", "append"):
            command.add_argument("--body-file", type=Path, required=True)
        if name in ("replace", "append"):
            command.add_argument("--expect-source", required=True, help="source_sha256 from the last read/list")
        if name == "replace":
            command.add_argument("--id", required=True)
        if name == "list":
            command.add_argument("--query", default="")
            command.add_argument("--offset", type=int, default=0)
            command.add_argument("--limit", type=int, default=50)
        if name == "read":
            command.add_argument("--id", action="append", required=True)
            command.add_argument("--related", action="store_true", help="also read direct related sections (one hop)")
            command.add_argument("--max-bytes", type=int, default=65536)
    args = parser.parse_args(argv)
    try:
        source = args.source.expanduser().resolve()
        if args.command == "build":
            result = build(source)
        elif args.command == "check":
            with snapshot(source) as (index, _):
                result = dict(source_sha256=index["source_sha256"], valid=True)
        elif args.command == "list":
            result = catalog(source, args.query, args.offset, args.limit)
        elif args.command == "read":
            result = read_sections(source, args.id, args.related, args.max_bytes)
        else:
            body = args.body_file.expanduser().read_bytes()
            meta = dict(id=args.id, title=args.title, summary=args.summary,
                        tags=args.tag, related=args.related) if args.command != "replace" else None
            result = (create_store(source, meta, body) if args.command == "init" else
                      change(source, args.id, body, args.expect_source, meta))
        # Explicit UTF-8 also works with redirected Windows stdout.
        sys.stdout.buffer.write(encoded(result))
        return 0
    except (StoreError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"section-store: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
