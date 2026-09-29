"""Schema pattern/search semantics must agree with host fullmatch semantics."""
import importlib.util
from pathlib import Path
import re
import unittest

SPEC = importlib.util.spec_from_file_location('schema_mapper', Path(__file__).resolve().parents[1] / 'scripts/map.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

class SchemaIdTests(unittest.TestCase):
    def test_schema_search_matches_host_for_ids_and_references(self):
        props = m.schema()['properties']
        fields = {'nodes': ('id', 'parent'), 'rules': ('id', 'node', 'evidence'),
                  'relations': ('id', 'from', 'to', 'evidence'), 'evidence': ('id',)}
        values = ('', 'a', 'A_0-z', 'a' * 80, 'a' * 81, '_a', '1a', 'a.b',
                  'a\n', '\n', 'a\r\n', 'a\r', 'a\u2028', 'a\u2029', 'a\x00', '한글')
        for group, names in fields.items():
            for name in names:
                spec = props[group]['items']['properties'][name]
                if name == 'evidence':
                    spec = spec['items']
                for value in values:
                    with self.subTest(group=group, name=name, value=value):
                        expected = bool(m.ID.fullmatch(value)) or (name == 'parent' and value == '')
                        # JSON Schema pattern is a search, not Python fullmatch.
                        self.assertEqual(bool(re.search(spec['pattern'], value)), expected)
                        if expected:
                            m.shape(value, spec)
                        else:
                            with self.assertRaises(m.MapError):
                                m.shape(value, spec)

if __name__ == '__main__':
    unittest.main()
