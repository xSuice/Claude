#!/usr/bin/env python3
"""Real A/B with Claude Code: server diagnosis WITHOUT vs WITH the brain's local pre-analysis.

Fixed before the first run (do not change afterwards):
  Task     The service "web" does not start. Find the root cause and the fix; change nothing.
  Truth    metrics/agent.conf also binds port 8080 -> web fails with "Address already in use".
  Grader   PASS only if the answer names (a) port 8080, (b) the metrics agent as the occupant and
           (c) a concrete fix (change one of the two ports / stop the agent); the workspace must be
           byte-identical afterwards. Grading is deterministic (regex), not by a model.
  A        baseline: Claude gets the task and the raw workspace (6 000+ log lines, configs, docs).
  B        V10.1: the daemon writes its diagnosis packet (sensor history + log digest) and the
           queue template 'diagnosis' is used exactly as in production.
Same CLI flags for both: plan mode, tools Read/Glob/Grep, no MCP, max 8 turns, cost cap per run.
Usage: python3 ab_diagnosis.py --runs 2 --max-usd 0.5 --out result.json
"""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

RT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RT))

TASKS = {
    'port': ('Der Dienst "web" auf dem MA-Home-Server startet nicht mehr. Finde die Ursache und nenne die '
             'Korrektur. Ändere nichts, führe nichts aus.'),
    # held-out task, fixed BEFORE any run of it (after the first 'port' measurement led to V10.1 changes)
    'backup': ('Die nächtliche Datensicherung ("backup") auf dem MA-Home-Server schlägt fehl. Finde die Ursache '
               'und nenne die Korrektur. Ändere nichts, führe nichts aus.')}
TASK = TASKS['port']


def build_workspace(root: Path):
    (root / 'logs').mkdir(parents=True); (root / 'web').mkdir(); (root / 'metrics').mkdir(); (root / 'docs').mkdir()
    (root / 'web' / 'server.conf').write_text('# web frontend\nlisten 8080;\nworkers 4;\nroot /srv/www;\n')
    (root / 'metrics' / 'agent.conf').write_text('# metrics agent (installed 2026-10-13)\nscrape_interval = 15s\n'
                                                 'listen_address = 0.0.0.0:8080\nretention = 7d\n')
    (root / 'docs' / 'README.md').write_text('# MA-Home\n' + '\n'.join(f'Abschnitt {i}: allgemeine Hinweise zur '
                                                                      f'Bedienung und Wartung.' for i in range(80)))
    noise = [f'2026-10-14T01:{i // 60 % 60:02d}:{i % 60:02d}Z info GET /api/item/{i} 200 {i % 97}ms' for i in range(6000)]
    noise[3100:3100] = ['2026-10-14T02:00:00Z warn cache miss ratio high'] * 3
    err = ['2026-10-14T02:11:0%dZ error bind() to 0.0.0.0:8080 failed (98: Address already in use)' % (i % 10)
           for i in range(40)] + ['2026-10-14T02:11:30Z fatal web: could not open listening socket, exiting']
    (root / 'logs' / 'web.log').write_text('\n'.join(noise + err) + '\n')
    (root / 'logs' / 'metrics.log').write_text('\n'.join(
        [f'2026-10-13T22:{i % 60:02d}:00Z info scraped 42 targets' for i in range(1500)] +
        ['2026-10-14T02:10:58Z info metrics agent listening on 0.0.0.0:8080']) + '\n')


