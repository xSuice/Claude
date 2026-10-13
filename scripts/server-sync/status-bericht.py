#!/usr/bin/env python3
"""Statusbericht (Server, ohne Modell, ohne Root): sammelt Zustand, Updates, Version, Neues und Offenes und schreibt
  /srv/ma-home/library/status.json              fuer den Reiter "Neu" im Portal
  <Vault>/_Claude-Memory/Dienste/Status.md      lesbare Fassung (kommt per Abgleich in den Vault)
Quellen: systemctl, apt (nur lesen), /proc, Watchdog-Dateien, CHANGELOG.md und BACKLOG.md im Projekt, Dienste-Notizen im Vault, Jarvis-Zustand.
Aufruf: python3 status-bericht.py [--stdout]     (per Cron ueber server/automations.json, auch auf Abruf)"""
import json
import os
import re
import shutil
import subprocess
import sys
import time

PROJ = '/home/andrew/MA-Server'
LIB = '/srv/ma-home/library'
DIENSTE = LIB + '/vault-notizen/_Claude-Memory/Dienste'
JARVIS = LIB + '/.jarvis'
OUT_JSON, OUT_MD = LIB + '/status.json', DIENSTE + '/Status.md'
SERVICES = ['ma-home-web', 'ma-claude-bridge', 'ma-term-bridge', 'ma-home-agent', 'ma-deploy.path', 'ma-job-notify.path', 'docker', 'ttyd', 'ma-home-terminal']


def run(*cmd, timeout=40):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ''


def read(path, limit=400_000):
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            return fh.read(limit)
    except OSError:
        return ''


def clean(s):
    s = re.sub(r'\[\[([^\]|]+)\|?([^\]]*)\]\]', lambda m: m.group(2) or m.group(1), s)
    return re.sub(r'\s+', ' ', s.replace('**', '').replace('`', '')).strip()


