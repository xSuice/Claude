#!/usr/bin/env python3
"""Test der GitHub-Veroeffentlichung im Abgleich (claude-abgleich.git_publish) mit lokalen Git-Repos (Remote = lokales Bare-Repo, kein Netz).
Aufruf: python3 tests/test_git_publish.py   Exit 0 = alles bestanden."""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('ab', os.path.join(HERE, '..', 'scripts', 'server-sync', 'claude-abgleich.py'))
ab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ab)
fails = []


def check(name, ok, info=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' – ' + str(info)))
    if not ok:
        fails.append(name)


def run(*a, cwd=None):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)


with tempfile.TemporaryDirectory() as t:
    remote, work = os.path.join(t, 'remote.git'), os.path.join(t, 'pc')
    run('git', 'init', '-q', '--bare', '-b', 'main', remote)
    run('git', 'clone', '-q', remote, work)
    for k, v in (('user.email', 'a@b.c'), ('user.name', 'Test')):
        run('git', 'config', k, v, cwd=work)
    open(os.path.join(work, 'start.txt'), 'w').write('x')
    run('git', 'add', '.', cwd=work); run('git', 'commit', '-qm', 'start', cwd=work); run('git', 'push', '-q', '-u', 'origin', 'main', cwd=work)
    ab.PC = work
    ab.log = lambda m: None

    def remote_log():
        return run('git', '--git-dir', remote, 'log', '--oneline', 'main').stdout.splitlines()

    # 1. geholte Datei -> committet und gepusht; fremde unfertige Arbeit bleibt unangetastet
    os.makedirs(os.path.join(work, 'scripts'))
    open(os.path.join(work, 'scripts', 'neu.py'), 'w').write('print(1)\n')
    open(os.path.join(work, 'wip.txt'), 'w').write('unfertig')
    n = ab.git_publish(['scripts/neu.py'])
    check('geholte Datei wird committet und gepusht', len(remote_log()) == 2 and any('gepusht' in x for x in n), (remote_log(), n))
    tracked = run('git', 'ls-files', cwd=work).stdout.split()
    check('unfertige PC-Arbeit wird NICHT mitcommittet', 'wip.txt' not in tracked and 'scripts/neu.py' in tracked, tracked)

    # 2. Geheimnisse: Dateiname und Inhalt
    open(os.path.join(work, '.env.local'), 'w').write('A=1')
    open(os.path.join(work, 'notiz.md'), 'w').write('token ghp_' + 'a' * 36)
    open(os.path.join(work, 'ok.md'), 'w').write('harmlos')
    n = ab.git_publish(['.env.local', 'notiz.md', 'ok.md'])
    tracked = run('git', 'ls-files', cwd=work).stdout.split()
    check('Dateien mit Geheimnis-Namen/-Inhalt werden nicht committet und gemeldet', '.env.local' not in tracked and 'notiz.md' not in tracked and any('Geheimnisse' in x for x in n), (tracked, n))
    check('harmlose Datei derselben Runde wird committet', 'ok.md' in tracked)

    # 3. nichts geholt, aber lokaler Commit voraus -> wird nachtraeglich gepusht
    open(os.path.join(work, 'manuell.txt'), 'w').write('m')
    run('git', 'add', 'manuell.txt', cwd=work); run('git', 'commit', '-qm', 'manuell', cwd=work)
    before = len(remote_log())
    n = ab.git_publish([])
    check('lokaler Commit ohne neue Serverdateien wird gepusht', len(remote_log()) == before + 1, (before, remote_log(), n))

    # 4. Push schlaegt fehl -> Meldung, kein Absturz
    open(os.path.join(work, 'x2.txt'), 'w').write('2')
    run('git', 'add', 'x2.txt', cwd=work); run('git', 'commit', '-qm', 'x2', cwd=work)
    shutil.rmtree(remote)
    try:
        n = ab.git_publish([])
        check('fehlgeschlagener Push wird gemeldet (kein Absturz)', any('Push fehlgeschlagen' in x for x in n), n)
    except Exception as e:
        check('fehlgeschlagener Push wird gemeldet (kein Absturz)', False, e)

print('\nAlle Prüfungen bestanden.' if not fails else '\n%d Prüfung(en) fehlgeschlagen' % len(fails))
sys.exit(1 if fails else 0)
