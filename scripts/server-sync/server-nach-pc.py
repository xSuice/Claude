#!/usr/bin/env python3
"""Server -> PC: holt Projektdateien, die auf dem MA-Server (~/MA-Server) geaendert oder neu sind, ins PC-Repo.
Das PC-Repo bleibt die Hauptkopie, aber nichts geht verloren: Gegenstueck zu pc-nach-server.py (PC -> Server).

Regeln (pro Datei, Zeilenenden werden bei Textdateien ignoriert):
  gleich                                  -> nichts
  nur auf dem Server (und nie abgeglichen) -> holen
  verschieden, PC seit dem letzten Abgleich unveraendert -> holen (Server hat sie geaendert)
  verschieden, Server unveraendert        -> PC hat sie geaendert, nichts holen (geht mit pc-nach-server.py)
  verschieden, beide geaendert / unbekannt -> KONFLIKT: Serverfassung landet in server-konflikte/, nichts wird ueberschrieben
Ohne --apply wird nur angezeigt (Trockenlauf). Zustand des letzten Abgleichs: .server-sync-state.json im Repo.
Aufruf:  python server-nach-pc.py [--apply] [--take-server PFAD ...]
Exit-Code: 0 ok, 1 Konflikte offen, 2 Server nicht erreichbar.   Test ohne SSH: --local-server ORDNER --pc-root ORDNER"""
import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = 'ma-server'
REMOTE = 'MA-Server'
SKIP_PARTS = {'.git', 'node_modules', '__pycache__', 'out', 'server-konflikte'}
SKIP_EXT = ('.apk', '.idsig', '.class', '.pyc', '.dex', '.zip', '.key', '.token', '.env', '.pem', '.sqlite', '.db')
SKIP_FILES = {'.server-sync-state.json'}
TEXT_EXT = ('.py', '.sh', '.js', '.mjs', '.css', '.html', '.md', '.json', '.ps1', '.bat', '.java', '.xml', '.txt', '.yml', '.yaml',
            '.webmanifest', '.toml', '.ini', '.conf', '.service', '.timer', '.gitignore', '.gitattributes')
MAX_BYTES = 3_000_000


def skipped(rel):
    parts = rel.replace('\\', '/').split('/')
    return (any(p in SKIP_PARTS for p in parts[:-1]) or parts[-1] in SKIP_FILES
            or parts[-1].lower().endswith(SKIP_EXT))


def digest(data, rel):
    if rel.lower().endswith(TEXT_EXT) or '.' not in os.path.basename(rel):
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def walk(root):
    out = {}
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_PARTS]
        for f in files:
            full = os.path.join(base, f)
            rel = os.path.relpath(full, root).replace('\\', '/')
            if skipped(rel) or os.path.islink(full) or os.path.getsize(full) > MAX_BYTES:
                continue
            with open(full, 'rb') as fh:
                out[rel] = digest(fh.read(), rel)
    return out


