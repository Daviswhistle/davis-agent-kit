#!/usr/bin/env python3
"""Isolated browser write/performance fixture; never points at live sessions."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_workspace.demo import create
from agent_workspace.serve import main


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8767)
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix='workspace-browser-') as td:
            config = create(Path(td), port=args.port, turns=5000)
            claude_path = next(config.claude_root.rglob('*.jsonl'))
            with claude_path.open('a', encoding='utf-8') as f:
                f.write(json.dumps({'type': 'assistant', 'message': {'content': [
                    {'type': 'text', 'text': 'order-before'},
                    {'type': 'tool_use', 'id': 'order-fixture', 'name': 'order_probe', 'input': {}},
                    {'type': 'text', 'text': 'order-after'}]}}) + '\n')
            approvals = config.data_dir / 'approvals.json'
            items = json.loads(approvals.read_text(encoding='utf-8'))
            items.append({'title': '장비 123456789012 확인', 'detail': '표시는 가리고 완료 식별자는 보존하는 시험입니다.'})
            approvals.write_text(json.dumps(items, ensure_ascii=False), encoding='utf-8')
            path = next(config.codex_root.rglob('*.jsonl'))
            with path.open('a', encoding='utf-8') as f:
                f.write(json.dumps({'type': 'response_item', 'payload': {
                    'type': 'message', 'role': 'user', 'content': [{'type': 'text',
                    'text': '<img src=x onerror=alert(1)> token=exampleCredential\nAuthorization: Bearer ' + 'z' * 24}]}}) + '\n')
            boundary_id = 'bbbbbbbb-cccc-4ddd-8eee-ffffffffffff'
            boundary_path = config.codex_root / '2026/01/01' / ('rollout-boundary-' + boundary_id + '.jsonl')
            canonical = {'type': 'response_item', 'timestamp': '2026-01-01T03:00:00Z', 'payload': {
                'type': 'message', 'role': 'assistant', 'content': [{'type': 'text', 'text': '페이지 경계 답변'}]}}
            event = {'type': 'event_msg', 'timestamp': '2026-01-01T03:00:00.005Z',
                     'payload': {'type': 'agent_message', 'message': '페이지 경계 답변'}}
            tool = {'type': 'response_item', 'payload': {'type': 'function_call_output', 'output': 'ok'}}
            boundary_path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in [canonical, event, *([tool] * 119)]), encoding='utf-8')
            main(config)
    except KeyboardInterrupt:
        pass
