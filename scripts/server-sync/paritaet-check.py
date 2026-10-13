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
    ('Morgenbrief-Skript (Cron)', 'scripts/server-sync/morgenbrief.py', '/home/andrew/MA-Server/scripts/server-sync/morgenbrief.py'),
    ('Graph-Export (Cron)', 'scripts/server-sync/vault-graph-export.py', '/home/andrew/MA-Server/scripts/server-sync/vault-graph-export.py'),
    ('Vault-Abfrage (vault-q)', 'scripts/vault-q.py', '/home/andrew/MA-Server/scripts/vault-q.py'),
    ('Such-Goldstandard (vault-q-gold)', 'scripts/vault-q-gold.py', '/home/andrew/MA-Server/scripts/vault-q-gold.py'),
    ('Vault-Index PostgreSQL (vault-pg)', 'scripts/vault-pg.py', '/home/andrew/MA-Server/scripts/vault-pg.py'),
    ('Server-settings.json', 'server/claude-config/settings.json', '/home/andrew/.claude/settings.json'),
    ('Hook ma-guard', 'server/claude-config/hooks/ma-guard.py', '/home/andrew/.claude/hooks/ma-guard.py'),
    ('Hook council-auto', 'server/claude-config/hooks/council-auto.py', '/home/andrew/.claude/hooks/council-auto.py'),
    ('Verbrauchs-Datenbank (usage-db)', 'server/tools/usage-db.py', '/home/andrew/MA-Server/server/tools/usage-db.py'),
    ('Terminal-Brücke', 'server/term-bridge/ma-term-bridge.py', '/usr/local/lib/ma-term-bridge.py'),
    ('Auto-Einspielung (Root-Skript)', 'server/auto-deploy/ma-deploy.sh', '/usr/local/lib/ma-deploy.sh'),
    ('Sudo-Freigabe (Root-Skript)', 'server/auto-deploy/ma-sudo-run.sh', '/usr/local/lib/ma-sudo-run.sh'),
    ('Meldung Auftrag fertig (Root-Skript)', 'server/auto-deploy/ma-job-notify.sh', '/usr/local/lib/ma-job-notify.sh'),
]
# Hooks, die es bewusst nur am PC gibt (Grund steht dabei). Jeder andere PC-Hook ohne Gegenstück wird gemeldet.
PC_ONLY_HOOKS = {'kontext-waechter.py': 'Token-Zähler der PC-Sitzung', 'uebergabe-laden.py': 'Übergabe-Start nur am PC',
                 'coach_gate_launcher.mjs': 'fixmyprompt-Plugin (PC)'}
# Jobs: (Name, Höchstalter des letzten Laufs in Stunden)
PC_TASKS = [('VaultZuServer', 2), ('VaultVomServer', 1.5), ('ClaudeAbgleich', 2), ('VaultDateienZuServer', 26), ('VaultAutopflege', 26), ('MA-Paritaet-Check', 26)]
SERVER_TIMERS = ['ma-home-maintenance.timer', 'ma-usb-backup.timer', 'ma-watchdog.timer', 'ma-sicherheitsbericht.timer', 'ma-deploy.path', 'ma-job-notify.path']
SERVER_CRON = ['vault-graph-export.py', 'morgenbrief.py', 'fristen-erinnerung.py', 'lern-impuls.py', 'fristen-ics.py']


def _aus_registry():
    """Automatisierungen aus server/automations.json (eine Quelle fuer PC und Server) zu den Erwartungen ergaenzen."""
    import json
    try:
        items = json.load(open(os.path.join(PC, 'server', 'automations.json'), encoding='utf-8'))['automations']
    except Exception:
        return
    for a in items:
        if 'pc' in a.get('ort', []) and a.get('pc_task') and a['pc_task'] not in [t[0] for t in PC_TASKS]:
            PC_TASKS.append((a['pc_task'], a.get('max_alter_h', 26)))
        if 'server' in a.get('ort', []) and os.path.basename(a.get('skript', '')) not in SERVER_CRON:
            SERVER_CRON.append(os.path.basename(a['skript']))


_aus_registry()
VAULT = r'C:\Users\andre\Documents\Obsidian Vault'
SERVER_NOTIZEN = '/srv/ma-home/library/vault-notizen'
# /opt/ma-home/web ist nur fuer root und ma-web lesbar: deploy-ui.sh schreibt die Pruefsummen der installierten Dateien nach DEPLOYED
PORTAL_FILES = ('index.html', 'app.js', 'style.css', 'sw.js', 'manifest.webmanifest')
DEPLOYED = '/opt/ma-home/DEPLOYED-UI.sha256'
MARKERS = [('PWA im Portal', 'MA-PWA'), ('Claude-Verwaltung im Portal', 'MA-CLAUDE-OPS'),
           ('Dateien/Bilder an Claude', "'images', 'files'"), ('Suggest/Upload im Portal', "'suggest', 'upload'"),
           ('Weiterlaufende Aufträge (attach)', "'attach', 'from'"), ('Suche und Zeitplan im Portal', "'search', 'sched_list'"),
           ('Terminal im Portal', 'MA-TERM-BRIDGE'), ('Reiter Verbindungen (Op connectors)', "'connectors'")]