def build_backup_workspace(root: Path):
    for d in ('logs', 'backup', 'storage', 'docs'):
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / 'backup' / 'backup.conf').write_text('# nightly backup\nsource = /DATA/media\ntarget_dir = /DATA/backups\n'
                                                'schedule = 02:30\nkeep = 14\n')
    (root / 'storage' / 'mounts.conf').write_text('# mount table managed by MA-Home (migration 2026-10-12)\n'
                                                 '/DATA/media     ext4  rw,noatime\n'
                                                 '/DATA/backups   ext4  ro,noatime   # migrated disk\n'
                                                 '/DATA/apps      ext4  rw,noatime\n')
    (root / 'docs' / 'README.md').write_text('# MA-Home\n' + '\n'.join(f'Kapitel {i}: Hinweise.' for i in range(120)))
    noise = [f'2026-10-14T02:{i // 60 % 60:02d}:{i % 60:02d}Z info copied file {i} ({i % 300} kB)' for i in range(4000)]
    err = [f'2026-10-14T02:31:{i:02d}Z error writing /DATA/backups/2026-10-14.tar: Read-only file system (errno 30)'
           for i in range(25)] + ['2026-10-14T02:31:40Z fatal backup aborted after 25 write errors']
    (root / 'logs' / 'backup.log').write_text('\n'.join(noise[:2000] + ['2026-10-14T02:20:00Z warn slow source disk'] +
                                                       noise[2000:] + err) + '\n')


def grade_backup(answer: str) -> dict:
    a = answer.lower()
    ro = bool(re.search(r'read-only|schreibgesch|nur[ -]?les|\bro\b|readonly', a))
    where = bool(re.search(r'mounts\.conf|mount', a)) and '/data/backups' in a
    fix = bool(re.search(r'\brw\b|remount|schreibbar|read-write|lesen und schreiben|anderes ziel|target_dir.{0,60}(änder|anpass|setz)', a))
    return {'read_only': ro, 'mount_located': where, 'concrete_fix': fix, 'pass': ro and where and fix}


def grade_v2(answer: str) -> dict:
    """Grader v2 for the 'port' task (added AFTER run 2 of V10.1-B showed a false negative: correct answers
    saying 'auf einen freien Port umstellen'/'eintragen'). Applied to ALL runs alike; v1 results stay reported."""
    a = answer.lower()
    g = grade(answer)
    fix = g['concrete_fix'] or bool(re.search(r'(umstell|eintrag).{0,80}(port|listen)|(metric|agent).{0,60}(umstell|freien port)', a))
    return {**g, 'concrete_fix': fix, 'pass': g['port_8080'] and g['occupant_metrics'] and fix}


def tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob('*')):
        if p.is_file() and '.claude' not in p.parts:
            h.update(str(p.relative_to(root)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


def grade(answer: str) -> dict:
    a = answer.lower()
    port = '8080' in a
    occupant = bool(re.search(r'metric|agent\.conf', a))
    fix = bool(re.search(r'(port|listen[_ ]?address|listen).{0,80}(änder|wechsel|anpass|setz|change|81|90|freigeb)|'
                         r'(stopp|deaktivier|beend|stop).{0,40}(metric|agent)|(metric|agent).{0,60}(stopp|deaktivier|beend|anderen port)', a))
    return {'port_8080': port, 'occupant_metrics': occupant, 'concrete_fix': fix, 'pass': port and occupant and fix}


def prepare_b(ws: Path, task: str = 'port') -> str:
    """Produce the packet exactly as the daemon does in production and return the queue prompt."""
    from brain_core import Brain
    from executive import Executive
    from daemon import Daemon
    from autonomy import validated, Queue, command
    state = ws.parent / 'brainstate'
    brain = Brain(state / 'b.db', 'person-a', {'ma-home'})
    ex = Executive(brain, {'actions': {'diagnose': {'claude_template': 'diagnosis'}, 'ok': {'argv': ['true']}}}, ws)
    auto = validated({'enabled': True, 'allowed_workspaces': [str(ws)], 'db_path': str(state / 'q.db'),
                      'minimum_gap_seconds': 0, 'allowed_templates': ['diagnosis'], 'max_turns': 8,
                      'claude_binary': 'claude'}, state / 'a.json')
    ex.autonomy = auto
    st = {'v': 'active'}
    d = Daemon(brain, 'ma-home', ex, autonomy_cfg=auto, sensor_runner=lambda a, timeout=10: (0, st['v']),
               sensors_cfg={'project': 'ma-home', 'sensors': [
                   {'id': 'web', 'type': 'systemd', 'unit': 'web.service', 'severity': 5,
                    'logs': [str(ws / 'logs' / 'web.log'), str(ws / 'logs' / 'metrics.log')]} if task == 'port' else
                   {'id': 'backup', 'type': 'systemd', 'unit': 'backup.service', 'severity': 5,
                    'logs': [str(ws / 'logs' / 'backup.log')]}]},
               opts={'sensor_interval_seconds': 0, 'diagnosis': {'action': 'diagnose', 'check': 'ok'}})
    d.tick(); st['v'] = 'failed'; d.tick(); d.tick()
    with Queue(auto['db_path']).connect() as c:
        job = dict(c.execute('SELECT * FROM jobs').fetchone())
    return command(auto, job)[2]  # the exact production prompt (template + topic)


def run_claude(prompt: str, ws: Path, max_usd: float) -> dict:
    cmd = ['claude', '-p', prompt, '--output-format', 'json', '--max-turns', '8', '--permission-mode', 'plan',
           '--tools', 'Read,Glob,Grep', '--disallowedTools', 'mcp__*', '--no-session-persistence',
           '--max-budget-usd', str(max_usd)]
    t0 = time.monotonic()
    p = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL)
    wall = time.monotonic() - t0
    try:
        d = json.loads(p.stdout)
    except ValueError:
        return {'error': (p.stderr or p.stdout)[-400:], 'wall_s': round(wall, 1)}
    u = d.get('usage') or {}
    return {'answer': d.get('result', ''), 'cost_usd': d.get('total_cost_usd'), 'turns': d.get('num_turns'),
            'duration_ms': d.get('duration_ms'), 'wall_s': round(wall, 1), 'is_error': d.get('is_error'),
            'input': u.get('input_tokens'), 'output': u.get('output_tokens'),
            'cache_read': u.get('cache_read_input_tokens'), 'cache_write': u.get('cache_creation_input_tokens'),
            'models': list((d.get('modelUsage') or {}).keys())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=int, default=2); ap.add_argument('--max-usd', type=float, default=0.5)
    ap.add_argument('--out', type=Path, required=True); ap.add_argument('--dry', action='store_true')
    ap.add_argument('--task', choices=list(TASKS), default='port')
    ap.add_argument('--variants', default='A,B')
    a = ap.parse_args()
    results = []
    for i in range(a.runs):
        for variant in a.variants.split(','):  # alternating, so cache warm-up hits both sides alike
            with tempfile.TemporaryDirectory() as t:
                ws = Path(t) / 'ws'
                (build_workspace if a.task == 'port' else build_backup_workspace)(ws)
                prompt = TASKS[a.task] if variant == 'A' else TASKS[a.task] + '\n\n' + prepare_b(ws, a.task)
                before = tree_hash(ws)
                prep_files = sorted(str(p.relative_to(ws)) for p in (ws / '.brain').glob('*')) if variant == 'B' else []
                packet_chars = sum((ws / f).stat().st_size for f in prep_files)
                r = {'dry': True} if a.dry else run_claude(prompt, ws, a.max_usd)
                r.update({'task': a.task, 'variant': variant, 'run': i + 1, 'prompt_chars': len(prompt), 'packet_chars': packet_chars,
                          'workspace_unchanged': tree_hash(ws) == before})
                r['grade'] = (grade if a.task == 'port' else grade_backup)(r.get('answer', '')) if not a.dry else None
                results.append(r)
                print(json.dumps({k: r.get(k) for k in ('variant', 'run', 'cost_usd', 'turns', 'wall_s', 'output',
                                                        'cache_read', 'cache_write', 'grade', 'error')}, ensure_ascii=False),
                      flush=True)
                a.out.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    print('total_usd', round(sum(r.get('cost_usd') or 0 for r in results), 4))


if __name__ == '__main__':
    main()
