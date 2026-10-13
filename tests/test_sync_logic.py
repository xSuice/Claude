#!/usr/bin/env python3
"""Tests der Abgleichs-Logik PC <-> Server (reine Funktionen, ohne SSH und ohne Netz):
Hauptkopie-Modus (vault-to-server.divert, server-to-vault.vanished), MCP-Abgleich (claude-abgleich.mcp_plan/mcp_portable und das Zusammenfuehren
auf dem Server), Automatisierungsliste (automations.py). Aufruf: python3 tests/test_sync_logic.py   Exit 0 = alles bestanden."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(HERE, '..', 'scripts')
fails = []


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(S, rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def check(name, ok, info=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' – ' + str(info)))
    if not ok:
        fails.append(name)


up, down = load('up', 'server-sync/vault-to-server.py'), load('down', 'server-sync/server-to-vault.py')
old = {'a.md': [100, 10], 'b.md': [100, 10], 'bild.png': [100, 10]}
srv = {'a.md': [100, 10], 'b.md': [500, 99], 'bild.png': [500, 99]}
send, copies = up.divert(['a.md', 'b.md', 'bild.png', 'c.md'], old, srv)
check('Hauptkopie: vom Server geänderte Notiz wird nicht überschrieben (Kopie)', copies == ['b.md'], copies)
check('Hauptkopie: gleiche, neue und Anhänge werden normal gesendet', send == ['a.md', 'bild.png', 'c.md'], send)
sent = {'x.md': [1, 1], 'y.md': [1, 1], 'bild.png': [1, 1], '.obsidian/w.md': [1, 1]}
check('Hauptkopie: auf dem Server entfernte Notiz wird erkannt (nur Text, nicht versteckt/Anhang)', down.vanished(sent, {'x.md': (1, 1), 'bild.png': (1, 1)}, lambda r, b: True) == ['y.md'])
check('Hauptkopie: lokal geänderte Notiz wird nicht entfernt', down.vanished(sent, {'x.md': (1, 1)}, lambda r, b: r != 'y.md') == [])
check('Hauptkopie: Sicherheitsstopp bei auffällig kleiner Serverliste', down.vanished({f'n{i}.md': [1, 1] for i in range(10)}, {'n1.md': (1, 1)}, lambda r, b: True) == [])

ab = load('ab', 'server-sync/claude-abgleich.py')
check('MCP: Remote-Verbindung ohne Zugangsdaten ist portabel', ab.mcp_portable({'type': 'http', 'url': 'https://example.org/mcp'}))
check('MCP: npx-Server ohne Geheimnisse ist portabel', ab.mcp_portable({'command': 'npx', 'args': ['-y', '@x/server']}))
check('MCP: Windows-Programm ist nicht portabel', not ab.mcp_portable({'command': r'C:\Users\a\.local\bin\mcp-email-server.exe', 'args': ['stdio']}))
check('MCP: Zugangsdaten in env sind nicht portabel', not ab.mcp_portable({'command': 'npx', 'args': ['x'], 'env': {'API_KEY': 'abc'}}))
check('MCP: Header mit Anmeldung ist nicht portabel', not ab.mcp_portable({'type': 'http', 'url': 'https://x', 'headers': {'Authorization': 'Bearer abc'}}))
pc = {'a': {'type': 'http', 'url': 'https://a'}, 'b': {'command': 'npx', 'args': ['b']}, 'gmx': {'command': 'x.exe'}, 'privat': {'command': 'npx', 'args': ['p']}, 'same': {'command': 'npx', 'args': ['s']}}
add, differ, nicht = ab.mcp_plan(pc, {'b': {'command': 'npx', 'args': ['anders']}, 'same': {'command': 'npx', 'args': ['s']}}, {'privat'})
check('MCP: nur fehlende portable werden hinzugefügt', list(add) == ['a'], add)
check('MCP: abweichende werden nicht überschrieben, nur gemeldet', differ == ['b'], differ)
check('MCP: nicht portable und „nur PC“ werden nicht übertragen', nicht == ['gmx'] and 'privat' not in add, (nicht, add))
pc2 = {'tok': {'command': 'npx', 'args': ['x'], 'env': {'API_KEY': 'abc'}}, 'hdr': {'type': 'http', 'url': 'https://x', 'headers': {'Authorization': 'Bearer abc'}},
       'gmx': {'command': r'C:\Users\a\mcp-email-server.exe', 'args': ['stdio'], 'env': {'PASSWORD': 'p'}}, 'fremd': {'command': 'meinprogramm', 'env': {'TOKEN': 't'}}}
add2, _, nicht2 = ab.mcp_plan(pc2, {}, set())
check('MCP ohne Freigabe: nichts mit Zugangsdaten wird übertragen', not add2 and sorted(nicht2) == ['fremd', 'gmx', 'hdr', 'tok'], (add2, nicht2))
add3, _, nicht3 = ab.mcp_plan(pc2, {}, set(), mit_zugang=True)
check('MCP mit Freigabe: Zugangsdaten ja, Windows-/unbekannte Programme weiterhin nein', sorted(add3) == ['hdr', 'tok'] and sorted(nicht3) == ['fremd', 'gmx'], (sorted(add3), sorted(nicht3)))
add4, _, _ = ab.mcp_plan(pc2, {}, {'tok'}, mit_zugang=True)
check('MCP mit Freigabe: „nur PC“-Liste gilt weiterhin', 'tok' not in add4, add4)
check('MCP: Freigabedatei liegt im Projekt und enthält keine Geheimnisse', os.path.exists(os.path.join(HERE, '..', 'server', 'claude-config', 'mcp-zugang.ok')) and not ab.SECRET_TEXT.search(open(os.path.join(HERE, '..', 'server', 'claude-config', 'mcp-zugang.ok'), 'rb').read()))

# Zusammenführen auf dem Server: bestehende Einträge und andere Schlüssel bleiben, Sicherung entsteht, Rechte 0600
with tempfile.TemporaryDirectory() as home:
    json.dump({'oauthAccount': {'x': 1}, 'mcpServers': {'alt': {'command': 'npx'}}}, open(os.path.join(home, '.claude.json'), 'w'))
    cmd = ab.MCP_MERGE
    r = subprocess.run(['bash', '-c', cmd], input=json.dumps({'a': {'type': 'http', 'url': 'https://a'}, 'alt': {'command': 'ueberschreibt-nicht'}}).encode(),
                       capture_output=True, env=dict(os.environ, HOME=home))
    d = json.load(open(os.path.join(home, '.claude.json')))
    check('MCP-Merge: neuer Eintrag da, alter unverändert, andere Schlüssel erhalten',
          'a' in d['mcpServers'] and d['mcpServers']['alt'] == {'command': 'npx'} and d['oauthAccount'] == {'x': 1}, (r.stderr[:200], d))
    check('MCP-Merge: Sicherung angelegt, Datei 0600', os.path.exists(os.path.join(home, '.claude.json.ma-bak')) and oct(os.stat(os.path.join(home, '.claude.json')).st_mode & 0o777) == '0o600')

am = subprocess.run([sys.executable, '-I', os.path.join(S, 'automations.py'), 'validate'], capture_output=True, text=True)
check('Automatisierungsliste ist gültig', am.returncode == 0, am.stdout + am.stderr)
cr = subprocess.run([sys.executable, '-I', os.path.join(S, 'automations.py'), 'cron', '--user', 'andrew', '--skip', 'none'], capture_output=True, text=True).stdout.splitlines()
check('Cron-Zeilen: 5 Server-Aufträge mit Zeit (Morgenbrief, 2x Fristen, 3x Status, ICS, Lern-Impuls = 8 Zeilen)', len(cr) == 8 and all(' andrew python3 ' in l for l in cr), cr)

print('\n%d Prüfungen, %d fehlgeschlagen' % (len(fails) + 0, len(fails)) if fails else '\nAlle Prüfungen bestanden.')
sys.exit(1 if fails else 0)
