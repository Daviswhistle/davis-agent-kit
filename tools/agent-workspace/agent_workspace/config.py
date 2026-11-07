"""Explicit paths; importing this module never creates or reads user data."""
from dataclasses import dataclass, fields
import json
import os
from pathlib import Path


@dataclass(frozen=True)
class Config:
    data_dir: Path
    board: Path
    codex_root: Path
    claude_root: Path
    chat_log: Path
    chat_cli: Path
    port: int = 8765
    timezone: str = 'Asia/Seoul'
    idle_seconds: float = 600

    @property
    def lock(self):
        return self.data_dir / '.lock'

    @classmethod
    def defaults(cls):
        home = Path.home()
        return cls(home / '.agents/board', home / '.agents/BOARD.md', home / '.codex/sessions',
                   home / '.claude/projects', home / '.agents/chat.jsonl', Path(__file__).with_name('agent_chat.py'))

    @classmethod
    def load(cls, filename=None, overrides=None):
        defaults = cls.defaults()
        values = {f.name: getattr(defaults, f.name) for f in fields(cls)}
        allowed = {f.name for f in fields(cls)}
        if filename:
            supplied = json.loads(Path(filename).read_text(encoding='utf-8'))
            if not isinstance(supplied, dict) or set(supplied) - allowed:
                raise ValueError('설정 필드가 잘못되었습니다.')
            values.update(supplied)
        for key in allowed:
            if 'AGENT_WORKSPACE_' + key.upper() in os.environ:
                values[key] = os.environ['AGENT_WORKSPACE_' + key.upper()]
        values.update({k: v for k, v in (overrides or {}).items() if v is not None})
        for key in allowed - {'port', 'timezone', 'idle_seconds'}:
            values[key] = Path(values[key]).expanduser().absolute()
        values['port'] = int(values.get('port', 8765))
        if not 1 <= values['port'] <= 65535:
            raise ValueError('포트는 1~65535입니다.')
        values['idle_seconds'] = float(values['idle_seconds'])
        import math
        if not math.isfinite(values['idle_seconds']) or values['idle_seconds'] < 0:
            raise ValueError('idle_seconds must be finite and nonnegative')
        from zoneinfo import ZoneInfo
        try:
            ZoneInfo(values.get('timezone', 'Asia/Seoul'))
        except (KeyError, TypeError) as exc:
            raise ValueError('잘못된 시간대입니다.') from exc
        return cls(**values)


def configure(config):
    # One configured workspace per server process. No path is accepted from HTTP.
    from . import board_store, dashboard
    board_store.BOARD, board_store.LOCK = config.board, config.lock
    dashboard.CODEX, dashboard.CLAUDE = config.codex_root, config.claude_root
    dashboard.ROOM, dashboard.CHAT = config.chat_log, config.chat_cli
    from zoneinfo import ZoneInfo
    dashboard.KST = ZoneInfo(config.timezone)
    with dashboard._lock:
        dashboard._cache.clear()
