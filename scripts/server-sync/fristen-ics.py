#!/usr/bin/env python3
"""Fristen als Kalenderdatei (Jarvis, Server, per cron): liest Fristen-Uebersicht, Kalender-Eintraege und Termine aus dem Notizen-Spiegel,
findet Zeilen mit ISO-Datum (JJJJ-MM-TT) und schreibt /srv/ma-home/library/fristen.ics (ganztaegige Termine, von gestern bis in 180 Tagen).
Im Portal als Datei "Bibliothek/fristen.ics" oeffnen oder laden und im Handy-Kalender importieren. Erledigte Eintraege werden uebersprungen.
Aufruf: python3 fristen-ics.py [--stdout]"""
import datetime
import hashlib
import os
import re
import sys

BASE = '/srv/ma-home/library/vault-notizen/_Claude-Memory/Dienste'
QUELLEN = ['Fristen-Uebersicht.md', 'Kalender-Eintraege.md', 'Termine-und-offene-Vorgaenge.md']
OUT = '/srv/ma-home/library/fristen.ics'
ISO = re.compile(r'\b(20\d\d-\d\d-\d\d)\b')
SKIP = re.compile(r'erledigt|abgeschlossen|bestätigt als', re.I)


def esc(s):
    return s.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def fold(line):
    """Zeilen laenger als 75 Bytes werden gefaltet (RFC 5545)."""
    raw, out = line.encode('utf-8'), []
    while len(raw) > 75:
        cut = 75
        while cut > 0 and (raw[cut] & 0xC0) == 0x80:      # nicht mitten in einem UTF-8-Zeichen trennen
            cut -= 1
        out.append(raw[:cut].decode('utf-8'))
        raw = b' ' + raw[cut:]
    out.append(raw.decode('utf-8'))
    return '\r\n'.join(out)


def eintraege(heute):
    seen, res = set(), []
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
                if not heute - datetime.timedelta(days=1) <= d <= heute + datetime.timedelta(days=180):
                    continue
                titel = re.sub(r'\[\[([^\]|]+)\|?([^\]]*)\]\]', lambda x: x.group(2) or x.group(1), ln)
                titel = re.sub(r'[*_`#]', '', titel).replace(m.group(1), '').strip(' -–:|,;0123456789.')[:120].rstrip(' ,;:.') or 'Frist'
                if (d, titel) not in seen:
                    seen.add((d, titel))
                    res.append((d, titel))
    return sorted(res)


def main():
    heute = datetime.date.today()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//MA Home//Fristen//DE', 'CALSCALE:GREGORIAN', 'X-WR-CALNAME:MA Home Fristen']
    for d, titel in eintraege(heute):
        uid = hashlib.sha1(f'{d}|{titel}'.encode('utf-8')).hexdigest()[:20] + '@ma-server'
        lines += ['BEGIN:VEVENT', 'UID:' + uid, 'DTSTAMP:' + stamp, 'DTSTART;VALUE=DATE:' + d.strftime('%Y%m%d'),
                  'DTEND;VALUE=DATE:' + (d + datetime.timedelta(days=1)).strftime('%Y%m%d'), 'SUMMARY:' + esc(titel), 'END:VEVENT']
    lines.append('END:VCALENDAR')
    data = '\r\n'.join(fold(x) for x in lines) + '\r\n'
    if '--stdout' in sys.argv:
        sys.stdout.write(data)
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as fh:
        fh.write(data)
    os.replace(tmp, OUT)
    print('Geschrieben:', OUT, '|', data.count('BEGIN:VEVENT'), 'Termine')
    return 0


if __name__ == '__main__':
    sys.exit(main())
