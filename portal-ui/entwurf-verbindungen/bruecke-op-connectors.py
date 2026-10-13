# ENTWURF, nicht eingebaut. Ziel: server/claude-bridge/ma-claude-bridge.py
# 1) Funktion vor "class Handler" einfuegen, 2) Zweig in Handler.op nach "if op == 'usage':" einhaengen.
# Quelle der Daten: `claude mcp list` (am 2026-10-13 getestet: Zeilen "claude.ai NAME: URL - ✔ Connected" bzw. "- ! Needs authentication").
# Nur lesen, startet nichts ausser dem Gesundheitscheck von claude. Ergebnis 60 s im Speicher, damit Reiter-Wechsel nicht jedes Mal prueft.

CONN_CACHE = {'t': 0.0, 'data': None}
CONN_LINE = re.compile(r'^(?P<name>.+?): (?P<url>\S+) - (?P<mark>\S+) (?P<state>.+)$')


def connectors_status():
    """Verbindungen mit Status fuer den Portal-Reiter. Rueckgabe: {'ok': bool, 'items': [{name, url, state}], 'error': str}."""
    now = time.time()
    if CONN_CACHE['data'] and now - CONN_CACHE['t'] < 60:
        return CONN_CACHE['data']
    try:
        out = subprocess.run([CLAUDE, 'mcp', 'list'], capture_output=True, text=True, timeout=60, cwd='/home/andrew', stdin=subprocess.DEVNULL).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        return {'ok': False, 'items': [], 'error': f'claude mcp list fehlgeschlagen: {exc.__class__.__name__}'}
    items = []
    for line in out.splitlines():
        m = CONN_LINE.match(line.strip())
        if not m:
            continue
        state = 'ok' if 'Connected' in m['state'] else 'login' if 'authentication' in m['state'] else 'fehler'
        items.append({'name': m['name'].replace('claude.ai ', '', 1), 'url': m['url'], 'state': state})
    res = {'ok': bool(items), 'items': items, 'error': '' if items else 'Keine Verbindungen gelesen'}
    if items:
        CONN_CACHE.update(t=now, data=res)
    return res


# Zweig in Handler.op (neben 'usage'):
#            if op == 'connectors':
#                return self.reply({'type': 'connectors', **connectors_status()})
