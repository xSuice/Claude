#!/usr/bin/env python3
"""Automatisierungen aus einer Quelle: liest server/automations.json und
  list      zeigt alle Automatisierungen (Ort, Zeiten, Skript, ob das Skript existiert)
  validate  prueft die Liste (Pfade im Projekt, Zeitformat, doppelte IDs); Exit 1 bei Fehlern
  cron      gibt die Cron-Zeilen fuer den Server aus (Benutzer andrew), nur fuer Eintraege mit ort=server und Zeiten
Aufruf:  python3 automations.py list|validate|cron [--user andrew] [--skip id1,id2]"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
REG = os.path.join(ROOT, 'server', 'automations.json')
TIME = re.compile(r'([01]\d|2[0-3]):[0-5]\d\Z')
ID = re.compile(r'[a-z0-9][a-z0-9-]{1,40}\Z')


def load():
    with open(REG, encoding='utf-8') as fh:
        return json.load(fh)['automations']


def problems(items):
    out, seen = [], set()
    for a in items:
        i = a.get('id', '?')
        if not ID.fullmatch(str(i)) or i in seen:
            out.append(f'{i}: ID ungueltig oder doppelt')
        seen.add(i)
        sk = str(a.get('skript', ''))
        full = os.path.normpath(os.path.join(ROOT, sk))
        if sk.startswith(('/', '..')) or not full.startswith(ROOT + os.sep) or not os.path.isfile(full):
            out.append(f'{i}: Skript fehlt oder liegt ausserhalb des Projekts ({sk})')
        if set(a.get('ort', [])) - {'pc', 'server'} or not a.get('ort'):
            out.append(f'{i}: ort muss pc und/oder server sein')
        for t in a.get('zeiten') or []:
            if not TIME.fullmatch(str(t)):
                out.append(f'{i}: Uhrzeit {t!r} ungueltig')
        tage = a.get('tage', 'taeglich')
        if tage != 'taeglich' and not (isinstance(tage, list) and tage and all(isinstance(d, int) and 0 <= d <= 6 for d in tage)):
            out.append(f'{i}: tage muss "taeglich" oder eine Liste 0-6 sein')
    return out


def cron_lines(items, user, skip):
    lines = []
    for a in items:
        if 'server' not in a['ort'] or not a.get('zeiten') or a['id'] in skip:
            continue
        tage = '*' if a.get('tage', 'taeglich') == 'taeglich' else ','.join(str((d + 1) % 7) for d in a['tage'])      # cron: 0 = Sonntag
        for t in a['zeiten']:
            h, m = t.split(':')
            lines.append(f"{int(m)} {int(h)} * * {tage} {user} python3 {os.path.join(ROOT, a['skript'])} >> /home/{user}/.{a['id']}.log 2>&1")
    return lines


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'list'
    items = load()
    if cmd == 'validate':
        pr = problems(items)
        print('\n'.join(pr) if pr else f'{len(items)} Automatisierungen gueltig')
        return 1 if pr else 0
    if cmd == 'skripte':                                     # id <Tab> Skriptname fuer Server-Eintraege (fuer die Erkennung vorhandener Crontab-Zeilen)
        for a in items:
            if 'server' in a['ort']:
                print('%s\t%s' % (a['id'], os.path.basename(a['skript'])))
        return 0
    if cmd == 'cron':
        pr = problems(items)
        if pr:
            print('\n'.join(pr), file=sys.stderr)
            return 1
        user = sys.argv[sys.argv.index('--user') + 1] if '--user' in sys.argv else 'andrew'
        skip = set(sys.argv[sys.argv.index('--skip') + 1].split(',')) if '--skip' in sys.argv else set()
        print('\n'.join(cron_lines(items, user, skip)))
        return 0
    for a in items:
        ok = os.path.isfile(os.path.join(ROOT, a['skript']))
        print('%-20s %-7s %-16s %s %s' % (a['id'], '+'.join(a['ort']), ','.join(a.get('zeiten') or []) or (a.get('pc_task') or '-'), a['skript'], '' if ok else '(FEHLT)'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
