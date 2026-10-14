"""V8.1 regression tests for the audit findings (written before the fixes). Offline only."""
import datetime as dt
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from knowledge_index import VaultIndex
from mcp_server_v5 import Server

D14, D15 = dt.date(2026, 10, 14), dt.date(2026, 10, 15)


def bump(f: Path):
    t = time.time() + 30
    os.utime(f, (t, t))


class VaultRegressions(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.dir = Path(t.name); self.vault = self.dir / 'vault'
        self.w('A/Frist.md', '---\nvalid_until: 2026-10-14\n---\n# Frist\nWartungsfenster Dienstag')
        self.w('A/Offen.md', '# Offen\nWartungsfenster Mittwoch')
        self.vi = VaultIndex(self.dir / 'i.db', self.vault)
        self.vi.build(today=D14)

    def w(self, rel, text):
        f = self.vault / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(text, encoding='utf-8')
        return f

    def sources(self, **kw):
        return {i['source'] for i in self.vi.search('Wartungsfenster', k=10, **kw)['items']}

    # Finding 1: expiry must apply at query time, even for unchanged files.
    def test_expiry_without_file_change(self):
        self.assertIn('A/Frist.md', self.sources(today=D14))       # valid through end of that day
        self.assertEqual(self.vi.build(today=D15)['reindexed'], 0)  # file unchanged
        self.assertNotIn('A/Frist.md', self.sources(today=D15))
        hist = self.vi.search('Wartungsfenster', k=10, today=D15, include_expired=True)['items']
        self.assertTrue(any(i['source'] == 'A/Frist.md' and i.get('historical') for i in hist))

    # Finding 2: private / retracted / deleted / edited must act on the next query, no rebuild.
    def test_private_flag_without_rebuild(self):
        bump(self.w('A/Offen.md', '---\nprivate: true\n---\n# Offen\nWartungsfenster Mittwoch'))
        self.assertNotIn('A/Offen.md', self.sources(today=D14))

    def test_retracted_and_deleted_without_rebuild(self):
        bump(self.w('A/Offen.md', '---\nstatus: retracted\n---\nWartungsfenster Mittwoch'))
        (self.vault / 'A/Frist.md').unlink()
        self.assertEqual(self.sources(today=D14), set())

    def test_edited_note_not_served_stale(self):
        bump(self.w('A/Offen.md', '# Offen\nWartungsfenster Freitag'))
        items = self.vi.search('Wartungsfenster', k=10, today=D14)['items']
        texts = ' '.join(i['text'] for i in items if i['source'] == 'A/Offen.md')
        self.assertIn('Freitag', texts); self.assertNotIn('Mittwoch', texts)

    def test_query_time_root_check(self):
        vi = VaultIndex(self.dir / 'i.db', self.vault, exclude=['A'])  # config changed, same index file
        self.assertEqual({i['source'] for i in vi.search('Wartungsfenster', k=10, today=D14)['items']}, set())


class ProjectScope(unittest.TestCase):
    """Finding 3: brain_lookup(project=A) must never return vault content of project B."""
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); d = Path(t.name)
        for rel, txt in {'project-a/Plan.md': 'Geheimplan Alpha', 'project-b/Plan.md': 'Geheimplan Beta',
                         'Gemeinsam/Info.md': 'Geheimplan gemeinsam', 'Privat/Tagebuch.md': 'Geheimplan privat'}.items():
            f = d / 'v' / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(txt)
        self.base = {'allowed_projects': ['project-a', 'project-b'], 'vault': str(d / 'v')}
        self.d = d

    def server(self, ident, **extra):
        return Server({**self.base, 'identity': ident, 'state_db': str(self.d / f'{ident}.db'),
                       'vault_index': str(self.d / f'{ident}-idx.db'), **extra})

    def lookup(self, s, project):
        r = s.call('brain_lookup', {'project': project, 'query': 'Geheimplan'})
        self.assertFalse(r.get('isError'), r)
        return {i['source'] for i in json.loads(r['content'][0]['text'])['existing_knowledge']}

    def test_project_folders_enforced(self):
        s = self.server('person-a', vault_projects={'project-a': ['project-a', 'Gemeinsam'],
                                                    'project-b': ['project-b']})
        self.assertEqual(self.lookup(s, 'project-a'), {'project-a/Plan.md', 'Gemeinsam/Info.md'})
        self.assertEqual(self.lookup(s, 'project-b'), {'project-b/Plan.md'})

    def test_unmapped_project_gets_no_vault_content(self):
        s = self.server('person-a', vault_projects={'project-a': ['project-a']})
        self.assertEqual(self.lookup(s, 'project-b'), set())
        s2 = self.server('person-c')  # no vault_projects at all -> secure default: nothing
        self.assertEqual(self.lookup(s2, 'project-a'), set())

    def test_two_identities_separated(self):
        a = self.server('person-a', vault_projects={'project-a': ['project-a', 'Privat']})
        b = self.server('person-b', vault_projects={'project-a': ['project-a']}, vault_exclude=['Privat'])
        self.assertIn('Privat/Tagebuch.md', self.lookup(a, 'project-a'))
        self.assertNotIn('Privat/Tagebuch.md', self.lookup(b, 'project-a'))

    def test_traversal_in_project_roots_rejected(self):
        with self.assertRaises(ValueError):
            self.server('person-a', vault_projects={'project-a': ['../etc']})
        with self.assertRaises(ValueError):
            self.server('person-a', vault_projects={'unknown-project': ['x']})

    def test_results_carry_authority(self):
        s = self.server('person-a', vault_projects={'project-a': ['project-a']})
        r = json.loads(s.call('brain_lookup', {'project': 'project-a', 'query': 'Geheimplan'})['content'][0]['text'])
        self.assertTrue(all(i['authority'] == 'obsidian' for i in r['existing_knowledge']))
        self.assertIn('conflict_rule', r)


