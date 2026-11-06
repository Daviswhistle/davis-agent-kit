#!/usr/bin/env python3
"""Run Agent Workspace from any directory without installing dependencies."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_workspace.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
