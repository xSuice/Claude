#!/usr/bin/python3
"""Baut die Route /api/deploy/sudo-switch (nur Admin) in /opt/ma-home/portal.py ein: der Admin-Schalter "Sudo-Skripte erlauben (Root)".
Der Schalter ist die Datei /srv/ma-home/deploy-schalter/sudo-erlaubt (gleicher Ordner wie der Schalter der Auto-Einspielung, root:ma-web 0775).
ma-sudo-run.sh fuehrt Skripte von andrew nur aus, wenn die Datei existiert. Setzt voraus, dass patch-portal-deployswitch.py schon lief.
Idempotent (Marker MA-SUDO-SWITCH), mit Sicherung und Syntaxpruefung. Als root ausfuehren (macht server/auto-deploy/sudo-einrichten.sh)."""
import py_compile
import shutil
import sys
import time

P = sys.argv[1] if len(sys.argv) > 1 else '/opt/ma-home/portal.py'
MARK = '# --- MA-SUDO-SWITCH ---'
ANCHOR = '# --- MA-DEPLOY-SWITCH-ENDE ---'
BLOCK = '''
''' + MARK + '''
SUDO_SWITCH = '/srv/ma-home/deploy-schalter/sudo-erlaubt'


def _sudo_switch_on():
    return os.path.isfile(SUDO_SWITCH) and not os.path.islink(SUDO_SWITCH)


@app.route('/api/deploy/sudo-switch', methods=['GET', 'POST'])
def sudo_switch():
    """Admin-Schalter: darf ma-sudo Skripte von Claude als root ausfuehren? GET liest, POST {"on": true|false} setzt."""
    if not g.admin:
        abort(403)
    if request.method == 'POST':
        on = bool((request.get_json(silent=True) or {}).get('on'))
        try:
            if on:
                with open(SUDO_SWITCH, 'a'):
                    pass
            elif os.path.lexists(SUDO_SWITCH):
                os.remove(SUDO_SWITCH)
        except OSError:
            return jsonify(ok=False, error='Schalter nicht beschreibbar (Ordner /srv/ma-home/deploy-schalter pruefen)'), 500
    return jsonify(ok=True, on=_sudo_switch_on())


# --- MA-SUDO-SWITCH-ENDE ---
'''
src = open(P, encoding='utf-8').read()
if MARK in src:
    print('Schon eingebaut.')
    sys.exit(0)
if src.count(ANCHOR) != 1:
    print('Stelle nicht gefunden (', ANCHOR, '), nichts geaendert. Zuerst schalter-einrichten.sh ausfuehren.')
    sys.exit(1)
backup = f'{P}.bak-{time.strftime("%Y%m%d-%H%M%S")}'
shutil.copy2(P, backup)
open(P, 'w', encoding='utf-8', newline='\n').write(src.replace(ANCHOR, ANCHOR + '\n' + BLOCK, 1))
try:
    py_compile.compile(P, doraise=True)
except Exception as exc:
    shutil.copy2(backup, P)
    print('Pruefung fehlgeschlagen, zurueckgesetzt:', exc)
    sys.exit(1)
print('Eingebaut. Sicherung:', backup)
