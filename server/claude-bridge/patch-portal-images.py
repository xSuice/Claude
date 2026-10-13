#!/usr/bin/python3
"""Reicht das Feld 'images' in /api/claude an die Claude-Bruecke weiter (idempotent, mit Sicherung und Pruefung). Als root ausfuehren."""
import py_compile
import shutil
import sys
import time

P = sys.argv[1] if len(sys.argv) > 1 else '/opt/ma-home/portal.py'
OLD = "('prompt', 'session', 'dir', 'mode', 'model')"
MID = "('prompt', 'session', 'dir', 'mode', 'model', 'images')"
NEW = "('prompt', 'session', 'dir', 'mode', 'model', 'images', 'files')"
src = open(P, encoding='utf-8').read()
if NEW in src or "'images', 'files'" in src:      # auch spaetere Staende (attach, from) gelten als eingebaut
    print('Schon eingebaut.')
    sys.exit(0)
if OLD not in src and MID not in src:
    print('Stelle nicht gefunden, nichts geaendert.')
    sys.exit(1)
backup = f'{P}.bak-{time.strftime("%Y%m%d-%H%M%S")}'
shutil.copy2(P, backup)
open(P, 'w', encoding='utf-8', newline='\n').write(src.replace(OLD, NEW, 1).replace(MID, NEW, 1))
try:
    py_compile.compile(P, doraise=True)
except Exception as exc:
    shutil.copy2(backup, P)
    print('Pruefung fehlgeschlagen, zurueckgesetzt:', exc)
    sys.exit(1)
print('Eingebaut. Sicherung:', backup)