SERVICES = ['ma-claude-bridge', 'ma-home-web', 'ma-term-bridge']
# Lokale MCP-Verbindungen, die bewusst nur am PC laufen (Name -> Grund). Alles andere soll auf beiden Seiten gleich heißen.
PC_ONLY_MCP = {}
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
    lines.append('for h in "$HOME"/.claude/hooks/*; do [ -f "$h" ] && echo "HK $(basename "$h")"; done')
    lines.append('for t in ' + ' '.join(SERVER_TIMERS) + '; do echo "TM $t $(systemctl is-active $t 2>&1) $(systemctl is-enabled $t 2>&1)"; done')
    lines.append('for c in ' + ' '.join(SERVER_CRON) + '; do crontab -l 2>/dev/null | grep -v "^#" | grep -qF "$c" && echo "CR $c 1" || echo "CR $c 0"; done')
    lines.append('[ -f "$HOME/MA-Server/DEPLOYED-REV" ] && echo "R $(cut -d" " -f1 "$HOME/MA-Server/DEPLOYED-REV")" || echo "R -"')
    lines.append('echo "VN $(find ' + SERVER_NOTIZEN + ' -type f -name "*.md" 2>/dev/null | wc -l)"')
    # Namen der lokalen MCP-Verbindungen (nur die Namen, nie Zugangsdaten)
    lines.append("python3 -c 'import json,os\n"
                 "try: d=json.load(open(os.path.expanduser(\"~/.claude.json\")))\n"
                 "except Exception: d={}\n"
                 "[print(\"MC \"+k) for k in sorted(d.get(\"mcpServers\",{}))]'")
    return '\n'.join(lines) + '\n'


def local_mcp():
    """Namen der lokalen MCP-Verbindungen am PC (Benutzerebene und .mcp.json im Projekt); keine Zugangsdaten."""
    import json
    names = set()
    for p in (os.path.expanduser('~/.claude.json'), os.path.join(PC, '.mcp.json')):
        try:
            names |= set(json.load(open(p, encoding='utf-8')).get('mcpServers', {}))
        except Exception:
            pass
    return names


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


def pc_hook_files():
    """Hook-Dateien, die in der PC-settings.json vorkommen (Skriptnamen)."""
    try:
        import json
        cfg = json.load(open(os.path.join(HOME_CLAUDE, 'settings.json'), encoding='utf-8'))
    except Exception:
        return set()
    names = set()
    for groups in cfg.get('hooks', {}).values():
        for g in groups:
            for h in g.get('hooks', []):
                for tok in ' '.join([str(h.get('command', ''))] + [str(a) for a in h.get('args', [])]).replace('"', ' ').split():
                    if tok.lower().endswith(('.py', '.mjs', '.js', '.sh')):
                        names.add(os.path.basename(tok.replace('\\', '/')))
    return names


def pc_tasks():
    ps = ("Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\\' } | ForEach-Object { $i = Get-ScheduledTaskInfo $_; "
          "'{0}|{1}|{2}|{3}' -f $_.TaskName, $_.State, $i.LastTaskResult, [int](((Get-Date) - $i.LastRunTime).TotalMinutes) }")
    r = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, timeout=60)
    out = {}
    for ln in r.stdout.decode('utf-8', 'replace').splitlines():
        parts = ln.strip().split('|')
        if len(parts) == 4:
            out[parts[0]] = parts[1:]
    return out


SRV_REV = ['-']   # Commit-Hash aus ~/MA-Server/DEPLOYED-REV auf dem Server ('-' = Datei fehlt)


def git_rev_notes():
    """Dreier-Vergleich PC-HEAD / GitHub (origin/main) / Server (DEPLOYED-REV)."""
    def git(*a):
        r = subprocess.run(['git', '-C', PC, *a], capture_output=True, timeout=30)
        return r.stdout.decode('utf-8', 'replace').strip() if r.returncode == 0 else ''
    head = git('rev-parse', 'HEAD')
    remote = ''
    try:
        remote = git('ls-remote', 'origin', 'refs/heads/main').split()[0]
    except IndexError:
        pass
    srv = SRV_REV[0]
    notes = [f"Stand: PC {head[:7] or '?'}, GitHub {remote[:7] or '? (nicht erreichbar)'}, Server {srv[:7] if srv != '-' else 'unbekannt (DEPLOYED-REV fehlt)'}"]
    if remote and head and remote != head:
        n = git('rev-list', '--count', f'{remote}..HEAD')
        notes.append(f'PC und GitHub weichen ab ({n or "?"} Commit(s) nur am PC; GitHub ggf. vorn)')
    if srv != '-' and head and srv != head:
        n = git('rev-list', '--count', f'{srv}..HEAD')
        notes.append(f'Server-Stand liegt {n or "?"} Commit(s) hinter dem PC-HEAD (Auto-Deploy liefert nur betroffene Dateien)')
    return notes


