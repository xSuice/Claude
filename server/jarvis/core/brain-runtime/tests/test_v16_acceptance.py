"""V16 acceptance checks: every check type positive and negative; parsers only in the sandbox."""
import json
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v16_fakes import tmpdir  # noqa: E402

import sandbox  # noqa: E402
from acceptance import Acceptance, validate_checks  # noqa: E402
from capabilities import Registry  # noqa: E402

LINUX = sys.platform == 'linux' and sandbox.available()


class Schema(unittest.TestCase):
    def test_refuses_unknown(self):
        for bad in ([], [{'type': 'shell'}], [{'type': 'contains'}], [{'type': 'min_bytes', 'value': '9'}],
                    [{'type': 'exists', 'cmd': 'x'}], [{'type': 'regex', 'value': '('}], [{'type': 'magic', 'value': 'exe'}]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_checks(bad)

    def test_accepts(self):
        self.assertEqual(len(validate_checks([{'type': 'exists'}, {'type': 'capability', 'capability': 'python.unittest', 'args': {}}])), 2)


@unittest.skipUnless(LINUX, 'needs Linux with a sandbox backend')
class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        cls._t = tempfile.TemporaryDirectory()
        cls.reg = Registry(Path(cls._t.name) / 's.db', 'server')
        cls.reg.discover(only={'python.run', 'python.unittest'})
        cls.acc = Acceptance(cls.reg)

    @classmethod
    def tearDownClass(cls):
        cls._t.cleanup()

    def ok(self, w, rel, check):
        return self.acc.check_one(w, rel, check)[0]

    def test_text_checks(self):
        w = tmpdir(self)
        (w / 'a.md').write_text('# Titel\n\nDas ist ein vollständiger Text mit sieben Wörtern.\n')
        (w / 'p.md').write_text('Einleitung\n\nTODO: hier fehlt noch was\n')
        self.assertTrue(self.ok(w, 'a.md', {'type': 'exists'}))
        self.assertFalse(self.ok(w, 'fehlt.md', {'type': 'exists'}))
        self.assertTrue(self.ok(w, 'a.md', {'type': 'contains', 'value': 'VOLLSTÄNDIGER'}))
        self.assertFalse(self.ok(w, 'a.md', {'type': 'not_contains', 'value': 'Titel'}))
        self.assertTrue(self.ok(w, 'a.md', {'type': 'regex', 'value': r'^# \w+'}))
        self.assertTrue(self.ok(w, 'a.md', {'type': 'words_min', 'value': 8}))
        self.assertFalse(self.ok(w, 'a.md', {'type': 'words_min', 'value': 50}))
        self.assertTrue(self.ok(w, 'a.md', {'type': 'no_placeholders'}))
        self.assertFalse(self.ok(w, 'p.md', {'type': 'no_placeholders'}))
        self.assertFalse(self.ok(w, '../a.md', {'type': 'exists'}))

    def test_json_and_python(self):
        w = tmpdir(self)
        (w / 'd.json').write_text(json.dumps({'a': 1, 'b': 2}))
        (w / 'x.json').write_text('{kaputt')
        (w / 'ok.py').write_text('def f():\n    return 1\n')
        (w / 'bad.py').write_text('def f(:\n')
        (w / 'boom.py').write_text('open("PWNED","w")\n')
        self.assertTrue(self.ok(w, 'd.json', {'type': 'json_keys', 'value': ['a', 'b']}))
        self.assertFalse(self.ok(w, 'd.json', {'type': 'json_keys', 'value': ['c']}))
        self.assertFalse(self.ok(w, 'x.json', {'type': 'json_valid'}))
        self.assertTrue(self.ok(w, 'ok.py', {'type': 'python_compiles'}))
        self.assertFalse(self.ok(w, 'bad.py', {'type': 'python_compiles'}))
        self.assertTrue(self.ok(w, 'boom.py', {'type': 'python_compiles'}))
        self.assertFalse((w / 'PWNED').exists())                       # compiling never executes

    def test_binary_formats_via_sandboxed_inspector(self):
        w = tmpdir(self)
        from PIL import Image
        Image.new('RGB', (64, 32), (200, 10, 10)).save(w / 'i.png')
        import docx
        d = docx.Document()
        d.add_heading('Bericht', 1)
        d.add_paragraph('Eins zwei drei vier fünf sechs sieben acht neun zehn.')
        d.save(w / 'b.docx')
        import openpyxl
        wb = openpyxl.Workbook()
        wb.create_sheet('Zwei')
        wb.save(w / 't.xlsx')
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(w / 'p.pdf'))
        c.drawString(72, 720, 'Seite eins')
        c.showPage()
        c.drawString(72, 720, 'Seite zwei')
        c.save()
        with zipfile.ZipFile(w / 'm.jar', 'w') as z:
            z.writestr('fabric.mod.json', '{}')
            z.writestr('com/x/Main.class', b'\xca\xfe')
        (w / 'fake.png').write_text('kein Bild')
        self.assertTrue(self.ok(w, 'i.png', {'type': 'image_min', 'width': 64, 'height': 32}))
        self.assertFalse(self.ok(w, 'i.png', {'type': 'image_min', 'width': 65, 'height': 32}))
        self.assertFalse(self.ok(w, 'fake.png', {'type': 'image_min', 'width': 1, 'height': 1}))
        self.assertTrue(self.ok(w, 'i.png', {'type': 'magic', 'value': 'png'}))
        self.assertTrue(self.ok(w, 'b.docx', {'type': 'docx_min_words', 'value': 10}))
        self.assertFalse(self.ok(w, 'b.docx', {'type': 'docx_min_words', 'value': 100}))
        self.assertTrue(self.ok(w, 't.xlsx', {'type': 'xlsx_sheets_min', 'value': 2}))
        self.assertTrue(self.ok(w, 'p.pdf', {'type': 'pdf_min_pages', 'value': 2}))
        self.assertFalse(self.ok(w, 'p.pdf', {'type': 'pdf_min_pages', 'value': 3}))
        self.assertTrue(self.ok(w, 'm.jar', {'type': 'zip_contains', 'value': ['fabric.mod.json', 'Main.class']}))
        self.assertFalse(self.ok(w, 'm.jar', {'type': 'zip_contains', 'value': ['mixins.json']}))

    def test_capability_check_runs_tests_in_sandbox(self):
        w = tmpdir(self)
        (w / 'test_x.py').write_text('import unittest\nclass T(unittest.TestCase):\n    def test(self):\n        self.assertTrue(True)\n')
        self.assertTrue(self.ok(w, 'test_x.py', {'type': 'capability', 'capability': 'python.unittest', 'args': {}}))
        (w / 'test_y.py').write_text('import unittest\nclass T(unittest.TestCase):\n    def test(self):\n        self.fail("nein")\n')
        ok, detail = self.acc.check_one(w, 'test_y.py', {'type': 'capability', 'capability': 'python.unittest', 'args': {}})
        self.assertFalse(ok)
        self.assertIn('nein', detail)


if __name__ == '__main__':
    unittest.main()
