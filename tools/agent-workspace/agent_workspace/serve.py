#!/usr/bin/env python3
"""Loopback HTTP service. Origin + CSRF protect the two explicit write routes.

Session logs are projected read-only; chat writes go through the configured CLI.
"""
from __future__ import annotations

import json
import os
import select
import socket
import time
import secrets
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

from pathlib import Path
from . import render, dashboard, board_store
from .config import Config, configure

MOVABLE = ('진행', '검토 대기', '할 일')


def setup(config):
    global BOARD, APPROVALS, DONE_LOG, LOCK, PORT
    configure(config)
    render.CONFIG = config
    BOARD = config.board
    APPROVALS = config.data_dir / 'approvals.json'
    DONE_LOG = config.data_dir / 'done-log.jsonl'
    LOCK = config.lock
    PORT = config.port


_defaults = Config.defaults()
BOARD, LOCK, PORT = _defaults.board, _defaults.lock, _defaults.port
APPROVALS = _defaults.data_dir / 'approvals.json'
DONE_LOG = _defaults.data_dir / 'done-log.jsonl'


def local_origins():
    hosts = [f'{host}:{PORT}' for host in ('localhost', '127.0.0.1')]
    if PORT == 80:
        hosts += ['localhost', '127.0.0.1']
    return tuple('http://' + host for host in hosts)


def _atomic_write(path, text, expected=None):
    board_store.atomic_write(path, text, expected)


def complete_card(card_id, now):
    text, version = board_store.snapshot(BOARD)
    # Resolve and validate the latest owner column inside the write lock.
    updated, col = board_store.move(text, card_id, '완료')
    if col not in MOVABLE:
        raise LookupError(f"{card_id}는 '{col}' 열에 있습니다.")
    updated, _ = board_store.move(text, card_id, '완료',
                                  [f'요약 ({now}):', '- 결론: 운영자 완료 처리.', f'- 근거: 로컬 작업실에서 확인. 이전 열: {col}.', '- 다음: 세부 검증 근거는 카드에 연결된 보고서를 참고하세요.'])
    _atomic_write(BOARD, updated, version)
    return col


def complete_approval(title, now, by_id=False):
    text, version = board_store.snapshot(APPROVALS)
    items = json.loads(text)
    if not isinstance(items, list) or any(not isinstance(a, dict) for a in items):
        raise ValueError('잘못된 운영자 확인 목록')
    keep = [a for a in items if (board_store.approval_key(a.get('title', '')) if by_id else a.get('title')) != title]
    if len(keep) == len(items):
        raise LookupError("해당 항목을 찾지 못했습니다.")
    original_title = next(a.get('title', '') for a in items if a not in keep)
    _atomic_write(APPROVALS, json.dumps(keep, ensure_ascii=False, indent=1) + "\n", version)
    return original_title


class Handler(BaseHTTPRequestHandler):
    token = ""

    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, code, value):
        return self._send(code, json.dumps(value, ensure_ascii=False))

    def _local_request(self):
        origins = local_origins()
        hosts = tuple(origin.removeprefix('http://') for origin in origins)
        origin = self.headers.get('Origin')
        return (self.headers.get('Host') in hosts and
                (not origin or origin in origins) and
                self.headers.get('Sec-Fetch-Site') != 'cross-site')

    def do_GET(self):
        if not self._local_request():
            return self._json(403, {'error': '허용되지 않은 출처'})
        url = urlsplit(self.path)
        if url.path in ('/dashboard.js', '/dashboard.css'):
            ctype = 'text/javascript' if url.path.endswith('.js') else 'text/css'
            with open(Path(__file__).parent / 'static' / url.path[1:], encoding='utf-8') as f:
                return self._send(200, f.read(), ctype + '; charset=utf-8')
        if url.path == '/api/health':
            return self._json(200, {'ok': True, 'service': 'agent-workspace'})
        if url.path in ('/', '/index.html'):
            # Cron and simultaneous page requests must not overwrite one another's tokens.
            try:
                with PAGE_LOCK:
                    page = render.render(token=self.token)
                return self._send(200, page, 'text/html; charset=utf-8')
            except (OSError, ValueError):
                return self._send(503, render.error_page(), 'text/html; charset=utf-8')
        try:
            query = parse_qs(url.query)
            before = query.get('before', [None])[0]
            before = int(before) if before is not None else None
            if before is not None and before < 0:
                raise ValueError()
            if url.path == '/api/sessions':
                return self._json(200, {'sessions': dashboard.sessions(render.parse_board())})
            if url.path == '/api/session':
                return self._json(200, dashboard.conversation(query.get('id', [''])[0], before))
            if url.path == '/api/chat':
                return self._json(200, dashboard.chat(before))
        except ValueError:
            return self._json(400, {'error': '잘못된 조회 요청'})
        except LookupError:
            return self._json(404, {'error': '기록을 찾을 수 없습니다.'})
        except OSError:
            return self._json(503, {'error': '로컬 기록을 읽지 못했습니다.'})
        return self._send(404, '{}')

    def do_POST(self):
        if self.path not in ("/api/done", "/api/chat/send"):
            return self._send(404, "{}")
        self.connection.settimeout(10)
        origin = self.headers.get("Origin", "")
        if not self._local_request() or origin not in local_origins():
            return self._send(403, json.dumps({"error": "허용되지 않은 출처"}, ensure_ascii=False))
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 100_000 or self.headers.get('Transfer-Encoding'):
                return self._json(413, {'error': '요청이 너무 크거나 길이가 없습니다.'})
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError()
        except (ValueError, UnicodeDecodeError, TimeoutError):
            return self._send(400, "{}")
        if not secrets.compare_digest(str(body.get("token", "")).encode(), self.token.encode()):
            return self._json(403, {'error': '서버가 재시작되었습니다. 토큰을 갱신한 뒤 다시 시도하세요.', 'code': 'csrf_expired'})
        if self.path == '/api/chat/send':
            try:
                result = dashboard.send_message(body)
                return self._json(200 if result.get('ok') else 409, result)
            except ValueError as exc:
                return self._json(400, {'error': str(exc)})
            except OSError:
                return self._json(503, {'error': 'agent-chat을 실행하지 못했습니다.'})
        now = datetime.now(ZoneInfo(render.CONFIG.timezone)).strftime("%Y-%m-%d %H:%M")
        try:
            with board_store.locked(LOCK):
                audit_title = body.get('title')
                approval_id = None
                if body.get("kind") == "card":
                    detail = complete_card(str(body.get("id", "")), now)
                elif body.get("kind") == "approval":
                    key = body.get('approval_id')
                    title = complete_approval(str(key if key is not None else body.get('title', '')), now, by_id=key is not None)
                    audit_title = dashboard.mask(title)
                    approval_id = board_store.approval_key(title)
                    detail = '운영자 확인'
                else:
                    return self._send(400, "{}")
                with open(DONE_LOG, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"at": now, "kind": body.get("kind"), "id": body.get("id"),
                                        "title": audit_title, "from": detail,
                                        **({'approval_id': approval_id} if approval_id is not None else {})}, ensure_ascii=False) + "\n")
        except LookupError as exc:
            return self._send(409, json.dumps({"error": str(exc)}, ensure_ascii=False))
        except ValueError:
            return self._json(400, {'error': '잘못된 카드 요청'})
        except OSError:
            return self._json(503, {'error': '저장 결과를 확인하지 못했습니다. 새로고침해 상태를 확인하세요.'})
        return self._send(200, json.dumps({"ok": True}))


