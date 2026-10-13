#!/usr/bin/python3
"""Schaltet die Op 'connectors' (Portal-Reiter Verbindungen) in /opt/ma-home/portal.py frei: haengt sie an die Liste der erlaubten
Ops der Route /api/claude/op an. Aendert nur diese Liste (alle anderen Ops bleiben), idempotent, mit Sicherung und Pruefung.
Als root ausfuehren. Gegenstueck: server/claude-bridge/ma-claude-bridge.py (connectors_status), portal-ui/web/app.js (verbindungen)."""
import py_compile
import re
import shutil
import sys
import time

P = sys.argv[1] if len(sys.argv) > 1 else '/opt/ma-home/portal.py'
src = open(P, encoding='utf-8').read()
m = re.search(r"if op not in \(([^)]*)\):", src)
if not m:
    print('Stelle nicht gefunden (Route /api/claude/op), nichts geaendert.')
    sys.exit(1)
if "'connectors'" in m.group(1):
    print('Schon eingebaut.')
    sys.exit(0)
backup = f'{P}.bak-{time.strftime("%Y%m%d-%H%M%S")}'
shutil.copy2(P, backup)
new = src[:m.start(1)] + m.group(1).rstrip() + ", 'connectors'" + src[m.end(1):]
open(P, 'w', encoding='utf-8', newline='\n').write(new)
try:
    py_compile.compile(P, doraise=True)
except Exception as exc:
    shutil.copy2(backup, P)
    print('Pruefung fehlgeschlagen, zurueckgesetzt:', exc)
    sys.exit(1)
print('Eingebaut. Sicherung:', backup)
