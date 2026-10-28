"""/api/jarvis/health – Dienstestatus aus dem lokalen Uptime-Kuma (127.0.0.1:3001/metrics, Prometheus-Text).
Admin only. Nur Name, Zustand, Antwortzeit – keine URLs, Hosts oder Fehlertexte (koennen interne Details enthalten)."""
import re, time, urllib.request
from flask import Blueprint, abort, g, jsonify

health_bp = Blueprint('jarvis_health', __name__)
METRICS = 'http://127.0.0.1:3001/metrics'
STATES = {'0': 'down', '1': 'up', '2': 'pending', '3': 'maintenance'}
LINE = re.compile(r'^(monitor_status|monitor_response_time)\{(.*)\}\s+(-?[0-9.eE+]+)\s*$')
NAME = re.compile(r'monitor_name="((?:[^"\\]|\\.)*)"')


def parse(text):
    mons = {}
    for line in text.splitlines():
        m = LINE.match(line)
        if not m:
            continue
        n = NAME.search(m.group(2))
        if not n:
            continue
        name = n.group(1).replace('\\"', '"')[:80]
        item = mons.setdefault(name, {'name': name, 'status': 'unknown', 'ms': None})
        if m.group(1) == 'monitor_status':
            item['status'] = STATES.get(m.group(3).split('.')[0], 'unknown')
        else:
            v = float(m.group(3))
            item['ms'] = round(v) if v >= 0 else None
    return sorted(mons.values(), key=lambda x: (x['status'] == 'up', x['name']))


@health_bp.route('/api/jarvis/health', methods=['GET'])
def jarvis_health():
    if not getattr(g, 'admin', False):
        abort(403)
    try:
        with urllib.request.urlopen(METRICS, timeout=4) as r:
            text = r.read(512 * 1024).decode('utf-8', 'replace')
    except (OSError, ValueError):
        return jsonify(ok=False, error='Statusmonitor (Uptime Kuma) nicht erreichbar', monitors=[], ts=int(time.time()))
    mons = parse(text)
    return jsonify(ok=True, source='Uptime Kuma', monitors=mons, down=sum(m['status'] == 'down' for m in mons), ts=int(time.time()))
