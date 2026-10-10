#!/bin/bash
# Auf dem Server:  sudo bash ~/portal-ui/alles-installieren.sh
# Installiert Claude-Bruecke + Portal-Anbindung und die neue Oberflaeche in einem Schritt.
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
bash /home/andrew/claude-bridge/install.sh
bash /home/andrew/portal-ui/deploy-ui.sh
echo "== Alles installiert. Jetzt noch einmal Claude anmelden: ssh -t ma-server '~/.local/bin/claude' =="
