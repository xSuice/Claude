#!/bin/bash
# Auf dem MA-Server:  sudo bash ~/portal-ui/deploy-ui.sh
# Installiert die Oberflaeche samt PWA-Dateien und patcht portal.py (PWA, Claude-Verwaltung; Sicherung portal.py.bak-<Zeit>).
# Sicherung: /opt/ma-home/web.bak-<Zeit>.  Rueckgaengig: sudo rm -rf /opt/ma-home/web && sudo mv /opt/ma-home/web.bak-<Zeit> /opt/ma-home/web
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
SRC="$(cd "$(dirname "$0")" && pwd)/web"
B=/opt/ma-home/web.bak-$(date +%Y%m%d-%H%M%S)
cp -a /opt/ma-home/web "$B"
install -m 640 -o root -g ma-web "$SRC"/index.html "$SRC"/app.js "$SRC"/style.css "$SRC"/sw.js "$SRC"/manifest.webmanifest "$SRC"/icon-192.png "$SRC"/icon-512.png "$SRC"/apple-touch-icon.png /opt/ma-home/web/
# Pruefsummen der installierten Dateien (Zeilenenden egal) fuer scripts/server-sync/paritaet-check.py; /opt/ma-home/web ist nur fuer ma-web lesbar
( cd /opt/ma-home/web && for f in index.html app.js style.css sw.js manifest.webmanifest; do echo "$(tr -d '\r' < "$f" | sha256sum | cut -d' ' -f1)  $f"; done ) > /opt/ma-home/DEPLOYED-UI.sha256
chmod 644 /opt/ma-home/DEPLOYED-UI.sha256
# Portal-Patches (idempotent, Sicherung von portal.py, nur wenn noetig; danach Neustart): PWA-Dateien und Claude-Verwaltung
CHANGED=0
for PATCH in patch-portal-pwa.py patch-portal-claudeops.py; do
  if python3 "$(dirname "$SRC")/$PATCH" | tee /dev/stderr | grep -q "^Eingebaut"; then CHANGED=1; fi
done
if [ "$CHANGED" = 1 ]; then systemctl restart ma-home-web; sleep 2; fi
ls -l /opt/ma-home/web
echo "Sicherung: $B"
curl -s -o /dev/null -w "Portal intern: HTTP %{http_code}\n" http://127.0.0.1:18765/healthz
echo "Fertig. Seite im Browser neu laden (Strg+F5)."