def remote_list():
    excl = ' '.join("! -path '*/%s/*'" % d for d in sorted(SKIP_PARTS)) + ' ' + ' '.join("! -name '*%s'" % e for e in SKIP_EXT)
    cmd = 'cd ~/%s && find . -type f -size -%dk %s -print0 | xargs -0 -r sha256sum' % (REMOTE, MAX_BYTES // 1000, excl)
    r = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', HOST, cmd], capture_output=True, timeout=300)
    if r.returncode != 0:
        raise OSError(r.stderr.decode('utf-8', 'replace')[:300] or 'ssh fehlgeschlagen')
    out = {}
    for line in r.stdout.decode('utf-8', 'replace').splitlines():
        h, rel = line[:64], line[66:]
        rel = rel[2:] if rel.startswith('./') else rel
        if len(h) == 64 and rel and not skipped(rel):
            out[rel] = h
    return out


def remote_fetch(rel):
    r = subprocess.run(['ssh', '-o', 'BatchMode=yes', HOST, 'cat ' + shlex.quote(REMOTE + '/' + rel)], capture_output=True, timeout=120)
    if r.returncode != 0:
        raise OSError('Holen fehlgeschlagen: ' + rel)
    return r.stdout


def plan(pc, srv, state):
    pull, conflict, same, pc_only, deleted = [], [], [], [], []
    for p in sorted(set(pc) | set(srv)):
        s, c = srv.get(p), pc.get(p)
        if s is None:
            pc_only.append(p)
        elif c is None:
            (deleted if p in state else pull).append(p)       # am PC bewusst geloescht? dann nicht zurueckholen
        elif s == c:
            same.append(p)
        else:
            base = state.get(p)
            if base == c:
                pull.append(p)
            elif base == s:
                pc_only.append(p)
            else:
                conflict.append(p)
    return pull, conflict, same, pc_only, deleted


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--apply', action='store_true', help='Dateien wirklich holen (sonst nur anzeigen)')
    ap.add_argument('--take-server', nargs='*', default=[], metavar='PFAD', help='diese Dateien auf jeden Fall vom Server uebernehmen (auch bei Konflikt)')
    ap.add_argument('--local-server', help='Test: Ordner statt SSH-Server')
    ap.add_argument('--pc-root', default=os.path.normpath(os.path.join(HERE, '..', '..')), help='Repo-Ordner am PC')
    a = ap.parse_args()
    pc_root = a.pc_root
    state_file = os.path.join(pc_root, '.server-sync-state.json')
    try:
        state = json.load(open(state_file, encoding='utf-8'))
    except (OSError, ValueError):
        state = {}
    try:
        if a.local_server:
            srv = walk(a.local_server)
            fetch = lambda rel: open(os.path.join(a.local_server, rel), 'rb').read()
        else:
            srv, fetch = remote_list(), remote_fetch
    except (OSError, subprocess.SubprocessError) as exc:
        print('Server nicht erreichbar:', exc)
        return 2
    pc = walk(pc_root)
    pull, conflict, same, pc_only, deleted = plan(pc, srv, state)
    for p in a.take_server:
        p = p.replace('\\', '/')
        if p in srv:
            for lst in (conflict, pc_only, deleted):
                if p in lst:
                    lst.remove(p)
            if p not in pull:
                pull.append(p)
    print('Server -> PC: %d zu holen, %d Konflikte, %d nur am PC geaendert, %d gleich, %d am PC geloescht' %
          (len(pull), len(conflict), len(pc_only), len(same), len(deleted)))
    for title, lst in (('Zu holen', pull), ('KONFLIKT (beide geaendert oder unbekannt)', conflict), ('Am PC geaendert (nicht zurueckgeholt)', pc_only)):
        if lst:
            print('\n' + title + ':')
            for p in lst:
                print('  ' + p)
    if not a.apply:
        print('\nTrockenlauf. Mit --apply holen; Konflikte einzeln mit --take-server PFAD uebernehmen.')
        return 1 if conflict else 0
    for p in pull:
        data = fetch(p)
        if digest(data, p) != srv[p]:
            print('Pruefsumme stimmt nicht, uebersprungen:', p)
            continue
        dest = os.path.join(pc_root, *p.split('/'))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as fh:
            fh.write(data)
        state[p] = srv[p]
    for p in conflict:
        dest = os.path.join(pc_root, 'server-konflikte', *p.split('/'))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as fh:
            fh.write(fetch(p))
    for p in same:
        state[p] = srv[p]
    with open(state_file, 'w', encoding='utf-8') as fh:
        json.dump(state, fh, indent=0, sort_keys=True)
    if conflict:
        print('\nKonflikt-Fassungen vom Server liegen in server-konflikte/ (nichts ueberschrieben). Pruefen, dann ggf. --take-server PFAD.')
    return 1 if conflict else 0


if __name__ == '__main__':
    sys.exit(main())
