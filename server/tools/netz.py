#!/usr/bin/env python3
"""Netz- und Geraete-Werkzeug fuer Claude auf dem MA-Server (nur Standardbibliothek, kein sudo, kein Scan fremder Geraete).

Alles laeuft ueber eine Zulassungsliste (Allowlist) in ~/.ma-netz.json (chmod 600, nicht im Git). Was dort nicht steht, wird nicht angefasst.
Stufen je Geraet: 1 nur lesen, 2 steuern (reversibel: Home-Assistant-Schalter ein/aus), 3 aendern (nur mit Bestaetigung von Philipp,
das Werkzeug verweigert und nennt, was Philipp selbst tun muss).

Aufruf:
  netz.py liste                      Geraete aus der Zulassungsliste
  netz.py status [name]              Erreichbarkeit (Ping und optional TCP-Port); ohne Name alle Geraete
  netz.py nachbarn                   passiv: bekannte Nachbarn aus der ARP-Tabelle (kein Scan)
  netz.py dienste                    lokale Server-Dienste (Ports), nur lesen
  netz.py ha-zustand [entity]        Home Assistant: Zustand lesen (nur Entities aus der Liste)
  netz.py ha-schalten entity an|aus  Home Assistant: Schalter (nur Stufe 2, nur Entities aus der Liste)
Konfiguration (Beispiel):
  {"geraete": {"drucker": {"host": "192.168.0.50", "port": 631, "stufe": 1, "info": "Flur"}},
   "ha": {"url": "http://127.0.0.1:8123", "token_datei": "~/.ma-ha-token",
          "entities": {"switch.steckdose_flur": {"stufe": 2, "info": "Flurlicht"}, "sensor.temperatur": {"stufe": 1}}}}
Exit-Code 0 = ok, 1 = Fehler oder verweigert."""
import json
import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request

CONFIG = os.environ.get('MA_NETZ_CONFIG', os.path.expanduser('~/.ma-netz.json'))
HOST_RE = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$|^[A-Za-z0-9][A-Za-z0-9.-]{0,60}$')
ENTITY_RE = re.compile(r'^[a-z_]+\.[a-z0-9_]+$')


def load():
    try:
        return json.load(open(CONFIG, encoding='utf-8'))
    except FileNotFoundError:
        return {}
    except ValueError as exc:
        raise SystemExit(f'Konfiguration {CONFIG} ist kein gueltiges JSON: {exc}')


def ping(host):
    if not HOST_RE.fullmatch(host or ''):
        return False
    r = subprocess.run(['ping', '-c', '1', '-W', '1', host], capture_output=True, timeout=5)
    return r.returncode == 0


def tcp(host, port):
    try:
        with socket.create_connection((host, int(port)), timeout=1.5):
            return True
    except (OSError, ValueError):
        return False


def cmd_liste(cfg):
    geraete = cfg.get('geraete', {})
    for name, g in sorted(geraete.items()):
        print(f"{name}: {g.get('host')}" + (f":{g['port']}" if g.get('port') else '') + f" Stufe {g.get('stufe', 1)} {g.get('info', '')}".rstrip())
    ents = cfg.get('ha', {}).get('entities', {})
    for e, v in sorted(ents.items()):
        print(f"ha {e}: Stufe {v.get('stufe', 1)} {v.get('info', '')}".rstrip())
    if not geraete and not ents:
        print(f'Keine Geraete freigegeben. Zulassungsliste anlegen: {CONFIG} (chmod 600), Aufbau siehe Kopf von netz.py.')
    return 0


def cmd_status(cfg, name=None):
    geraete = cfg.get('geraete', {})
    if name and name not in geraete:
        print(f'{name}: nicht in der Zulassungsliste.')
        return 1
    ok = True
    for n in ([name] if name else sorted(geraete)):
        g = geraete[n]
        up = ping(g.get('host', ''))
        line = f"{n}: {'erreichbar' if up else 'NICHT erreichbar'}"
        if g.get('port'):
            line += f", Port {g['port']} {'offen' if tcp(g.get('host', ''), g['port']) else 'zu'}"
        print(line)
        ok = ok and up
    if not geraete:
        print('Keine Geraete freigegeben.')
    return 0 if ok else 1


