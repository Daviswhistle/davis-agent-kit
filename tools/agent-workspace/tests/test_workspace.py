import contextlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_workspace import dashboard, render, serve
from agent_workspace.config import Config, configure
from agent_workspace.demo import create, CODEX_ID


class WorkspaceTests(unittest.TestCase):
    def test_claude_mixed_blocks_keep_order_and_adjacent_text_runs(self):
        events = [
            {'type': 'assistant', 'message': {'content': [
                {'type': 'text', 'text': 'before one'},
                {'type': 'thinking', 'thinking': 'hidden reasoning'},
                {'type': 'text', 'text': 'before two'},
                {'type': 'tool_use', 'name': 'Read', 'id': 'tool', 'input': {}},
                {'type': 'text', 'text': 'after tool'}]}},
            {'type': 'user', 'message': {'content': [
                {'type': 'tool_result', 'content': [{'type': 'text', 'text': 'result token=exampleCredential'}]},
                {'type': 'text', 'text': 'continue'}]}},
            {'type': 'assistant', 'message': {'content': 'legacy text'}}]
        rows = dashboard.project_messages(events, 'claude')
        self.assertEqual([r['role'] for r in rows], ['assistant', 'tool', 'assistant', 'tool', 'user', 'assistant'])
        self.assertEqual([r['text'] for r in rows], ['before one\nbefore two', '호출: Read', 'after tool', 'result [가림]', 'continue', 'legacy text'])

    def test_multiple_owner_rows_keep_the_current_worker_in_inventory_and_board(self):
        from agent_workspace.demo import CLAUDE_ID
        reviewer = 'bbbbbbbb-cccc-4ddd-8eee-ffffffffffff'
        card = {'id': 'B-1', 'title': 'handoff', 'proj': 'demo', 'lines': [
            '담당: 1단계 codex:' + CODEX_ID + ' · 검토: claude:' + reviewer,
            '담당: 2단계 claude:' + CLAUDE_ID,
            '검토: codex:' + reviewer]}
        self.assertEqual(dashboard.owner_id(card), 'claude:' + CLAUDE_ID)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); codex = root / 'codex.jsonl'; claude = root / 'claude.jsonl'
            codex.write_text('{}\n'); claude.write_text('{}\n')
            old = time.time() - 2 * 86400
            os.utime(codex, (old, old)); os.utime(claude, (old, old))
            with patch.object(dashboard, 'paths', return_value={'codex:' + CODEX_ID: codex, 'claude:' + CLAUDE_ID: claude}), patch.object(dashboard, 'process_sessions', return_value={}):
                self.assertEqual([r['id'] for r in dashboard.sessions({'진행': [card]})], ['claude:' + CLAUDE_ID])
        cols = {name: [] for name in ('진행', '검토 대기', '할 일', '완료', '기각')}; cols['진행'] = [card]
        with patch.object(render, 'parse_board', return_value=cols), patch.object(render, 'approvals', return_value=[]), patch.object(render, 'schedule', return_value=[]):
            page = render.render()
        self.assertIn('담당: 2단계 claude:' + CLAUDE_ID, page)
        self.assertNotIn('담당: 1단계 codex:' + CODEX_ID, page)

    def test_identifier_dense_record_restores_ids_in_one_pass_before_summary(self):
        text = (CODEX_ID + '\n') * 20000 + ' commit ' + 'a' * 40 + ' date 2099-01-01 token=exampleCredential'
        event = {'type': 'response_item', 'payload': {'type': 'function_call_output', 'output': text}}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'session.jsonl'
            raw = (json.dumps(event) + '\n').encode(); self.assertLess(len(raw), 768000)
            path.write_bytes(raw); started = time.perf_counter()
            with patch.object(dashboard, 'paths', return_value={'codex:' + CODEX_ID: path}):
                data = dashboard.conversation('codex:' + CODEX_ID)
            self.assertLess(time.perf_counter() - started, 1.5)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(len(data['messages']), 1)
            self.assertTrue(data['messages'][0]['text'].startswith(CODEX_ID))
            self.assertLessEqual(len(data['messages'][0]['text']), 4010)
        masked = dashboard.mask(text)
        self.assertEqual(masked.count(CODEX_ID), 20000)
        self.assertIn('a' * 40, masked); self.assertIn('2099-01-01', masked)
        self.assertNotIn('exampleCredential', masked)
        self.assertNotIn('\ue000', masked)
        unknown_placeholder = '\ue000\u0001\ue001'
        self.assertEqual(dashboard.mask(unknown_placeholder), '\ue000\ue001')

    def test_repeated_jwt_prefix_is_fast_and_embedded_tokens_still_detected(self):
        from agent_workspace.agent_chat import safe_text
        for size in (16000, 160000):
            text = 'eyJ-' * (size // 4)
            started = time.perf_counter()
            self.assertEqual(dashboard.mask(text), text)
            if size <= 16000:
                safe_text(text)
            self.assertLess(time.perf_counter() - started, 1.5)
        token = '.'.join(('eyJabcdefghijk', 'abcdefghijk', 'abcdefghijk'))
        for prefix in ('', 'name-', '漢字-', '/workspace/file-', 'token='):
            with self.subTest(prefix=prefix):
                text = prefix + token
                self.assertNotIn(token, dashboard.mask(text))
                with self.assertRaises(ValueError):
                    safe_text(text)
        for ordinary in ('eyJabc.short.short', 'name-eyJabcdefghijk.short.abcdefghijk', 'plain.report.filename'):
            self.assertEqual(dashboard.mask(ordinary), ordinary)
            safe_text(ordinary)

    def test_hyphenated_identifiers_do_not_stall_redaction_or_send_validation(self):
        from agent_workspace.agent_chat import safe_text
        # Test bounded cases first so the old quadratic algorithm fails quickly.
        for text in ('a-' * 8000, 'key-' * 4000, 'secret-' * 2000):
            started = time.perf_counter()
            self.assertEqual(dashboard.mask(text), text)
            safe_text(text)
            self.assertLess(time.perf_counter() - started, 1.5)
        large = 'key-' * 100000
        started = time.perf_counter()
        row = dashboard.project_messages([{'type': 'response_item', 'payload': {
            'type': 'function_call_output', 'output': large}}], 'codex')[0]
        self.assertEqual(row['role'], 'tool')
        self.assertLessEqual(len(row['text']), 4010)
        self.assertLess(time.perf_counter() - started, 2.5)
        for name in ('a-' * 1000 + 'api-key', 'token-' * 200 + 'suffix', 'x-Authorization', 'κey-token'):
            value = name + '="exampleCredential"'
            self.assertNotIn('exampleCredential', dashboard.mask(value))
            with self.assertRaises(ValueError):
                safe_text(value)
        value = 'a-' * 1300 + 'api-key=exampleCredential'
        row = dashboard.project_messages([{'type': 'user', 'message': {'content': value}}], 'claude')[0]
        self.assertNotIn('exampleCredential', row['text'])

    def test_process_roots_accept_canonical_alias_and_dotdot_for_both_clients(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for kind in ('codex', 'claude'):
                canonical = root / kind
                relative = ('2026/01/01/rollout-' + CODEX_ID + '.jsonl') if kind == 'codex' else ('project/' + CODEX_ID + '.jsonl')
                log = canonical / relative; log.parent.mkdir(parents=True); log.write_text('{}\n')
                (canonical / 'nested').mkdir()
                alias = root / (kind + '-alias'); alias.symlink_to(canonical, target_is_directory=True)
                proc = root / ('proc-' + kind) / '99999'; (proc / 'fd').mkdir(parents=True)
                (proc / 'exe').symlink_to('/opt/bin/' + kind)
                (proc / 'comm').write_text(kind)
                (proc / 'cmdline').write_bytes(kind.encode() + b'\0')
                (proc / 'fd/4').symlink_to(log)
                def mapped_path(value):
                    return proc.parent if str(value) == '/proc' else Path(value)
                for configured in (canonical, alias, canonical / 'nested/..'):
                    with self.subTest(kind=kind, configured=configured.name):
                        with patch.object(dashboard, 'Path', side_effect=mapped_path), patch.object(dashboard, kind.upper() if kind == 'codex' else 'CLAUDE', configured):
                            self.assertEqual(dashboard.process_sessions(), {kind + ':' + CODEX_ID: [99999]})
                (proc / 'exe').unlink()
                (proc / 'exe').symlink_to('/opt/bin/' + kind + ' (deleted)')
                with patch.object(dashboard, 'Path', side_effect=mapped_path), patch.object(dashboard, 'CODEX' if kind == 'codex' else 'CLAUDE', canonical):
                    self.assertEqual(dashboard.process_sessions(), {kind + ':' + CODEX_ID: [99999]})
                    (proc / 'fd/4').unlink()
                    flag = 'resume' if kind == 'codex' else '--resume'
                    (proc / 'cmdline').write_bytes(('\0'.join([kind, flag, CODEX_ID]) + '\0').encode())
                    self.assertEqual(dashboard.process_sessions(), {kind + ':' + CODEX_ID: [99999]})

    def test_claude_fork_excludes_only_its_source_and_preserves_normal_resume(self):
        from agent_workspace.demo import CLAUDE_ID
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); logs = root / 'logs'; logs.mkdir()
            for sid in (CODEX_ID, CLAUDE_ID):
                (logs / (sid + '.jsonl')).write_text('{}\n')
            proc = root / 'proc/101'; (proc / 'fd').mkdir(parents=True)
            (proc / 'exe').symlink_to('/opt/bin/claude'); (proc / 'comm').write_text('claude')
            (proc / 'fd/4').symlink_to(logs / (CLAUDE_ID + '.jsonl'))
            (proc / 'fd/5').symlink_to(logs / (CODEX_ID + '.jsonl'))
            other = root / 'proc/102'; (other / 'fd').mkdir(parents=True)
            (other / 'exe').symlink_to('/opt/bin/claude'); (other / 'comm').write_text('claude')
            (other / 'cmdline').write_bytes(('claude\0--resume\0' + CODEX_ID + '\0').encode())
            def mapped_path(value):
                return proc.parent if str(value) == '/proc' else Path(value)
            def detected():
                return {who: sorted(pids) for who, pids in dashboard.process_sessions().items()}
            with patch.object(dashboard, 'Path', side_effect=mapped_path), patch.object(dashboard, 'CLAUDE', logs):
                for resume in (['--resume', CODEX_ID], ['--resume=' + CODEX_ID], ['-r', CODEX_ID]):
                    (proc / 'cmdline').write_bytes(('\0'.join(['claude', *resume, '--fork-session']) + '\0').encode())
                    self.assertEqual(detected(), {'claude:' + CLAUDE_ID: [101], 'claude:' + CODEX_ID: [102]})
                for fd in (proc / 'fd').iterdir():
                    fd.unlink()
                (proc / 'cmdline').write_bytes(('\0'.join(['claude', '--resume', CODEX_ID, '--fork-session', '--session-id', CLAUDE_ID]) + '\0').encode())
                self.assertEqual(detected(), {'claude:' + CLAUDE_ID: [101], 'claude:' + CODEX_ID: [102]})
                (proc / 'cmdline').write_bytes(('claude\0--resume\0' + CODEX_ID + '\0').encode())
                self.assertEqual(detected(), {'claude:' + CODEX_ID: [101, 102]})
                (proc / 'cmdline').write_bytes(('claude\0--resume\0' + CODEX_ID + '\0--\0--fork-session\0').encode())
                self.assertEqual(detected(), {'claude:' + CODEX_ID: [101, 102]})

    def test_invalid_receipt_after_provider_write_reports_uncertain_delivery(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); provider = root / 'provider'
            record = json.dumps({'id': 'stored', 'text': 'stored before failure', 'from': 'codex:board-operator', 'to': 'all'}) + '\n'
            for stdout in ('not-json', '{}', '{"stored":"false"}', '{"stored":null}', '{"stored":1}'):
                provider.write_text('#!' + sys.executable + '\nfrom pathlib import Path\nimport sys\nPath(sys.argv[sys.argv.index("--home")+1], "chat.jsonl").write_text(' + repr(record) + ')\nprint(' + repr(stdout) + ')\n')
                provider.chmod(0o700)
                with patch.object(dashboard, 'ROOM', root / 'chat.jsonl'), patch.object(dashboard, 'CHAT', provider):
                    result = dashboard.send_message({'to': 'all', 'text': 'example'})
                    self.assertTrue(result['uncertain']); self.assertNotIn('stored', result)
                    self.assertEqual(dashboard.chat()['messages'][0]['text'], 'stored before failure')
                self.assertEqual((root / 'chat.jsonl').read_text(), record)
            provider.write_text('#!' + sys.executable + '\nimport sys\nsys.stderr.buffer.write(bytes([255]))\nprint(\'{"stored":true}\')\n')
            with patch.object(dashboard, 'ROOM', root / 'chat.jsonl'), patch.object(dashboard, 'CHAT', provider):
                self.assertTrue(dashboard.send_message({'to': 'all', 'text': 'example'})['stored'])
            for stored, code in ((False, 0), (True, 0), (True, 3)):
                response = subprocess.CompletedProcess([], code, json.dumps({'stored': stored}), '')
                with patch.object(dashboard, 'ROOM', root / 'chat.jsonl'), patch.object(dashboard.subprocess, 'run', return_value=response):
                    result = dashboard.send_message({'to': 'all', 'text': 'example'})
                self.assertEqual(result['stored'], stored)
                self.assertEqual(result['ok'], stored and code == 0)
            receipt = {'stored': True, 'password': 'a' * 40, 'id': 'a' * 40, 'metadata': {'access_token': 'b' * 40}}
            response = subprocess.CompletedProcess([], 0, json.dumps(receipt), '')
            with patch.object(dashboard, 'ROOM', root / 'chat.jsonl'), patch.object(dashboard.subprocess, 'run', return_value=response):
                result = dashboard.send_message({'to': 'all', 'text': 'example'})
            self.assertEqual(result['receipt']['password'], '[가림]')
            self.assertEqual(result['receipt']['metadata']['access_token'], '[가림]')
            self.assertEqual(result['receipt']['id'], 'a' * 40)

    def test_config_precedence_and_all_paths(self):
        with tempfile.TemporaryDirectory() as td:
            config_file = Path(td) / 'config.json'
            config_file.write_text(json.dumps({'port': 9011, 'data_dir': td, 'board': td + '/tasks.md'}))
            with patch.dict(os.environ, {'AGENT_WORKSPACE_PORT': '9012'}):
                config = Config.load(config_file, {'port': 9013})
                self.assertEqual(config.port, 9013)
                self.assertEqual(config.board, Path(td) / 'tasks.md')
                self.assertEqual(config.data_dir, Path(td))
            config_file.write_text('{"host":"0.0.0.0"}')
            with self.assertRaises(ValueError):
                Config.load(config_file)

    def test_10000_tool_records_are_bounded_and_sources_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            config = create(Path(td), turns=5000)
            configure(config)
            path = next(config.codex_root.rglob('*.jsonl'))
            before = path.read_bytes()
            started = time.monotonic()
            data = dashboard.conversation('codex:' + CODEX_ID)
            elapsed = time.monotonic() - started
            self.assertLessEqual(len(data['messages']), 120)
            self.assertIsNotNone(data['before'])
            self.assertEqual(data['messages'][-1]['role'], 'assistant')
            self.assertEqual(path.read_bytes(), before)
            # Generous regression guard; observed timings are separately reported.
            self.assertLess(elapsed, 5)

    def test_record_count_pagination_has_no_duplicates_or_gaps(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'log.jsonl'
            path.write_text(''.join(json.dumps({'n': i}) + '\n' for i in range(1000)))
            cursor, result = None, []
            while True:
                rows, cursor, _ = dashboard.read_events(path, cursor, limit=120)
                result = [r['n'] for r in rows] + result
                if not cursor:
                    break
            self.assertEqual(result, list(range(1000)))

    def test_analysis_channel_and_thinking_never_projected(self):
        rows = dashboard.project_messages([{'type': 'response_item', 'payload': {
            'type': 'message', 'role': 'assistant', 'channel': 'analysis',
            'content': [{'type': 'text', 'text': 'private reasoning'}]}}], 'codex')
        self.assertEqual(rows, [])

    def test_html_escapes_board_and_never_contains_pattern_secret(self):
        with tempfile.TemporaryDirectory() as td:
            config = create(Path(td))
            config.board.write_text('## 진행\n### B-1 [demo] <img src=x onerror=alert(1)>\ntoken=exampleCredential\nAuthorization: Bearer ' + 'f' * 40 + '\n')
            with patch.object(render, 'CONFIG', config):
                text = render.render('demo-csrf')
                self.assertIn('&lt;img', text)
                self.assertNotIn('<img src=x', text)
                self.assertNotIn('exampleCredential', text)
                self.assertNotIn('f' * 40, text)
                self.assertIn('content="demo-csrf"', text)
                self.assertNotIn('f' * 40, render.render())

    def test_empty_board_and_absent_optional_files_render(self):
        with tempfile.TemporaryDirectory() as td:
            config = Config.load(overrides={'data_dir': td, 'board': Path(td) / 'missing.md'})
            with patch.object(render, 'CONFIG', config):
                page = render.render()
                self.assertEqual(page.count('class="board-column"'), 5)
                self.assertIn('아직 카드가 없습니다', page)

    def test_invalid_optional_data_has_recoverable_error(self):
        with tempfile.TemporaryDirectory() as td:
            config = create(Path(td))
            (config.data_dir / 'approvals.json').write_text('{malformed')
            with patch.object(render, 'CONFIG', config):
                with self.assertRaises(ValueError):
                    render.render()
            self.assertIn('다시 연결', render.error_page())

    def test_outgoing_secrets_are_rejected_before_any_cli(self):
        samples = ['{"api_key":"exampleCredential"}', 'Bearer ' + 'aB9' * 15, 'password=exampleCredential', '123-456-789012']
        with patch.object(dashboard.subprocess, 'run') as run:
            for sample in samples:
                with self.assertRaises(ValueError):
                    dashboard.send_message({'to': 'all', 'text': sample})
            run.assert_not_called()

    def test_demo_transport_cannot_use_an_unmarked_room(self):
        with tempfile.TemporaryDirectory() as td:
            command = [sys.executable, str(Path(dashboard.__file__).with_name('demo_chat.py')),
                       '--home', td, 'send', '--from', 'codex:board-operator', '--to', 'all', '--', 'hello']
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((Path(td) / 'chat.jsonl').exists())

    def test_alternate_timezone(self):
        with patch.object(dashboard, 'KST', __import__('zoneinfo').ZoneInfo('UTC')):
            self.assertEqual(dashboard.kst('2026-01-01T03:00:00Z'), '2026-01-01 03:00:00 UTC')

    def test_dates_remain_readable_while_account_patterns_are_masked(self):
        self.assertEqual(dashboard.mask('2099-01-01 · 10:00'), '2099-01-01 · 10:00')
        self.assertIn('[가림]', dashboard.mask('123-456-789012'))
        self.assertNotIn('2099-01-01', dashboard.mask('token=2099-01-01'))

    def test_first_cli_edit_creates_its_lock_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            board = root / 'BOARD.md'
            board.write_text('## 진행\n\n## 검토 대기\n\n## 할 일\n\n## 완료\n\n## 기각\n')
            env = {k: v for k, v in os.environ.items() if not k.startswith('AGENT_WORKSPACE_')}
            env.update(AGENT_WORKSPACE_BOARD=str(board), AGENT_WORKSPACE_DATA_DIR=str(root / 'new-state'))
            result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'workspace.py'),
                                     'board', 'add', '--project', 'demo', '--title', 'first edit',
                                     '--owner', 'codex:' + CODEX_ID], capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('### B-1 [demo] first edit', board.read_text())
            self.assertTrue((root / 'new-state/.lock').is_file())

    def test_static_snapshot_needs_no_server_assets_or_javascript(self):
        from html.parser import HTMLParser
        class Parser(HTMLParser):
            board_hidden = None
            scripts = 0
            buttons = 0
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if attrs.get('id') == 'board-view':
                    self.board_hidden = 'hidden' in attrs
                self.scripts += tag == 'script'
                self.buttons += tag == 'button'
        with tempfile.TemporaryDirectory() as td:
            config = create(Path(td))
            with patch.object(render, 'CONFIG', config):
                page = render.render()
            parser = Parser(); parser.feed(page)
            self.assertIs(parser.board_hidden, False)
            self.assertEqual(parser.scripts, 0)
            self.assertEqual(parser.buttons, 0)
            self.assertIn('<style>', page)
            self.assertNotIn('href="/dashboard.css"', page)
            self.assertIn('검색 화면 접근성 개선', page)

    def test_codex_extra_filename_uuid_does_not_change_thread_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / '2026/01/01' / ('rollout-demo-' + CODEX_ID + '_aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee.jsonl')
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': CODEX_ID}}) + '\n')
            with patch.object(dashboard, 'CODEX', root), patch.object(dashboard, 'CLAUDE', root / 'missing'):
                self.assertEqual(dashboard.paths(), {'codex:' + CODEX_ID: path})

    def test_cli_render_override_does_not_reparse_bad_environment_on_import(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / 'snapshot.html'
            env = {k: v for k, v in os.environ.items() if not k.startswith('AGENT_WORKSPACE_')}
            env['AGENT_WORKSPACE_PORT'] = 'bad'
            entry = str(Path(__file__).resolve().parents[1] / 'workspace.py')
            result = subprocess.run([sys.executable, entry, '--demo', '--port', '8766', '--render', str(output)],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('검색 화면 접근성 개선', output.read_text())
            invalid = subprocess.run([sys.executable, entry, '--demo', '--render', str(output)],
                                     env=env, capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 2)

    def test_cli_server_override_does_not_reparse_bad_environment_on_import(self):
        import signal
        import socket
        import urllib.request
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        env = {k: v for k, v in os.environ.items() if not k.startswith('AGENT_WORKSPACE_')}
        env['AGENT_WORKSPACE_PORT'] = 'bad'
        entry = str(Path(__file__).resolve().parents[1] / 'workspace.py')
        child = subprocess.Popen([sys.executable, entry, '--demo', '--port', str(port)],
                                 env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            ready = False
            for _ in range(60):
                if child.poll() is not None:
                    break
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=1) as response:
                        ready = json.load(response)['ok']; break
                except OSError:
                    time.sleep(.05)
            self.assertTrue(ready)
        finally:
            if child.poll() is None:
                child.send_signal(signal.SIGINT)
            child.communicate(timeout=5)

    def test_chat_page_exposes_read_boundary_for_gap_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'chat.jsonl'
            path.write_text(''.join(json.dumps({'id': str(i), 'text': f'message {i}'}) + '\n' for i in range(300)))
            with patch.object(dashboard, 'ROOM', path):
                latest = dashboard.chat()
                prior = dashboard.chat(latest['before'])
            self.assertEqual(latest['end'], path.stat().st_size)
            self.assertEqual(prior['end'], latest['before'])
            self.assertEqual(len(latest['messages']), 120)

    def test_default_and_relative_cli_writers_share_one_lock(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            board = root / 'BOARD.md'
            board.write_text('## 진행\n\n## 검토 대기\n\n## 할 일\n\n## 완료\n\n## 기각\n')
            env = {k: v for k, v in os.environ.items() if not k.startswith('AGENT_WORKSPACE_')}
            env.update(AGENT_WORKSPACE_BOARD=str(board), AGENT_WORKSPACE_DATA_DIR=str(root / 'state'))
            entry = str(Path(__file__).resolve().parents[1] / 'workspace.py')
            children = []
            for i in range(16):
                command = [sys.executable, entry, 'board'] + (['--file', 'BOARD.md'] if i % 2 else [])
                command += ['add', '--project', 'demo', '--title', f'writer {i}', '--owner', 'codex:' + CODEX_ID]
                children.append(subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
            for child in children:
                _, error = child.communicate(timeout=15)
                self.assertEqual(child.returncode, 0, error)
            import re
            ids = re.findall(r'^### (B-\d+)', board.read_text(), re.M)
            self.assertEqual(len(ids), 16)
            self.assertEqual(len(set(ids)), 16)
            self.assertTrue((root / 'state/.lock').exists())
            self.assertFalse((root / '.board.lock').exists())

    def test_custom_chat_filename_remains_readable_but_cannot_write_elsewhere(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'private.jsonl'
            original = json.dumps({'id': 'demo', 'text': 'existing message'}) + '\n'
            path.write_text(original)
            with patch.object(dashboard, 'ROOM', path), patch.object(dashboard.subprocess, 'run') as run:
                self.assertEqual(dashboard.chat()['messages'][0]['text'], 'existing message')
                with self.assertRaisesRegex(ValueError, '조회 전용'):
                    dashboard.send_message({'to': 'all', 'text': 'new message'})
                run.assert_not_called()
            self.assertEqual(path.read_text(), original)
            self.assertFalse((Path(td) / 'chat.jsonl').exists())

    def test_codex_paging_pairs_adjacent_envelopes_without_losing_repeated_speech(self):
        canonical = {'type': 'response_item', 'timestamp': '2026-01-01T03:00:00Z', 'payload': {
            'type': 'message', 'role': 'assistant', 'content': [{'type': 'text', 'text': 'boundary answer'}]}}
        event = {'type': 'event_msg', 'timestamp': '2026-01-01T03:00:00.005Z',
                 'payload': {'type': 'agent_message', 'message': 'boundary answer'}}
        tool = {'type': 'response_item', 'payload': {'type': 'function_call_output', 'output': 'ok'}}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'session.jsonl'
            for pair in ([canonical, event], [event, canonical]):
                path.write_text(''.join(json.dumps(e) + '\n' for e in [*pair, *([tool] * 119)]))
                original = path.read_bytes()
                with patch.object(dashboard, 'paths', return_value={'codex:' + CODEX_ID: path}):
                    latest = dashboard.conversation('codex:' + CODEX_ID)
                    older = dashboard.conversation('codex:' + CODEX_ID, latest['before'])
                self.assertEqual(sum(m['role'] == 'assistant' for m in latest['messages']), 1)
                self.assertEqual(sum(m['role'] == 'assistant' for m in older['messages']), 0)
                self.assertEqual(path.read_bytes(), original)
        for repetition in ([canonical, canonical], [event, event]):
            self.assertEqual(len(dashboard.project_messages(repetition, 'codex')), 2)
        different = {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant',
                     'content': [{'type': 'text', 'text': 'other answer'}]}}
        self.assertEqual(len(dashboard.project_messages([event, different], 'codex')), 2)

    def test_codex_repeated_paired_emissions_survive_every_page_boundary(self):
        import copy
        response = {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant',
                    'content': [{'type': 'text', 'text': 'repeated answer'}]}}
        event = {'type': 'event_msg', 'payload': {'type': 'agent_message', 'message': 'repeated answer'}}
        tool = {'type': 'response_item', 'payload': {'type': 'function_call_output', 'output': 'ok'}}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'session.jsonl'
            for order in ([response, event], [event, response]):
                for timestamps in (False, True):
                    repeated = [copy.deepcopy(e) for e in order * 3]
                    if timestamps:
                        for index, row in enumerate(repeated):
                            row['timestamp'] = f'2026-01-01T03:00:0{index // 2}.00{index % 2}Z'
                    self.assertEqual(len(dashboard.project_messages(repeated, 'codex')), 3)
                    for trailing in range(115, 122):
                        with self.subTest(order=order[0]['type'], timestamps=timestamps, trailing=trailing):
                            path.write_text(''.join(json.dumps(e) + '\n' for e in repeated + [tool] * trailing))
                            with patch.object(dashboard, 'paths', return_value={'codex:' + CODEX_ID: path}):
                                cursor, messages = None, []
                                while True:
                                    page = dashboard.conversation('codex:' + CODEX_ID, cursor)
                                    messages.extend(page['messages'])
                                    cursor = page['before']
                                    if cursor is None:
                                        break
                            self.assertEqual(sum(m['role'] == 'assistant' for m in messages), 3)
        # An unanchored, bounded chain is kept conservatively rather than losing speech.
        self.assertEqual(len(dashboard.project_messages([response, event] * 3, 'codex', anchored=False)), 6)

    def test_bundled_transport_preserves_16000_chars_and_reply_route(self):
        from agent_workspace import agent_chat
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'chat.jsonl'
            with patch.object(dashboard, 'ROOM', path), patch.object(dashboard, 'CHAT', Path(agent_chat.__file__)):
                text = 'x' * 16000
                result = dashboard.send_message({'to': 'all', 'text': text})
            self.assertTrue(result['stored'])
            message = json.loads(path.read_text())
            self.assertEqual(message['text'], text)
            self.assertEqual(message['reply_target'], 'all')
            self.assertEqual(message['reply_command'][-4:], ['send', '--to', 'all', '--'])
            output = subprocess.run([sys.executable, str(Path(agent_chat.__file__)), '--home', td,
                                     'read', '--from', 'claude:demo', '--all', '--max-chars', '1000'],
                                    capture_output=True, text=True)
            self.assertEqual(output.returncode, 0, output.stderr)
            self.assertIn('reply_target', output.stdout)
            self.assertIn('--to', output.stdout)
            self.assertIn('"reply_target": "all"', output.stdout)
            self.assertIn('reply_command', output.stdout)

    def test_dashboard_uses_transport_validation_for_normal_paths_and_ids(self):
        from agent_workspace import agent_chat
        allowed = ['Report: /workspace/research-20261107/output/REPORT.md',
                   'Review on 2099-01-01 with codex:ordinary-session-2026',
                   'commit ' + 'a' * 40]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'chat.jsonl'
            with patch.object(dashboard, 'ROOM', path), patch.object(dashboard, 'CHAT', Path(agent_chat.__file__)):
                for text in allowed:
                    self.assertTrue(dashboard.send_message({'to': 'all', 'text': text})['stored'])
                original = path.read_bytes()
                for text in ['token=exampleCredential', '/workspace/sk-' + 'A' * 40, '123-456-789012']:
                    with self.assertRaises(ValueError):
                        dashboard.send_message({'to': 'all', 'text': text})
                self.assertEqual(path.read_bytes(), original)
            self.assertEqual([json.loads(line)['text'] for line in path.read_text().splitlines()], allowed)
