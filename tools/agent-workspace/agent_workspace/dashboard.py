"""Read-only, bounded projections of local session logs and the agent-chat room."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

HOME = Path.home()
CODEX = HOME / '.codex/sessions'
CLAUDE = HOME / '.claude/projects'
ROOM = HOME / '.agents/chat.jsonl'
CHAT = Path(__file__).with_name('agent_chat.py')
OPERATOR = 'codex:board-operator'  # CLI accepts only user or codex:/claude: identifiers.
UUID = r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'
SESSION = re.compile(rf'(codex|claude):({UUID})\Z')
KST = timezone(timedelta(hours=9), 'KST')
_cache = {}
_lock = threading.RLock()

# Same credential/account families as agent-chat.safe_text; display replaces values.
_patterns = [
    r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)',
    r'\b(?:sk-(?:ant-)?|gh[pousr]_|github_pat_|xox[baprs]-|AIza|AKIA|ASIA)[A-Za-z0-9_\-]{10,}',
    # Check token separators once before trying embedded JWT header prefixes.
    r'(?<![A-Za-z0-9_-])(?=[A-Za-z0-9_-]+\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})[A-Za-z0-9_-]*?\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}',
    r'(?i)\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/-]{10,}',
    # Restart only at identifier boundaries; the lookahead avoids nested scans.
    r'''(?i)(?<![\w-])(?=[\w-]*(?:key|token|secret|password|authorization))[\w-]+["']?\s*[=:]\s*["']?[^\s,"'}]{6,}''',
    r'\b\d{10,}\b|(?<![\w])\d{2,6}(?:[- ]\d{2,6}){2,5}(?![\w])',
]
_redact = [re.compile(p) for p in _patterns]


def mask(value):
    text = str(value)
    # Keep known public IDs and hashes intact, without exempting credentials in paths.
    saved = []
    def protect(m):
        saved.append(m.group())
        return '\ue000' + chr(0xE100 + len(saved) - 1) + '\ue001'
    for rx in _redact[:5]:
        text = rx.sub('[가림]', text)
    text = re.sub(rf'(?<!\w){UUID}(?!\w)|(?<!\w)[0-9a-fA-F]{{40}}(?:[0-9a-fA-F]{{24}})?(?!\w)', protect, text)
    def date_value(m):
        try:
            datetime.strptime(m.group(), '%Y-%m-%d')
            return protect(m)
        except ValueError:
            return m.group()
    text = re.sub(r'(?<!\w)\d{4}-\d{2}-\d{2}(?!\w)', date_value, text)
    text = _redact[5].sub('[가림]', text)
    def opaque(m):
        s = m.group()
        return '[가림]' if all(re.search(p, s) for p in ('[a-z]', '[A-Z]', '[0-9]')) else s
    text = re.sub(r'(?<![\w/])[A-Za-z0-9_+=/\-]{32,}(?![\w/])', opaque, text)
    def restore(m):
        index = ord(m[1]) - 0xE100
        return saved[index] if 0 <= index < len(saved) else m.group()
    text = re.sub('\ue000(.)\ue001', restore, text)
    return ''.join(c for c in text if ord(c) >= 32 or c in '\n\t')


def kst(value):
    try:
        d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(KST).strftime('%Y-%m-%d %H:%M:%S %Z')
    except (ValueError, TypeError):
        return '시각 미상'


def read_events(path, before=None, budget=768_000, limit=None):
    """Read a byte page, excluding partial first/last records. Never repairs sources."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
            raise ValueError('일반 기록 파일만 읽을 수 있습니다.')
        fcntl.flock(f, fcntl.LOCK_SH)
        size = os.fstat(f.fileno()).st_size
        end = size if before is None else min(max(0, before), size)
        start = page_start = max(0, end - budget)
        f.seek(start)
        if start:
            f.seek(start - 1)
            if f.read(1) != b'\n':
                # Align to an entire line without allocating an unbounded record.
                skipped = f.readline(budget)
                start = min(f.tell(), end)
                if not skipped.endswith(b'\n') or start >= end:
                    # A giant record can span the entire page. Still move backward.
                    return [], page_start, size
        raw = f.read(max(0, end - start))
    lines = raw.splitlines(keepends=True)
    if limit and len(lines) > limit:
        start += sum(map(len, lines[:-limit]))
        lines = lines[-limit:]
    events = []
    for line in lines:
        if not line.endswith(b'\n'):
            continue
        try:
            e = json.loads(line)
            if isinstance(e, dict):
                events.append(e)
        except (ValueError, UnicodeDecodeError):
            pass
    return events, start, size


