#!/usr/bin/env python3
"""Fristen-Erinnerung (ohne Modell, Server, per cron 07:30 und 17:30). Liest Fristen-Uebersicht, Kalender-Eintraege und Termine aus dem
Notizen-Spiegel, findet Eintraege mit ISO-Datum (JJJJ-MM-TT) und meldet ueber ntfy: einen Tag vorher und am Tag selbst, je Eintrag einmal.
Ohne ~/.ntfy-token passiert nichts ausser dem Eintrag in ~/.fristen-state.json (der Morgenbrief zeigt Fristen ohnehin).
Aufruf: python3 fristen-erinnerung.py [--dry]"""
import datetime
import json
import os
import re
import sys
import urllib.request

BASE = '/srv/ma-home/library/vault-notizen/_Claude-Memory/Dienste'
QUELLEN = ['Fristen-Uebersicht.md', 'Kalender-Eintraege.md', 'Termine-und-offene-Vorgaenge.md']
TOKEN = os.path.expanduser('~/.ntfy-token')
STATE = os.path.expanduser('~/.fristen-state.json')
DRY = '--dry' in sys.argv
heute = datetime.date.today()
morgen = heute + datetime.timedelta(days=1)
ISO = re.compile(r'\b(20\d\d-\d\d-\d\d)\b')
SKIP = re.compile(r'erledigt|abgeschlossen|bestätigt als', re.I)

try:
    state = json.load(open(STATE, encoding='utf-8'))
except Exception:
    state = {}

treffer = []
for q in QUELLEN:
    try:
        text = open(os.path.join(BASE, q), encoding='utf-8').read()
    except OSError:
        continue
    skip_block = False
    for ln in text.splitlines():
        if ln.startswith('## '):
            skip_block = 'abgeschlossen' in ln.lower() or 'erledigt' in ln.lower()
        if skip_block or SKIP.search(ln):
            continue
        for m in ISO.finditer(ln):
            try:
                d = datetime.date.fromisoformat(m.group(1))
            except ValueError:
                continue
            if d in (heute, morgen):
                titel = re.sub(r'[*_`#]', '', ln).strip(' -0123456789.')[:140]
                treffer.append((d, titel))

neu, gesehen, je_tag = [], set(), {}
for d, t in treffer:                       # Quellen-Reihenfolge = Wichtigkeit; je Tag hoechstens 2 Meldungen
    kern = re.sub(r'\W+', '', t.lower())[:14]
    key = f'{d}|{kern}|{"heute" if d == heute else "morgen"}'
    if kern in gesehen or je_tag.get(d, 0) >= 2 or key in state:
        continue
    gesehen.add(kern); je_tag[d] = je_tag.get(d, 0) + 1
    state[key] = heute.isoformat()
    neu.append(('Heute' if d == heute else 'Morgen') + ': ' + t[:90])

if neu and not DRY:
    json.dump({k: v for k, v in state.items() if v >= (heute - datetime.timedelta(days=30)).isoformat()}, open(STATE, 'w', encoding='utf-8'))
    if os.path.exists(TOKEN):
        try:
            req = urllib.request.Request('https://ntfy.ma-server.duckdns.org/ma-home', data='\n'.join(neu).encode('utf-8'),
                                         headers={'Authorization': 'Bearer ' + open(TOKEN).read().strip(), 'Title': 'Fristen', 'Priority': '4'})
            urllib.request.urlopen(req, timeout=15).read()
        except Exception as e:
            print('ntfy fehlgeschlagen:', e)
print('\n'.join(neu) if neu else 'Keine neuen Fristen fuer heute/morgen.')
