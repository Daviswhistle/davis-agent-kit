from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "store.py"
spec = importlib.util.spec_from_file_location("section_store", SCRIPT)
store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store)


def meta(key="goal", **kwargs):
    return dict(id=key, title=key, summary=f"About {key}", **kwargs)


def section(key="goal", body="body\n", **kwargs):
    return store.section_bytes(meta(key, **kwargs), body.encode("utf-8"))


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "프로젝트 문서.md"

    def seed(self, data=None):
        self.source.write_bytes(data if data is not None else section() + section("checks", "검증 📌\n"))
        return store.build(self.source)["source_sha256"]

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args, "--source", str(self.source)],
                              capture_output=True, timeout=10)

    def test_unicode_crlf_offsets_and_lines(self):
        data = (section("goal", "목표 😀\n두 번째 줄\n") + section("checks", "검증\n")).replace(b"\n", b"\r\n")
        self.seed(data)
        result = store.read_sections(self.source, ["checks"])
        self.assertEqual(result["sections"][0]["body"], "검증\r\n")
        entry = result["sections"][0]
        self.assertEqual((entry["start_line"], entry["body_start_line"], entry["end_line"]), (4, 5, 5))
        self.assertEqual(data[entry["body_start_byte"]:entry["end_byte"]], "검증\r\n".encode())

    def test_empty_final_body_bom_and_no_final_newline(self):
        self.seed(b"\xef\xbb\xbf" + section(body="").rstrip(b"\n"))
        result = store.read_sections(self.source, ["goal"])
        self.assertEqual(result["sections"][0]["body"], "")
        store.change(self.source, "goal", b"new", result["source_sha256"])
        self.assertEqual(store.read_sections(self.source, ["goal"])["sections"][0]["body"], "new")

    def test_fenced_marker_examples_are_not_sections(self):
        for fence in ("```", "~~~~", "   ````"):
            data = section("goal", fence + "text\n" + section("fake").decode() + fence + "\n")
            with self.subTest(fence=fence):
                self.assertEqual(len(store.make_index(data)["sections"]), 1)

    def test_shorter_fence_does_not_close_block(self):
        data = section(body="````\n```\n" + section("fake").decode() + "````\n")
        self.assertEqual(len(store.make_index(data)["sections"]), 1)

    def test_reject_hidden_or_unindexed_content(self):
        for data in (b"# Lost preamble\n" + section(),
                     b"```\nhidden\n```\n" + section(), section(body="```\nunclosed\n")):
            with self.subTest(data=data):
                with self.assertRaises(store.StoreError):
                    store.make_index(data)

    def test_reject_duplicate_malformed_and_dangling_markers(self):
        cases = [section() + section(), b"<!-- section: not JSON -->\n", b" " + section(),
                 section(related=["missing"]), b'<!-- section: {"id":"goal"} -->\n',
                 section() + b'<!-- section: {bad} -->\n', b"no markers"]
        for data in cases:
            with self.subTest(data=data):
                with self.assertRaises((store.StoreError, json.JSONDecodeError)):
                    store.make_index(data)

    def test_reject_invalid_metadata(self):
        for value in ([], meta(tags="tag"), meta(tags=[1]), meta(tags=["x", "x"]),
                      meta(related=["bad id"]), dict(meta(), title=""), dict(meta(), surprise=1)):
            with self.subTest(value=value):
                with self.assertRaises(store.StoreError):
                    store.metadata(value)

    def test_invalid_utf8_is_not_repaired(self):
        with self.assertRaises(UnicodeError):
            store.make_index(section() + b"\xff")

    def test_index_deterministic_and_rebuild_recovers(self):
        self.seed()
        first = store.index_path(self.source).read_bytes()
        store.build(self.source)
        self.assertEqual(first, store.index_path(self.source).read_bytes())
        store.index_path(self.source).write_text("broken")
        with self.assertRaises(store.StoreError):
            store.catalog(self.source)
        store.build(self.source)
        self.assertEqual(store.catalog(self.source)["total_sections"], 2)

    def test_catalog_metadata_only_query_and_pagination(self):
        self.seed(section("goal", "secret body phrase\n", tags=["자막", "VIDEO"]) + section("checks"))
        result = store.catalog(self.source, "자막 video")
        self.assertEqual([x["id"] for x in result["sections"]], ["goal"])
        self.assertNotIn("body", result["sections"][0])
        self.assertEqual(store.catalog(self.source, "secret body phrase")["matches"], 0)
        page = store.catalog(self.source, limit=1)
        self.assertEqual(page["next_offset"], 1)
        self.assertEqual(store.catalog(self.source, offset=1, limit=1)["sections"][0]["id"], "checks")
        for offset, limit in ((-1, 1), (0, 0)):
            with self.assertRaises(store.StoreError):
                store.catalog(self.source, offset=offset, limit=limit)

    def test_related_is_one_hop_and_deduplicated(self):
        self.seed(section("goal", related=["checks"]) + section("checks", related=["other"]) + section("other"))
        result = store.read_sections(self.source, ["goal", "goal"], related=True)
        self.assertEqual([x["id"] for x in result["sections"]], ["goal", "checks"])

    def test_unknown_id_and_output_budget_are_errors(self):
        self.seed()
        for ids, budget in ((["absent"], 999), (["goal"], 1), ([], 999), (["goal"], 0)):
            with self.assertRaises(store.StoreError):
                store.read_sections(self.source, ids, max_bytes=budget)

    def test_same_size_same_mtime_change_is_stale(self):
        self.seed()
        stamp = self.source.stat()
        self.source.write_bytes(self.source.read_bytes().replace(b"body", b"BODY"))
        os.utime(self.source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        for action in (store.catalog, lambda p: store.read_sections(p, ["goal"])):
            with self.assertRaisesRegex(store.StoreError, "stale"):
                action(self.source)
        store.build(self.source)
        self.assertEqual(store.read_sections(self.source, ["goal"])["sections"][0]["body"], "BODY\n")

    def test_checksum_detects_cache_edit(self):
        self.seed()
        path = store.index_path(self.source)
        path.write_bytes(path.read_bytes().replace(b"About goal", b"Wrong goal"))
        with self.assertRaisesRegex(store.StoreError, "checksum"):
            store.catalog(self.source)

    def test_replace_keeps_id_and_other_bytes_and_moves_lines(self):
        expected = self.seed()
        before = self.source.read_bytes()
        other = before[before.index(b'<!-- section: {"id": "checks"'):]
        store.change(self.source, "goal", "一\n二\n三".encode(), expected)
        self.assertTrue(self.source.read_bytes().endswith(other))
        result = store.read_sections(self.source, ["goal", "checks"])
        self.assertEqual(result["sections"][0]["body"], "一\n二\n三\n")
        self.assertEqual(result["sections"][1]["start_line"], 5)

    def test_replace_empty_body(self):
        expected = self.seed()
        store.change(self.source, "goal", b"", expected)
        self.assertEqual(store.read_sections(self.source, ["goal"])["sections"][0]["body"], "")
        self.assertEqual(store.catalog(self.source)["total_sections"], 2)

    def test_stale_writer_cannot_overwrite_newer_change(self):
        expected = self.seed()
        store.change(self.source, "goal", b"first writer\n", expected)
        before = self.source.read_bytes()
        with self.assertRaisesRegex(store.StoreError, "version conflict"):
            store.change(self.source, "checks", b"second writer\n", expected)
        self.assertEqual(self.source.read_bytes(), before)

    def test_replacement_cannot_inject_or_hide_sections(self):
        expected = self.seed()
        original = self.source.read_bytes()
        for body in (section("injected"), b"```\n", b"bad\xff"):
            with self.subTest(body=body):
                with self.assertRaises((store.StoreError, UnicodeError)):
                    store.change(self.source, "goal", body, expected)
                self.assertEqual(self.source.read_bytes(), original)

    def test_append_and_reference_existing_id(self):
        expected = self.seed(section(body="no terminal newline"))
        result = store.change(self.source, "checks", b"verified\n", expected, meta("checks", related=["goal"]))
        self.assertEqual(result["sections"], 2)
        self.assertEqual(store.read_sections(self.source, ["checks"])["sections"][0]["body"], "verified\n")
        with self.assertRaises(store.StoreError):
            store.change(self.source, "checks", b"duplicate", result["source_sha256"], meta("checks"))

    def test_init_no_clobber_and_no_injected_marker(self):
        store.create_store(self.source, meta(), b"first\n")
        with self.assertRaises(FileExistsError):
            store.create_store(self.source, meta(), b"overwrite\n")
        self.assertEqual(store.read_sections(self.source, ["goal"])["sections"][0]["body"], "first\n")
        with self.assertRaises(store.StoreError):
            store.create_store(self.root / "new.md", meta(), section("extra"))

    def test_live_writer_lock_blocks_mutation_but_not_reads(self):
        expected = self.seed()
        with store.writer(self.source):
            self.assertEqual(store.catalog(self.source)["total_sections"], 2)
            with self.assertRaisesRegex(store.StoreError, "writer lock"):
                store.change(self.source, "goal", b"overwrite", expected)
        self.assertFalse(self.source.with_name(self.source.name + ".lock").exists())

    def test_two_process_writers_cannot_both_commit_same_version(self):
        expected = self.seed()
        body = self.root / "body.txt"
        body.write_bytes(b"new body\n")
        args = [sys.executable, str(SCRIPT), "replace", "--source", str(self.source), "--id", "goal",
                "--body-file", str(body), "--expect-source", expected]
        processes = [subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        outputs = [proc.communicate(timeout=10) for proc in processes]
        self.assertEqual(sorted(proc.returncode for proc in processes), [0, 2], outputs)
        self.assertEqual(store.read_sections(self.source, ["goal"])["sections"][0]["body"], "new body\n")

    def test_source_saved_index_failure_is_explicit_and_recoverable(self):
        expected = self.seed()
        write = store.atomic_write
        def fail_cache(path, data, create=False):
            if path == store.index_path(self.source):
                raise OSError("simulated disk failure")
            write(path, data, create=create)
        with patch.object(store, "atomic_write", side_effect=fail_cache):
            with self.assertRaisesRegex(store.StoreError, "SOURCE SAVED"):
                store.change(self.source, "goal", b"new body\n", expected)
        with self.assertRaisesRegex(store.StoreError, "stale"):
            store.catalog(self.source)
        store.build(self.source)
        self.assertEqual(store.read_sections(self.source, ["goal"])["sections"][0]["body"], "new body\n")

    def test_atomic_source_failure_preserves_original_and_cleans_temp(self):
        expected = self.seed()
        original = self.source.read_bytes()
        with patch.object(store.os, "replace", side_effect=OSError("simulated failure")):
            with self.assertRaises(OSError):
                store.change(self.source, "goal", b"new body", expected)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(len(list(self.root.iterdir())), 2)

    def test_symlink_cache_cannot_overwrite_target(self):
        self.source.write_bytes(section())
        target = self.root / "other.txt"
        target.write_bytes(b"do not touch")
        try:
            store.index_path(self.source).symlink_to(target)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(store.StoreError):
            store.build(self.source)
        self.assertEqual(target.read_bytes(), b"do not touch")

    @unittest.skipIf(os.name == "nt", "POSIX mode test")
    def test_replace_preserves_permission_bits(self):
        expected = self.seed()
        self.source.chmod(0o640)
        store.change(self.source, "goal", b"changed", expected)
        self.assertEqual(self.source.stat().st_mode & 0o777, 0o640)

    def test_cli_end_to_end_and_errors(self):
        body = self.root / "본문.txt"
        body.write_text("유니코드 본문\n", encoding="utf-8")
        result = self.cli("init", "--id", "goal", "--title", "목적", "--summary", "프로젝트 목적",
                          "--body-file", str(body))
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.cli("read", "--id", "goal")
        self.assertEqual(json.loads(result.stdout)["sections"][0]["body"], "유니코드 본문\n")
        self.assertEqual(self.cli("check").returncode, 0)
        result = self.cli("read", "--id", "missing")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertNotIn(b"Traceback", result.stderr)
        self.source.write_bytes(self.source.read_bytes() + b"changed\n")
        self.assertEqual(self.cli("check").returncode, 2)
        self.assertEqual(self.cli("build").returncode, 0)
        self.assertEqual(self.cli("check").returncode, 0)

    def test_read_uses_existing_index_without_reparsing_or_writing(self):
        self.seed()
        with patch.object(store, "make_index", side_effect=AssertionError("must not reparse")), \
             patch.object(store, "atomic_write", side_effect=AssertionError("must not write")):
            self.assertEqual(store.catalog(self.source)["total_sections"], 2)
            self.assertEqual(store.read_sections(self.source, ["goal"])["sections"][0]["body"], "body\n")

    def test_changed_selected_bytes_after_hash_are_rejected(self):
        self.seed()
        original_digest = store.file_digest
        def race(stream):
            expected = original_digest(stream)
            self.source.write_bytes(self.source.read_bytes().replace(b"body", b"BODY"))
            return expected
        with patch.object(store, "file_digest", side_effect=race):
            with self.assertRaisesRegex(store.StoreError, "changed during read"):
                store.read_sections(self.source, ["goal"])

    def test_large_body_not_returned_by_catalog(self):
        self.seed(section(body="private body\n" * 10000))
        self.assertLess(len(store.encoded(store.catalog(self.source))), 2000)
        with self.assertRaises(store.StoreError):
            store.read_sections(self.source, ["goal"])


if __name__ == "__main__":
    unittest.main()
