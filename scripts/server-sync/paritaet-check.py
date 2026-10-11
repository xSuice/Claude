#!/usr/bin/env python3
"""Paritaets-Check PC <-> MA-Server (ohne Modell, nur lesen). Prueft, ob beide Seiten gleich bleiben:
 1. Betriebsdateien: Router-Modul, Claude-Bruecke, ask.py, Portal-Oberflaeche (Repo-Stand gegen laufende Installation,
    Zeilenenden werden ignoriert).
 2. Portal: Patches eingebaut (PWA, Claude-Verwaltung, Dateien), Dienste aktiv.
 3. Skills und Agenten: PC (global + Projekt) gegen Server.
 4. Werkzeuge auf dem Server (Buero-Werkzeuge).
Bericht -> Vault _Claude-Memory/Dienste/Paritaet.md (nur die neueste Pruefung), Log ~/.claude/state/paritaet-check.log.
Exit-Code 0 = alles gleich, 1 = Abweichungen, 2 = Server nicht erreichbar.   Aufruf: python paritaet-check.py [--quiet]"""
import hashlib
import os
import subprocess
import sys
import time

PC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
VAULT_REPORT = r"C:\Users\andre\Documents\Obsidian Vault\_Claude-Memory\Dienste\Paritaet.md"
LOG = os.path.expanduser('~/.claude/state/paritaet-check.log')
HOST = 'ma-server'
HOME_CLAUDE = os.path.expanduser('~/.claude')

# (Name, Pfad im Repo, Pfad auf dem Server)
FILES = [
    ('Router-Modul', 'scripts/router/router_core.py', '/usr/local/lib/router_core.py'),
    ('Claude-Brücke', 'server/claude-bridge/ma-claude-bridge.py', '/usr/local/lib/ma-claude-bridge.py'),
    ('ask.py', 'scripts/ext-ai/ask.py', '/home/andrew/MA-Server/scripts/ext-ai/ask.py'),
]
# /opt/ma-home/web ist nur fuer root und ma-web lesbar: deploy-ui.sh schreibt die Pruefsummen der installierten Dateien nach DEPLOYED
PORTAL_FILES = ('index.html', 'app.js', 'style.css', 'sw.js', 'manifest.webmanifest')
DEPLOYED = '/opt/ma-home/DEPLOYED-UI.sha256'
MARKERS = [('PWA im Portal', 'MA-PWA'), ('Claude-Verwaltung im Portal', 'MA-CLAUDE-OPS'),
           ('Dateien/Bilder an Claude', "'images', 'files'"), ('Suggest/Upload im Portal', "'suggest', 'upload'")]
SERVICES = ['ma-claude-bridge', 'ma-home-web']
TOOLS = ['soffice', 'pandoc', 'ffmpeg', 'convert']
IGNORE_SKILLS = {'synced'}


def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(time.strftime('%Y-%m-%d %H:%M:%S ') + m + '\n')


def sha_local(path):
    try:
        data = open(path, 'rb').read().replace(b'\r\n', b'\n')
    except OSError:
        return None
    return hashlib.sha256(data).hexdigest()


def server_script():
    lines = ['for f in ' + ' '.join(f"'{s}'" for _, _, s in FILES) + '; do',
             '  if [ -f "$f" ]; then echo "H $f $(tr -d \'\\r\' < "$f" | sha256sum | cut -d" " -f1)"; else echo "H $f -"; fi; done']
    lines.append(f'[ -f {DEPLOYED} ] && sed "s/^/D /" {DEPLOYED} || echo "D -"')
    for label, mark in MARKERS:
        lines.append(f'echo "M {label}|$(grep -cF -- "{mark}" /opt/ma-home/portal.py 2>/dev/null || echo 0)"')
    lines.append('for s in ' + ' '.join(SERVICES) + '; do echo "S $s $(systemctl is-active $s 2>&1)"; done')
    lines.append('for t in ' + ' '.join(TOOLS) + '; do command -v $t >/dev/null && echo "T $t 1" || echo "T $t 0"; done')
    lines.append('for d in "$HOME"/.claude/skills/*/ "$HOME"/MA-Server/.claude/skills/*/; do [ -f "$d/SKILL.md" ] && echo "K $(basename "$d")"; done')
    lines.append('for a in "$HOME"/.claude/agents/*.md; do [ -f "$a" ] && echo "A $(basename "$a")"; done')
    return '\n'.join(lines) + '\n'


def ask_server():
    r = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', HOST, 'bash -s'], input=server_script().encode(),
                       capture_output=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode('utf-8', 'replace')[:300] or f'ssh Code {r.returncode}')
    return r.stdout.decode('utf-8', 'replace').splitlines()