def git_notes():
    """Hinweise (keine Abweichungen): nicht committete oder nicht gepushte Änderungen."""
    notes = []
    try:
        notes += git_rev_notes()
    except Exception:
        pass
    try:
        st = subprocess.run(['git', '-C', PC, 'status', '--short', '-b'], capture_output=True, timeout=30).stdout.decode('utf-8', 'replace').splitlines()
        if st and 'ahead' in st[0]:
            notes.append('Commits noch nicht auf GitHub (' + st[0].split('[', 1)[-1].rstrip(']') + ')')
        dirty = [x[3:] for x in st[1:] if x[3:].startswith(('portal-ui/', 'server/', 'scripts/'))]
        if dirty:
            notes.append(f'{len(dirty)} Datei(en) nicht committet, z. B. ' + ', '.join(dirty[:3]))
    except Exception:
        pass
    return notes


def extra_checks(row, rows, srv_hooks, timers, cron, vn):
    pc_h = pc_hook_files()
    fehlt = sorted(h for h in pc_h if h not in srv_hooks and h not in PC_ONLY_HOOKS)
    row('Hooks', not fehlt, ('PC-Hook ohne Gegenstück auf dem Server (und nicht als "nur PC" erlaubt): ' + ', '.join(fehlt)) if fehlt
        else f'{len(pc_h)} am PC, davon {len(pc_h & srv_hooks)} auch auf dem Server, Rest bewusst nur PC')
    for n in SERVER_TIMERS:
        v = timers.get(n, '?')
        row('Server-Timer ' + n, v.startswith('active') and 'enabled' in v, v)
    for n in SERVER_CRON:
        row('Server-Cron ' + n, cron.get(n, False), '' if cron.get(n, False) else 'fehlt in der crontab')
    tasks = pc_tasks()
    for n, max_h in PC_TASKS:
        t = tasks.get(n)
        if not t:
            row('PC-Aufgabe ' + n, False, 'nicht gefunden')
            continue
        state, res, age = t[0], t[1], int(t[2])
        ok = state != 'Disabled' and res in (('0', '1') if n == 'MA-Paritaet-Check' else ('0', '267009')) and age <= max_h * 60   # 1 = Prüfung fand Abweichungen, kein Fehler
        row('PC-Aufgabe ' + n, ok, f'{state}, Ergebnis {res}, letzter Lauf vor {age} Min' + ('' if ok else f' (erwartet höchstens {int(max_h * 60)})'))
    if vn is not None:
        pc_n = sum(1 for r, d, fs in os.walk(VAULT) if '.obsidian' not in r for f in fs if f.endswith('.md'))
        rows.append(f"| Vault-Notizen | {'Hinweis' if abs(pc_n - vn) > 5 else 'gleich'} | PC {pc_n} .md, Server-Spiegel {vn} (bis 5 Unterschied ist Verzögerung) |")
    for n in git_notes():
        rows.append(f'| Git | Hinweis | {n} |')


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
    srv_hooks, timers, cron, vn, srv_mcp = set(), {}, {}, None, set()
    for line in out:
        kind, _, rest = line.partition(' ')
        if kind == 'H':
            path, _, h = rest.rpartition(' ')
            srv_hash[path] = h
        elif kind == 'D':
            h, _, n = rest.partition('  ')
            if n:
                deployed[n.strip()] = h.strip()
        elif kind == 'R':
            SRV_REV[0] = rest.strip()
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
        elif kind == 'HK':
            srv_hooks.add(rest.strip())
        elif kind == 'TM':
            n, _, st = rest.partition(' ')
            timers[n] = st.strip()
        elif kind == 'CR':
            n, _, v = rest.partition(' ')
            cron[n] = v.strip() == '1'
        elif kind == 'VN':
            vn = int(rest.strip() or 0)
        elif kind == 'MC':
            srv_mcp.add(rest.strip())

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

    pm = local_mcp()
    nur_pc, nur_srv = sorted(pm - srv_mcp - set(PC_ONLY_MCP)), sorted(srv_mcp - pm)
    row('Verbindungen (MCP)', not nur_pc and not nur_srv,
        ('nur am PC: ' + ', '.join(nur_pc) + '. ' if nur_pc else '') + ('nur auf dem Server: ' + ', '.join(nur_srv) if nur_srv else '') or f'{len(pm)} gleich')
    extra_checks(row, rows, srv_hooks, timers, cron, vn)
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
