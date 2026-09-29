"""Public-output policy regressions; independent of snapshot/ID changes."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('map_fixture', Path(__file__).with_name('test_map.py'))
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
m = fixture.m

class PublicBoundaryTests(unittest.TestCase):
    setUp = fixture.MapTests.setUp
    git = fixture.MapTests.git
    save = fixture.MapTests.save

    def test_sentence_final_paths_still_rejected(self):
        for text in ('Read app.py.', 'Read app.py...', 'Read app.py. Next sentence.',
                     'Ignored README.md.', 'Read app.py!', 'Read app.py?'):
            with self.subTest(text=text):
                self.model['summary'] = text
                self.save()
                with self.assertRaises(m.MapError):
                    m.build(self.work)

    def test_nested_and_excluded_basenames_with_punctuation(self):
        (self.repo / 'src').mkdir()
        (self.repo / 'src/helper.py').write_text('VALUE=1\n')
        self.git('add', '.'); self.git('commit', '-qm', 'nested fixture')
        work = m.prepare(self.repo, self.root / 'nested')
        candidate = copy.deepcopy(self.model)
        candidate['snapshot'] = m.read_json(work / 'private/manifest.json')['snapshot']
        for text in ('Read helper.py.', 'Ignored README.md.', 'Read src/helper.py.', 'Read src\\helper.py.'):
            with self.subTest(text=text):
                candidate['summary'] = text
                m.write_json(work / 'private/model.json', candidate)
                with self.assertRaises(m.MapError):
                    m.build(work)

    def test_longer_unrelated_names_do_not_match(self):
        for text in ('myapp.py', 'app.pyc', 'app.py.backup', 'app.py-extra',
                     '.app.py', 'prefix_app.py', 'app.py...suffix'):
            with self.subTest(text=text):
                self.assertFalse(m.contains_source_path(text, 'app.py'))

    def test_host_metadata_and_valid_ids_are_not_prose(self):
        for name in ('HEAD', 'gate', 'minimum', 'data', 'source_interpretation', 'a'):
            (self.repo / name).write_text('metadata\n')
        self.git('add', '.'); self.git('commit', '-qm', 'ambiguous names')
        work = m.prepare(self.repo, self.root / 'metadata')
        candidate = copy.deepcopy(self.model)
        candidate['snapshot'] = m.read_json(work / 'private/manifest.json')['snapshot']
        m.write_json(work / 'private/model.json', candidate)
        self.assertTrue((m.build(work) / 'map.html').is_file())
        # Exempting metadata must not exempt the same token in prose.
        candidate['summary'] = 'Inspect gate.'
        m.write_json(work / 'private/model.json', candidate)
        with self.assertRaises(m.MapError):
            m.build(work)

    def test_all_prose_fields_are_checked(self):
        base = copy.deepcopy(self.model)
        base['relations'] = [{'id': 'edge1', 'from': 'gate', 'to': 'gate', 'kind': 'data',
                              'label': 'flow', 'condition': 'enabled', 'timing': 'now', 'evidence': ['E1']}]
        cases = [('top', field) for field in ('title', 'summary', 'unknowns')]
        cases += [('nodes', field) for field in ('label', 'purpose', 'inputs', 'outputs', 'state', 'unknowns')]
        cases += [('rules', field) for field in ('title', 'text')]
        cases += [('relations', field) for field in ('label', 'condition', 'timing')]
        for group, field in cases:
            for forbidden in ('Read app.py.', '```hidden```'):
                with self.subTest(group=group, field=field, forbidden=forbidden):
                    candidate = copy.deepcopy(base)
                    item = candidate if group == 'top' else candidate[group][0]
                    item[field] = [forbidden] if isinstance(item[field], list) else forbidden
                    m.write_json(self.work / 'private/model.json', candidate)
                    with self.assertRaises(m.MapError):
                        m.build(self.work)

    def test_missing_or_duplicate_slots_fail_closed(self):
        for template in ('__PAGE_TITLE__', '__MAP_JSON__',
                         '__PAGE_TITLE__ __PAGE_TITLE__ __MAP_JSON__',
                         '__PAGE_TITLE__ __MAP_JSON__ __MAP_JSON__'):
            with self.subTest(template=template), self.assertRaises(m.MapError):
                m.render_viewer(template, 'title', '{}')

if __name__ == '__main__':
    unittest.main()
