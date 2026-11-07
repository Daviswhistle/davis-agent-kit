"""Socket activation, bounded workers/cache, and standalone compatibility."""
import dataclasses
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_workspace import dashboard, serve
from agent_workspace.config import Config
from agent_workspace.demo import create

PACKAGE = Path(__file__).resolve().parents[1]


class ActivationTests(unittest.TestCase):
    def child(self, code, env=None):
        return subprocess.run([sys.executable, '-c', code], env={**os.environ, 'PYTHONPATH': str(PACKAGE), **(env or {})},
                              capture_output=True, text=True, timeout=15)

    def test_absent_or_foreign_pid_never_consumes_fd(self):
        for env in ({}, {'LISTEN_PID': '0', 'LISTEN_FDS': '1', 'LISTEN_FDNAMES': 'test'}):
            with patch.dict(os.environ, env, clear=True), patch.object(serve.socket, 'socket') as factory:
                self.assertIsNone(serve.inherited_socket(8888))
                factory.assert_not_called()
                self.assertNotIn('LISTEN_PID', os.environ)
                self.assertNotIn('LISTEN_FDS', os.environ)
                self.assertNotIn('LISTEN_FDNAMES', os.environ)

    def test_fd3_adoption_and_rejection_in_isolated_process(self):
        for address, listening, expected in [('127.0.0.1', True, True), ('0.0.0.0', True, False), ('127.0.0.1', False, False)]:
            code = f'''
import os, socket
from agent_workspace.serve import inherited_socket
s=socket.socket(); s.bind(({address!r}, 0)); port=s.getsockname()[1]
if {listening!r}: s.listen()
if s.fileno()!=3: os.dup2(s.fileno(),3); s.close()
else: s.detach()
os.set_inheritable(3,True)
os.environ.update(LISTEN_PID=str(os.getpid()),LISTEN_FDS='1',LISTEN_FDNAMES='test')
try:
 listener=inherited_socket(port)
 assert {expected!r}
 assert listener.getsockname()==('127.0.0.1',port)
 assert not os.get_inheritable(3)
 listener.close()
except ValueError:
 assert not {expected!r}
assert 'LISTEN_PID' not in os.environ and 'LISTEN_FDS' not in os.environ
'''
            result = self.child(code)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_multiple_or_invalid_descriptor_count_fails(self):
        for count in ('2', '-1', 'invalid'):
            with patch.dict(os.environ, {'LISTEN_PID': str(os.getpid()), 'LISTEN_FDS': count}):
                with self.assertRaises(ValueError): serve.inherited_socket(8888)

    def test_idle_config_validation(self):
        for value in (-1, 'nan', 'inf'):
            with self.assertRaises(ValueError): Config.load(overrides={'idle_seconds': value})
        with patch.dict(os.environ, {'AGENT_WORKSPACE_IDLE_SECONDS': '7'}):
            self.assertEqual(Config.load().idle_seconds, 7)
            self.assertEqual(Config.load(overrides={'idle_seconds': 3}).idle_seconds, 3)

    def test_activated_server_exits_and_restarts_on_same_listener(self):
        with tempfile.TemporaryDirectory() as tmp, socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); listener.listen()
            port = listener.getsockname()[1]
            config = create(Path(tmp), port=port, turns=1)
            cfg = Path(tmp) / 'config.json'
            cfg.write_text(json.dumps({f.name: str(getattr(config, f.name)) for f in dataclasses.fields(config)}))
            code = '''
import os, sys
from agent_workspace.serve import main
from agent_workspace.config import Config
fd=int(sys.argv[1])
if fd!=3: os.dup2(fd,3); os.close(fd)
os.environ.update(LISTEN_PID=str(os.getpid()),LISTEN_FDS='1')
main(Config.load(sys.argv[2], {'idle_seconds': .2}))
'''
            old_token = None
            for _ in range(2):
                proc = subprocess.Popen([sys.executable, '-c', code, str(listener.fileno()), str(cfg)],
                                        pass_fds=(listener.fileno(),), env={**os.environ, 'PYTHONPATH': str(PACKAGE)},
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
                    conn.request('GET', '/'); response = conn.getresponse(); page = response.read().decode(); conn.close()
                    self.assertEqual(response.status, 200)
                    token = page.split('name="csrf-token" content="')[1].split('"')[0]
                    if old_token:
                        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
                        conn.request('POST', '/api/done', json.dumps({'token': old_token, 'kind': 'card', 'id': 'B-1'}),
                                     {'Origin': f'http://localhost:{port}'})
                        response = conn.getresponse(); payload = json.loads(response.read()); conn.close()
                        self.assertEqual((response.status, payload['code']), (403, 'csrf_expired'))
                        self.assertIn('## 진행\n\n### B-1', config.board.read_text())
                    old_token = token
                    out, err = proc.communicate(timeout=5)
                    self.assertEqual(proc.returncode, 0, err)
                finally:
                    if proc.poll() is None: proc.kill(); proc.communicate()

    def test_standalone_ignores_idle_timeout(self):
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1', 0)); port = reserve.getsockname()[1]
        proc = subprocess.Popen([sys.executable, str(PACKAGE / 'workspace.py'), '--demo', '--port', str(port), '--idle-seconds', '.05'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                env={k: v for k,v in os.environ.items() if not k.startswith('LISTEN_')})
        try:
            self.assertIn('127.0.0.1 only', proc.stdout.readline())
            time.sleep(.15)
            self.assertIsNone(proc.poll())
        finally: proc.terminate(); proc.communicate(timeout=5)


class BoundedStateTests(unittest.TestCase):
    def test_metadata_replaces_old_versions_and_evicts_lru(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(dashboard, 'CACHE_LIMIT', 3):
            with dashboard._lock: dashboard._cache.clear()
            p = Path(tmp) / 'one.jsonl'
            for i in range(12):
                p.write_text(json.dumps({'timestamp': str(i)}) + '\n')
                dashboard.metadata(p, 'codex')
                self.assertEqual(len(dashboard._cache), 1)
            for name in ('two', 'three', 'four'):
                q = Path(tmp) / (name + '.jsonl'); q.write_text('{}\n'); dashboard.metadata(q, 'codex')
            self.assertEqual(len(dashboard._cache), 3)
            self.assertNotIn(str(p), dashboard._cache)
            with dashboard._lock: dashboard._cache.clear()

    def test_metadata_preview_matches_full_projection(self):
        fixtures = {
            'codex': [
                {'type': 'turn_context', 'payload': {'model': 'synthetic model'}},
                {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'content': [{'type': 'text', 'text': 'first'}]}},
                {'type': 'event_msg', 'payload': {'type': 'agent_message', 'message': 'first'}},
                {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'content': [{'type': 'text', 'text': 'last\npreview'}]}},
                {'type': 'response_item', 'payload': {'type': 'function_call_output', 'output': 'tool ' * 1000}},
                {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'text', 'text': 'latest user'}]}},
            ],
            'claude': [
                {'type': 'assistant', 'message': {'model': 'synthetic model', 'content': [
                    {'type': 'text', 'text': 'before'}, {'type': 'tool_use', 'name': 'test'}, {'type': 'text', 'text': 'after'}]}},
                {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'trailing'}]}},
                {'type': 'user', 'message': {'content': 'latest user'}},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            for kind, events in fixtures.items():
                p = Path(tmp) / (kind + '.jsonl')
                p.write_text(''.join(json.dumps(e) + '\n' for e in events))
                messages = dashboard.project_messages(events, kind)
                expected = [m['text'].replace('\n', ' ')[:140] for m in messages if m['role'] == 'assistant'][-1]
                self.assertEqual(dashboard.metadata(p, kind)['preview'], expected)

    def test_workers_and_pending_requests_are_bounded(self):
        entered, release = threading.Event(), threading.Event()
        class Slow(serve.BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self): entered.set(); release.wait(3)
        server = serve.WorkspaceServer(('127.0.0.1', 0), Slow)
        clients = []
        try:
            for _ in range(9):
                client = socket.create_connection(server.server_address); clients.append(client)
                client.sendall(b'GET / HTTP/1.0\r\n\r\n')
                server._handle_request_noblock()
            self.assertTrue(entered.wait(2))
            self.assertEqual(server.active_requests, 8)
            self.assertEqual(len(server._workers._threads), 4)
            self.assertEqual(clients[-1].recv(1), b'')
        finally:
            release.set(); server.server_close()
            for client in clients: client.close()
        self.assertEqual(server.active_requests, 0)

    def test_slow_request_does_not_block_other_clients_or_expire_early(self):
        entered, release = threading.Event(), threading.Event()
        class Slow(serve.BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                if self.path == '/slow': entered.set(); release.wait(3)
                self.send_response(200); self.end_headers()
        server = serve.WorkspaceServer(('127.0.0.1', 0), Slow)
        runner = threading.Thread(target=server.run, args=(.1,)); runner.start()
        conn = http.client.HTTPConnection(*server.server_address, timeout=5)
        slow = threading.Thread(target=lambda: (conn.request('GET', '/slow'), conn.getresponse().read(), conn.close()))
        slow.start()
        try:
            self.assertTrue(entered.wait(2)); time.sleep(.15)
            self.assertTrue(runner.is_alive())
            fast = http.client.HTTPConnection(*server.server_address, timeout=2)
            fast.request('GET', '/fast'); self.assertEqual(fast.getresponse().status, 200); fast.close()
            self.assertLessEqual(len(server._workers._threads), 4)
        finally:
            release.set(); slow.join(5); runner.join(5); server.server_close()
        self.assertFalse(runner.is_alive())


if __name__ == '__main__': unittest.main()