class ExperienceTasks(unittest.TestCase):
    """Audit P3: task vs. session, separated token kinds, no premature routing advice."""
    def setUp(self):
        from experience import Experience
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); d = Path(t.name)
        root = d / 'projects' / 'p'; root.mkdir(parents=True)
        self.sid = 'abcdef12-0000-1111-2222-333344445555'
        rows = [
            {'type': 'user', 'timestamp': '2026-10-14T10:00:00Z', 'message': {'content': 'Aufgabe 1'}},
            {'type': 'assistant', 'timestamp': '2026-10-14T10:00:30Z', 'requestId': 'r1', 'effort': 'high',
             'message': {'model': 'claude-opus-5-5', 'content': [], 'usage': {
                 'input_tokens': 10, 'output_tokens': 500, 'cache_read_input_tokens': 9000,
                 'cache_creation_input_tokens': 300}}},
            {'type': 'user', 'timestamp': '2026-10-14T10:05:00Z', 'message': {'content': 'Aufgabe 2'}},
            {'type': 'assistant', 'timestamp': '2026-10-14T10:05:10Z', 'requestId': 'r2', 'effort': 'low',
             'message': {'model': 'claude-haiku-5-5', 'content': [], 'usage': {
                 'input_tokens': 5, 'output_tokens': 40, 'cache_read_input_tokens': 100}}}]
        self.tp = root / f'{self.sid}.jsonl'
        self.tp.write_text('\n'.join(json.dumps(r) for r in rows))
        self.x = Experience(d / 'b.db', 'person-a', {'ma-home'}, 'ma-home', None, d / 'projects')
        self.x.record({'session_id': self.sid, 'transcript_path': str(self.tp)})

    def test_task_slice_measured_separately(self):
        self.x.rate(self.sid, 'success', 'translate', turns=(2, 2), rework_minutes=0)
        self.x.rate(self.sid, 'failure', 'coding', turns=(1, 1), rework_minutes=15)
        g = {r['task_type']: r for r in self.x.stats()['groups']}
        self.assertEqual((g['translate']['model'], g['translate']['median_out_per_success'],
                          g['translate']['median_cached_per_success']), ('claude-haiku-5-5', 40, 100))
        self.assertEqual((g['coding']['model'], g['coding']['success_rate'], g['coding']['median_rework_minutes']),
                         ('claude-opus-5-5', 0.0, 15))
        self.assertFalse(any(r['sufficient'] for r in g.values()))
        self.assertIsNone(self.x.stats()['pro_quota'])

    def test_session_rating_marked_and_bad_ranges(self):
        r = self.x.rate(self.sid[:8], 'success', 'review')
        self.assertEqual(r['granularity'], 'session')
        self.assertEqual(self.x.stats()['groups'][0]['task_level_runs'], 0)
        for bad in [(0, 1), (2, 1), (1, 3)]:
            with self.assertRaises(ValueError):
                self.x.rate(self.sid, 'success', 'review', turns=bad)


if __name__ == '__main__':
    unittest.main()