def cmd_nachbarn():
    r = subprocess.run(['ip', '-4', 'neigh'], capture_output=True, text=True, timeout=5)
    for line in r.stdout.splitlines():
        p = line.split()
        if len(p) >= 4 and p[0].count('.') == 3:
            print(p[0], p[-1])         # nur Adresse und Zustand, keine MAC-Adresse (Klasse B/C)
    return 0


def cmd_dienste():
    r = subprocess.run(['ss', '-tlnH'], capture_output=True, text=True, timeout=5)
    for line in r.stdout.splitlines():
        p = line.split()
        if len(p) >= 4:
            print(p[3])
    return 0


def ha_call(cfg, method, path, body=None):
    ha = cfg.get('ha') or {}
    url, tf = ha.get('url'), os.path.expanduser(ha.get('token_datei', '~/.ma-ha-token'))
    if not url:
        raise SystemExit('Home Assistant ist nicht konfiguriert ("ha" in der Zulassungsliste fehlt).')
    try:
        token = open(tf, encoding='utf-8').read().strip()
    except OSError:
        raise SystemExit(f'Kein Home-Assistant-Token in {tf} (Philipp legt es selbst an, chmod 600).')
    req = urllib.request.Request(url.rstrip('/') + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode() or 'null')
    except urllib.error.HTTPError as exc:
        raise SystemExit(f'Home Assistant antwortet mit {exc.code}')
    except (urllib.error.URLError, OSError) as exc:
        raise SystemExit(f'Home Assistant nicht erreichbar: {exc}')


def entity(cfg, eid):
    ents = (cfg.get('ha') or {}).get('entities', {})
    if not ENTITY_RE.fullmatch(eid or '') or eid not in ents:
        print(f'{eid}: nicht in der Zulassungsliste.')
        return None
    return ents[eid]


def cmd_ha_zustand(cfg, eid=None):
    ents = (cfg.get('ha') or {}).get('entities', {})
    for e in ([eid] if eid else sorted(ents)):
        if entity(cfg, e) is None:
            return 1
        st = ha_call(cfg, 'GET', '/api/states/' + e)
        print(f"{e}: {st.get('state')}")
    return 0


def cmd_ha_schalten(cfg, eid, wert):
    ent = entity(cfg, eid)
    if ent is None:
        return 1
    stufe = int(ent.get('stufe', 1))
    if stufe >= 3:
        print(f'{eid}: Stufe 3 (aendern). Das braucht die Bestaetigung von Philipp, bitte als Anweisung an ihn formulieren.')
        return 1
    if stufe < 2:
        print(f'{eid}: nur Stufe 1 (nur lesen), Schalten ist nicht freigegeben.')
        return 1
    if eid.split('.')[0] not in ('switch', 'light', 'input_boolean') or wert not in ('an', 'aus'):
        print('Nur switch, light und input_boolean mit an oder aus.')
        return 1
    dom = eid.split('.')[0]
    ha_call(cfg, 'POST', f"/api/services/{dom}/turn_{'on' if wert == 'an' else 'off'}", {'entity_id': eid})
    now = ha_call(cfg, 'GET', '/api/states/' + eid)
    print(f"{eid}: jetzt {now.get('state')} (rueckgaengig: ha-schalten {eid} {'aus' if wert == 'an' else 'an'})")
    return 0


def main(argv):
    if not argv or argv[0] in ('-h', '--help', 'hilfe'):
        print(__doc__)
        return 0
    cfg, cmd, args = load(), argv[0], argv[1:]
    if cmd == 'liste':
        return cmd_liste(cfg)
    if cmd == 'status':
        return cmd_status(cfg, args[0] if args else None)
    if cmd == 'nachbarn':
        return cmd_nachbarn()
    if cmd == 'dienste':
        return cmd_dienste()
    if cmd == 'ha-zustand':
        return cmd_ha_zustand(cfg, args[0] if args else None)
    if cmd == 'ha-schalten' and len(args) == 2:
        return cmd_ha_schalten(cfg, args[0], args[1])
    print('Unbekannter Befehl. netz.py hilfe zeigt alle.')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