def paths():
    found = {}
    for kind, root, pattern in [('codex', CODEX, '*/*/*/rollout-*.jsonl'), ('claude', CLAUDE, '**/*.jsonl')]:
        for p in root.glob(pattern):
            # Claude subagent records are not independently addressable sessions.
            if kind == 'claude' and not re.fullmatch(UUID, p.stem):
                continue
            if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
                continue
            ids = re.findall(UUID, p.stem)
            if ids:
                who = kind + ':' + ids[0]
                try:
                    if who not in found or p.stat().st_mtime > found[who].stat().st_mtime:
                        found[who] = p
                except OSError:
                    pass
    return found


def process_sessions():
    """Match real client executables and their log FDs/explicit session arguments."""
    result = {}
    for proc in Path('/proc').iterdir() if Path('/proc').is_dir() else []:
        if not proc.name.isdigit():
            continue
        try:
            exe = Path(os.readlink(proc / 'exe').removesuffix(' (deleted)'))
            comm = (proc / 'comm').read_text().strip()
            kind = 'codex' if exe.name == 'codex' else 'claude' if (
                exe.name == 'claude' or comm == 'claude' or 'claude' in str(exe) and comm.startswith('2.')) else None
            if not kind:
                continue
            args = (proc / 'cmdline').read_bytes().decode(errors='replace').split('\0')
            if '--' in args:
                args = args[:args.index('--')]
            fork = kind == 'claude' and '--fork-session' in args
            resume_flags = ('--resume', '-r') if kind == 'claude' else ('--resume', 'resume')
            fork_sources = set()
            ids = set()
            for i, arg in enumerate(args):
                if re.fullmatch(UUID, arg) and i and args[i - 1] in (*resume_flags, '--session-id'):
                    (fork_sources if fork and args[i - 1] in resume_flags else ids).add(arg)
                m = re.fullmatch(rf'--(resume|session-id)=({UUID})', arg)
                if m:
                    (fork_sources if fork and m[1] == 'resume' else ids).add(m[2])
            for fd in (proc / 'fd').iterdir():
                try:
                    target = os.readlink(fd)
                    root = str((CODEX if kind == 'codex' else CLAUDE).resolve(strict=False)).rstrip('/') + '/'
                    if target.startswith(root) and target.endswith('.jsonl'):
                        ids.update(re.findall(UUID, Path(target).stem)[:1])
                except OSError:
                    pass
            for sid in ids - fork_sources:
                result.setdefault(kind + ':' + sid, []).append(int(proc.name))
        except OSError:
            continue
    return result


def metadata(path, kind):
    st = path.stat()
    key = (str(path), st.st_mtime_ns, st.st_size)
    with _lock:
        if key in _cache:
            return dict(_cache[key])
    tail, _, _ = read_events(path)
    head, _, _ = read_events(path, before=min(st.st_size, 512_000))
    model, last, preview = '미상', '', ''
    for ev in head + tail:
        pl = ev.get('payload') or ev.get('message') or {}
        if not isinstance(pl, dict):
            continue
        if pl.get('model'):
            model = str(pl['model'])
        if ev.get('timestamp'):
            last = max(last, str(ev['timestamp']))
    messages = project_messages(tail, kind)
    for m in messages:
        if m['role'] == 'assistant':
            preview = m['text'].replace('\n', ' ')[:140]
    data = {'model': mask(model), 'last_activity': last or datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
            'preview': preview, 'mtime': st.st_mtime}
    with _lock:
        if len(_cache) > 1024:
            _cache.clear()
        _cache[key] = data
    return dict(data)


def owner_id(card):
    ids = []
    for line in card['lines']:
        if line.startswith('담당'):
            owner = re.split(r'\s*(?:/|·)?\s*검토\s*:', line)[0]
            ids.extend(re.findall(rf'(?:codex|claude):{UUID}', owner))
    return ids[-1] if ids else None


def owner_status(card, ps='', inventory=None):
    who = owner_id(card)
    if not who:
        return None
    row = next((r for r in (inventory if inventory is not None else sessions({'진행': [card]})) if r['id'] == who), None)
    if not row:
        return {'state': '기록 없음', 'age': None, 'msg': ''}
    return {'state': '실행 중' if row['running'] else '대기',
            'age': max(0, int((time.time() - row['mtime']) / 60)), 'msg': row['preview']}


