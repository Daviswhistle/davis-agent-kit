#!/usr/bin/env python3
"""Isolated demo transport. It cannot deliver to a model or use a live room."""
import argparse
import fcntl
import json
from pathlib import Path
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_workspace.agent_chat import safe_text


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--home', type=Path, required=True)
    p.add_argument('command', choices=['send'])
    p.add_argument('--from', dest='sender', required=True)
    p.add_argument('--to', required=True)
    p.add_argument('--reply-target', choices=['all'])
    p.add_argument('text')
    args = p.parse_args()
    try:
        safe_text(args.text)
    except ValueError:
        print(json.dumps({'stored': False, 'error': '데모가 거부했습니다.'})); return 2
    if not (args.home / '.workspace-demo').is_file():
        print(json.dumps({'stored': False, 'error': '데모가 거부했습니다.'})); return 2
    event = {'id': str(uuid.uuid4()), 'ts': datetime.now(timezone.utc).isoformat(),
             'from': args.sender, 'to': args.to, 'text': args.text}
    if args.reply_target:
        event['reply_target'] = args.reply_target
    with (args.home / 'chat.jsonl').open('a', encoding='utf-8') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(event, ensure_ascii=False) + '\n')
    print(json.dumps({'stored': True, 'demo': True, 'delivery': []})); return 0


if __name__ == '__main__':
    raise SystemExit(main())
