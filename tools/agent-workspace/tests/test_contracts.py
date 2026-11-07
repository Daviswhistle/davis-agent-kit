import contextlib
import http.client
import json
from pathlib import Path
import tempfile
import subprocess
import threading
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_workspace import dashboard as d, render, serve, board_store
from agent_workspace.demo import CODEX_ID

ENTRYPOINT = Path(__file__).resolve().parents[1] / 'workspace.py'
DEMO_CHAT = ENTRYPOINT.parent / 'agent_workspace/demo_chat.py'

SID = CODEX_ID
WHO = 'codex:' + SID


class DataTests(unittest.TestCase):
    def test_masks_credentials_including_json_and_multiline_key(self):
        samples = [
            'sk-' + 'aB9' * 10, 'ghp_' + 'aB9' * 10,
            'eyJabcdefghij.abcdefghijk.abcdefghijk',
            'Bearer ' + 'abCD12' * 5,
            'token=exampleCredential', '{"api_key":"exampleCredential"}',
            'password: exampleCredential', '123456789012', '123-456-789012',
            'aBcDeF0123456789' * 3,
            '-----BEGIN PRIVATE KEY-----\nabc\ndef\n-----END PRIVATE KEY-----',
            '/tmp/token=exampleCredential',
        ]
        for sample in samples:
            with self.subTest(sample_type=samples.index(sample)):
                self.assertIn('[가림]', d.mask(sample))
                self.assertNotIn('exampleCredential', d.mask(sample))

    def test_preserves_public_ids_kst_and_unicode(self):
        self.assertEqual(d.mask(WHO), WHO)
        self.assertEqual(d.mask('a' * 40), 'a' * 40)
        self.assertEqual(d.mask('한글 demo /example/workspace'), '한글 demo /example/workspace')
        self.assertEqual(d.kst('2026-11-06T23:30:00Z'), '2026-11-07 08:30:00 KST')
        self.assertEqual(d.kst('bad'), '시각 미상')

    def test_authorization_headers_mask_the_entire_credential(self):
        tokens = ['x' * 24, '0123456789abcdef' * 2 + '01234567', 'ZHVtbXk6ZHVtbXk=']
        for token in tokens:
            for header in ['Authorization: Bearer ' + token,
                           json.dumps({'Authorization': 'Bearer ' + token}),
                           'Authorization: Basic ' + token]:
                self.assertNotIn(token, d.mask(header))
                projected = d.project_messages([{'type': 'assistant', 'message': {'content': header}}], 'claude')
                self.assertNotIn(token, json.dumps(projected))
        self.assertEqual(d.mask('commit ' + tokens[1]), 'commit ' + tokens[1])

    def test_owner_excludes_reviewer_and_supports_phase_owner(self):
        card = {'lines': ['담당: codex:' + SID + ' / 검토: claude:11111111-1111-1111-1111-111111111111']}
        self.assertEqual(d.owner_id(card), WHO)
        status = render.owner_status(card, WHO, [{'id': WHO, 'running': False, 'mtime': 0, 'preview': ''}])
        self.assertEqual(status['state'], '대기')  # recent files/quoted IDs do not prove liveness
        card['lines'] = ['담당: 1단계 codex:' + SID + ' · 2단계 claude:11111111-1111-1111-1111-111111111111']
        self.assertEqual(d.owner_id(card), 'claude:11111111-1111-1111-1111-111111111111')

    def test_codex_no_duplicate_messages_and_tools_are_masked(self):
        events = [
            {'type': 'event_msg', 'payload': {'type': 'agent_message', 'message': 'hello'}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': 'hello'}]}},
            {'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'output': 'password=exampleCredential'}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'phase': 'analysis', 'content': [{'type': 'text', 'text': 'internal'}]}},
        ]
        rows = d.project_messages(events, 'codex')
        self.assertEqual([m['role'] for m in rows], ['assistant', 'tool'])
        self.assertEqual(rows[1]['text'], '[가림]')

    def test_claude_text_and_tool_results_exclude_thinking(self):
        events = [{'type': 'assistant', 'message': {'content': [{'type': 'thinking', 'thinking': 'private thought'}, {'type': 'text', 'text': 'answer'}]}},
                  {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': '123456789012'}]}}]
        rows = d.project_messages(events, 'claude')
        self.assertEqual([m['text'] for m in rows], ['answer', '[가림]'])

    def test_mask_before_truncation(self):
        value = 'a' * 2390 + ' token=' + 'Secret' * 20
        rows = d.project_messages([{'type': 'user', 'message': {'content': value}}], 'claude')
        self.assertNotIn('Secret', rows[0]['text'])

    def test_paging_and_incomplete_row_preserve_source(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'log.jsonl'
            raw = b''.join((json.dumps({'n': i}) + '\n').encode() for i in range(200)) + b'{"incomplete":'
            path.write_bytes(raw)
            before, seen = None, []
            while True:
                events, start, _ = d.read_events(path, before, budget=128)
                seen = [e['n'] for e in events] + seen
                if not start:
                    break
                self.assertTrue(before is None or start < before)
                before = start
            self.assertEqual(seen, list(range(200)))
            self.assertEqual(path.read_bytes(), raw)

    def test_paging_giant_single_record_does_not_stall(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'log.jsonl'
            path.write_text('{"n":0}\n' + json.dumps({'large': 'x' * 1000}) + '\n{"n":1}\n')
            before, seen, steps = None, [], 0
            while True:
                events, cursor, _ = d.read_events(path, before, budget=128)
                seen += [e['n'] for e in events if 'n' in e]
                steps += 1
                if not cursor:
                    break
                self.assertTrue(before is None or cursor < before)
                before = cursor
                self.assertLess(steps, 20)
            self.assertEqual(sorted(seen), [0, 1])

    def test_page_start_at_record_boundary_keeps_first_record(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'log.jsonl'
            path.write_bytes(b'{"n":0}\n{"n":1}\n{"n":2}\n')
            rows, cursor, _ = d.read_events(path, budget=16)
            self.assertEqual([e['n'] for e in rows], [1, 2])
            self.assertEqual(d.read_events(path, before=cursor, budget=16)[0], [{'n': 0}])

    def test_symlink_rejected_and_session_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td); (p / 'file').write_text('{}\n'); (p / 'link').symlink_to(p / 'file')
            with self.assertRaises(OSError):
                d.read_events(p / 'link')
        with self.assertRaises(ValueError):
            d.conversation('../../credentials.env')

    def test_session_and_chat_projection_masks_without_writing(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'log.jsonl'
            event = {'type': 'response_item', 'timestamp': '2026-11-06T14:00:00Z', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'token=exampleCredential'}]}}
            raw = json.dumps(event).encode() + b'\n'; path.write_bytes(raw)
            with patch.object(d, 'paths', return_value={WHO: path}):
                self.assertEqual(d.conversation(WHO)['messages'][0]['text'], '[가림]')
            self.assertEqual(path.read_bytes(), raw)
            path.write_text(json.dumps({'text': '123456789012', 'ts': '2026-11-06T14:00:00Z'}) + '\n')
            with patch.object(d, 'ROOM', path):
                self.assertEqual(d.chat()['messages'][0]['text'], '[가림]')

    def test_send_runs_cli_in_isolated_room_and_cli_works_without_server(self):
        with tempfile.TemporaryDirectory() as td, patch.object(d, 'ROOM', Path(td) / 'chat.jsonl'), patch.object(d, 'CHAT', DEMO_CHAT):
            (Path(td) / '.workspace-demo').touch()
            result = d.send_message({'to': 'all', 'text': 'demo isolated UI test', 'from': 'user'})
            self.assertTrue(result['stored'])
            message = json.loads(d.ROOM.read_text())
            self.assertEqual(message['from'], d.OPERATOR)
            self.assertEqual(d.chat()['messages'][0]['text'], message['text'])
            raw = d.ROOM.read_bytes()
            with self.assertRaises(ValueError):
                d.send_message({'to': 'all', 'text': 'token=exampleCredential'})
            self.assertEqual(d.ROOM.read_bytes(), raw)

    def test_send_rejects_user_arbitrary_target_and_empty_text(self):
        for body in [{'to': 'user', 'text': 'hello'}, {'to': '--help', 'text': 'hello'}, {'to': 'all', 'text': ' '}]:
            with self.assertRaises(ValueError):
                d.send_message(body)

    def test_uncoordinated_board_edit_is_rejected_and_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'BOARD.md'
            initial = '## 진행\n### B-1 [agents] move\n\n### B-2 [agents] old\n\n## 완료\n'
            p.write_text(initial)
            actual = serve._atomic_write
            def race(path, text, expected):
                p.write_text(initial.replace('old', 'new external content'))
                return actual(path, text, expected)
            with patch.object(serve, 'BOARD', str(p)), patch.object(serve, '_atomic_write', side_effect=race):
                with self.assertRaises(board_store.Conflict):
                    serve.complete_card('B-1', 'fixture')
            self.assertIn('new external content', p.read_text())
            self.assertIn('## 진행\n### B-1', p.read_text())

    def test_atomic_replacement_with_identical_content_changes_version(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'BOARD.md'; p.write_text('original')
            _, version = board_store.snapshot(p)
            other = Path(td) / 'replacement'; other.write_text('original'); other.replace(p)
            with self.assertRaises(board_store.Conflict):
                board_store.atomic_write(p, 'lost', version)
            self.assertEqual(p.read_text(), 'original')

    def test_cooperating_cli_concurrent_add_and_move(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'BOARD.md'; p.write_text('## 진행\n\n## 검토 대기\n\n## 할 일\n\n## 완료\n\n## 기각\n')
            command = [sys.executable, str(ENTRYPOINT), 'board', '--file', str(p)]
            children = [subprocess.Popen(command + ['add', '--project', 'agents', '--title', f'fixture {i}', '--owner', WHO], stdout=subprocess.PIPE, stderr=subprocess.PIPE) for i in range(8)]
            for child in children:
                child.communicate(timeout=10)
                self.assertEqual(child.returncode, 0)
            text = p.read_text()
            self.assertEqual(len(__import__('re').findall(r'^### B-\d+', text, __import__('re').M)), 8)
            self.assertEqual(len(set(__import__('re').findall(r'^### (B-\d+)', text, __import__('re').M))), 8)
            args = command + ['move', 'B-1', '검토 대기', '--summary', 'result', '--summary', 'evidence', '--summary', 'next']
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertIn('## 검토 대기\n\n### B-1', p.read_text())

    def test_duplicate_card_id_is_rejected(self):
        text = '## 진행\n### B-1 [agents] one\n### B-1 [agents] two\n## 완료\n'
        with self.assertRaises(board_store.Conflict):
            board_store.move(text, 'B-1', '완료')


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.board = self.root / 'BOARD.md'
        self.board.write_text('## 진행\n\n### B-1 [agents] test\n담당: sample\n\n### B-2 [agents] preserve\nother\n\n## 완료\n\n')
        self.approvals = self.root / 'approvals.json'
        self.approvals.write_text('[{"title":"test"},{"title":"keep"}]')
        self.patches = contextlib.ExitStack()
        for name, value in [('BOARD', str(self.board)), ('APPROVALS', str(self.approvals)), ('LOCK', str(self.root / 'lock')), ('DONE_LOG', str(self.root / 'done.jsonl'))]:
            self.patches.enter_context(patch.object(serve, name, value))
        self.patches.enter_context(patch.object(render, 'render', return_value='<html>fixture</html>'))
        self.server = serve.ThreadingHTTPServer(('127.0.0.1', 0), serve.Handler)
        self.port = self.server.server_port
        self.patches.enter_context(patch.object(serve, 'PORT', self.port))
        self.patches.enter_context(patch.object(serve.Handler, 'token', 'fixture-token'))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.patches.close(); self.tmp.cleanup()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers or {})
        response = conn.getresponse(); data = response.read(); code = response.status
        conn.close(); return code, data

    def post(self, body, path='/api/done', **headers):
        return self.request('POST', path, body, {'Origin': f'http://localhost:{self.port}', **headers})

    def test_get_host_rebinding_and_foreign_origin_denied(self):
        self.assertEqual(self.request('GET', '/', headers={'Host': 'evil.example'})[0], 403)
        self.assertEqual(self.request('GET', '/api/chat', headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request('GET', '/')[0], 200)

    def test_post_requires_origin_and_token_for_both_routes(self):
        for route in ['/api/done', '/api/chat/send']:
            self.assertEqual(self.request('POST', route, {'token': 'fixture-token'})[0], 403)
            self.assertEqual(self.post({'token': 'wrong'}, route)[0], 403)
            self.assertEqual(self.post({'token': '한글'}, route)[0], 403)
            self.assertEqual(self.post({'token': 'fixture-token'}, route, Origin='http://evil.example')[0], 403)

    def test_bad_body_and_large_request(self):
        self.assertEqual(self.post([])[0], 400)
        self.assertEqual(self.post({'token': 'fixture-token', 'text': 'x' * 100001})[0], 413)

    def test_card_completion_preserves_other_card_and_audits(self):
        self.assertEqual(self.post({'token': 'fixture-token', 'kind': 'card', 'id': 'B-1'})[0], 200)
        text = self.board.read_text()
        self.assertIn('### B-2 [agents] preserve\nother', text)
        self.assertRegex(text, r'## 완료\n\s*### B-1')
        self.assertEqual(json.loads((self.root / 'done.jsonl').read_text())['from'], '진행')
        self.assertEqual(self.post({'token': 'fixture-token', 'kind': 'card', 'id': 'B-1'})[0], 409)

    def test_approval_completion_keeps_other_approval(self):
        self.assertEqual(self.post({'token': 'fixture-token', 'kind': 'approval', 'title': 'test'})[0], 200)
        self.assertEqual(json.loads(self.approvals.read_text()), [{'title': 'keep'}])
        self.assertEqual(json.loads((self.root / 'done.jsonl').read_text())['title'], 'test')

    def test_opaque_approval_audits_server_title_even_without_browser_title(self):
        title = 'Review release checklist'
        self.approvals.write_text(json.dumps([{'title': title}, {'title': 'keep'}]))
        key = board_store.approval_key(title)
        self.assertEqual(self.post({'token': 'fixture-token', 'kind': 'approval', 'approval_id': key})[0], 200)
        audit = json.loads((self.root / 'done.jsonl').read_text())
        self.assertEqual((audit['title'], audit['approval_id']), (title, key))
        self.assertEqual(json.loads(self.approvals.read_text()), [{'title': 'keep'}])

    def test_opaque_approval_id_round_trip_preserves_redaction(self):
        title = '장비 123456789012 확인'
        self.approvals.write_text(json.dumps([{'title': title}, {'title': 'keep'}]))
        button = render.done_button('approval', title)
        key = board_store.approval_key(title)
        self.assertNotIn('123456789012', button)
        self.assertIn('data-key="' + key + '"', button)
        self.assertEqual(self.post({'token': 'fixture-token', 'kind': 'approval', 'approval_id': key})[0], 200)
        self.assertEqual(json.loads(self.approvals.read_text()), [{'title': 'keep'}])
        audit = json.loads((self.root / 'done.jsonl').read_text())
        self.assertEqual(audit['title'], '장비 [가림] 확인')
        self.assertEqual(audit['approval_id'], key)
        self.assertNotIn('123456789012', (self.root / 'done.jsonl').read_text())

    def test_committed_completion_does_not_depend_on_page_render(self):
        with patch.object(render, 'render', side_effect=ValueError('invalid optional data')):
            self.assertEqual(self.post({'token': 'fixture-token', 'kind': 'card', 'id': 'B-1'})[0], 200)
        self.assertRegex(self.board.read_text(), r'## 완료\n\s*### B-1')

    def test_default_http_port_accepts_browser_normalized_authorities(self):
        with patch.object(serve, 'PORT', 80):
            self.assertEqual(self.request('GET', '/', headers={'Host': 'localhost'})[0], 200)
            self.assertEqual(self.request('POST', '/api/done', {'token': 'fixture-token', 'kind': 'card', 'id': 'B-1'},
                                          {'Host': 'localhost', 'Origin': 'http://localhost'})[0], 200)
            self.assertEqual(self.request('GET', '/', headers={'Host': 'evil.example'})[0], 403)
            self.assertEqual(self.request('GET', '/', headers={'Host': 'localhost:8766'})[0], 403)

    def test_chat_calls_cli_wrapper_and_reports_stored_delivery_failure(self):
        with patch.object(d, 'send_message', return_value={'ok': False, 'stored': True}) as send:
            code, data = self.post({'token': 'fixture-token', 'to': WHO, 'text': 'hello'}, '/api/chat/send')
            self.assertEqual(code, 409); self.assertTrue(json.loads(data)['stored']); send.assert_called_once()

    def test_private_files_not_served_and_bad_cursor_rejected(self):
        for path in ['/.token', '/credentials.env', '/../../BOARD.md', '/serve.py']:
            self.assertEqual(self.request('GET', path)[0], 404)
        self.assertEqual(self.request('GET', '/api/chat?before=-1')[0], 400)


if __name__ == '__main__':
    unittest.main(verbosity=2)
