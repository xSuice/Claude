"""V16.1 Cloud-Fallback-Brain: Offline-Tests (kein Netz, kein echter Key)."""
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tests'))

from cloud_worker import CloudWorker, CloudError, _first_json, _safe_rel, write_files_emulation, quota_exhausted


def _key_file(d: Path) -> Path:
    k = d / 'nexum.key'
    k.write_text('test-key', encoding='utf-8')
    k.chmod(0o600)
    return k


class TestSafeRel(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(_safe_rel('a/b/c.txt'), 'a/b/c.txt')
        self.assertEqual(_safe_rel('/abs/x.py'), 'abs/x.py')
        self.assertEqual(_safe_rel('a\\\\b.txt'), 'a/b.txt')

    def test_rejects_escape(self):
        for bad in ('../x', 'a/../../etc/passwd', '..', 'a//../b', 'C:/win', 'a:b', '', 'a\x00b', 'x' * 300):
            with self.assertRaises(CloudError, msg=bad):
                _safe_rel(bad)


class TestFirstJson(unittest.TestCase):
    def test_extracts_object(self):
        self.assertEqual(_first_json('Rauschen {"a": 1} mehr'), {'a': 1})

    def test_nested_and_noise(self):
        d = _first_json('prefix {"files": [{"path": "x", "content": "{"}], "notes": "y"} suffix')
        self.assertEqual(d['notes'], 'y')

    def test_no_json(self):
        self.assertIsNone(_first_json('kein json hier'))
        self.assertIsNone(_first_json(''))


class TestWriteFilesEmulation(unittest.TestCase):
    def test_writes_and_jails(self):
        with tempfile.TemporaryDirectory() as td:
            w = Path(td)
            written, err = write_files_emulation(w, [
                {'path': 'src/app.py', 'content': 'print(1)'},
                {'path': 'README.md', 'content': '# hi'},
            ])
            self.assertIsNone(err)
            self.assertEqual(sorted(written), ['README.md', 'src/app.py'])
            self.assertEqual((w / 'src/app.py').read_text(), 'print(1)')

    def test_escape_attempt_fails(self):
        with tempfile.TemporaryDirectory() as td:
            w = Path(td)
            written, err = write_files_emulation(w, [{'path': '../outside.txt', 'content': 'x'}])
            self.assertIsNotNone(err)
            self.assertFalse((Path(td).parent / 'outside.txt').exists())

    def test_limits(self):
        with tempfile.TemporaryDirectory() as td:
            w = Path(td)
            _w, err = write_files_emulation(w, [{'path': f'f{i}.txt', 'content': 'x'} for i in range(41)])
            self.assertIn('zu groß', err)
            _w, err = write_files_emulation(w, [{'path': 'big.txt', 'content': 'x' * 2_000_001}])
            self.assertIn('überschritten', err)
            _w, err = write_files_emulation(w, [{'path': 'nocontent.txt'}])
            self.assertIn('content', err)


class _FakeCloud(CloudWorker):
    def __init__(self, cfg, reply=None, error=None):
        super().__init__(cfg)
        self._reply, self._error = reply, error

    def _post(self, payload):
        if self._error:
            raise CloudError(self._error)
        return self._reply

    def _post_with_retry(self, payload):
        if self._error and 'HTTP 429' in self._error:
            raise CloudError(self._error)
        return self._post(payload)


def _cfg(d: Path) -> dict:
    return {'base_url': 'https://router.example/v1', 'model': 'test-model',
            'key_file': str(_key_file(d)), 'timeout_s': 10}


class TestCloudWorker(unittest.TestCase):
    def test_available_requires_https(self):
        with tempfile.TemporaryDirectory() as td:
            c = CloudWorker({**_cfg(Path(td)), 'base_url': 'http://insecure/v1'})
            self.assertFalse(c.available())

    def test_available_requires_key_perms(self):
        with tempfile.TemporaryDirectory() as td:
            k = _key_file(Path(td))
            k.chmod(0o644)
            self.assertFalse(CloudWorker(_cfg(Path(td))).available())

    def test_run_ok_shape(self):
        with tempfile.TemporaryDirectory() as td:
            reply = {'choices': [{'message': {'role': 'assistant', 'content': '{"a": 1}'}}],
                     'usage': {'prompt_tokens': 10, 'completion_tokens': 5}}
            c = _FakeCloud(_cfg(Path(td)), reply=reply)
            r = c.run(prompt='p', system='s', json_schema={'type': 'object'})
            self.assertTrue(r['ok'])
            self.assertEqual(r['structured'], {'a': 1})
            self.assertEqual(r['usage']['new'], 15)
            self.assertTrue(r['usage']['known'])
            self.assertEqual(r['error'], None)

    def test_run_error_shape(self):
        with tempfile.TemporaryDirectory() as td:
            c = _FakeCloud(_cfg(Path(td)), error='HTTP 401: bad key')
            r = c.run(prompt='p', system='s')
            self.assertFalse(r['ok'])
            self.assertIn('401', r['error'])
            self.assertEqual(r['usage']['new'], 0)

    def test_run_files_writes(self):
        with tempfile.TemporaryDirectory() as td:
            w = Path(td) / 'ws'
            w.mkdir()
            body = '{"files": [{"path": "out/ergebnis.md", "content": "# Ergebnis"}], "notes": "fertig"}'
            reply = {'choices': [{'message': {'content': body}}],
                     'usage': {'prompt_tokens': 20, 'completion_tokens': 10}}
            c = _FakeCloud(_cfg(Path(td)), reply=reply)
            r = c.run_files(prompt='p', system='s', workspace=w)
            self.assertTrue(r['ok'])
            self.assertEqual(r['written'], ['out/ergebnis.md'])
            self.assertEqual((w / 'out/ergebnis.md').read_text(), '# Ergebnis')
            self.assertEqual(r['text'], 'fertig')

    def test_run_files_invalid_json(self):
        with tempfile.TemporaryDirectory() as td:
            w = Path(td) / 'ws'
            w.mkdir()
            reply = {'choices': [{'message': {'content': 'kein json'}}], 'usage': {}}
            c = _FakeCloud(_cfg(Path(td)), reply=reply)
            r = c.run_files(prompt='p', system='s', workspace=w)
            self.assertFalse(r['ok'])
            self.assertIn('JSON', r['error'])


class TestQuotaExhausted(unittest.TestCase):
    def test_detects_quota(self):
        self.assertTrue(quota_exhausted("subtype success You've hit your weekly limit · resets 5am"))
        self.assertTrue(quota_exhausted('api_error usage_limit_reached'))
        self.assertTrue(quota_exhausted('Hit your usage limit'))

    def test_ignores_other_errors(self):
        self.assertFalse(quota_exhausted('HTTP 500 timeout'))
        self.assertFalse(quota_exhausted('invalid json'))
        self.assertFalse(quota_exhausted(''))


if __name__ == '__main__':
    unittest.main()
