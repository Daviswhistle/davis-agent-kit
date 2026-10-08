#!/usr/bin/env python3
"""Ari — a local-first Codex coding pet. Python 3.9+, standard library only."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from urllib.parse import urlsplit
import webbrowser

VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
ACTION_MESSAGES = {
    "pet": ["손길이 따뜻해. 조금만 더 여기 있을래?", "후후. 내 별꼬리가 반짝였어!", "네 곁에 있는 게 좋아. ✦"],
    "feed": ["별사탕 냠! 이제 다시 힘낼 수 있어.", "이 반짝임, 네가 준 거야?", "달콤한 에너지가 충전됐어!"],
    "play": ["같이 놀자! 오늘의 작은 승리야.", "잡았다! ...어라? 내 꼬리네.", "우주 저 끝까지 달리고 싶어!"],
    "rest": ["잠깐 눈 감고 별을 세어볼게. zZ", "충전 중... 꿈속에서도 응원할게.", "조용히 옆에 있을게."],
}
STATUS_MESSAGES = {
    "idle": "오늘도 네 곁에서 반짝이고 있을게.",
    "focus": "생각이 깊어지는 중... 쉿, 집중이야!",
    "working": "도구가 움직이고 있어. 꼬리도 바빠!",
    "waiting": "네 확인이 필요해. 여기서 기다릴게.",
    "complete": "이번 작업 턴이 끝났어! 별 하나 추가 ✦",
    "interrupted": "잠깐 멈췄어. 괜찮아, 다음 걸 해보자.",
    "sleepy": "별빛 충전 중... zZ",
}
VALID_ACTIONS = set(ACTION_MESSAGES)
VALID_EVENTS = {"prompt", "tool", "wait", "stop", "interrupt", "session"}


def pet_home() -> Path:
    override = os.environ.get("ARI_PET_HOME")
    return Path(override).expanduser().resolve() if override else Path.home() / ".ari-pet"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or now_utc()).isoformat(timespec="seconds")


def initial_state() -> dict:
    return {
        "schema_version": 1,
        "name": "아리",
        "species": "별꼬리 여우",
        "born_at": iso(),
        "xp": 0,
        "bond": 68,
        "energy": 86,
        "stardust": 0,
        "turns": 0,
        "tools": 0,
        "streak": 0,
        "last_turn_date": None,
        "activity": "idle",
        "activity_until": None,
        "message": STATUS_MESSAGES["idle"],
        "message_until": None,
        "interactions": 0,
        "recent_turn_ids": [],
        "updated_at": iso(),
    }


@contextmanager
def state_lock():
    home = pet_home()
    home.mkdir(parents=True, exist_ok=True)
    lock_file = home / ".lock"
    with lock_file.open("a+b") as file:
        if os.name == "nt":
            import msvcrt
            file.seek(0, 2)
            if file.tell() == 0:
                file.write(b"0")
                file.flush()
            deadline = time.monotonic() + 4
            while True:
                try:
                    file.seek(0)
                    msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise TimeoutError("Ari state file is busy")
                    time.sleep(0.05)
            try:
                yield
            finally:
                file.seek(0)
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)


def load_state() -> dict:
    path = pet_home() / "state.json"
    if not path.exists():
        return initial_state()
    with path.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("Unknown or corrupt Ari state; back up ~/.ari-pet/state.json and inspect it")
    return {**initial_state(), **raw}


def write_state(state: dict) -> None:
    home = pet_home()
    home.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = iso()
    fd, tmp = tempfile.mkstemp(prefix=".state-", suffix=".json", dir=home)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, home / "state.json")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def bump(state: dict, kind: str, *, message: str | None = None, lifespan: int = 30) -> None:
    state["activity"] = kind
    state["activity_until"] = iso(now_utc() + timedelta(seconds=lifespan)) if lifespan else None
    state["message"] = message or STATUS_MESSAGES.get(kind, STATUS_MESSAGES["idle"])
    state["message_until"] = iso(now_utc() + timedelta(seconds=lifespan)) if lifespan else None


def interaction(action: str) -> dict:
    if action not in VALID_ACTIONS:
        raise ValueError("Unknown action")
    with state_lock():
        state = load_state()
        state["interactions"] += 1
        seq = state["interactions"] - 1
        if action == "pet":
            state["bond"] = min(100, state["bond"] + 6)
            bump(state, "complete", message=ACTION_MESSAGES[action][seq % 3], lifespan=14)
        elif action == "feed":
            state["energy"] = min(100, state["energy"] + 16)
            state["bond"] = min(100, state["bond"] + 2)
            bump(state, "complete", message=ACTION_MESSAGES[action][seq % 3], lifespan=15)
        elif action == "play":
            if state["energy"] < 7:
                bump(state, "sleepy", message="조금 지쳤어. 별사탕 하나 먹고 놀자.", lifespan=16)
            else:
                state["energy"] -= 7
                state["bond"] = min(100, state["bond"] + 5)
                state["stardust"] += 2
                bump(state, "complete", message=ACTION_MESSAGES[action][seq % 3], lifespan=15)
        elif action == "rest":
            state["energy"] = min(100, state["energy"] + 12)
            bump(state, "sleepy", message=ACTION_MESSAGES[action][seq % 3], lifespan=23)
        write_state(state)
        return public_state(state)


def read_hook_payload(raw: str | None = None) -> dict:
    if raw is None:
        if sys.stdin.isatty():
            return {}
        raw = sys.stdin.read(65537)
    if len(raw) > 65536:
        return {}
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def set_event(event: str, payload: dict | None = None) -> dict:
    if event not in VALID_EVENTS and event != "notify":
        raise ValueError("Unknown event")
    data = payload or {}
    with state_lock():
        state = load_state()
        if event == "prompt":
            bump(state, "focus", lifespan=150)
        elif event == "tool":
            state["tools"] += 1
            bump(state, "working", lifespan=150)
        elif event == "wait":
            bump(state, "waiting", lifespan=150)
        elif event in ("stop", "notify"):
            if event == "notify" and data.get("type") not in ("agent-turn-complete", None):
                return public_state(state)
            turn_id = str(data.get("turn_id") or data.get("turn-id") or "")
            session_id = str(data.get("session_id") or data.get("thread-id") or "")
            unique_id = hashlib.sha256(f"{session_id}:{turn_id}".encode("utf-8")).hexdigest() if turn_id else ""
            previous = state["recent_turn_ids"]
            if not unique_id or unique_id not in previous:
                if unique_id:
                    state["recent_turn_ids"] = (previous + [unique_id])[-50:]
                state["xp"] += 12
                state["turns"] += 1
                state["stardust"] += 3
                state["bond"] = min(100, state["bond"] + 1)
                state["energy"] = max(8, state["energy"] - 2)
                today = datetime.now().astimezone().date()
                prev_date = state.get("last_turn_date")
                if prev_date != today.isoformat():
                    if prev_date == (today - timedelta(days=1)).isoformat():
                        state["streak"] += 1
                    else:
                        state["streak"] = 1
                    state["last_turn_date"] = today.isoformat()
                bump(state, "complete", lifespan=25)
        elif event == "interrupt":
            bump(state, "interrupted", lifespan=20)
        elif event == "session":
            bump(state, "idle", lifespan=0)
        write_state(state)
        return public_state(state)


def level_stats(xp: int) -> tuple[int, int, int]:
    level = 1
    while xp >= 50 * level * level:
        level += 1
    return level, (50 * (level - 1) ** 2 if level > 1 else 0), 50 * level * level


def public_state(state: dict) -> dict:
    level, current_floor, next_floor = level_stats(int(state["xp"]))
    activity = state["activity"]
    expiry = state.get("activity_until")
    if expiry:
        try:
            if now_utc() >= datetime.fromisoformat(expiry):
                activity = "idle"
        except ValueError:
            activity = "idle"
    msg = state["message"]
    msg_expiry = state.get("message_until")
    if msg_expiry:
        try:
            if now_utc() >= datetime.fromisoformat(msg_expiry):
                msg = STATUS_MESSAGES[activity]
        except ValueError:
            msg = STATUS_MESSAGES[activity]
    elif activity == "idle":
        msg = STATUS_MESSAGES["idle"]
    # Expose no Codex prompts, tool arguments, session IDs, or filesystem paths.
    keys = ("name", "species", "born_at", "xp", "bond", "energy", "stardust", "turns", "tools", "streak")
    result = {key: state[key] for key in keys}
    result.update(
        level=level,
        next_level_xp=next_floor,
        level_progress=round(100 * (state["xp"] - current_floor) / (next_floor - current_floor), 1),
        activity=activity,
        message=msg,
        form=("성운 여우" if level >= 8 else "별지기 여우" if level >= 4 else "별꼬리 여우"),
        version=VERSION,
    )
    return result


def status() -> dict:
    with state_lock():
        return public_state(load_state())


def card(state: dict) -> str:
    faces = {"focus": "•̀ᴗ•́", "working": "•̀ᴗ•́", "waiting": "•́﹏•̀", "sleepy": "－ᴗ－", "complete": "˃ᴗ˂", "interrupted": "•́ᴗ•̀"}
    eyes = faces.get(state["activity"], "•ᴗ•")
    progress = min(10, round(state["level_progress"] / 10))
    return "\n".join([
        "        ✧       ✦",
        "       /\\_/\\   ✧",
        f"      ( {eyes} )  ~☆",
        "       >  ✦  <",
        "",
        f"  {state['name']} · {state['form']}  Lv.{state['level']}",
        f"  별 경험치  [{'█' * progress}{'░' * (10-progress)}] {state['level_progress']:.0f}%",
        f"  유대 {state['bond']}/100 · 에너지 {state['energy']}/100",
        f"  함께 끝낸 작업 턴 {state['turns']}개 · 별가루 {state['stardust']}",
        f"  ❝ {state['message']} ❞",
    ])


class AriHTTP(BaseHTTPRequestHandler):
    server_version = "AriPet/1.0"

    def log_message(self, fmt, *args):
        return  # no per-request logs or interaction tracking

    def _safe_host(self):
        host = self.headers.get("Host", "")
        return host in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}")

    def _send(self, status_code: int, content: bytes, mime: str):
        self.send_response(status_code)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _json(self, obj: dict, status_code: int = 200):
        self._send(status_code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        if not self._safe_host():
            self._json({"error": "invalid host"}, 403)
            return
        assets = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/theme.css": ("theme.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
        }
        path = urlsplit(self.path).path
        if path == "/api/status":
            self._json(status())
        elif path in assets:
            filename, mime = assets[path]
            self._send(200, (WEB_DIR / filename).read_bytes(), mime)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if not self._safe_host():
            self._json({"error": "invalid host"}, 403)
            return
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"):
            self._json({"error": "invalid origin"}, 403)
            return
        if self.headers.get("X-Ari-Pet") != "1":
            self._json({"error": "missing local app header"}, 403)
            return
        if urlsplit(self.path).path != "/api/action":
            self._json({"error": "not found"}, 404)
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 < n <= 1024:
                raise ValueError("invalid body length")
            data = json.loads(self.rfile.read(n))
            if not isinstance(data, dict) or data.get("action") not in VALID_ACTIONS:
                raise ValueError("invalid action")
            self._json(interaction(data["action"]))
        except (ValueError, json.JSONDecodeError):
            self._json({"error": "invalid request"}, 400)


def run_server(port: int, open_browser: bool) -> None:
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), AriHTTP)
    except OSError as err:
        raise SystemExit(f"Cannot start Ari on port {port}: {err}") from err
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"✦ 아리의 별정원: {url}  (Ctrl+C to close)", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        print("\n아리: 다음에 또 만나! ✦")
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ari", description="Ari, a starlit fox who keeps you company while coding")
    parser.add_argument("--version", action="version", version=VERSION)
    subs = parser.add_subparsers(dest="command")
    status_p = subs.add_parser("status", help="Show Ari's state")
    status_p.add_argument("--json", action="store_true")
    subs.add_parser("card", help="Show Ari's shareable terminal card")
    for action in sorted(VALID_ACTIONS):
        subs.add_parser(action, help=f"Interact with Ari: {action}")
    serve_p = subs.add_parser("serve", help="Launch the animated local pet garden")
    serve_p.add_argument("--port", type=int, default=8765)
    serve_p.add_argument("--open", action="store_true")
    hook_p = subs.add_parser("hook", help="Receive Codex hooks from stdin")
    hook_p.add_argument("event", choices=sorted(VALID_EVENTS))
    notify_p = subs.add_parser("notify", help="Receive Codex notify JSON argument")
    notify_p.add_argument("payload", nargs="?")
    args = parser.parse_args(argv)
    if args.command in (None, "status", "card"):
        s = status()
        print(json.dumps(s, indent=2, ensure_ascii=False) if getattr(args, "json", False) else card(s))
    elif args.command in VALID_ACTIONS:
        print(card(interaction(args.command)))
    elif args.command == "serve":
        if not 0 <= args.port <= 65535:
            parser.error("port must be 0-65535")
        run_server(args.port, args.open)
    elif args.command == "hook":
        set_event(args.event, read_hook_payload())
    elif args.command == "notify":
        set_event("notify", read_hook_payload(args.payload))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, TimeoutError) as exc:
        print(f"ari: {exc}", file=sys.stderr)
        sys.exit(1)
