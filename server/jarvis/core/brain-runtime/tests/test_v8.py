"""V8 tests: sensors, vault index, experience learning, MCP wiring. Offline only."""
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain_core import Brain
from cognitive_loop import CognitiveLoop
import sensors
from knowledge_index import VaultIndex
from experience import Experience, parse_transcript
from mcp_server_v5 import Server


def fake(results):
    calls = []
    def run(argv, timeout=10):
        calls.append(argv)
        return results.get(argv[-1], (0, 'active\n'))
    run.calls = calls
    return run


class SensorTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.dir = Path(t.name)
        self.loop = CognitiveLoop(Brain(self.dir / 'b.db', 'person-a', {'ma-home'}))
        self.cfg = {'project': 'ma-home', 'sensors': [
            {'id': 'nginx', 'type': 'systemd', 'unit': 'nginx.service', 'severity': 4},
            {'id': 'immich', 'type': 'docker', 'container': 'immich_server', 'severity': 5},
            {'id': 'data', 'type': 'disk', 'path': str(self.dir), 'min_free_percent': 0.001},
            {'id': 'backup', 'type': 'file_age', 'path': str(self.dir / 'last'), 'max_age_hours': 1}]}
        (self.dir / 'last').write_text('x')

    def test_healthy_then_deviation_then_dedup(self):
        ok = sensors.scan(self.loop, self.cfg, fake({'immich_server': (0, 'healthy')}))
        self.assertEqual(ok['deviations'], 0)
        self.assertEqual(self.loop.health('ma-home')['active_anomalies'], 0)
        bad = fake({'nginx.service': (3, 'failed\n'), 'immich_server': (0, 'unhealthy')})
        r = sensors.scan(self.loop, self.cfg, bad)
        self.assertEqual(r['deviations'], 2)
        self.assertEqual(self.loop.health('ma-home')['active_anomalies'], 2)
        again = sensors.scan(self.loop, self.cfg, bad)
        self.assertTrue(all(not s['recorded'] and s['new_anomalies'] == 0 for s in again['sensors']))
        self.assertEqual(self.loop.health('ma-home')['active_anomalies'], 2)
        focus = self.loop.focus('ma-home')['candidates']
        self.assertEqual(focus[0]['subject'], 'sensor:immich')  # severity 5 first
        sensors.scan(self.loop, self.cfg, fake({'immich_server': (0, 'healthy')}))
        self.assertEqual(self.loop.health('ma-home')['active_anomalies'], 0)  # recovery resolves

    def test_fixed_argv_no_shell_and_missing_tools(self):
        run = fake({'nginx.service': (127, ''), 'immich_server': (1, '')})
        r = {s['id']: s['state'] for s in sensors.scan(self.loop, self.cfg, run)['sensors']}
        self.assertEqual(r['nginx'], 'sensor-missing'); self.assertEqual(r['immich'], 'absent')
        self.assertIn(['systemctl', 'is-active', '--', 'nginx.service'], run.calls)
        self.assertTrue(all(isinstance(a, list) and '--' in a for a in run.calls))

    def test_stale_backup_and_garbage_output(self):
        old = time.time() + 7200
        r = {s['id']: s['state'] for s in sensors.scan(
            self.loop, self.cfg, fake({'immich_server': (0, 'rm -rf / ; $(x)')}), now=old)['sensors']}
        self.assertEqual(r['backup'], 'stale')
        self.assertEqual(r['immich'], 'unknown')  # raw output never stored

    def test_validation(self):
        bad = [{'project': 'ma-home', 'sensors': [{'id': 'x', 'type': 'shell', 'cmd': 'ls'}]},
               {'project': 'ma-home', 'sensors': [{'id': 'w', 'type': 'http', 'url': 'http://example.com/'}]},
               {'project': 'ma-home', 'sensors': [{'id': 'u', 'type': 'systemd', 'unit': 'a; reboot'}]},
               {'project': 'ma-home', 'sensors': [{'id': 'd', 'type': 'disk', 'path': 'relative'}]},
               {'project': 'ma-home', 'sensors': [{'id': 's', 'type': 'systemd', 'unit': 'a', 'extra': 1}]}]
        for cfg in bad:
            with self.assertRaises(ValueError):
                sensors.validate(cfg)
        sensors.validate({'project': 'ma-home', 'sensors': [{'id': 'w', 'type': 'http', 'url': 'http://127.0.0.1:1/'}]})

    def test_expectation_kept_between_scans_and_pause(self):
        run = fake({'immich_server': (0, 'healthy')})
        sensors.scan(self.loop, self.cfg, run); sensors.scan(self.loop, self.cfg, run)
        with self.loop.brain.connection() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM cognitive_expectations').fetchone()[0], 4)
        self.loop.set_paused('ma-home', True)
        n = len(run.calls)
        self.assertTrue(sensors.scan(self.loop, self.cfg, run)['paused'])
        self.assertEqual(len(run.calls), n)

    def test_http_loopback(self):
        import http.server, threading
        srv = http.server.HTTPServer(('127.0.0.1', 0), http.server.SimpleHTTPRequestHandler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close); self.addCleanup(srv.shutdown)
        s = {'id': 'w', 'type': 'http', 'url': f'http://127.0.0.1:{srv.server_port}/does-not-exist'}
        self.assertEqual(sensors.read(s)[0], 'status-404')
        self.assertEqual(sensors.read({**s, 'url': 'http://127.0.0.1:1/'})[0], 'down')


class VaultTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.dir = Path(t.name); self.vault = self.dir / 'vault'
        self.write('Server/Backup.md', '# Backup\nrestic nachts 02:30.\n## Restore\nrestic restore latest')
        self.write('Server/Alt.md', '---\nstatus: superseded\n---\n# Alt\nrestic früher 01:00')
        self.write('Server/Abgelaufen.md', '---\nvalid_until: 2020-01-01\n---\nrestic ganz alt')
        self.write('Privat/Arzt.md', '# Arzt\nrestic Termin')
        self.write('Notizen/Zertifikate.md', '# Zertifikate\nErneuerung alle 60 Tage.')
        (self.vault / '.obsidian').mkdir(); (self.vault / '.obsidian' / 'x.md').write_text('restic')

    def write(self, rel, text):
        f = self.vault / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(text, encoding='utf-8')

    def test_exclusions_sections_and_bounds(self):
        vi = VaultIndex(self.dir / 'i.db', self.vault, exclude=['Privat'])
        vi.build(today=dt.date(2026, 10, 14))
        res = vi.search('restic', k=10)
        sources = {i['source'] for i in res['items']}
        self.assertEqual(sources, {'Server/Backup.md'})
        self.assertLessEqual(res['chars'], 1500)
        self.assertTrue(any(i['section'] == 'Backup › Restore' for i in res['items']))

    def test_roots_per_identity(self):
        vi = VaultIndex(self.dir / 'b.db', self.vault, allowed_roots=['Notizen'])
        vi.build()
        self.assertEqual(vi.search('restic')['items'], [])
        self.assertEqual(vi.search('Zertifikatserneuerung')['items'][0]['source'], 'Notizen/Zertifikate.md')

    def test_incremental_and_deletion(self):
        vi = VaultIndex(self.dir / 'i.db', self.vault)
        first = vi.build()
        self.assertEqual(vi.build()['reindexed'], 0)
        self.write('Server/Backup.md', '# Backup\nborg statt restic')
        os.utime(self.vault / 'Server/Backup.md', (time.time() + 5, time.time() + 5))
        self.assertEqual(vi.build()['reindexed'], 1)
        (self.vault / 'Notizen/Zertifikate.md').unlink()
        self.assertEqual(vi.build()['removed'], 1)
        self.assertEqual(vi.search('Zertifikate')['items'], [])
        self.assertGreater(first['notes'], 0)

    @unittest.skipIf(os.name != 'posix', 'symlinks')
    def test_symlinks_ignored(self):
        outside = self.dir / 'secret.md'; outside.write_text('geheimwort')
        (self.vault / 'link.md').symlink_to(outside)
        od = self.dir / 'outdir'; od.mkdir(); (od / 'n.md').write_text('geheimwort')
        (self.vault / 'linkdir').symlink_to(od, target_is_directory=True)
        vi = VaultIndex(self.dir / 'i.db', self.vault); vi.build()
        self.assertEqual(vi.search('geheimwort')['items'], [])

    def test_query_injection_safe(self):
        vi = VaultIndex(self.dir / 'i.db', self.vault); vi.build()
        for q in ['"', 'NEAR(a b)', 'restic OR *', 'a" OR "b', '-- ; DROP TABLE sec']:
            vi.search(q)  # must not raise sqlite errors


def transcript(path, sid):
    rows = [
        {'type': 'user', 'timestamp': '2026-10-14T10:00:00Z', 'message': {'content': 'Fix bug'}},
        {'type': 'assistant', 'timestamp': '2026-10-14T10:00:05Z', 'requestId': 'r1', 'effort': 'high',
         'message': {'model': 'claude-sonnet-5-5', 'content': [{'type': 'text', 'text': 'x'}],
                     'usage': {'input_tokens': 10, 'output_tokens': 50, 'cache_read_input_tokens': 1000,
                               'cache_creation_input_tokens': 200}}},
        {'type': 'assistant', 'timestamp': '2026-10-14T10:00:06Z', 'requestId': 'r1', 'effort': 'high',
         'message': {'model': 'claude-sonnet-5-5', 'content': [{'type': 'tool_use', 'name': 'Read'}],
                     'usage': {'input_tokens': 10, 'output_tokens': 50, 'cache_read_input_tokens': 1000,
                               'cache_creation_input_tokens': 200}}},
        {'type': 'user', 'timestamp': '2026-10-14T10:00:07Z', 'message': {'content': [{'type': 'tool_result'}]}},
        {'type': 'assistant', 'timestamp': '2026-10-14T10:01:00Z', 'requestId': 'r2', 'effort': 'high',
         'message': {'model': 'claude-haiku-5-5', 'content': [{'type': 'text'}],
                     'usage': {'input_tokens': 5, 'output_tokens': 20}}},
    ]
    path.write_text('\n'.join(json.dumps(r) for r in rows) + '\nnot json\n')


class ExperienceTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.dir = Path(t.name); self.root = self.dir / 'projects' / 'p'; self.root.mkdir(parents=True)
        self.sid = 'abcdef12-0000-1111-2222-333344445555'
        self.tp = self.root / f'{self.sid}.jsonl'; transcript(self.tp, self.sid)
        self.x = Experience(self.dir / 'b.db', 'person-a', {'ma-home', 'notes'}, 'ma-home',
                            {str(self.dir / 'repo'): 'notes'}, self.dir / 'projects')

    def test_parse_counts_each_request_once(self):
        a = parse_transcript(self.tp)
        self.assertEqual(a['requests'], 2); self.assertEqual(a['output_tokens'], 70)
        self.assertEqual(a['cache_read_tokens'], 1000); self.assertEqual(a['tool_uses'], 1)
        self.assertEqual(a['user_turns'], 1); self.assertEqual(a['duration_s'], 60)
        self.assertEqual(a['models'], {'claude-sonnet-5-5': 1, 'claude-haiku-5-5': 1}); self.assertEqual(a['effort'], 'high')

    def test_record_rate_stats_export_and_project_mapping(self):
        (self.dir / 'repo' / 'sub').mkdir(parents=True)
        r = self.x.record({'session_id': self.sid, 'transcript_path': str(self.tp),
                           'cwd': str(self.dir / 'repo' / 'sub')})
        self.assertEqual(r['project'], 'notes')
        self.x.record({'session_id': self.sid, 'transcript_path': str(self.tp)})  # upsert, no dup
        self.assertEqual(len(self.x.unrated()), 1)
        self.assertEqual(self.x.stats()['groups'], [])  # unrated never counts
        self.x.rate(self.sid[:8], 'success', 'Coding')
        g = self.x.stats('coding')['groups'][0]
        self.assertEqual((g['runs'], g['success_rate'], g['median_out_per_success']), (1, 1.0, 70))
        out = self.dir / 'router-experience.json'
        self.assertEqual(self.x.export(out, min_runs=1)['groups'], 1)
        self.assertEqual(json.loads(out.read_text())['groups'][0]['task_type'], 'coding')

    def test_safety(self):
        self.assertEqual(self.x.record({'stop_hook_active': True})['skipped'], 'stop_hook_active')
        outside = self.dir / 'evil.jsonl'; transcript(outside, self.sid)
        with self.assertRaises(PermissionError):
            self.x.record({'session_id': self.sid, 'transcript_path': str(outside)})
        with self.assertRaises(ValueError):
            self.x.rate('abc', 'success', 'coding')
        with self.assertRaises(ValueError):
            self.x.rate(self.sid, 'great', 'coding')
        other = Experience(self.dir / 'b.db', 'person-b', {'ma-home'}, 'ma-home', None, self.dir / 'projects')
        self.x.record({'session_id': self.sid, 'transcript_path': str(self.tp)})
        self.assertEqual(other.unrated(), [])  # owners separated

    def test_hook_cli_never_fails(self):
        cfg = self.dir / 'c.json'
        cfg.write_text(json.dumps({'identity': 'person-a', 'allowed_projects': ['ma-home'],
                                   'state_db': str(self.dir / 'b.db'), 'transcript_root': str(self.dir / 'projects')}))
        for payload in ['garbage', '{}', json.dumps({'session_id': self.sid, 'transcript_path': str(self.tp)})]:
            p = subprocess.run([sys.executable, str(ROOT / 'experience.py'), '--config', str(cfg), 'hook'],
                               input=payload, capture_output=True, text=True, timeout=30)
            self.assertEqual((p.returncode, p.stdout), (0, ''))
        self.assertEqual(len(Experience(self.dir / 'b.db', 'person-a', {'ma-home'}, 'ma-home', None,
                                        self.dir / 'projects').unrated()), 1)


class McpV8Tests(unittest.TestCase):
    def test_lookup_uses_vault_and_experience_tool(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); d = Path(t.name)
        (d / 'v').mkdir(); (d / 'v' / 'Router.md').write_text('# Modellrouter\nHaiku für Übersetzungen.')
        s = Server({'identity': 'person-a', 'allowed_projects': ['ma-home'], 'state_db': str(d / 'b.db'),
                    'vault': str(d / 'v'), 'vault_index': str(d / 'i.db'), 'vault_projects': {'ma-home': ['']}})
        r = json.loads(s.call('brain_lookup', {'project': 'ma-home', 'query': 'Welches Modell für Übersetzung'})
                       ['content'][0]['text'])
        self.assertEqual(r['existing_knowledge'][0]['source'], 'Router.md')
        e = json.loads(s.call('brain_experience', {})['content'][0]['text'])
        self.assertEqual(e['groups'], [])
        self.assertTrue(s.call('brain_experience', {'x': 1}).get('isError'))


if __name__ == '__main__':
    unittest.main()