def system():
    up = float(read('/proc/uptime').split()[0] or 0)
    mem = {k: int(v.split()[0]) for k, v in (l.split(':', 1) for l in read('/proc/meminfo').splitlines() if ':' in l)}
    du = shutil.disk_usage('/')
    out = {'uptime_h': round(up / 3600, 1), 'ram_frei_mb': mem.get('MemAvailable', 0) // 1024, 'ram_gesamt_mb': mem.get('MemTotal', 0) // 1024,
           'platte_frei_gb': du.free // 2 ** 30, 'platte_belegt_prozent': du.used * 100 // du.total}
    if os.path.ismount('/mnt/ma-backup'):
        b = shutil.disk_usage('/mnt/ma-backup')
        out['backup_platte_frei_gb'] = b.free // 2 ** 30
    wd = read('/var/lib/ma-watchdog/status.txt').splitlines()
    out['wachhund'] = wd[1] if len(wd) > 1 else '?'
    out['wachhund_stand'] = wd[0].replace('Stand ', '') if wd else '?'
    out['akku'] = (read('/sys/class/power_supply/BAT1/capacity').strip() + ' % ' + read('/sys/class/power_supply/BAT1/status').strip()).strip() if os.path.exists('/sys/class/power_supply/BAT1') else '-'
    return out


def dienste():
    return {s: run('systemctl', 'is-active', s).strip() or '?' for s in SERVICES}


def updates():
    lines = [l for l in run('apt', 'list', '--upgradable').splitlines() if '/' in l]
    names = [l.split('/')[0] for l in lines]
    return {'anzahl': len(names), 'beispiele': names[:8], 'neustart_noetig': os.path.exists('/var/run/reboot-required'),
            'sicherheit': sum(1 for l in lines if 'security' in l)}


def version():
    def ver(p):
        m = re.search(r"VERSION = '([^']+)'", read(p))
        return m.group(1) if m else ''
    laufend, repo = ver('/opt/ma-home/web/sw.js'), ver(PROJ + '/portal-ui/web/sw.js')
    return {'portal_laufend': laufend, 'portal_repo': repo, 'aktuell': bool(laufend) and laufend == repo,
            'bruecke_aktuell': read('/usr/local/lib/ma-claude-bridge.py') == read(PROJ + '/server/claude-bridge/ma-claude-bridge.py')}


def neues(n=6):
    """Die letzten Eintraege aus dem CHANGELOG: Ueberschrift und erste Aufzaehlungszeile."""
    out = []
    for blk in re.split(r'^(?=## )', read(PROJ + '/CHANGELOG.md'), flags=re.M)[-n:][::-1]:
        h = re.match(r'## (.+)', blk)
        b = re.search(r'^- (.+)$', blk, re.M)
        if h:
            out.append({'titel': clean(h.group(1))[:120], 'text': clean(b.group(1))[:220] if b else ''})
    return out


def offen():
    """Offene Aufgaben mit hoher Prioritaet aus dem BACKLOG (nicht als erledigt markiert)."""
    out = []
    for line in read(PROJ + '/BACKLOG.md').splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 5 and re.fullmatch(r'B\d+', cells[0]) and cells[1] == 'Hoch' and 'erledigt' not in cells[-1].lower():
            out.append({'id': cells[0], 'titel': clean(cells[2])[:110], 'status': clean(cells[-1])[:140]})
    return out[:10]


def abschnitt(text, titel):
    m = re.search(r'^## ' + re.escape(titel) + r'.*?\n(.*?)(?=^## |\Z)', text, re.S | re.M)
    return [clean(re.sub(r'^\s*(\d+\.|-|\*)\s+', '', l)) for l in (m.group(1).splitlines() if m else []) if re.match(r'^\s*(\d+\.|-|\*)\s+', l)]


def wichtig():
    fr = read(DIENSTE + '/Fristen-Uebersicht.md')
    mail = read(DIENSTE + '/Mail-Tagesbericht.md')
    neu = re.search(r'^## (\d{4}-\d{2}-\d{2}).*?\n(.*?)(?=^## |\Z)', mail, re.S | re.M)
    mails = []
    if neu:
        w = re.search(r'\*\*Wichtig:\*\*\n(.*?)(?=\n- \*\*|\Z)', neu.group(2), re.S)
        mails = [clean(re.sub(r'^\s*[-*]\s+', '', l))[:200] for l in (w.group(1).splitlines() if w else []) if l.strip().startswith(('-', '*'))][:6]
    geplant = []
    gdir = DIENSTE + '/Geplant'
    if os.path.isdir(gdir):
        for f in sorted(os.listdir(gdir), key=lambda x: os.path.getmtime(os.path.join(gdir, x)), reverse=True)[:8]:
            if f.endswith('.md'):
                geplant.append({'datei': f, 'pfad': '_Claude-Memory/Dienste/Geplant/' + f, 'alter_min': int((time.time() - os.path.getmtime(os.path.join(gdir, f))) / 60)})
    return {'fristen_woche': abschnitt(fr, 'Diese Woche')[:6], 'fristen_bald': abschnitt(fr, 'Bald')[:5], 'mails_bericht': mails,
            'mails_bericht_datum': neu.group(1) if neu else '', 'geplante_ergebnisse': geplant}


def eingang():
    d = LIB + '/inbox'
    try:
        names = [f for f in os.listdir(d) if not f.startswith('.')]
    except OSError:
        names = []
    return {'anzahl': len(names), 'beispiele': sorted(names)[:6]}


def verbrauch():
    try:
        with open(JARVIS + '/usage.json', encoding='utf-8') as fh:
            u = json.load(fh).get(time.strftime('%Y-%m-%d'), {})
    except (OSError, ValueError):
        u = {}
    return {k: {'auftraege': v.get('jobs', 0), 'tokens_rein': v.get('in', 0), 'tokens_raus': v.get('out', 0)} for k, v in u.items()}


def paritaet():
    m = re.search(r'Stand ([\d\- :]+): \*\*(.+?)\*\*', read(DIENSTE + '/Paritaet.md'))
    return {'stand': m.group(1) if m else '', 'ergebnis': m.group(2) if m else 'noch kein Bericht'}


def sammeln():
    ds, up, ver = dienste(), updates(), version()
    probleme = [f'Dienst {s} ist {st}' for s, st in ds.items() if st not in ('active', 'activating') and s not in ('ma-term-bridge', 'ma-deploy.path', 'ma-job-notify.path', 'ma-home-terminal')]
    if up['neustart_noetig']:
        probleme.append('Neustart nötig (Updates)')
    if not ver['aktuell']:
        probleme.append('Portal-Oberfläche auf dem Server ist nicht auf dem Stand des Projekts')
    return {'stand': time.strftime('%Y-%m-%d %H:%M'), 'system': system(), 'dienste': ds, 'updates': up, 'version': ver, 'neues': neues(), 'offen': offen(),
            'wichtig': wichtig(), 'eingang': eingang(), 'verbrauch_heute': verbrauch(), 'paritaet': paritaet(), 'probleme': probleme}


def als_markdown(d):
    s, up, v = d['system'], d['updates'], d['version']
    L = ['---', 'typ: status', 'quelle: status-bericht.py', 'datenklasse: B', '---', '# Statusbericht Server', f"Stand {d['stand']} · [[Übersicht]]", '']
    L += ['## Zusammenfassung', ('- ⚠ ' + '\n- ⚠ '.join(d['probleme'])) if d['probleme'] else '- Alles in Ordnung.', '']
    L += ['## System', f"- Laufzeit {s['uptime_h']} h · RAM frei {s['ram_frei_mb']} von {s['ram_gesamt_mb']} MB · Platte {s['platte_belegt_prozent']} % belegt, {s['platte_frei_gb']} GB frei",
          f"- Wachhund ({s['wachhund_stand']}): {s['wachhund']} · Akku: {s['akku']}", '']
    L += ['## Updates', f"- {up['anzahl']} Pakete aktualisierbar ({up['sicherheit']} Sicherheitsupdates)" + (' · **Neustart nötig**' if up['neustart_noetig'] else ''),
          ('- z. B. ' + ', '.join(up['beispiele'])) if up['beispiele'] else '', '']
    L += ['## Version', f"- Portal laufend {v['portal_laufend'] or '?'}, Projekt {v['portal_repo']} → {'aktuell' if v['aktuell'] else 'NICHT aktuell'}; Brücke {'aktuell' if v['bruecke_aktuell'] else 'NICHT aktuell'}", '']
    L += ['## Dienste', ', '.join(f'{k}: {x}' for k, x in d['dienste'].items()), '']
    L += ['## Neu am System'] + [f"- **{n['titel']}**: {n['text']}" for n in d['neues']] + ['']
    L += ['## Offen (hohe Priorität)'] + [f"- {o['id']} {o['titel']} — {o['status']}" for o in d['offen']] + ['']
    L += ['## Wichtig', '- Fristen diese Woche: ' + ('; '.join(d['wichtig']['fristen_woche']) or '-'), '- Mails (Bericht vom ' + (d['wichtig']['mails_bericht_datum'] or '?') + '): ' + ('; '.join(d['wichtig']['mails_bericht']) or '-'), '']
    L += ['## Eingang', f"- {d['eingang']['anzahl']} Datei(en) im Eingang", '']
    return '\n'.join(x for x in L if x is not None) + '\n'


def main():
    d = sammeln()
    if '--stdout' in sys.argv:
        print(json.dumps(d, ensure_ascii=False, indent=1))
        return 0
    for path, text in ((OUT_JSON, json.dumps(d, ensure_ascii=False)), (OUT_MD, als_markdown(d))):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as fh:
                fh.write(text)
            os.replace(tmp, path)
        except OSError as e:
            print('Schreiben fehlgeschlagen:', path, e)
            return 1
    print('Statusbericht geschrieben:', OUT_JSON, '|', len(d['probleme']), 'Hinweis(e)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
