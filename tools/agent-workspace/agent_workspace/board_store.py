"""Shared local board mutation contract: one lock plus optimistic source validation."""
import contextlib
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile

BOARD = Path.home() / '.agents/BOARD.md'
LOCK = Path.home() / '.agents/board/.lock'
COLUMNS = ('진행', '검토 대기', '할 일', '완료', '기각')


def approval_key(title):
    return hashlib.sha256(str(title).encode('utf-8')).hexdigest()


class Conflict(LookupError):
    pass


def snapshot(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as f:
        st = os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode):
            raise ValueError('보드는 일반 파일이어야 합니다.')
        raw = f.read()
    version = (st.st_dev, st.st_ino, st.st_mtime_ns, st.st_ctime_ns, st.st_size, hashlib.sha256(raw).digest())
    return raw.decode('utf-8'), version


@contextlib.contextmanager
def locked(path=LOCK):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def atomic_write(path, text, expected=None):
    """Reject observed outside edits. All cooperating writers must also hold LOCK.

    POSIX has no content CAS for a noncooperating writer: a direct edit between
    the final comparison and rename is still possible. Never claim full exclusion.
    """
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix='.board-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            if path.exists():
                os.fchmod(f.fileno(), stat.S_IMODE(path.stat().st_mode))
            f.write(text); f.flush(); os.fsync(f.fileno())
        if expected is not None and snapshot(path)[1] != expected:
            raise Conflict('저장 직전 보드 변경을 감지했습니다. 최신 보드를 확인하고 다시 시도하세요.')
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def move(text, card_id, column, extra=()):
    if column not in COLUMNS or not re.fullmatch(r'B-\d+', card_id):
        raise ValueError('올바른 카드 ID와 열이 필요합니다.')
    lines = text.split('\n')
    hits = [i for i, line in enumerate(lines) if re.match(rf'^### {re.escape(card_id)}\s', line)]
    if len(hits) != 1:
        raise Conflict('카드가 없거나 ID가 중복되었습니다.')
    start = hits[0]
    prior = [line[3:].strip() for line in lines[:start] if line.startswith('## ')]
    old = prior[-1] if prior else ''
    if old == column:
        raise Conflict(f'{card_id}는 이미 {column} 열에 있습니다.')
    end = start + 1
    while end < len(lines) and not lines[end].startswith(('### ', '## ')):
        end += 1
    block = lines[start:end]
    while block and not block[-1].strip():
        block.pop()
    block += list(extra)
    rest = lines[:start] + lines[end:]
    heads = [i for i, line in enumerate(rest) if line.strip() == '## ' + column]
    if len(heads) != 1:
        raise Conflict('대상 열이 없거나 중복되었습니다.')
    rest[heads[0] + 1:heads[0] + 1] = ['', *block, '']
    return '\n'.join(rest), old
