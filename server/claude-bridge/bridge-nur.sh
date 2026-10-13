#!/usr/bin/env bash
# Nur die Claude-Bruecke installieren (ohne Router und Portal-Patches wie update-bridge.sh) und den Neustart verzoegert einplanen.
# Start ueber die Sudo-Bruecke: bash ~/MA-Server/server/claude-bridge/../auto-deploy/sudo-anfordern.sh ~/MA-Server/server/claude-bridge/bridge-nur.sh
# Der Neustart beendet laufende Claude-Auftraege (auch den Chat, der dieses Skript angefordert hat): deshalb 60 s Verzoegerung (BRIDGE_DELAY aenderbar).
# Rueckgaengig: sudo cp /usr/local/lib/ma-claude-bridge.py.bak /usr/local/lib/ma-claude-bridge.py && sudo systemctl restart ma-claude-bridge
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
SRC=/home/andrew/MA-Server/server/claude-bridge/ma-claude-bridge.py
python3 -I -m py_compile "$SRC"
[ -f /usr/local/lib/ma-claude-bridge.py ] && cp -a /usr/local/lib/ma-claude-bridge.py /usr/local/lib/ma-claude-bridge.py.bak
install -m 755 -o root -g root "$SRC" /usr/local/lib/ma-claude-bridge.py
sha256sum "$SRC" /usr/local/lib/ma-claude-bridge.py
D="${BRIDGE_DELAY:-60}"
systemd-run --on-active="${D}s" --unit=ma-bridge-neustart systemctl restart ma-claude-bridge
echo "Installiert. Neustart der Bruecke in ${D} s (Einheit ma-bridge-neustart)."
