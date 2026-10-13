#!/usr/bin/python3
"""Erlaubt in /opt/ma-home/portal.py (Route /api/claude) die Felder attach und from, damit sich das Portal an einen laufenden
Claude-Auftrag wieder anhaengen kann (idempotent, mit Sicherung und Pruefung). Als root ausfuehren."""
import py_compile
import shutil
import sys
import time

P = sys.argv[1] if len(sys.argv) > 1 else '/opt/ma-home/portal.py'
# Ersetzungen (alt, neu): attach/from fuer /api/claude, und die erlaubten Verwaltungsbefehle (op) fuer /api/claude/op
OPS_OLD = "('jobs', 'cancel', 'sessions', 'show', 'rename', 'suggest', 'upload')"
OPS_NEW = "('jobs', 'cancel', 'sessions', 'show', 'rename', 'suggest', 'upload', 'search', 'sched_list', 'sched_set', 'sched_del', 'usage', 'lern_feedback', 'note')"
OPS_MID2 = "('jobs', 'cancel', 'sessions', 'show', 'rename', 'suggest', 'upload', 'search', 'sched_list', 'sched_set', 'sched_del', 'usage', 'lern_feedback')"   # frueherer Stand
OPS_MID ="('jobs', 'cancel', 'sessions', 'show', 'rename', 'suggest', 'upload', 'search', 'sched_list', 'sched_set', 'sched_del')"   # frueherer Stand dieses Patches
REPL = [
    (["('prompt', 'session', 'dir', 'mode', 'model', 'images', 'files')"], "('prompt', 'session', 'dir', 'mode', 'model', 'images', 'files', 'attach', 'from')"),
    ([OPS_OLD, OPS_MID, OPS_MID2], OPS_NEW),
]
src = open(P, encoding='utf-8').read()
todo = []
for olds, n in REPL:
    if n in src or (n == OPS_NEW and n[:-1] + ", 'connectors')" in src):      # 'connectors' kommt spaeter von patch-portal-connectors.py
        continue
    o = next((x for x in olds if x in src), None)
    if o is None:
        sys.exit('Fehler: erwartete Zeile in portal.py nicht gefunden (Route geaendert?). Nichts veraendert.')
    todo.append((o, n))
if not todo:
    print('Schon eingebaut.')
    sys.exit(0)
backup = f'{P}.bak-{time.strftime("%Y%m%d-%H%M%S")}'
shutil.copy2(P, backup)
for o, n in todo:
    src = src.replace(o, n, 1)
open(P, 'w', encoding='utf-8').write(src)
try:
    py_compile.compile(P, doraise=True)
except py_compile.PyCompileError as exc:
    shutil.copy2(backup, P)
    sys.exit(f'Fehler, Sicherung wiederhergestellt: {exc}')
print(f'Eingebaut. Sicherung: {backup}')
