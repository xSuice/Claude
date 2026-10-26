#!/usr/bin/env python3
"""git-sync: ~/MA-Server auf dem Server mit GitHub abgleichen (GitHub ist der Vergleichsmassstab zwischen Server und PC).
Der Server committet seine Aenderungen auf den Zweig "server-live" und pusht ihn; der PC holt ihn per "git fetch" und fuehrt ihn bewusst
mit main zusammen (kein Force-Push, keine stillen Ueberschreibungen). Der Hauptzweig main wird auf dem Server nur gelesen.

  git-sync.py status     Zustand zeigen (Repo, Remote, Schluessel, offene Aenderungen, voraus/zurueck)
  git-sync.py run        committen (nach Geheimnis-Pruefung) und pushen
  git-sync.py init       Repo anlegen und Remote setzen (nach "git-sync-einrichten.sh")
Konfiguration: ~/.config/ma-github/repo (eine Zeile: git@github.com:BENUTZER/REPO.git), Schluessel ~/.config/ma-github/deploy_ed25519 (nie ins Repo)."""
import os
import re
import subprocess
import sys
import time

ROOT = os.path.expanduser('~/MA-Server')
CFG = os.path.expanduser('~/.config/ma-github')
KEY = os.path.join(CFG, 'deploy_ed25519')
BRANCH = 'server-live'
SECRET = re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{32,}|xox[baprs]-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}")
MAX = 5 * 1024 * 1024
ENV = dict(os.environ, GIT_SSH_COMMAND='ssh -i %s -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=%s/known_hosts' % (KEY, CFG),
           GIT_TERMINAL_PROMPT='0')


def git(*args, check=False, raw=False):
    r = subprocess.run(['git', '-C', ROOT, *args], capture_output=True, env=ENV, timeout=120)
    if check and r.returncode:
        sys.exit('git %s: %s' % (' '.join(args), (r.stderr or r.stdout).decode('utf-8', 'replace').strip()[:300]))
    out = r.stdout.decode('utf-8', 'replace')
    return r.returncode, out if raw else out.strip()


def remote_url():
    try:
        return open(os.path.join(CFG, 'repo')).read().strip()
    except OSError:
        return ''


def cmd_init():
    url = remote_url()
    if not url:
        sys.exit('Keine Repo-Adresse: Datei %s/repo fehlt (Inhalt: git@github.com:BENUTZER/REPO.git).' % CFG)
    if not os.path.isdir(os.path.join(ROOT, '.git')):
        git('init', '-b', BRANCH, check=True)
        git('config', 'user.name', 'MA-Server', check=True)
        git('config', 'user.email', 'ma-server@localhost', check=True)
    if git('remote', 'get-url', 'origin')[0]:
        git('remote', 'add', 'origin', url, check=True)
    else:
        git('remote', 'set-url', 'origin', url, check=True)
    rc, out = git('fetch', 'origin', 'main')
    print('Remote gesetzt. Fetch main: ' + ('ok' if rc == 0 else 'FEHLER ' + out[:200]))
    if rc == 0 and git('rev-parse', '--verify', 'HEAD')[0]:      # noch kein Commit: Server-Zweig auf main aufsetzen, Dateien bleiben
        git('reset', '--mixed', 'origin/main', check=True)
        git('checkout', '-B', BRANCH)
        print('Zweig %s steht auf origin/main; Unterschiede zum Server stehen jetzt als Aenderungen an.' % BRANCH)


def cmd_status():
    print('Repo:    ' + ('ja' if os.path.isdir(os.path.join(ROOT, '.git')) else 'NEIN (git-sync.py init)'))
    print('Remote:  ' + (remote_url() or 'nicht gesetzt (%s/repo)' % CFG))
    print('Schluessel: ' + ('vorhanden' if os.path.exists(KEY) else 'FEHLT (git-sync-einrichten.sh)'))
    if os.path.isdir(os.path.join(ROOT, '.git')):
        print('Aenderungen: %d Dateien' % len(git('status', '--porcelain')[1].splitlines()))
        rc, out = git('rev-list', '--left-right', '--count', 'origin/main...HEAD')
        print('zurueck/voraus gegen origin/main: ' + (out.replace('\t', ' / ') if rc == 0 else 'unbekannt (noch kein Fetch)'))


def e_mod(f):
    """True, wenn die Datei schon im Repo steht (nur dann gibt es einen Zeilenende-Vergleich)."""
    return git('ls-files', '--error-unmatch', '--', f)[0] == 0


def cmd_run():
    if not os.path.isdir(os.path.join(ROOT, '.git')) or not os.path.exists(KEY):
        sys.exit('Nicht eingerichtet (git-sync.py status).')
    rc, out = git('status', '--porcelain', '-z', raw=True)
    files = [e[3:] for e in out.split('\0') if len(e) > 3]
    # PC-Dateien haben CRLF, Serverdateien LF: reine Zeilenende-Unterschiede nicht committen (sonst Rauschen in jedem Diff)
    files = [f for f in files if not (e_mod(f) and not git('diff', '--ignore-cr-at-eol', '--numstat', '--', f)[1])]
    ok, bad = [], []
    for f in files:
        p = os.path.join(ROOT, f)
        try:
            if os.path.isdir(p):
                ok.append(f)
            elif os.path.getsize(p) > MAX or SECRET.search(open(p, 'rb').read()):
                bad.append(f)
            else:
                ok.append(f)
        except OSError:
            ok.append(f)                                      # geloescht
    if bad:
        print('NICHT committet (zu gross oder moegliche Geheimnisse): ' + ', '.join(bad[:8]))
    if ok:
        git('add', '--', *ok, check=True)
        rc, o = git('commit', '-m', 'Server-Stand %s (%d Dateien)' % (time.strftime('%Y-%m-%d %H:%M'), len(ok)))
        print('Commit: ' + ('ok' if rc == 0 else o[:200]))
    rc, o = git('push', 'origin', 'HEAD:refs/heads/' + BRANCH)
    print('Push %s: %s' % (BRANCH, 'ok' if rc == 0 else 'FEHLER ' + o[:200]))
    sys.exit(0 if rc == 0 else 1)


if __name__ == '__main__':
    {'status': cmd_status, 'run': cmd_run, 'init': cmd_init}.get(sys.argv[1] if len(sys.argv) > 1 else 'status', cmd_status)()
