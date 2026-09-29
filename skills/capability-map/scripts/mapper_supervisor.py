#!/usr/bin/env python3
"""Linux mapper lifetime supervisor; not a sandbox or hostile-process boundary.

Run only as a fresh process. Become a subreaper BEFORE spawning the worker so
setsid/double-fork descendants are adopted here, not by the calling application.
Timeout (124) and success are reported only after waitpid confirms ECHILD.
Cleanup may outlast the execution deadline (e.g. uninterruptible kernel I/O).
SIGKILL/crash of this supervisor or privilege-changing hostile children are not
covered. Unsupported kernels/platforms fail before worker execution (125).
"""
import ctypes
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

TIMED_OUT = 124
UNAVAILABLE = 125


def enable_subreaper():
    if sys.platform != 'linux':
        raise OSError('Linux subreaper support is required')
    proc = Path('/proc')
    (proc / 'self/stat').read_bytes()  # Fail closed before spawning without procfs.
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.restype = ctypes.c_int
    prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                     ctypes.c_ulong, ctypes.c_ulong]
    if prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'Cannot enable child subreaper')
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    return proc


def direct_children(proc):
    parent = os.getpid()
    for entry in proc.iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            # comm may contain spaces and ')' characters; parse after its last ')'.
            fields = (entry / 'stat').read_bytes().rpartition(b')')[2].split()
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if len(fields) >= 2 and int(fields[1]) == parent:
            yield int(entry.name)


def drain_descendants(proc):
    # This fresh supervisor owns no unrelated children. Do not reap between
    # enumeration and signaling: exited children remain zombies, preventing
    # PID reuse. A racing /proc scan is NEVER completion; only ECHILD is.
    while True:
        for pid in direct_children(proc):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        while True:
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                return
            if pid == 0:
                break
        time.sleep(0.01)


def interrupted(signum, frame):
    raise InterruptedError('Supervisor interrupted')


def supervise(command, data, timeout):
    if not command or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Command and finite positive timeout required')
    children = enable_subreaper()
    process = None
    outcome = 1
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, start_new_session=True)
        process.communicate(input=data, timeout=timeout)
        # Reserve supervisor status codes; worker exit 124 is a failure, not timeout.
        outcome = 0 if process.returncode == 0 else 1
    except subprocess.TimeoutExpired:
        outcome = TIMED_OUT
    except (InterruptedError, KeyboardInterrupt):
        outcome = 1
    finally:
        # Do not let repeated cancellation interrupt descendant cleanup.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait()
            if process.stdin is not None:
                process.stdin.close()
        drain_descendants(children)
    return outcome


def main():
    if sys.argv[1:] == ['--help']:
        print(__doc__)
        print('Usage: mapper_supervisor.py TIMEOUT COMMAND [ARG ...] < INPUT')
        return 0
    try:
        timeout = float(sys.argv[1])
        return supervise(sys.argv[2:], sys.stdin.buffer.read(), timeout)
    except (OSError, ValueError, IndexError) as exc:
        print('Mapper supervisor unavailable/failed: ' + str(exc), file=sys.stderr)
        return UNAVAILABLE


if __name__ == '__main__':
    raise SystemExit(main())
