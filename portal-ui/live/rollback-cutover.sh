#!/bin/bash
# Rollback der Produktiv-Umschaltung vom 2026-10-27: klassisches Portal wieder auf '/'.
set -e
[ -f /opt/ma-home/portal.py.bak-vor-cutover-20261027 ] || { echo "Backup fehlt: /opt/ma-home/portal.py.bak-vor-cutover-20261027"; exit 1; }
cp -p /opt/ma-home/portal.py.bak-vor-cutover-20261027 /opt/ma-home/portal.py
python3 -m py_compile /opt/ma-home/portal.py
systemctl restart ma-home-web
sleep 2
systemctl is-active ma-home-web
echo "Rollback fertig: '/' zeigt wieder das klassische Portal (web/ unveraendert; Staging unter /staging/ bleibt)."
