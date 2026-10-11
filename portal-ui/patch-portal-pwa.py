#!/usr/bin/python3
"""Erlaubt dem Portal die PWA-Dateien (sw.js im Wurzelpfad, Manifest, Icons). Idempotent, mit Sicherung und Pruefung.
Als root ausfuehren: python3 patch-portal-pwa.py [/opt/ma-home/portal.py]. Aufgerufen von deploy-ui.sh.
Gehoert zu: portal-ui/web/sw.js, manifest.webmanifest, make-icons.py (Vault: Server-Claude Variante 2)."""
import py_compile
import shutil
import sys
import time

P = sys.argv[1] if len(sys.argv) > 1 else '/opt/ma-home/portal.py'
OLD = "    if name not in ('app.js', 'style.css'):\n        abort(404)\n    return send_from_directory(STATIC, name)\n"
NEW = ("    if name not in ('app.js', 'style.css', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png'):\n"
       "        abort(404)\n    return send_from_directory(STATIC, name)\n\n\n"
       "@app.get('/sw.js')   # --- MA-PWA ---\n"
       "def service_worker():\n"
       "    response = send_from_directory(STATIC, 'sw.js', mimetype='application/javascript')\n"
       "    response.headers['Service-Worker-Allowed'] = '/'\n"
       "    return response\n")
src = open(P, encoding='utf-8').read()
if '--- MA-PWA ---' in src:
    print('Schon eingebaut.')
    sys.exit(0)
if OLD not in src:
    print('Stelle nicht gefunden, nichts geaendert.')
    sys.exit(1)
backup = f'{P}.bak-{time.strftime("%Y%m%d-%H%M%S")}'
shutil.copy2(P, backup)
open(P, 'w', encoding='utf-8').write(src.replace(OLD, NEW, 1))
try:
    py_compile.compile(P, doraise=True)
except Exception as exc:
    shutil.copy2(backup, P)
    print('Pruefung fehlgeschlagen, zurueckgesetzt:', exc)
    sys.exit(1)
print('Eingebaut. Sicherung:', backup)
