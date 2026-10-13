#!/usr/bin/python3
"""Baut die Route /api/deploy/switch (nur Admin) in /opt/ma-home/portal.py ein: der Admin-Schalter "Auto-Einspielung erlauben".
Der Schalter ist die Datei /srv/ma-home/deploy-schalter/erlaubt. Der Ordner gehoert root:ma-web (0775): nur das Portal (ma-web) und root
koennen die Datei anlegen oder loeschen, andrew (und damit Claude) nicht. ma-deploy.sh spielt nur ein, wenn die Datei existiert.
Idempotent (Marker MA-DEPLOY-SWITCH), mit Sicherung und Syntaxpruefung. Als root ausfuehren (macht server/auto-deploy/schalter-einrichten.sh)."""
import py_compile
import shutil
import sys
import time

P = sys.argv[1] if len(sys.argv) > 1 else '/opt/ma-home/portal.py'
MARK = '# --- MA-DEPLOY-SWITCH ---'
ANCHOR = '# --- MA-AUDIO ---'
BLOCK = MARK + '''
DEPLOY_SWITCH = '/srv/ma-home/deploy-schalter/erlaubt'


def _deploy_switch_on():
    return os.path.isfile(DEPLOY_SWITCH) and not os.path.islink(DEPLOY_SWITCH)


@app.route('/api/deploy/switch', methods=['GET', 'POST'])
def deploy_switch():
    """Admin-Schalter: darf die Auto-Einspielung (ma-deploy) Anforderungen ausfuehren? GET liest, POST {"on": true|false} setzt."""
    if not g.admin:
        abort(403)
    if request.method == 'POST':
        on = bool((request.get_json(silent=True) or {}).get('on'))
        try:
            if on:
                with open(DEPLOY_SWITCH, 'a'):
                    pass
            elif os.path.lexists(DEPLOY_SWITCH):
                os.remove(DEPLOY_SWITCH)
        except OSError:
            return jsonify(ok=False, error='Schalter nicht beschreibbar (Ordner /srv/ma-home/deploy-schalter pruefen)'), 500
    return jsonify(ok=True, on=_deploy_switch_on())


# --- MA-DEPLOY-SWITCH-ENDE ---


'''
src = open(P, encoding='utf-8').read()
if MARK in src:
    print('Schon eingebaut.')
    sys.exit(0)
if src.count(ANCHOR) != 1:
    print('Stelle nicht gefunden (', ANCHOR, '), nichts geaendert.')
    sys.exit(1)
backup = f'{P}.bak-{time.strftime("%Y%m%d-%H%M%S")}'
shutil.copy2(P, backup)
open(P, 'w', encoding='utf-8', newline='\n').write(src.replace(ANCHOR, BLOCK + ANCHOR, 1))
try:
    py_compile.compile(P, doraise=True)
except Exception as exc:
    shutil.copy2(backup, P)
    print('Pruefung fehlgeschlagen, zurueckgesetzt:', exc)
    sys.exit(1)
print('Eingebaut. Sicherung:', backup)
