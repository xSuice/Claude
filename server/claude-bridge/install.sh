#!/bin/bash
# Auf dem MA-Server:  sudo bash ~/claude-bridge/install.sh
# Installiert die Claude-Bruecke (Dienst ma-claude-bridge als andrew, ohne sudo-Rechte) und baut /api/claude ins Portal ein.
# Rueckgaengig: sudo systemctl disable --now ma-claude-bridge; sudo cp /opt/ma-home/portal.py.bak-<Zeit> /opt/ma-home/portal.py; sudo systemctl restart ma-home-web
set -Eeuo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausfuehren."; exit 1; }
D="$(cd "$(dirname "$0")" && pwd)"
install -m 755 -o root -g root "$D/ma-claude-bridge.py" /usr/local/lib/ma-claude-bridge.py
cat > /etc/systemd/system/ma-claude-bridge.service <<'EOF'
[Unit]
Description=MA Home Claude-Bruecke (Portal -> Claude Code)
After=network.target
[Service]
User=andrew
Group=ma-web
RuntimeDirectory=ma-claude
RuntimeDirectoryMode=0750
ExecStart=/usr/bin/python3 /usr/local/lib/ma-claude-bridge.py
Restart=on-failure
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=/home/andrew /srv/ma-home/library
CapabilityBoundingSet=
Environment=HOME=/home/andrew
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now ma-claude-bridge
sleep 2
systemctl is-active ma-claude-bridge
ls -l /run/ma-claude/
python3 "$D/patch-portal.py"
systemctl restart ma-home-web
sleep 3
curl -s -o /dev/null -w "Portal intern: HTTP %{http_code}\n" http://127.0.0.1:18765/healthz
echo "Fertig. Falls Claude noch nicht angemeldet ist: ssh -t ma-server '~/.local/bin/claude'"
