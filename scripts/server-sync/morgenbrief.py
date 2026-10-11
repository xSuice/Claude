#!/usr/bin/env python3
"""Morgenbrief (ohne Modell, laeuft auf dem Server, taeglich 06:55): liest Fristen, Mail-Tagesbericht und Server-Abgleich aus dem
Notizen-Spiegel und schreibt _Claude-Memory/Dienste/Morgenbrief.md (kommt per Abgleich in den Vault).
Optional Push aufs Handy: Datei ~/.ntfy-token (nur Token) anlegen, dann wird an https://ntfy.ma-server.duckdns.org/ma-home gesendet."""
import os
import re
import time
import urllib.request

BASE = '/srv/ma-home/library/vault-notizen/_Claude-Memory/Dienste'
OUT = os.path.join(BASE, 'Morgenbrief.md')
TOKEN = os.path.expanduser('~/.ntfy-token')
TAGE = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']


def read(name):
    try:
        return open(os.path.join(BASE, name), encoding='utf-8').read()
    except OSError:
        return ''


def clean(s):
    s = re.sub(r'\[\[([^\]|]+)\|?([^\]]*)\]\]', lambda m: m.group(2) or m.group(1), s)
    return re.sub(r'\s+', ' ', s.replace('**', '').replace('`', '')).strip()


def short(t, n=130):
    if len(t) <= n:
        return t
    cut = t[:n].rsplit(' ', 1)[0]
    return cut.rstrip(' ,;:.') + ' …'


def section(text, title):
    m = re.search(r'^## ' + re.escape(title) + r'.*?\n(.*?)(?=^## |\Z)', text, re.S | re.M)
    return m.group(1) if m else ''


def items(block, limit):
    out = []
    for line in block.splitlines():
        if re.match(r'^\s*(\d+\.|-|\*)\s+', line):
            out.append(short(clean(re.sub(r'^\s*(\d+\.|-|\*)\s+', '', line))))
    return out[:limit]


now = time.localtime()
fr = read('Fristen-Uebersicht.md')
mail = read('Mail-Tagesbericht.md')
abg = read('Server-Abgleich.md')
lines = [f'## {TAGE[now.tm_wday]}, {time.strftime("%d.%m.%Y", now)}']
woche = items(section(fr, 'Diese Woche'), 4)
bald = items(section(fr, 'Bald'), 4)
neu = re.search(r'^## (\d{4}-\d{2}-\d{2}).*?\n(.*?)(?=^## |\Z)', mail, re.S | re.M)
wichtig = pruefen = None
if neu:
    wichtig = re.search(r'\*\*Wichtig:\*\*\n(.*?)(?=\n- \*\*|\Z)', neu.group(2), re.S)
    pruefen = re.search(r'\*\*Prüfen[^\n]*\n(.*?)(?=\n- \*\*|\Z)', neu.group(2), re.S)
prio = []
for x in woche + (items(wichtig.group(1), 3) if wichtig else []) + bald:
    if x not in prio:
        prio.append(x)
offen = items(pruefen.group(1), 2) if pruefen else []
lines.append('**Top 3 heute:**')
lines += [f'{i}. {x}' for i, x in enumerate(prio[:3], 1)] or ['- keine offenen Prioritäten gefunden']
if prio:
    lines.append(f'**Nächster Schritt:** {prio[0]}')
if offen:
    lines.append('**Fehlende Info / prüfen:**')
    lines += [f'- {x}' for x in offen]
lines.append('**Diese Woche (Stufe 3):**')
lines += [f'- {x}' for x in woche] or ['- nichts Dringendes in der Fristen-Übersicht']
if bald:
    lines.append('**Bald (Stufe 2):**')
    lines += [f'- {x}' for x in bald]
if neu:
    lines.append(f'**Mails (Bericht vom {neu.group(1)}):**')
    for blk in (wichtig, pruefen):
        if blk:
            lines += [f'- {x}' for x in items(blk.group(1), 3)]
a = re.search(r'^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2})\n(.*?)(?=^## |\Z)', abg, re.S | re.M)
if a:
    lines.append(f'**Server (Abgleich {a.group(1)}):**')
    lines += [f'- {short(clean(x[2:]))}' for x in a.group(2).splitlines() if x.startswith('- ')][:3]
try:                                    # Speicher-Fruehwarnung (80 % gelb, 90 % rot), Verursacher aus der Bibliothek
    import shutil
    u = shutil.disk_usage('/')
    pct, frei = u.used * 100 // u.total, u.free // 2 ** 30
    msg = f'{pct} % belegt, {frei} GB frei'
    if pct >= 80:
        big = []
        for d in sorted(os.listdir('/srv/ma-home')):
            p = os.path.join('/srv/ma-home', d)
            try:
                size = sum(os.path.getsize(os.path.join(r, f)) for r, _d, fs in os.walk(p) for f in fs) // 2 ** 30
                big.append((size, d))
            except OSError:
                pass
        msg += ' — größte Bereiche: ' + ', '.join(f'{d} {s} GB' for s, d in sorted(big, reverse=True)[:3])
    lines.append(('**⚠ Speicher knapp:** ' if pct >= 90 else '**Speicher (Warnung):** ' if pct >= 80 else '**Speicher:** ') + msg)
except Exception:
    pass
brief = '\n'.join(lines)
head = '---\ntyp: morgenbrief\nquelle: morgenbrief.py (täglich 06:55, ohne Modell)\ndatenklasse: B\n---\n# Morgenbrief\nÜbergeordnet: [[Fristen-Uebersicht]] · [[Mail-Tagesbericht]] · [[Server-Abgleich]] · [[Index]]\n\n'
old = read('Morgenbrief.md')
old = ('## ' + old.split('\n## ', 1)[1]) if '\n## ' in old else ''
blocks = (brief + '\n\n' + old).split('\n## ')
open(OUT, 'w', encoding='utf-8').write(head + '\n## '.join(blocks[:15]).rstrip() + '\n')
if os.path.exists(TOKEN):
    try:
        req = urllib.request.Request('https://ntfy.ma-server.duckdns.org/ma-home', data=brief.replace('## ', '').encode('utf-8'),
                                     headers={'Authorization': 'Bearer ' + open(TOKEN).read().strip(), 'Title': 'Morgenbrief'})
        urllib.request.urlopen(req, timeout=15)
    except Exception as exc:
        print('Push fehlgeschlagen:', type(exc).__name__)
print(brief)