def sessions(cols):
    live = process_sessions()
    owned = {}
    for col, cards in cols.items():
        for c in cards:
            who = owner_id(c)
            if who:
                owned.setdefault(who, []).append({'id': c['id'], 'title': mask(c['title']), 'column': col})
    rows = []
    for who, p in paths().items():
        try:
            if who not in live and time.time() - p.stat().st_mtime > 86400 and not any(
                    c['column'] in ('진행', '검토 대기') for c in owned.get(who, [])):
                continue
            data = metadata(p, who.split(':')[0])
            rows.append({'id': who, 'client': who.split(':')[0], **data,
                         'last_activity_kst': kst(data['last_activity']), 'running': who in live,
                         'pids': live.get(who, []), 'cards': owned.get(who, []),
                         'basis': '클라이언트 프로세스 확인' if who in live else '실행 프로세스 미확인'})
        except (OSError, ValueError):
            continue
    return sorted(rows, key=lambda r: (r['running'], any(c['column'] in ('진행', '검토 대기') for c in r['cards']), r['last_activity']), reverse=True)


def content_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(c.get('text', '') for c in content if isinstance(c, dict) and c.get('type') in ('text', 'input_text', 'output_text') and isinstance(c.get('text'), str))
    return ''


def codex_message(event):
    payload = event.get('payload') or {}
    if not isinstance(payload, dict) or payload.get('channel') == 'analysis' or payload.get('phase') == 'analysis':
        return None
    if event.get('type') == 'response_item' and payload.get('type') == 'message' and payload.get('role') in ('user', 'assistant'):
        return ('response', payload['role'], content_text(payload.get('content')))
    if event.get('type') == 'event_msg' and payload.get('type') in ('user_message', 'agent_message'):
        return ('event', 'user' if payload['type'] == 'user_message' else 'assistant', str(payload.get('message', '')))
    return None


