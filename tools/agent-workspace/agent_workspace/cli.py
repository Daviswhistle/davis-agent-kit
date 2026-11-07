"""One entrypoint for serving, isolated demos, board edits and static rendering."""
import argparse
from pathlib import Path
import sys
import tempfile
from .config import Config, configure


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'chat':
        from .agent_chat import main as chat_main
        try:
            return chat_main(sys.argv[2:])
        except (ValueError, OSError) as exc:
            print('agent-workspace chat: ' + type(exc).__name__, file=sys.stderr)
            return 2
    parser = argparse.ArgumentParser(description=__doc__, epilog='Independent room CLI: workspace.py chat --help')
    parser.add_argument('--config', type=Path, help='JSON configuration file')
    parser.add_argument('--port', type=int)
    parser.add_argument('--idle-seconds', type=float, help='socket activation idle timeout (default 600; 0 disables)')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--demo', action='store_true', help='temporary synthetic data; never reads live sessions')
    parser.add_argument('--render', type=Path, metavar='OUTPUT', help='render a static board snapshot without a CSRF token')
    parser.add_argument('command', nargs='?', choices=['serve', 'board'], default='serve')
    args, rest = parser.parse_known_args()
    if args.command != 'board' and rest:
        parser.error('unknown arguments: ' + ' '.join(rest))
    with tempfile.TemporaryDirectory(prefix='agent-workspace-demo-') if args.demo else __import__('contextlib').nullcontext() as demo_root:
        try:
            config = Config.load(args.config, dict(port=args.port, data_dir=args.data_dir, idle_seconds=args.idle_seconds))
            if demo_root:
                from .demo import create
                from dataclasses import replace
                config = replace(create(Path(demo_root), port=config.port, timezone=config.timezone), idle_seconds=config.idle_seconds)
            configure(config)
            if args.command == 'board':
                from .board_cli import main as board_main
                board_main(rest)
            elif args.render:
                from . import render, board_store
                render.CONFIG = config
                args.render.parent.mkdir(parents=True, exist_ok=True)
                board_store.atomic_write(args.render, render.render())
            else:
                from .serve import main as serve
                serve(config)
        except KeyboardInterrupt:
            return 0
        except (ValueError, LookupError, OSError) as exc:
            # Avoid printing configuration paths or unexpected raw source content.
            print('agent-workspace: ' + type(exc).__name__ + '. Check configuration, permissions and port availability.', file=sys.stderr)
            return 2
    return 0
