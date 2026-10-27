#!/usr/bin/env python3
"""Produktiv-Umschaltung (M4, 2026-10-27): neue Shell auf '/', klassisches Portal unter '/classic/'.
Idempotent. Sichert web/ und portal.py, legt Rollback-Skript an. KEIN Neustart (separat)."""
import os, pathlib, py_compile, shutil, stat, sys

PP = pathlib.Path("/opt/ma-home/portal.py")
WEB = pathlib.Path("/opt/ma-home/web")
TAG = "bak-vor-cutover-20261027"
BAK_PP = pathlib.Path(str(PP) + "." + TAG)
BAK_WEB = pathlib.Path("/opt/ma-home/web." + TAG)
ROLL = pathlib.Path("/opt/ma-home/rollback-cutover.sh")

if not (WEB / "staging" / "index.html").exists():
    sys.exit("ABBRUCH: neue Shell fehlt (web/staging/index.html)")
idx = (WEB / "staging" / "index.html").read_text()
if '<base href="/staging/">' not in idx:
    sys.exit("ABBRUCH: base-Tag fehlt in staging/index.html")

src = PP.read_text()
OLD = "@app.get('/')\ndef index():\n    return send_from_directory(STATIC, 'index.html')\n"
NEW = ("@app.get('/')\ndef index():   # M4-Cutover 2026-10-27: neue Shell (base href=/staging/); klassisch unter /classic/\n"
       "    return send_from_directory(STATIC / 'staging', 'index.html')\n\n\n"
       "@app.get('/classic')\n@app.get('/classic/')\ndef classic_index():\n    return send_from_directory(STATIC, 'index.html')\n")

if "def classic_index" in src:
    print("portal.py: bereits umgestellt")
else:
    assert src.count(OLD) == 1, "Anker nicht eindeutig/ nicht gefunden"
    if not BAK_PP.exists():
        shutil.copy2(PP, BAK_PP)
    if not BAK_WEB.exists():
        shutil.copytree(WEB, BAK_WEB, symlinks=True)
    tmp = PP.with_suffix(".py.new")
    tmp.write_text(src.replace(OLD, NEW))
    py_compile.compile(str(tmp), doraise=True)
    os.chmod(tmp, 0o644)
    os.replace(tmp, PP)
    print("portal.py: umgestellt + kompiliert; Backups:", BAK_PP.name, BAK_WEB.name)

ROLL.write_text("""#!/bin/bash
# Rollback der Produktiv-Umschaltung vom 2026-10-27: klassisches Portal wieder auf '/'.
set -e
[ -f %(bak)s ] || { echo "Backup fehlt: %(bak)s"; exit 1; }
cp -p %(bak)s %(pp)s
python3 -m py_compile %(pp)s
systemctl restart ma-home-web
sleep 2
systemctl is-active ma-home-web
echo "Rollback fertig: '/' zeigt wieder das klassische Portal (web/ unveraendert; Staging unter /staging/ bleibt)."
""" % {"bak": str(BAK_PP), "pp": str(PP)})
os.chmod(ROLL, 0o755)
print("Rollback-Skript:", ROLL)
