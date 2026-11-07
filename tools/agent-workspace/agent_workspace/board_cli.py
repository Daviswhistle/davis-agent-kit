#!/usr/bin/env python3
"""Safely move/add a local card under the dashboard's shared lock."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

from . import board_store as store, dashboard


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, default=store.BOARD, help='isolated board path; configured board path')
    commands = parser.add_subparsers(dest='action', required=True)
    move = commands.add_parser('move')
    move.add_argument('id'); move.add_argument('column', choices=store.COLUMNS)
    move.add_argument('--summary', action='append', default=[], help='repeat 3-5 times for review/done/rejected')
    add = commands.add_parser('add')
    add.add_argument('--project', required=True); add.add_argument('--title', required=True)
    add.add_argument('--owner', required=True); add.add_argument('--column', choices=store.COLUMNS, default='할 일')
    args = parser.parse_args(argv)
    lock = store.LOCK if args.file.resolve() == store.BOARD.resolve() else args.file.with_name('.board.lock')
    lock.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with store.locked(lock):
        text, version = store.snapshot(args.file)
        if args.action == 'move':
            if args.column in ('검토 대기', '완료', '기각') and not 3 <= len(args.summary) <= 5:
                raise ValueError('결과 열 이동에는 --summary를 3~5개 지정하세요.')
            if any('\n' in s or '\r' in s for s in args.summary):
                raise ValueError('각 요약은 한 줄이어야 합니다.')
            stamp = datetime.now(dashboard.KST).strftime('%Y-%m-%d %H:%M %Z')
            extra = [f'요약 ({stamp}):', *('- ' + s for s in args.summary)] if args.summary else []
            updated, old = store.move(text, args.id, args.column, extra)
            result = f'{args.id}: {old} → {args.column}'
        else:
            values = (args.project, args.title, args.owner)
            if any(not s.strip() or '\n' in s or '\r' in s for s in values) or any(c in args.project for c in '[]'):
                raise ValueError('카드 필드는 비어 있지 않은 한 줄이어야 합니다.')
            if not re.fullmatch(r'(?:codex|claude):[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', args.owner):
                raise ValueError('담당은 codex:<id> 또는 claude:<id> 형식입니다.')
            n = max((int(s) for s in re.findall(r'^### B-(\d+)\s', text, re.M)), default=0) + 1
            head = '## ' + args.column
            lines = text.split('\n')
            hits = [i for i, l in enumerate(lines) if l.strip() == head]
            if len(hits) != 1:
                raise ValueError('대상 열이 없거나 중복되었습니다.')
            lines[hits[0] + 1:hits[0] + 1] = ['', f'### B-{n} [{args.project}] {args.title}', '담당: ' + args.owner, '']
            updated, result = '\n'.join(lines), f'B-{n}: {args.column}'
        store.atomic_write(args.file, updated, version)
    print(result)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, LookupError, OSError) as exc:
        print('board: ' + str(exc), file=sys.stderr)
        sys.exit(2)
