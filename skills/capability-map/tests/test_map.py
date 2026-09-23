import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('capability_mapper', Path(__file__).resolve().parents[1] / 'scripts/map.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

class MapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.repo / 'app.py').write_text('def accept(value):\n    return value >= 3\n', 'utf-8')
        (self.repo / 'README.md').write_text('Never use this narrative as behavior evidence.', 'utf-8')
        (self.repo / '.env').write_text('TOKEN=private', 'utf-8')
        (self.repo / 'config.json').write_text('{"enabled": true}', 'utf-8')
        (self.repo / 'other.go').write_text('package other\n', 'utf-8')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.work = m.prepare(self.repo, self.root / 'work')
        self.manifest = m.read_json(self.work / 'private/manifest.json')
        self.model = {'version': 1, 'snapshot': self.manifest['snapshot'], 'title': 'Gate system',
          'summary': '입력을 검사하고 허용 여부를 반환한다.',
          'nodes': [{'id': 'gate', 'label': '입력 검사', 'parent': '', 'purpose': '입력 허용 여부를 판단한다.',
            'inputs': ['검사할 값'], 'outputs': ['허용 여부'], 'state': [], 'unknowns': ['호출자의 입력 제약 미검토']}],
          'relations': [], 'rules': [{'id': 'minimum', 'node': 'gate', 'title': '최소 입력',
            'text': '입력이 3 이상이면 허용한다.', 'evidence': ['E1']}],
          'evidence': [{'id': 'E1', 'file': 'app.py', 'start': 1, 'end': 2, 'kind': 'source_interpretation'}],
          'reviewed_files': ['app.py'], 'unknowns': ['외부 실행 환경 미조회']}

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], capture_output=True, check=True).stdout

    def save(self):
        m.write_json(self.work / 'private/model.json', self.model)

    def test_documents_and_secrets_excluded(self):
        files = {x['path']: x for x in self.manifest['files']}
        self.assertEqual(files['README.md']['status'], 'excluded')
        self.assertEqual(files['.env']['status'], 'excluded')
        self.assertEqual(files['config.json']['reason'], 'config_candidate')
        self.assertFalse((self.work / 'private/input/README.md').exists())

    def test_head_bytes_not_untracked_inputs(self):
        (self.repo / 'untracked.py').write_text('secret=1')
        work = m.prepare(self.repo, self.root / 'another')
        self.assertFalse((work / 'private/input/untracked.py').exists())
        self.assertEqual((work / 'private/input/app.py').read_bytes(), self.git('show', 'HEAD:app.py'))

    def test_dirty_tracked_fails(self):
        (self.repo / 'app.py').write_text('changed')
        with self.assertRaises(m.MapError):
            m.prepare(self.repo, self.root / 'dirty')
        self.assertFalse((self.root / 'dirty').exists())

    def test_output_inside_repo_fails(self):
        with self.assertRaises(m.MapError):
            m.prepare(self.repo, self.repo / 'generated')

    def test_existing_output_not_overwritten(self):
        with self.assertRaises(FileExistsError):
            m.prepare(self.repo, self.work)

    def test_symlink_not_copied(self):
        (self.repo / 'linked.py').symlink_to(self.root / 'outside.py')
        self.git('add', 'linked.py'); self.git('commit', '-qm', 'link')
        w = m.prepare(self.repo, self.root / 'links')
        files = m.read_json(w / 'private/manifest.json')['files']
        self.assertEqual(next(x for x in files if x['path'] == 'linked.py')['reason'], 'symlink_or_submodule')

    def test_sensitive_content_rejected(self):
        (self.repo / 'token.py').write_text('v="ghp_' + 'a'*30 + '"')
        self.git('add', '.'); self.git('commit', '-qm', 'token')
        w = m.prepare(self.repo, self.root / 'sensitive')
        self.assertFalse((w / 'private/input/token.py').exists())

    def test_valid_model(self):
        manifest, files = m.validate(self.work, self.model)
        self.assertEqual(len(files), 3)
        self.assertEqual(manifest['snapshot'], self.model['snapshot'])

    def test_no_demo_fallback(self):
        with self.assertRaises(m.MapError):
            m.build(self.work)
        self.assertFalse((self.work / 'public').exists())

    def test_snapshot_mismatch(self):
        self.model['snapshot'] = 'wrong'
        with self.assertRaises(m.MapError): m.validate(self.work, self.model)

    def test_source_mutation_rejected(self):
        path = self.work / 'private/input/app.py'
        path.chmod(0o644); path.write_text('changed')
        with self.assertRaises(m.MapError): m.validate(self.work, self.model)

    def test_manifest_tampering_rejected(self):
        self.manifest['files'][0]['reason'] = 'tampered'
        m.write_json(self.work / 'private/manifest.json', self.manifest)
        with self.assertRaises(m.MapError): m.validate(self.work, self.model)

    def test_evidence_range_rejected(self):
        self.model['evidence'][0]['end'] = 999
        with self.assertRaises(m.MapError): m.validate(self.work, self.model)

    def test_readme_cannot_be_evidence(self):
        self.model['evidence'][0]['file'] = 'README.md'
        self.model['reviewed_files'].append('README.md')
        with self.assertRaises(m.MapError): m.validate(self.work, self.model)

    def test_unknown_rule_evidence_rejected(self):
        self.model['rules'][0]['evidence'] = ['missing']
        with self.assertRaises(m.MapError): m.validate(self.work, self.model)

    def test_duplicate_id_rejected(self):
        self.model['rules'][0]['id'] = 'gate'
        with self.assertRaises(m.MapError): m.validate(self.work, self.model)

    def test_cycle_rejected(self):
        self.model['nodes'][0]['parent'] = 'gate'
        with self.assertRaises(m.MapError): m.validate(self.work, self.model)

    def test_dangling_relation_rejected(self):
        self.model['relations'] = [{'id': 'edge1', 'from': 'gate', 'to': 'absent', 'kind': 'data',
                                   'label': 'link', 'condition': '', 'timing': '', 'evidence': ['E1']}]
        with self.assertRaises(m.MapError): m.validate(self.work, self.model)

    def test_schema_rejects_boolean_integer(self):
        self.model['evidence'][0]['start'] = True
        with self.assertRaises(m.MapError): m.validate(self.work, self.model)

    def test_schema_rejects_extra_fields(self):
        self.model['source_code'] = 'must not pass'
        with self.assertRaises(m.MapError): m.validate(self.work, self.model)

    def test_duplicate_json_keys(self):
        path = self.root / 'bad.json'; path.write_text('{"a": 1, "a": 2}')
        with self.assertRaises(m.MapError): m.read_json(path)

    def test_nonfinite_json(self):
        path = self.root / 'bad.json'; path.write_text('{"a": NaN}')
        with self.assertRaises(m.MapError): m.read_json(path)

    def test_source_paths_not_in_public(self):
        self.save(); output = m.build(self.work)
        for path in output.iterdir():
            self.assertNotIn('app.py', path.read_text('utf-8'))
        packet = m.read_json(output / 'astra-packet.json')
        self.assertEqual(packet['coverage']['unreviewed_files'], 2)
        self.assertNotIn('file', packet['evidence'][0])
        self.assertEqual(packet['evidence'][0]['status'], 'not_runtime_verified')

    def test_public_path_leak_rejected(self):
        self.model['summary'] = 'Read app.py'
        self.save()
        with self.assertRaises(m.MapError): m.build(self.work)

    def test_script_injection_escaped(self):
        self.model['title'] = '</script><img src=x onerror=alert(1)>'
        self.save(); output = m.build(self.work)
        content = (output / 'map.html').read_text('utf-8')
        self.assertNotIn('</script><img', content)
        self.assertIn('\\u003c/script', content)

    def test_path_traversal_and_symlink(self):
        with self.assertRaises(m.MapError): m.safe_path(self.root, '../escape')
        with self.assertRaises(m.MapError): m.safe_path(self.root, '/absolute')
        (self.root / 'escape').symlink_to(self.repo)
        with self.assertRaises(m.MapError): m.safe_path(self.root, 'escape/app.py')

    def test_public_symlink_not_overwritten(self):
        self.save(); (self.work / 'public').symlink_to(self.repo)
        with self.assertRaises(m.MapError): m.build(self.work)

    def test_source_change_needs_new_model(self):
        (self.repo / 'app.py').write_text('def accept(value):\n    return value > 3\n')
        self.git('add', '.'); self.git('commit', '-qm', 'change meaning')
        newer = m.prepare(self.repo, self.root / 'new')
        with self.assertRaises(m.MapError): m.validate(newer, self.model)

    def test_schema_cli(self):
        result = subprocess.run([sys.executable, str(m.SKILL / 'scripts/map.py'), 'schema'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), m.schema())

    def test_missing_codex_no_fallback(self):
        with patch.object(m.shutil, 'which', return_value=None):
            with self.assertRaises(m.MapError): m.run_mapper(self.work)
        self.assertFalse((self.work / 'public').exists())

    def test_runner_captures_raw_output_and_renders(self):
        calls = []
        def fake_run(command, **kwargs):
            calls.append((command, kwargs))
            if command[-1] == '--help':
                return subprocess.CompletedProcess(command, 0, stdout='--output-schema --output-last-message --sandbox --skip-git-repo-check')
            candidate = Path(command[command.index('--output-last-message')+1])
            m.write_json(candidate, self.model)
            self.assertIsNotNone(kwargs['stdout'])
            self.assertIs(kwargs['stdout'], kwargs['stderr'])
            return subprocess.CompletedProcess(command, 0)
        with patch.object(m.shutil, 'which', return_value='/fake/codex'), patch.object(m.subprocess, 'run', side_effect=fake_run):
            output = m.run_mapper(self.work)
        self.assertTrue((output / 'map.html').is_file())
        command = calls[-1][0]
        self.assertEqual(command[command.index('--sandbox')+1], 'read-only')
        self.assertIn('gpt-6-luna', command)
        self.assertEqual(m.read_json(self.work / 'private/launch.json')['actual_settings'], 'unverified')

    def test_runner_failure_not_success(self):
        help_text = '--output-schema --output-last-message --sandbox --skip-git-repo-check'
        with patch.object(m.shutil, 'which', return_value='/fake/codex'), patch.object(m.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0, stdout=help_text), subprocess.CompletedProcess([], 1)]):
            with self.assertRaises(m.MapError): m.run_mapper(self.work)
        self.assertFalse((self.work / 'public').exists())

if __name__ == '__main__':
    unittest.main()
