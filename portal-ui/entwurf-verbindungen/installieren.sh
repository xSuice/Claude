#!/bin/bash
# Auf dem MA-Server:  sudo bash ~/MA-Server/portal-ui/entwurf-verbindungen/installieren.sh
# Baut den Portal-Reiter "Verbindungen" ein: Op "connectors" in der Claude-Bruecke, Ansicht in app.js, Freischaltung in portal.py.
# Nutzt die vorhandenen Skripte (update-bridge.sh, deploy-ui.sh) und danach patch-portal-connectors.py (haengt nur 'connectors' an die Op-Liste an).
# Sicherungen:
#   Bruecke:  /usr/local/lib/ma-claude-bridge.py.bak
#   Portal:   /opt/ma-home/portal.py.bak-<Zeit>
#   Web:      /opt/ma-home/web.bak-<Zeit>
# ACHTUNG: update-bridge.sh startet die Bruecke neu und beendet laufende Claude-Auftraege (auch den Portal-Chat). Vorher pruefen, dass nichts laeuft.
# Rueckgaengig: Bruecke  sudo cp -a /usr/local/lib/ma-claude-bridge.py.bak /usr/local/lib/ma-claude-bridge.py && sudo systemctl restart ma-claude-bridge
#               Web      sudo rm -rf /opt/ma-home/web && sudo mv /opt/ma-home/web.bak-<Zeit> /opt/ma-home/web
#               Portal   sudo cp -a /opt/ma-home/portal.py.bak-<Zeit> /opt/ma-home/portal.py && sudo systemctl restart ma-home-web
# Alte Quellstaende (vor der Aenderung): ~/MA-Server/portal-ui/entwurf-verbindungen/*.vor-verbindungen
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
BASE="$(cd "$(dirname "$0")/../.." && pwd)"
python3 -I -m py_compile "$BASE/server/claude-bridge/ma-claude-bridge.py" "$BASE/portal-ui/patch-portal-claudeops.py" "$BASE/portal-ui/patch-portal-connectors.py"
echo "Pruefung der Quellen ok."
bash "$BASE/server/claude-bridge/update-bridge.sh"
bash "$BASE/portal-ui/deploy-ui.sh"
if python3 -I "$BASE/portal-ui/patch-portal-connectors.py" | tee /dev/stderr | grep -q "^Eingebaut"; then
  systemctl restart ma-home-web; sleep 2
fi
systemctl is-active ma-claude-bridge ma-home-web
curl -s -o /dev/null -w "Portal intern: HTTP %{http_code}\n" http://127.0.0.1:18765/healthz
echo "Fertig. Portal im Browser neu laden (Strg+F5), Reiter 'Verbindungen' oeffnen."
