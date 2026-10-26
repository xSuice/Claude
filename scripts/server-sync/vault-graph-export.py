#!/usr/bin/env python3
"""Baut aus dem Notizen-Spiegel einen Graphen wie in Obsidian (Notizen + [[Wikilinks]]) fuer die Portal-Seite "Wissen".
Laeuft auf dem Server (Cron, andrew). Ausgabe: /srv/ma-home/library/vault-graph.json"""
import json
import os
import re
import time

BASE = '/srv/ma-home/library/vault-notizen'
OUT = '/srv/ma-home/library/vault-graph.json'
LINK = re.compile(r'(?<!\\)\[\[([^\]|#^]+)(?:[#^][^\]|]*)?(?:\|[^\]]*)?\]\]')
SKIP = ('.obsidian', '.trash')

notes = []
for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for f in files:
        if f.lower().endswith('.md'):
            notes.append(os.path.relpath(os.path.join(root, f), BASE).replace(os.sep, '/'))
notes.sort()
by_path = {n[:-3].lower(): i for i, n in enumerate(notes)}
by_name = {}
for i, n in enumerate(notes):
    by_name.setdefault(os.path.basename(n)[:-3].lower(), i)


def resolve(target):
    t = target.strip().lower()
    if t.endswith('.md'):
        t = t[:-3]
    return by_path.get(t, by_name.get(t.split('/')[-1]))


links = set()
for i, n in enumerate(notes):
    try:
        text = open(os.path.join(BASE, n), encoding='utf-8', errors='replace').read()
    except OSError:
        continue
    for m in LINK.finditer(text):
        j = resolve(m.group(1))
        if j is not None and j != i:
            links.add((min(i, j), max(i, j)))
deg = [0] * len(notes)
for a, b in links:
    deg[a] += 1; deg[b] += 1
nodes = [{'p': n, 'n': os.path.basename(n)[:-3], 'g': n.split('/')[0] if '/' in n else '(Wurzel)', 'd': deg[i]} for i, n in enumerate(notes)]
data = {'stand': time.strftime('%Y-%m-%d %H:%M'), 'basis': 'Bibliothek/vault-notizen', 'nodes': nodes, 'links': sorted(links)}
tmp = OUT + '.tmp'
with open(tmp, 'w', encoding='utf-8') as fh:
    json.dump(data, fh, ensure_ascii=False, separators=(',', ':'))
os.chmod(tmp, 0o664)
os.replace(tmp, OUT)
print(len(nodes), 'Notizen,', len(links), 'Verbindungen')
