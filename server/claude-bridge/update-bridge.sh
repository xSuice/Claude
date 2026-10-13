#!/bin/bash
# Auf dem MA-Server:  sudo bash ~/MA-Server/server/claude-bridge/update-bridge.sh
# Aktualisiert die Claude-Bruecke (Auto-Modellwahl ueber router_core.py, Bildanhaenge) und das Portal.
# Rueckgaengig: Sicherung /opt/ma-home/portal.py.bak-<Zeit> zurueckkopieren, dann: systemctl restart ma-home-web
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
D="$(cd "$(dirname "$0")" && pwd)"
[ -f /usr/local/lib/ma-claude-bridge.py ] && cp -a /usr/local/lib/ma-claude-bridge.py /usr/local/lib/ma-claude-bridge.py.bak
install -m 755 -o root -g root "$D/ma-claude-bridge.py" /usr/local/lib/ma-claude-bridge.py
install -m 644 -o root -g root "$D/../../scripts/router/router_core.py" /usr/local/lib/router_core.py
python3 "$D/patch-portal-images.py"
python3 "$D/patch-portal-attach.py"
python3 "$D/../musik/patch-portal-audio.py"
# Achtung: ein Neustart der Bruecke beendet laufende Claude-Auftraege. Vorher im Portal pruefen, dass nichts laeuft.
systemctl restart ma-claude-bridge
systemctl restart ma-home-web
sleep 3
systemctl is-active ma-claude-bridge ma-home-web
curl -s -o /dev/null -w "Portal intern: HTTP %{http_code}\n" http://127.0.0.1:18765/healthz
