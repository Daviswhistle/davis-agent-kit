from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ari
import install_hooks as install


class AriStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ari-test-")
        self.old_env = os.environ.get("ARI_PET_HOME")
        os.environ["ARI_PET_HOME"] = str(Path(self.temp.name) / "pet")

    def tearDown(self):
        if self.old_env is None:
            os.environ.pop("ARI_PET_HOME", None)
        else:
            os.environ["ARI_PET_HOME"] = self.old_env
        self.temp.cleanup()

    def test_starts_as_ari(self):
        s = ari.status()
        self.assertEqual(s["name"], "아리")
        self.assertEqual(s["form"], "별꼬리 여우")
        self.assertEqual(s["level"], 1)
        self.assertEqual(s["xp"], 0)
        self.assertIn("아리", ari.card(s))

    def test_care_changes_stats_but_not_xp(self):
        initial = ari.status()
        after_pet = ari.interaction("pet")
        self.assertEqual(after_pet["bond"], min(100, initial["bond"] + 6))
        after_play = ari.interaction("play")
        self.assertEqual(after_play["energy"], initial["energy"] - 7)
        self.assertEqual(after_play["stardust"], 2)
        after_feed = ari.interaction("feed")
        self.assertEqual(after_feed["energy"], min(100, after_play["energy"] + 16))
        self.assertEqual(after_feed["xp"], 0)
        after_rest = ari.interaction("rest")
        self.assertEqual(after_rest["activity"], "sleepy")

    def test_hooks_are_observational_and_deduplicated(self):
        ari.set_event("prompt", {"prompt": "secret user text"})
        self.assertEqual(ari.status()["activity"], "focus")
        ari.set_event("tool", {"command": "SECRET_COMMAND_SHOULD_NOT_SAVE"})
        self.assertEqual(ari.status()["activity"], "working")
        ari.set_event("wait", {"approval": "SECRET_APPROVAL"})
        self.assertEqual(ari.status()["activity"], "waiting")
        payload = {"session_id": "SECRET_SESSION", "turn_id": "SECRET_TURN", "transcript": "SECRET_TRANSCRIPT"}
        completed = ari.set_event("stop", payload)
        self.assertEqual(completed["turns"], 1)
        self.assertEqual(completed["xp"], 12)
        self.assertEqual(completed["stardust"], 3)
        ari.set_event("stop", payload)
        self.assertEqual(ari.status()["turns"], 1)
        raw = (ari.pet_home() / "state.json").read_text()
        for secret in ("secret user text", "SECRET_COMMAND", "SECRET_APPROVAL", "SECRET_SESSION", "SECRET_TURN", "SECRET_TRANSCRIPT"):
            self.assertNotIn(secret, raw)

    def test_notify_filter_and_progression(self):
        ari.set_event("notify", {"type": "wrong-event", "turn-id": "1"})
        self.assertEqual(ari.status()["xp"], 0)
        for i in range(18):
            ari.set_event("notify", {"type": "agent-turn-complete", "thread-id": "A", "turn-id": f"{i}"})
        s = ari.status()
        self.assertEqual(s["turns"], 18)
        self.assertEqual(s["xp"], 216)
        self.assertEqual(s["level"], 3)
        for i in range(18, 39):
            ari.set_event("notify", {"type": "agent-turn-complete", "thread-id": "A", "turn-id": f"{i}"})
        self.assertEqual(ari.status()["form"], "별지기 여우")
        self.assertEqual(ari.status()["streak"], 1)

    def test_bad_action_rejected(self):
        with self.assertRaises(ValueError):
            ari.interaction("delete")

    def test_concurrent_state_writes_are_serialized(self):
        workers = [threading.Thread(target=lambda: [ari.interaction("pet") for _ in range(25)]) for _ in range(4)]
        for worker in workers: worker.start()
        for worker in workers: worker.join()
        with (ari.pet_home() / "state.json").open(encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertEqual(stored["interactions"], 100)

    def test_concurrent_actions_do_not_lose_updates(self):
        workers = [threading.Thread(target=lambda: [ari.interaction("play") for _ in range(20)]) for _ in range(4)]
        for worker in workers: worker.start()
        for worker in workers: worker.join()
        self.assertEqual(ari.status()["stardust"], 24)  # Starts at 86 energy => 12 plays


class AriHttpTests(AriStateTests):
    def setUp(self):
        super().setUp()
        self.server = ari.ThreadingHTTPServer(("127.0.0.1", 0), ari.AriHTTP)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(3)
        self.server.server_close()
        super().tearDown()

    def url(self, path): return f"http://127.0.0.1:{self.port}{path}"

    def test_serves_page_and_assets(self):
        for path, marker in (("/", b"ari-sprite"), ("/app.js", b"async function refresh"), ("/theme.css", b".garden")):
            with urlopen(self.url(path), timeout=2) as response:
                self.assertIn(marker, response.read())

    def test_status_does_not_expose_private_ids(self):
        ari.set_event("stop", {"session_id": "PRIVATEID", "turn_id": "PRIVATE123"})
        with urlopen(self.url("/api/status"), timeout=2) as response:
            body = response.read().decode()
        self.assertNotIn("PRIVATEID", body)
        self.assertEqual(json.loads(body)["turns"], 1)

    def test_actions_require_app_header(self):
        body = b'{"action":"pet"}'
        req = Request(self.url("/api/action"), data=body, headers={"Content-Type": "application/json"})
        with self.assertRaises(HTTPError) as ctx:
            urlopen(req, timeout=2)
        self.assertEqual(ctx.exception.code, 403)
        good = Request(self.url("/api/action"), data=body, headers={"X-Ari-Pet": "1"})
        with urlopen(good, timeout=2) as response:
            self.assertEqual(json.load(response)["bond"], 74)
        bad_origin = Request(self.url("/api/action"), data=body, headers={"X-Ari-Pet": "1", "Origin": "https://evil.example"})
        with self.assertRaises(HTTPError) as ctx:
            urlopen(bad_origin, timeout=2)
        self.assertEqual(ctx.exception.code, 403)


class AriHooksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ari-hooks-")
        self.hooks_path = Path(self.temp.name) / "hooks.json"
        self.root = Path(__file__).resolve().parents[1]

    def tearDown(self):
        self.temp.cleanup()

    def test_merge_is_idempotent_and_disable_preserves_user_hooks(self):
        original = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo user-hook"}]}]}, "other": 123}
        self.hooks_path.write_text(json.dumps(original))
        self.assertEqual(install.merge_hooks(self.hooks_path, self.root), 6)
        after = json.loads(self.hooks_path.read_text())
        self.assertEqual(after["other"], 123)
        self.assertEqual(after["hooks"]["Stop"][0], original["hooks"]["Stop"][0])
        self.assertEqual(len(after["hooks"]["Stop"]), 2)
        install.merge_hooks(self.hooks_path, self.root)
        self.assertEqual(len(json.loads(self.hooks_path.read_text())["hooks"]["Stop"]), 2)
        self.assertEqual(install.merge_hooks(self.hooks_path, self.root, uninstall=True), 6)
        after = json.loads(self.hooks_path.read_text())
        self.assertEqual(after["hooks"]["Stop"], original["hooks"]["Stop"])
        self.assertEqual(after["other"], 123)
        self.assertTrue(list(self.hooks_path.parent.glob("hooks.json.ari-backup-*")))

    def test_conflicting_schema_does_not_change_existing_hooks(self):
        malformed = '{"hooks": {"Stop": "not-a-list"}}'
        self.hooks_path.write_text(malformed)
        with self.assertRaises(ValueError):
            install.merge_hooks(self.hooks_path, self.root)
        self.assertEqual(self.hooks_path.read_text(), malformed)

    def test_disable_does_not_delete_skill_or_state(self):
        self.assertTrue((self.root / "SKILL.md").exists())
        self.assertEqual(install.merge_hooks(self.hooks_path, self.root, uninstall=True), 0)
        self.assertTrue((self.root / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