def read_next_event(path, offset, budget=768_000):
    """One bounded lookahead record, used only to pair adjacent log envelopes."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
            raise ValueError('일반 기록 파일만 읽을 수 있습니다.')
        fcntl.flock(f, fcntl.LOCK_SH)
        f.seek(offset)
        line = f.readline(budget)
    if not line.endswith(b'\n'):
        return []
    try:
        value = json.loads(line)
        return [value] if isinstance(value, dict) else []
    except (ValueError, UnicodeDecodeError):
        return []


def project_messages(events, kind, after=(), before=(), anchored=True):
    rows = []
    extended = [*before, *events, *after]
    suppressed = set()
    if kind == 'codex':
        index = 0
        while index < len(extended):
            message = codex_message(extended[index])
            following = codex_message(extended[index + 1]) if index + 1 < len(extended) else None
            paired = message and following and message[0] != following[0] and message[1:] == following[1:]
            if not anchored:
                # A bounded prefix may start inside an arbitrarily long chain.
                # Preserve uncertain repetitions until a definite pair boundary.
                if not paired:
                    anchored = True
                index += 1
            elif paired:
                suppressed.add(index)
                index += 2  # Each envelope belongs to at most one emission.
            else:
                index += 1
    for index, e in enumerate(events):
        pl = e.get('payload') or {} if kind == 'codex' else e.get('message') or {}
        if not isinstance(pl, dict):
            continue
        ts, role, text = e.get('timestamp', ''), '', ''
        if kind == 'codex':
            message = codex_message(e)
            if message:
                if index + len(before) in suppressed:
                    continue
                _, role, text = message
            elif e.get('type') == 'response_item':
                if pl.get('type') in ('function_call', 'custom_tool_call'):
                    role, text = 'tool', '호출: ' + str(pl.get('name', '도구'))
                elif pl.get('type') in ('function_call_output', 'custom_tool_call_output'):
                    role = 'tool'
                    output = pl.get('output', '')
                    text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
        elif e.get('type') in ('user', 'assistant'):
            role = e['type']
            if isinstance(pl.get('content'), list):
                parts = []
                def flush_text():
                    value = '\n'.join(parts); parts.clear()
                    if value.strip():
                        redacted = mask(value)
                        rows.append({'role': role, 'ts': kst(ts), 'text': redacted[:2400] + ('\n… (요약)' if len(redacted) > 2400 else '')})
                for c in pl['content']:
                    if not isinstance(c, dict):
                        continue
                    if c.get('type') in ('text', 'input_text', 'output_text') and isinstance(c.get('text'), str):
                        parts.append(c['text'])
                    elif c.get('type') == 'tool_result':
                        flush_text()
                        rows.append({'role': 'tool', 'ts': kst(ts), 'text': mask(content_text(c.get('content', '')))[:4000]})
                    elif c.get('type') == 'tool_use':
                        flush_text()
                        rows.append({'role': 'tool', 'ts': kst(ts), 'text': mask('호출: ' + str(c.get('name', '도구')))[:4000]})
                flush_text()
                continue
            text = content_text(pl.get('content'))
        if role and text.strip():
            redacted = mask(text)
            limit = 4000 if role == 'tool' else 2400
            rows.append({'role': role, 'ts': kst(ts), 'text': redacted[:limit] + ('\n… (요약)' if len(redacted) > limit else '')})
    return rows


def conversation(who, before=None):
    if not SESSION.fullmatch(who):
        raise ValueError('올바른 세션 ID가 필요합니다.')
    p = paths().get(who)
    if p is None:
        raise LookupError('세션 기록을 찾을 수 없습니다.')
    events, start, size = read_events(p, before, limit=120)
    kind = who.split(':')[0]
    after = read_next_event(p, before) if kind == 'codex' and before is not None and before < size else []
    prefix, prefix_start = [], 0
    if kind == 'codex' and start:
        prefix, prefix_start, _ = read_events(p, start)
    return {'id': who, 'messages': project_messages(events, kind, after, prefix, prefix_start == 0), 'before': start or None,
            'note': '사용자·어시스턴트 대화 우선 · 도구는 한 줄로 묶습니다. 한 번에 최대 120개 기록. 긴 메시지는 요약되며 큰 단일 기록·미완성 행은 건너뛸 수 있습니다.'}


def chat(before=None):
    try:
        events, start, size = read_events(ROOM, before, budget=256_000, limit=120)
    except FileNotFoundError:
        return {'messages': [], 'before': None, 'end': 0}
    return {'messages': [{k: mask(e.get(k, '')) for k in ('id', 'from', 'to', 'kind', 'text', 'reply_target')} | {'ts': kst(e.get('ts'))}
                         for e in events if 'text' in e], 'before': start or None,
            'end': size if before is None else min(before, size)}


def send_message(body):
    target, text = body.get('to', 'all'), body.get('text')
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 16000:
        raise ValueError('메시지는 1~16000자여야 합니다.')
    if target != 'all' and (not isinstance(target, str) or not SESSION.fullmatch(target)):
        raise ValueError('수신자는 전체 또는 세션 ID여야 합니다.')
    from .agent_chat import safe_text
    safe_text(text)
    if ROOM.name != 'chat.jsonl':
        raise ValueError('이 파일명은 조회 전용입니다. 전송하려면 chat_log를 방 디렉터리의 chat.jsonl로 설정하세요.')
    # No shell, no JSONL writes, no caller-selected sender or storage root.
    env = {k: v for k, v in os.environ.items() if k not in ('AGENT_CHAT_HOME',)}
    bundled = {Path(__file__).with_name(name).resolve() for name in ('agent_chat.py', 'demo_chat.py')}
    command = [sys.executable, str(CHAT)] if CHAT.resolve() in bundled else [str(CHAT)]
    try:
        result = subprocess.run([*command, '--home', str(ROOM.parent), 'send', '--from', OPERATOR,
                                 '--to', target, '--reply-target', 'all', '--', text], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, errors='replace', timeout=45, env=env)
    except subprocess.TimeoutExpired:
        return {'ok': False, 'uncertain': True, 'error': '전송 확인 시간이 지났습니다. 중복 전송 전에 채팅 내역을 확인하세요.'}
    try:
        receipt = json.loads(result.stdout)
        if not isinstance(receipt, dict) or not isinstance(receipt.get('stored'), bool):
            raise ValueError()
    except ValueError:
        return {'ok': False, 'uncertain': True, 'error': '전송 영수증을 확인하지 못했습니다. 중복 전송 전에 채팅 내역을 확인하세요.'}
    # A stored message can have failed immediate delivery; never call it unstored.
    def clean(value):
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                # Credential labels take precedence over public-looking hashes.
                sensitive = re.search(r'(?i)key|token|secret|password|authorization', key)
                result[key] = '[가림]' if sensitive and isinstance(item, str) and len(item) >= 6 else clean(item)
            return result
        if isinstance(value, list):
            return [clean(v) for v in value]
        return mask(value) if isinstance(value, str) else value
    return {'ok': result.returncode == 0 and receipt['stored'], 'stored': receipt['stored'], 'receipt': clean(receipt)}
