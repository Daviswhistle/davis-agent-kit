from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from kit_manifest import load_manifest, validate_manifest  # noqa: E402
from validate_kit import discover_helper_smoke_checks, discover_test_suites  # noqa: E402


class ToolingContractTests(unittest.TestCase):
    def test_manifest_covers_every_installed_skill(self) -> None:
        manifest = load_manifest(ROOT)

        self.assertEqual(manifest.schema_version, 1)
        self.assertRegex(manifest.kit_version, r"^\d+\.\d+\.\d+")
        self.assertEqual(manifest.minimum_python, (3, 11))
        self.assertEqual(validate_manifest(manifest, ROOT), [])
        self.assertEqual(
            {skill.name for skill in manifest.skills},
            {
                "translation-quality",
                "handoff-agent-builder",
                "software-engineering",
                "writing-quality",
            },
        )
        self.assertEqual(
            set(manifest.install.retired_skills),
            {"davis-operating-system", "coding-workflow"},
        )

    def test_manifest_reports_broken_skill_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Test\n", encoding="utf-8")

            listed = root / "skills" / "listed"
            listed.mkdir(parents=True)
            (listed / "SKILL.md").write_text(
                "---\n"
                "name: listed\n"
                "---\n"
                "# Listed\n\n"
                "Read `references/missing.md` and `references/../escape.md`.\n",
                encoding="utf-8",
            )

            unlisted = root / "skills" / "unlisted"
            unlisted.mkdir(parents=True)
            (unlisted / "SKILL.md").write_text(
                "---\nname: unlisted\ndescription: Unlisted test skill.\n---\n",
                encoding="utf-8",
            )

            (root / "kit.toml").write_text(
                'schema_version = 1\n'
                'kit_version = "0.1.0"\n'
                'minimum_python = "3.11"\n'
                'normative_source = "AGENTS.md"\n\n'
                '[install]\n'
                'kit_link = "davis-agent-kit"\n'
                'agents_link = "AGENTS.md"\n'
                'skills_dir = "skills"\n'
                'retired_skills = ["listed"]\n\n'
                '[[skills]]\n'
                'name = "listed"\n'
                'path = "skills/listed"\n'
                'entrypoint = "SKILL.md"\n',
                encoding="utf-8",
            )

            errors = validate_manifest(load_manifest(root), root)

        joined = "\n".join(errors)
        self.assertIn("active skills also listed as retired: listed", joined)
        self.assertIn("skill description is missing or empty", joined)
        self.assertIn("missing resource referenced", joined)
        self.assertIn("unsafe resource referenced", joined)
        self.assertIn("skills missing from manifest: skills/unlisted", joined)

    def test_validate_kit_discovers_all_test_directories_and_helpers(self) -> None:
        suite_names = {check.name for check in discover_test_suites(ROOT)}
        expected_test_dirs = {
            path.relative_to(ROOT).as_posix()
            for path in [ROOT / "tests", *sorted(ROOT.glob("skills/*/tests"))]
            if path.is_dir() and any(path.glob("test*.py"))
        }
        self.assertEqual(
            suite_names,
            {f"unittest:{path}" for path in expected_test_dirs},
        )

        helper_names = {check.name for check in discover_helper_smoke_checks(ROOT)}
        expected_helpers = {
            f"helper-help:{path.relative_to(ROOT).as_posix()}"
            for path in ROOT.glob("skills/*/scripts/*.py")
        }
        self.assertEqual(helper_names, expected_helpers)

    def test_ci_runs_the_single_validation_entrypoint(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn('python-version: "3.11"', workflow)
        self.assertIn("python3 scripts/validate_kit.py", workflow)
        self.assertTrue((ROOT / "scripts" / "doctor.py").is_file())
        self.assertTrue((ROOT / "scripts" / "validate_kit.py").is_file())

    @unittest.skipIf(os.name == "nt", "symlink contract is POSIX-oriented")
    def test_doctor_accepts_exact_codex_install_links(self) -> None:
        manifest = load_manifest(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / ".codex"
            skills_home = codex_home / manifest.install.skills_dir
            skills_home.mkdir(parents=True)

            (codex_home / manifest.install.kit_link).symlink_to(
                ROOT, target_is_directory=True
            )
            (codex_home / manifest.install.agents_link).symlink_to(
                ROOT / manifest.normative_source
            )
            for skill in manifest.skills:
                (skills_home / skill.name).symlink_to(
                    skill.root(ROOT), target_is_directory=True
                )

            completed = subprocess.run(
                (
                    sys.executable,
                    str(ROOT / "scripts" / "doctor.py"),
                    "--root",
                    str(ROOT),
                    "--codex-home",
                    str(codex_home),
                    "--json",
                ),
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        by_code = {result["code"]: result for result in payload["results"]}
        self.assertEqual(by_code["kit-link"]["level"], "PASS")
        self.assertEqual(by_code["agents-link"]["level"], "PASS")
        for skill in manifest.skills:
            self.assertEqual(by_code[f"skill-link:{skill.name}"]["level"], "PASS")
            self.assertEqual(
                by_code[f"skill-entrypoint:{skill.name}"]["level"], "PASS"
            )
        for retired_name in manifest.install.retired_skills:
            self.assertEqual(by_code[f"retired-skill:{retired_name}"]["level"], "PASS")

    @unittest.skipIf(os.name == "nt", "symlink contract is POSIX-oriented")
    def test_doctor_rejects_retired_kit_skill(self) -> None:
        manifest = load_manifest(ROOT)
        retired_name = manifest.install.retired_skills[0]
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / ".codex"
            skills_home = codex_home / manifest.install.skills_dir
            skills_home.mkdir(parents=True)

            (codex_home / manifest.install.kit_link).symlink_to(
                ROOT, target_is_directory=True
            )
            (codex_home / manifest.install.agents_link).symlink_to(
                ROOT / manifest.normative_source
            )
            for skill in manifest.skills:
                (skills_home / skill.name).symlink_to(
                    skill.root(ROOT), target_is_directory=True
                )
            (skills_home / retired_name).symlink_to(
                ROOT / "skills" / retired_name, target_is_directory=True
            )

            completed = subprocess.run(
                (
                    sys.executable,
                    str(ROOT / "scripts" / "doctor.py"),
                    "--root",
                    str(ROOT),
                    "--codex-home",
                    str(codex_home),
                    "--json",
                ),
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

        self.assertEqual(completed.returncode, 1, completed.stdout)
        payload = json.loads(completed.stdout)
        by_code = {result["code"]: result for result in payload["results"]}
        self.assertEqual(by_code[f"retired-skill:{retired_name}"]["level"], "FAIL")


class UserModelContractTests(unittest.TestCase):
    REQUIRED_FIELDS = (
        "ID:",
        "상태:",
        "마지막 확인:",
        "재검토:",
        "관찰:",
        "근거:",
        "작업에 미치는 영향:",
        "승격:",
        "대체:",
        "확신도:",
    )
    ALLOWED_STATUSES = {
        "candidate",
        "confirmed",
        "promoted",
        "superseded",
        "retired",
    }

    def test_every_observation_has_lifecycle_fields_and_live_promotions(self) -> None:
        text = (ROOT / "user-model" / "observations.md").read_text(encoding="utf-8")
        entries = re.split(r"(?m)^### ", text)[1:]
        self.assertGreater(len(entries), 0)

        ids: set[str] = set()
        records: dict[str, tuple[str, str, str]] = {}
        for entry in entries:
            title = entry.splitlines()[0]
            for field in self.REQUIRED_FIELDS:
                self.assertIn(field, entry, f"{title}: missing {field}")

            id_match = re.search(r"(?m)^ID: (OBS-\d{4}-\d{2}-\d{2}-\d{3})$", entry)
            self.assertIsNotNone(id_match, title)
            observation_id = id_match.group(1)
            self.assertNotIn(observation_id, ids)
            ids.add(observation_id)

            status_match = re.search(r"(?m)^상태: ([a-z]+)$", entry)
            self.assertIsNotNone(status_match, title)
            status = status_match.group(1)
            self.assertIn(status, self.ALLOWED_STATUSES)

            confirmed_match = re.search(r"(?m)^마지막 확인: (\d{4}-\d{2}-\d{2})$", entry)
            review_match = re.search(r"(?m)^재검토: (.+)$", entry)
            self.assertIsNotNone(confirmed_match, title)
            self.assertIsNotNone(review_match, title)
            confirmed_date = date.fromisoformat(confirmed_match.group(1))
            review_value = review_match.group(1).strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", review_value):
                self.assertGreaterEqual(date.fromisoformat(review_value), confirmed_date)
            else:
                self.assertRegex(review_value, r"^조건: \S.+", title)

            promotion_match = re.search(
                r"(?ms)^승격:\n(?P<body>.*?)\n\n대체:", entry
            )
            self.assertIsNotNone(promotion_match, title)
            promotion_paths = re.findall(r"`([^`]+)`", promotion_match.group("body"))
            if status == "promoted":
                self.assertGreater(len(promotion_paths), 0, title)
            for rel_path in promotion_paths:
                promotion_path = Path(rel_path)
                self.assertFalse(promotion_path.is_absolute(), title)
                self.assertNotIn("..", promotion_path.parts, title)
                self.assertTrue((ROOT / promotion_path).exists(), f"{title}: stale {rel_path}")

            replacement_match = re.search(
                r"(?ms)^대체:\n(?P<body>.*?)\n\n확신도:", entry
            )
            self.assertIsNotNone(replacement_match, title)
            replacement = replacement_match.group("body").strip()
            self.assertTrue(
                replacement == "없음"
                or re.fullmatch(
                    r"(?:supersedes|superseded_by) OBS-\d{4}-\d{2}-\d{2}-\d{3}",
                    replacement,
                ),
                f"{title}: invalid replacement relation {replacement!r}",
            )
            records[observation_id] = (status, replacement, title)

        for observation_id, (status, replacement, title) in records.items():
            if replacement == "없음":
                self.assertNotEqual(status, "superseded", title)
                continue

            relation, target_id = replacement.split(maxsplit=1)
            self.assertIn(target_id, records, f"{title}: unknown replacement target")
            self.assertNotEqual(target_id, observation_id, title)
            target_status, target_replacement, _ = records[target_id]

            if relation == "superseded_by":
                self.assertEqual(status, "superseded", title)
                self.assertEqual(
                    target_replacement,
                    f"supersedes {observation_id}",
                    f"{title}: replacement relation is not reciprocal",
                )
            else:
                self.assertEqual(target_status, "superseded", title)
                self.assertEqual(
                    target_replacement,
                    f"superseded_by {observation_id}",
                    f"{title}: replacement relation is not reciprocal",
                )


if __name__ == "__main__":
    unittest.main()
