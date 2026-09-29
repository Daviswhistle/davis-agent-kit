"""Execution-lifetime regressions only; no schema/rendering dependency."""
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

m = load('map')
supervisor = load('mapper_supervisor')

class LifetimeTests(unittest.TestCase):
    def test_supervisor_help_smoke(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / 'mapper_supervisor.py'), '--help'],
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn(b'Usage:', result.stdout)

    def test_unsupported_platform_does_not_launch(self):
        with patch.object(m.sys, 'platform', 'win32'), patch.object(m.subprocess, 'Popen') as popen:
            with self.assertRaisesRegex(m.MapError, 'prepare/build'):
                m.run_mapper_process(['unused'], b'', None, 1)
            popen.assert_not_called()

    def test_invalid_deadlines_do_not_launch(self):
        for timeout in (0, -1, float('nan'), float('inf')):
            with self.subTest(timeout=timeout), patch.object(m.subprocess, 'Popen') as popen:
                with self.assertRaises(m.MapError):
                    m.run_mapper_process(['unused'], b'', None, timeout)
                popen.assert_not_called()

    def test_proc_names_do_not_require_ascii(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            child = proc / '1234'
            child.mkdir()
            (child / 'stat').write_bytes(
                b'1234 (name ) \xff) S ' + str(os.getpid()).encode() + b' 1 2 3\n')
            self.assertEqual(list(supervisor.direct_children(proc)), [1234])

    def test_subreaper_setup_failure_does_not_launch(self):
        with patch.object(supervisor, 'enable_subreaper', side_effect=OSError('unavailable')), \
             patch.object(supervisor.subprocess, 'Popen') as popen:
            with self.assertRaises(OSError):
                supervisor.supervise(['unused'], b'', 1)
            popen.assert_not_called()

    @unittest.skipUnless(sys.platform == 'linux', 'Linux lifetime supervisor')
    def test_detached_double_fork_timeout_has_no_late_writes(self):
        self.check_descendants(timeout=True)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux lifetime supervisor')
    def test_normal_exit_reaps_detached_descendants(self):
        self.check_descendants(timeout=False)

    def check_descendants(self, timeout):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ready, release, marker = (root / name for name in ('ready', 'release', 'marker'))
            child = ("import os,time\nfrom pathlib import Path\n"
                     "if os.fork(): os._exit(0)\n"
                     "os.setsid()\n"
                     f"Path({str(ready)!r}).write_text(str(os.getpid()))\n"
                     f"while not Path({str(release)!r}).exists(): time.sleep(0.01)\n"
                     f"Path({str(marker)!r}).write_text('late')\n"
                     "print('late write',flush=True)\n")
            worker = ("import subprocess,sys,time\nfrom pathlib import Path\n"
                      f"subprocess.Popen([sys.executable,'-c',{child!r}], start_new_session=True)\n"
                      f"while not Path({str(ready)!r}).exists(): time.sleep(0.01)\n"
                      + ("time.sleep(30)\n" if timeout else ""))
            log = root / 'worker.log'
            try:
                with log.open('wb') as output:
                    args = [sys.executable, '-c', worker]
                    if timeout:
                        with self.assertRaises(subprocess.TimeoutExpired):
                            m.run_mapper_process(args, b'', output, 8)
                    else:
                        self.assertEqual(m.run_mapper_process(args, b'', output, 5), 0)
                self.assertTrue(ready.exists(), 'Child must start; a vacuous timeout is not success; ' + log.read_text())
                pid = int(ready.read_text())
                self.assertFalse(Path(f'/proc/{pid}').exists(), 'Descendant must be reaped, not merely signaled')
                before = log.read_bytes()
                release.write_text('only after return')
                time.sleep(0.15)
                self.assertFalse(marker.exists())
                self.assertEqual(log.read_bytes(), before)
            finally:
                if ready.exists():
                    try:
                        os.kill(int(ready.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    @unittest.skipUnless(sys.platform == 'linux', 'Linux lifetime supervisor')
    def test_worker_reserved_status_is_failure_not_timeout(self):
        with tempfile.TemporaryFile() as log:
            self.assertEqual(m.run_mapper_process([sys.executable, '-c', 'raise SystemExit(124)'], b'', log, 5), 1)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux lifetime supervisor')
    def test_help_uses_same_supervision(self):
        with patch.object(m, 'run_mapper_process', side_effect=subprocess.TimeoutExpired(['fake'], 15)) as run:
            with self.assertRaisesRegex(m.MapError, 'preflight timed out'):
                m.mapper_help('fake')
            self.assertEqual(run.call_args.args[0], ['fake', 'exec', '--help'])

if __name__ == '__main__':
    unittest.main()