def inherited_socket(port):
    """Consume sd_listen_fds' single fd 3, ignoring another process's environment."""
    pid = os.environ.pop('LISTEN_PID', None)
    count = os.environ.pop('LISTEN_FDS', None)
    os.environ.pop('LISTEN_FDNAMES', None)
    os.environ.pop('LISTEN_PIDFDID', None)
    if pid != str(os.getpid()):
        return None
    if count == '0' or count is None:
        return None
    if count != '1':
        raise ValueError('Expected one activation socket')
    listener = socket.socket(fileno=3)
    try:
        listener.set_inheritable(False)
        if (listener.family != socket.AF_INET or listener.type != socket.SOCK_STREAM or
                not listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) or
                listener.getsockname() != ('127.0.0.1', port)):
            raise ValueError('Activation requires a listening 127.0.0.1 TCP socket on the configured port')
        listener.setblocking(True)
        return listener
    except BaseException:
        listener.close()
        raise


class WorkspaceServer(HTTPServer):
    """Reuse at most four workers, with at most eight accepted requests in flight."""
    def __init__(self, address, handler, listener=None):
        from concurrent.futures import ThreadPoolExecutor
        self._workers = ThreadPoolExecutor(max_workers=4, thread_name_prefix='workspace')
        self._slots = threading.BoundedSemaphore(8)
        self._activity = threading.Lock()
        self.active_requests = 0
        self.last_activity = time.monotonic()
        super().__init__(address, handler, bind_and_activate=listener is None)
        if listener is not None:
            self.socket.close()
            self.socket = listener
            self.server_address = listener.getsockname()
            self.server_name, self.server_port = 'localhost', self.server_address[1]

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        with self._activity:
            self.active_requests += 1
            self.last_activity = time.monotonic()
        self._workers.submit(self._handle, request, client_address)

    def _handle(self, request, address):
        try:
            # Bound incomplete headers as well as incomplete POST bodies.
            request.settimeout(10)
            self.finish_request(request, address)
        except Exception:
            self.handle_error(request, address)
        finally:
            self.shutdown_request(request)
            with self._activity:
                self.active_requests -= 1
                self.last_activity = time.monotonic()
            self._slots.release()

    def run(self, idle_seconds=0):
        # No periodic poll or timer thread. A request or the idle deadline wakes select.
        while True:
            with self._activity:
                remaining = idle_seconds - (time.monotonic() - self.last_activity)
                if idle_seconds and not self.active_requests and remaining <= 0:
                    return
                timeout = max(0.01, remaining) if idle_seconds and not self.active_requests else (idle_seconds or None)
            if select.select([self], [], [], timeout)[0]:
                self._handle_request_noblock()

    def server_close(self):
        super().server_close()
        self._workers.shutdown(wait=True)


def main(config=None):
    config = config if config is not None else Config.load()
    setup(config)
    Path(LOCK).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    Handler.token = secrets.token_urlsafe(32)
    listener = inherited_socket(PORT)
    server = WorkspaceServer(("127.0.0.1", PORT), Handler, listener)
    print(f'Agent Workspace: http://localhost:{PORT} (127.0.0.1 only)', flush=True)
    try:
        # Standalone invocations remain running until Ctrl+C, including on macOS.
        server.run(config.idle_seconds if listener is not None else 0)
    finally:
        server.server_close()


PAGE_LOCK = threading.Lock()

if __name__ == "__main__":
    main()