def local_skills():
    names = set()
    for base in (os.path.join(HOME_CLAUDE, 'skills'), os.path.join(PC, '.claude', 'skills')):
        if os.path.isdir(base):
            names |= {d for d in os.listdir(base) if os.path.isfile(os.path.join(base, d, 'SKILL.md')) and not d.endswith('.disabled')}
    return names - IGNORE_SKILLS


def local_agents():
    base = os.path.join(HOME_CLAUDE, 'agents')
    return {f for f in os.listdir(base) if f.endswith('.md')} if os.path.isdir(base) else set()


def main():
    quiet = '--quiet' in sys.argv
    try:
        out = ask_server()
    except Exception as exc:
        log('Server nicht erreichbar: ' + str(exc))
        if not quiet:
            print('Server nicht erreichbar:', exc)
        return 2
    deployed = {}
    srv_hash, markers, services, tools, skills, agents = {}, {}, {}, {}, set(), set()
    for line in out:
        kind, _, rest = line.partition(' ')
        if kind == 'H':
            path, _, h = rest.rpartition(' ')
            srv_hash[path] = h
        elif kind == 'D':
            h, _, n = rest.partition('  ')
            if n:
                deployed[n.strip()] = h.strip()
        elif kind == 'M':
            label, _, n = rest.partition('|')
            markers[label] = int((n.strip() or '0').split()[-1] or 0)
        elif kind == 'S':
            n, _, st = rest.partition(' ')
            services[n] = st.strip()
        elif kind == 'T':
            n, _, v = rest.partition(' ')
            tools[n] = v.strip() == '1'
        elif kind == 'K':
            skills.add(rest.strip())
        elif kind == 'A':
            agents.add(rest.strip())

    rows, problems = [], []

    def row(name, ok, detail=''):
        rows.append(f"| {name} | {'gleich' if ok else 'ABWEICHUNG'} | {detail} |")
        if not ok:
            problems.append(f'{name}: {detail}')

    for name, rel, srv in FILES:
        a, b = sha_local(os.path.join(PC, rel)), srv_hash.get(srv, '-')
        row(name, a is not None and a == b, 'fehlt auf dem Server' if b == '-' else ('fehlt im Repo' if a is None else ('' if a == b else 'Inhalt unterschiedlich (Installation oder Abgleich fehlt)')))
    for n in PORTAL_FILES:
        a, b = sha_local(os.path.join(PC, 'portal-ui', 'web', n)), deployed.get(n)
        row('Portal ' + n, a is not None and a == b, 'Prüfsumme fehlt (deploy-ui.sh mit neuer Version noch nicht gelaufen)' if not deployed else ('' if a == b else 'installierte Fassung weicht vom Repo ab (deploy-ui.sh)'))
    for label, _ in MARKERS:
        row(label, markers.get(label, 0) > 0, '' if markers.get(label, 0) > 0 else 'im laufenden Portal nicht gefunden (deploy-ui.sh / update-bridge.sh)')
    for n in SERVICES:
        row('Dienst ' + n, services.get(n) == 'active', services.get(n, '?'))
    for n in TOOLS:
        row('Werkzeug ' + n, tools.get(n, False), '' if tools.get(n, False) else 'fehlt auf dem Server')
    ls, la = local_skills(), local_agents()
    row('Skills', ls <= skills, ('fehlen auf dem Server: ' + ', '.join(sorted(ls - skills))) if ls - skills else f'{len(ls)} gleich')
    extra = skills - ls
    if extra:
        rows.append(f"| Skills nur auf dem Server | Hinweis | {', '.join(sorted(extra))} (Abgleich holt sie zum PC) |")
    row('Agenten', la == agents, ('fehlen auf dem Server: ' + ', '.join(sorted(la - agents)) + '. ' if la - agents else '') +
        ('nur auf dem Server: ' + ', '.join(sorted(agents - la)) if agents - la else '') or f'{len(la)} gleich')

    stamp = time.strftime('%Y-%m-%d %H:%M')
    verdict = 'alles gleich' if not problems else f'{len(problems)} Abweichung(en)'
    body = ['---', 'typ: paritaet', 'quelle: paritaet-check.py (täglich)', 'datenklasse: B', '---', '# Parität PC ↔ Server',
            'Übergeordnet: [[MA-Server Zentrale]] · [[Server-Claude Variante 2]] · [[Server-Abgleich]] · [[Index]]', '',
            f'Stand {stamp}: **{verdict}**', '', '| Bereich | Ergebnis | Hinweis |', '|---|---|---|'] + rows + ['']
    if problems:
        body += ['## Zu tun'] + [f'- {p}' for p in problems] + ['']
    os.makedirs(os.path.dirname(VAULT_REPORT), exist_ok=True)
    with open(VAULT_REPORT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(body))
    log(f'{verdict}' + ('; ' + '; '.join(problems) if problems else ''))
    if not quiet:
        print(f'Parität {stamp}: {verdict}')
        for p in problems:
            print(' -', p)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
