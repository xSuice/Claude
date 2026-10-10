#!/bin/bash
# Auf dem Server:  sudo bash ~/fix-ma-home-rechte.sh
# Stellt /etc/ma-home auf 750 root:ma-web zurueck (das Portal laeuft als ma-web und liest dort portal.json).
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
chgrp ma-web /etc/ma-home
chmod 750 /etc/ma-home
stat -c "%A %U:%G %n" /etc/ma-home
sleep 1
curl -s -o /dev/null -w "Portal intern: HTTP %{http_code}\n" http://127.0.0.1:18765/healthz
sudo -u ma-web test -r /etc/ma-home/portal.json && echo "ma-web kann portal.json lesen" || echo "WARNUNG: ma-web kann portal.json nicht lesen (Datei-Rechte pruefen)"
ls -l /etc/ma-home/portal.json
